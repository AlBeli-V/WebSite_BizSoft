/**
 * Журнал согласий: запись доказательств волеизъявления.
 *
 * Три правила, из которых вытекает вся конструкция.
 *
 * 1. Версия и хэш документа берутся ТОЛЬКО с сервера, из legal-manifest.json
 *    (ТЗ 16.09.2026, п. 8). Всё, что прислал браузер по этим полям,
 *    игнорируется: иначе доказательством стало бы значение, которое может
 *    подставить кто угодно.
 *
 * 2. Одно событие — одно согласие. «Подтвердить всё» в интерфейсе создаёт два
 *    независимых события (PD и MARKETING), а не одно общее: общая запись
 *    «согласен со всем» не разделяет волеизъявления и как доказательство
 *    рекламного согласия не работает (дополнение к ТЗ, п. 7).
 *
 * 3. События пишутся ДО отправки лида в Bitrix24. Портал — зеркало; если
 *    журнал не принял запись, отправлять контакт в CRM нельзя, иначе в
 *    работе окажется заявка, законность обработки которой нечем подтвердить.
 */
import { randomUUID, createHash } from 'node:crypto';
import {
  createConsentEvent,
  type ConsentEventRow,
} from './directus';
import { legalDoc } from './legal';
import {
  CONSENT_DOC,
  type ConsentAction,
  type ConsentSourceAction,
  type ConsentType,
} from '../config/legal';

/** Приведение адреса к ключу реестра: регистр и пробелы значения не имеют. */
export function normalizeEmail(email: string): string {
  return String(email || '').trim().toLowerCase();
}

/**
 * Устойчивый идентификатор субъекта.
 *
 * UUID v5-подобный: детерминированно выводится из адреса, поэтому два
 * обращения одного человека связываются между собой без отдельной таблицы
 * соответствий, а сам адрес из идентификатора не восстанавливается.
 * Пространство имён — константа проекта, менять её нельзя: сменив, мы
 * разорвём связь со всеми ранее записанными событиями.
 */
const SUBJECT_NAMESPACE = 'biz-soft.pro/consent-subject/v1';

export function subjectIdFor(email: string): string {
  const h = createHash('sha256').update(`${SUBJECT_NAMESPACE}:${normalizeEmail(email)}`).digest('hex');
  // Раскладываем хэш в форму UUID: колонка в базе типизирована как uuid.
  // Версия 5 и вариант RFC 4122 проставляются явно, иначе Postgres примет
  // значение, но инструменты будут считать его некорректным UUID.
  const v = `${h.slice(0, 8)}-${h.slice(8, 12)}-5${h.slice(13, 16)}-${
    ((parseInt(h.slice(16, 18), 16) & 0x3f) | 0x80).toString(16).padStart(2, '0')
  }${h.slice(18, 20)}-${h.slice(20, 32)}`;
  return v;
}

/** Технический субъект для аналитических согласий: ПДн там нет. */
export function anonymousSubjectId(sessionId: string): string {
  return subjectIdFor(`session:${sessionId}`);
}

export interface ConsentSubject {
  email?: string;
  phone?: string;
  company?: string;
  /** ФИО одной строкой, как его ввёл человек. Разбирается ниже. */
  name?: string;
}

export interface ConsentEventInput {
  type: ConsentType;
  action: ConsentAction;
  /** Как выражена воля: обычный чекбокс, кнопка «Подтвердить всё», отписка. */
  sourceAction: ConsentSourceAction;
  /** Идентификатор формы или механизма: lead-form, cookie-banner, unsubscribe. */
  source: string;
  formId?: string;
  pageUrl?: string;
  /** Общий для одной отправки формы: связывает PD- и MARKETING-события. */
  requestId: string;
  subject?: ConsentSubject;
  /** Технический субъект, когда персональных данных нет (аналитика). */
  subjectId?: string;
  /** Текст, который человек видел в интерфейсе. Сохраняется снимком. */
  textSnapshot: string;
  /** Объём согласия: цели, каналы, состав данных. */
  scope?: Record<string, unknown>;
  ip?: string;
  userAgent?: string;
  leadId?: number | null;
  bitrixLeadId?: string | null;
  /** Исходное событие, которое исправляет это. Только для корректировок. */
  correctsEvent?: string;
}

/**
 * ФИО одной строкой → фамилия и имя.
 *
 * Разбор намеренно примитивный и честный: первое слово — фамилия, второе —
 * имя, всё остальное в имя не дописывается. Угадывать отчество и порядок
 * слов по строке из формы нельзя, а хранить неверно разобранное ФИО в
 * доказательстве хуже, чем хранить его целиком: полная строка всё равно
 * остаётся в заявке.
 */
function splitName(name?: string): { last_name: string | null; first_name: string | null } {
  const parts = String(name || '').trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return { last_name: null, first_name: null };
  if (parts.length === 1) return { last_name: null, first_name: parts[0] };
  return { last_name: parts[0], first_name: parts[1] };
}

/**
 * Записать одно событие согласия и вернуть его идентификатор.
 *
 * Идентификатор нужен вызывающему: он уходит в CRM и в рассылочный реестр
 * как ссылка на доказательство.
 */
export async function logConsentEvent(input: ConsentEventInput): Promise<string> {
  const eventId = randomUUID();
  const doc = legalDoc(CONSENT_DOC[input.type]);
  const { last_name, first_name } = splitName(input.subject?.name);
  const email = input.subject?.email ? normalizeEmail(input.subject.email) : null;

  const row: ConsentEventRow = {
    event_id: eventId,
    subject_id: input.subjectId || (email ? subjectIdFor(email) : null),
    source: input.source.slice(0, 120),
    source_action: input.sourceAction,
    page_url: input.pageUrl ? input.pageUrl.slice(0, 2000) : null,
    form_id: input.formId ? input.formId.slice(0, 120) : null,
    submitted_at: new Date().toISOString(),
    last_name,
    first_name,
    company: input.subject?.company?.slice(0, 200) || null,
    phone: input.subject?.phone?.slice(0, 50) || null,
    email,
    consent_type: input.type,
    consent_action: input.action,
    consent_scope: input.scope ?? null,
    // Версия и хэш — только отсюда. См. комментарий в шапке модуля.
    document_version: doc.version,
    document_sha256: doc.sha256,
    consent_text_snapshot: input.textSnapshot.slice(0, 4000),
    ip_address: input.ip || null,
    user_agent: input.userAgent ? input.userAgent.slice(0, 500) : null,
    request_id: input.requestId,
    lead_id: input.leadId ?? null,
    bitrix_lead_id: input.bitrixLeadId ?? null,
    corrects_event: input.correctsEvent ?? null,
  };

  await createConsentEvent(row);
  return eventId;
}

/**
 * Записать согласия формы: обязательное ПДн и, если отмечено, маркетинговое.
 *
 * Возвращает идентификаторы обоих событий. Маркетинговое отсутствует, если
 * галочка не стояла: отказ от рекламы отдельным событием `denied` не
 * пишется при каждой отправке формы — журнал заполнился бы отказами тех, кто
 * просто не трогал необязательный чекбокс, и найти в нём настоящий отзыв
 * стало бы невозможно. Отдельное событие `denied` пишется только там, где
 * человек выразил отказ действием: в cookie-механизме и по ссылке отписки.
 */
export async function logFormConsents(args: {
  personalData: boolean;
  marketing: boolean;
  sourceAction: ConsentSourceAction;
  source: string;
  formId: string;
  pageUrl?: string;
  requestId: string;
  subject: ConsentSubject;
  texts: { personalData: string; marketing: string };
  scope?: Record<string, unknown>;
  ip?: string;
  userAgent?: string;
  leadId?: number | null;
}): Promise<{ personalDataEventId: string; marketingEventId: string | null }> {
  if (!args.personalData) {
    throw new Error('согласие на обработку персональных данных не получено');
  }

  const base = {
    sourceAction: args.sourceAction,
    source: args.source,
    formId: args.formId,
    pageUrl: args.pageUrl,
    requestId: args.requestId,
    subject: args.subject,
    scope: args.scope,
    ip: args.ip,
    userAgent: args.userAgent,
    leadId: args.leadId,
  };

  const personalDataEventId = await logConsentEvent({
    ...base,
    type: 'personal_data',
    action: 'granted',
    textSnapshot: args.texts.personalData,
  });

  let marketingEventId: string | null = null;
  if (args.marketing) {
    marketingEventId = await logConsentEvent({
      ...base,
      type: 'marketing',
      action: 'granted',
      textSnapshot: args.texts.marketing,
    });
  }

  return { personalDataEventId, marketingEventId };
}
