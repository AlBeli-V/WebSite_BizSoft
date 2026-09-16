/**
 * Доступ к разделу «Комплаенс → Согласия и рассылки».
 *
 * Два фактора и две роли (решение руководителя 16.09.2026):
 *
 *  • первый фактор — токен роли из окружения. Их два, и они разные:
 *    COMPLIANCE_ADMIN_TOKEN открывает журнал и реестр, COMPLIANCE_OWNER_TOKEN
 *    добавляет к этому IP-адреса, user-agent и выгрузки;
 *  • второй фактор — шестизначный код из приложения-аутентификатора
 *    (COMPLIANCE_TOTP_SECRET). Один утёкший токен не открывает журнал ПДн:
 *    это худший из возможных объектов для единственного фактора.
 *
 * Почему роли привязаны к токенам, а не к учётным записям. Сайт ходит в
 * Directus сервисным токеном и пользовательских сессий не умеет — заводить
 * их ради двух человек значит строить слой логина, обновления токенов и
 * cookie. Смена сотрудника здесь решается сменой токена в окружении; это
 * записано в шагах эксплуатации и проверяется при ротации секретов.
 *
 * Каждое обращение к данным раздела пишется в admin_audit_log — кто, когда,
 * что смотрел и что выгрузил (HELP администратора, п. 7).
 */
import { timingSafeEqual } from 'node:crypto';
import { isValidBase32, verifyTotp } from './totp';
import { createAdminAuditEntry } from './directus';
import { clientIp } from './client-ip';

export type ComplianceRole = 'compliance_admin' | 'owner';

const envValue = (name: string): string =>
  String(process.env[name] || (import.meta.env as Record<string, string>)[name] || '').trim();

function tokens(): { admin: string; owner: string } {
  return { admin: envValue('COMPLIANCE_ADMIN_TOKEN'), owner: envValue('COMPLIANCE_OWNER_TOKEN') };
}

function totpSecret(): string {
  return envValue('COMPLIANCE_TOTP_SECRET');
}

/**
 * Настроен ли контур. Токен короче 16 символов и негодный секрет второго
 * фактора считаются «не настроено»: раздел в этом случае не открывается
 * вовсе, а не открывается без защиты.
 *
 * Формат секрета проверяется здесь, а не только длина. Ключ с посторонним
 * символом не даст сойтись ни одному коду, и без этой проверки раздел
 * выглядел бы настроенным, а на деле в него нельзя было бы войти —
 * с сообщением «неверный код», которое уводит не туда.
 */
export function isComplianceConfigured(): boolean {
  const t = tokens();
  const secret = totpSecret();
  return (t.admin.length >= 16 || t.owner.length >= 16)
    && secret.length >= 16
    && isValidBase32(secret);
}

function equals(a: string, b: string): boolean {
  if (!a || !b || a.length !== b.length) return false;
  return timingSafeEqual(Buffer.from(a), Buffer.from(b));
}

export interface ComplianceSession {
  role: ComplianceRole;
  /** Имя оператора из формы — попадает в admin_audit_log. */
  actor: string;
  ip: string;
}

export type ComplianceAuth =
  | { ok: true; session: ComplianceSession }
  | { ok: false; status: number; error: string };

/**
 * Разобрать и проверить заголовки доступа.
 *
 * Ожидаются `x-compliance-token`, `x-compliance-otp` и `x-compliance-actor`.
 * Имя оператора обязательно: запись в журнале действий без ответа на вопрос
 * «кто» бесполезна.
 */
export function authorizeCompliance(request: Request): ComplianceAuth {
  if (!isComplianceConfigured()) {
    // Причина называется конкретно: «не настроен» без подробностей заставляет
    // перебирать четыре секрета вслепую.
    const secret = totpSecret();
    const why = secret && !isValidBase32(secret)
      ? 'секрет второго фактора не в формате base32 (допустимы только A–Z и 2–7)'
      : 'нет токенов ролей или секрета второго фактора';
    return { ok: false, status: 503, error: `Раздел не настроен: ${why}.` };
  }
  const token = request.headers.get('x-compliance-token') || '';
  const otp = request.headers.get('x-compliance-otp') || '';
  const actor = (request.headers.get('x-compliance-actor') || '').trim().slice(0, 120);

  const t = tokens();
  let role: ComplianceRole | null = null;
  // Владелец проверяется первым: если оба токена почему-то совпали, больше
  // прав получает тот, кто их и так имеет.
  if (t.owner && equals(token, t.owner)) role = 'owner';
  else if (t.admin && equals(token, t.admin)) role = 'compliance_admin';

  if (!role) return { ok: false, status: 401, error: 'Неверный токен доступа.' };
  if (!verifyTotp(totpSecret(), otp)) return { ok: false, status: 401, error: 'Неверный или просроченный код подтверждения.' };
  if (!actor) return { ok: false, status: 422, error: 'Укажите, кто работает: имя попадает в журнал действий.' };

  return { ok: true, session: { role, actor, ip: clientIp(request) } };
}

/** Видит ли роль технические реквизиты события (IP и user-agent). */
export function canSeeTechnical(role: ComplianceRole): boolean {
  return role === 'owner';
}

/** Может ли роль выгружать данные и менять маркетинговый статус. */
export function canExport(role: ComplianceRole): boolean {
  return role === 'owner';
}

/**
 * Убрать из события то, чего роль видеть не должна.
 *
 * Менеджеру журнал нужен целиком, кроме IP и user-agent: по ним человека
 * отслеживают, а для работы с обращением они не нужны (ТЗ, п. 10).
 */
export function redactForRole<T extends object>(row: T, role: ComplianceRole): T {
  if (canSeeTechnical(role)) return row;
  const out = { ...row } as Record<string, unknown>;
  out.ip_address = null;
  out.user_agent = null;
  return out as T;
}

/**
 * Записать действие администратора.
 *
 * Не бросает исключений: отказ журнала действий не должен закрыть доступ к
 * доказательствам в момент, когда их запросил регулятор. Но и молчать
 * нельзя — сбой уходит в журнал прогона.
 */
export async function auditAdmin(
  session: ComplianceSession,
  action: string,
  target?: string,
  details?: Record<string, unknown>,
): Promise<void> {
  try {
    await createAdminAuditEntry({
      actor: session.actor,
      role: session.role,
      action,
      target: target ? target.slice(0, 200) : null,
      details: details ?? null,
      ip_address: session.ip || null,
    });
  } catch (e) {
    console.error('admin audit write failed', action, e);
  }
}
