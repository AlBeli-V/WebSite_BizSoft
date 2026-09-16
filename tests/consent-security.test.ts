/**
 * Защита контура согласий: подписи, второй фактор, права и роли.
 *
 * Отдельно от логики согласий: здесь проверяется, что подделать отписку,
 * открыть журнал одним токеном или переписать событие нельзя.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { totpAt, verifyTotp, base32Decode, isValidBase32 } from '../src/lib/totp';

const ROOT = resolve(__dirname, '..');
const read = (rel: string) => readFileSync(resolve(ROOT, rel), 'utf8');

// Модули читают секреты при загрузке, поэтому окружение задаётся до импорта.
const SECRET = 'unsubscribe-secret-for-tests-0123456789';
process.env.UNSUBSCRIBE_SECRET = SECRET;
const { createUnsubscribeToken, verifyUnsubscribeToken, unsubscribeUrl, UNSUBSCRIBE_TTL_SEC, isUnsubscribeConfigured } =
  await import('../src/lib/unsubscribe-token');

describe('подписанная ссылка отписки', () => {
  it('токен раскрывается только нашей подписью', () => {
    const token = createUnsubscribeToken('K@Romashka.RU');
    const out = verifyUnsubscribeToken(token);
    expect(out.ok).toBe(true);
    expect(out.email).toBe('k@romashka.ru');
    expect(out.expired).toBe(false);
  });

  it('подделанная подпись отвергается', () => {
    const token = createUnsubscribeToken('k@romashka.ru');
    const [payload] = token.split('.');
    expect(verifyUnsubscribeToken(`${payload}.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`).ok).toBe(false);
    expect(verifyUnsubscribeToken('мусор').ok).toBe(false);
    expect(verifyUnsubscribeToken('').ok).toBe(false);
  });

  it('подменённый адрес в теле токена ломает подпись', () => {
    const token = createUnsubscribeToken('k@romashka.ru');
    const sig = token.split('.')[1];
    const forged = Buffer.from(JSON.stringify({ e: 'boss@rival.ru', t: Math.floor(Date.now() / 1000) })).toString('base64url');
    expect(verifyUnsubscribeToken(`${forged}.${sig}`).ok).toBe(false);
  });

  it('просроченная ссылка не отказ, а повод подтвердить адрес', () => {
    const old = Date.now() - (UNSUBSCRIBE_TTL_SEC + 60) * 1000;
    const out = verifyUnsubscribeToken(createUnsubscribeToken('k@romashka.ru', old));
    expect(out.ok).toBe(true);
    expect(out.expired).toBe(true);
    expect(out.email).toBe('k@romashka.ru');
  });

  it('ссылка для письма собирается готовой', () => {
    expect(isUnsubscribeConfigured()).toBe(true);
    expect(unsubscribeUrl('k@romashka.ru')).toMatch(/^https:\/\/biz-soft\.pro\/unsubscribe\?t=/);
  });
});

describe('отписка выполняется POST, а не открытием ссылки', () => {
  const api = read('src/pages/api/unsubscribe.ts');

  it('GET ничего не меняет', () => {
    // Почтовые шлюзы открывают все ссылки письма ботом-сканером.
    const get = api.slice(api.indexOf('export const GET'));
    expect(get).not.toContain('unsubscribe(');
    expect(get).toContain('405');
  });

  it('POST закрыт проверкой CSRF и порогом по адресу', () => {
    expect(api).toContain('verifyCsrf(request');
    expect(api).toContain('overLimit(ip)');
  });

  it('адрес берётся из подписанного токена, а не из тела запроса', () => {
    expect(api).toContain('verifyUnsubscribeToken(token)');
    expect(api).toMatch(/verdict\.ok && verdict\.email \? verdict\.email : typed/);
    // Токен есть, но подпись не сошлась — это подделка, а не «истёк».
    expect(api).toMatch(/if \(token && !verdict\.ok\)/);
  });

  it('реестр не меняется, если журнал не принял отзыв', () => {
    const logBlock = api.slice(api.indexOf('logConsentEvent'), api.indexOf('unsubscribe({'));
    expect(logBlock).toContain('return json(');
  });

  it('страница отписки закрыта от индексации и выдаёт токен CSRF', () => {
    const page = read('src/pages/unsubscribe.astro');
    expect(page).toContain('noindex={true}');
    expect(page).toContain("X-Robots-Tag', 'noindex, nofollow'");
    expect(page).toContain('csrfCookieHeader(csrf)');
  });
});

describe('CSRF', () => {
  beforeEach(() => { vi.resetModules(); });
  afterEach(() => { delete process.env.CSRF_SECRET; });

  it('без секрета проверка не проходит: молча пропускать нельзя', async () => {
    const src = read('src/lib/csrf.ts');
    expect(src).toMatch(/if \(!isCsrfConfigured\(\)\) return false;/);
  });

  it('совпадение cookie и поля обязательно', async () => {
    process.env.CSRF_SECRET = 'csrf-secret-for-tests-0123456789';
    const { createCsrfToken, verifyCsrf, CSRF_COOKIE } = await import('../src/lib/csrf');
    const token = createCsrfToken();
    const req = (cookie: string, origin = 'https://biz-soft.pro') =>
      new Request('https://biz-soft.pro/api/unsubscribe', {
        method: 'POST',
        headers: { cookie, origin },
      });
    expect(verifyCsrf(req(`${CSRF_COOKIE}=${token}`), token)).toBe(true);
    expect(verifyCsrf(req(`${CSRF_COOKIE}=${token}`), createCsrfToken())).toBe(false);
    expect(verifyCsrf(req(''), token)).toBe(false);
    // Чужой источник отсекается до сравнения значений.
    expect(verifyCsrf(req(`${CSRF_COOKIE}=${token}`, 'https://evil.example'), token)).toBe(false);
  });

  it('навязанное с чужого домена значение не проходит проверку подписи', async () => {
    process.env.CSRF_SECRET = 'csrf-secret-for-tests-0123456789';
    const { verifyCsrf, CSRF_COOKIE } = await import('../src/lib/csrf');
    const planted = 'aaaa.bbbb';
    const req = new Request('https://biz-soft.pro/api/unsubscribe', {
      method: 'POST',
      headers: { cookie: `${CSRF_COOKIE}=${planted}`, origin: 'https://biz-soft.pro' },
    });
    expect(verifyCsrf(req, planted)).toBe(false);
  });
});

describe('второй фактор', () => {
  const SEC = 'JBSWY3DPEHPK3PXP';

  it('код проверяется с окном ±30 секунд', () => {
    const now = 1_760_000_000_000;
    const step = Math.floor(now / 1000 / 30);
    expect(verifyTotp(SEC, totpAt(SEC, step), now)).toBe(true);
    expect(verifyTotp(SEC, totpAt(SEC, step - 1), now)).toBe(true);
    expect(verifyTotp(SEC, totpAt(SEC, step + 1), now)).toBe(true);
    // Два шага — уже нет: каждый лишний шаг это лишний действующий код.
    expect(verifyTotp(SEC, totpAt(SEC, step + 2), now)).toBe(false);
  });

  it('мусор вместо кода отвергается', () => {
    expect(verifyTotp(SEC, '')).toBe(false);
    expect(verifyTotp(SEC, '12345')).toBe(false);
    expect(verifyTotp(SEC, 'abcdef')).toBe(false);
    expect(verifyTotp('', '123456')).toBe(false);
  });

  it('base32 разбирается по RFC 4648', () => {
    expect(base32Decode('JBSWY3DP').toString('utf8')).toBe('Hello');
    expect(base32Decode('jbswy3dp').toString('utf8')).toBe('Hello');
    expect(() => base32Decode('1!')).toThrow();
  });

  it('код совпадает с эталоном RFC 6238 для секрета 12345678901234567890', () => {
    // Секрет «12345678901234567890» в base32; шаг 59 с → счётчик 1.
    expect(totpAt('GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ', 1)).toBe('287082');
  });

  it('испорченный секрет возвращает false, а не роняет обработчик', () => {
    // Проверка доступа вызывается ДО блока try обработчика: исключение
    // отсюда отвечало бы 500 вместо понятного сообщения.
    for (const bad of ['НЕ-BASE32', 'ABCD0189', 'JBSWY3DP!', '   ', 'a b c']) {
      expect(() => verifyTotp(bad, '123456'), bad).not.toThrow();
      expect(verifyTotp(bad, '123456'), bad).toBe(false);
    }
  });

  it('алфавит base32 распознаётся: нет 0, 1, 8 и 9', () => {
    expect(isValidBase32('JBSWY3DPEHPK3PXP')).toBe(true);
    // Регистр, пробелы и разделители при переносе руками — не ошибка.
    expect(isValidBase32('jbswy3dp ehpk-3pxp')).toBe(true);
    expect(isValidBase32('JBSWY3DP====')).toBe(true);
    for (const bad of ['ABCD0', 'ABCD1', 'ABCD8', 'ABCD9', 'ABCD!', 'ЖЖЖЖ', '', '   ']) {
      expect(isValidBase32(bad), bad).toBe(false);
    }
  });
});

describe('роли и права раздела комплаенса', () => {
  const auth = read('src/lib/compliance-auth.ts');
  const api = read('src/pages/api/admin/compliance.ts');

  it('раздел не открывается вовсе, если второй фактор не настроен', () => {
    expect(auth).toMatch(/secret\.length >= 16/);
    expect(auth).toContain('Раздел не настроен');
  });

  it('негодный формат ключа — это «не настроено», а не «неверный код»', () => {
    // Ключ с посторонним символом не даст сойтись ни одному коду. Без этой
    // проверки раздел выглядел бы настроенным, а войти в него было бы нельзя.
    expect(auth).toContain('isValidBase32(secret)');
    expect(auth).toContain('не в формате base32');
  });

  it('оба фактора обязательны', () => {
    expect(auth).toContain('x-compliance-token');
    expect(auth).toContain('x-compliance-otp');
    expect(auth).toContain('verifyTotp(totpSecret(), otp)');
  });

  it('токены сравниваются постоянным временем', () => {
    expect(auth).toContain('timingSafeEqual');
  });

  it('IP и user-agent скрыты от роли администратора', () => {
    expect(auth).toMatch(/canSeeTechnical\(role: ComplianceRole\): boolean \{\s*return role === 'owner';/);
    expect(auth).toMatch(/out\.ip_address = null/);
    expect(auth).toMatch(/out\.user_agent = null/);
    expect(api).toContain('redactForRole');
  });

  it('выгрузки и смена статуса — только владельцу', () => {
    for (const op of ['export_journal', 'audience', 'set_marketing_status', 'record_withdrawal', 'admin_log']) {
      const block = api.slice(api.indexOf(`case '${op}'`), api.indexOf(`case '${op}'`) + 300);
      expect(block, `${op}: нет проверки роли`).toContain('canExport(session.role)');
    }
  });

  it('операции правки и удаления события в API нет', () => {
    expect(api).not.toMatch(/case 'delete_event'/);
    expect(api).not.toMatch(/case 'edit_event'/);
    expect(api).toContain("case 'correct'");
    expect(api).toContain('correctsEvent');
  });

  it('подписать вручную нельзя', () => {
    expect(api).toContain('Подписать вручную нельзя');
  });

  it('снятие блокировки проверяет, что событие granted принадлежит этому адресу', () => {
    const block = api.slice(api.indexOf("case 'resubscribe_after_block'"));
    expect(block).toContain("filter[event_id][_eq]");
    expect(block).toContain("filter[email][_eq]");
    expect(block).toContain("event.consent_type !== 'marketing'");
  });

  it('каждое обращение к данным пишется в журнал действий', () => {
    for (const op of ['journal', 'evidence', 'registry', 'export_journal', 'audience']) {
      const start = api.indexOf(`case '${op}'`);
      const block = api.slice(start, api.indexOf('case ', start + 10));
      expect(block, `${op}: действие не попадает в admin_audit_log`).toContain('auditAdmin(session');
    }
  });
});

describe('права сервисной роли Directus', () => {
  const setup = read('scripts/directus-setup.mjs');

  it('на журнал согласий выданы только create и read', () => {
    expect(setup).toContain("['consent_audit_log', 'create'], ['consent_audit_log', 'read']");
    expect(setup).not.toContain("['consent_audit_log', 'update']");
    expect(setup).not.toContain("['consent_audit_log', 'delete']");
  });

  it('реестр рассылок можно обновлять, но не удалять', () => {
    expect(setup).toContain("['marketing_registry', 'update']");
    expect(setup).not.toContain("['marketing_registry', 'delete']");
  });

  it('журнал действий администраторов тоже только на запись и чтение', () => {
    expect(setup).toContain("['admin_audit_log', 'create'], ['admin_audit_log', 'read']");
    expect(setup).not.toContain("['admin_audit_log', 'update']");
    expect(setup).not.toContain("['admin_audit_log', 'delete']");
  });

  it('поля журнала заведены с индексами по ТЗ', () => {
    const block = setup.slice(setup.indexOf("ensureCollection('consent_audit_log'"), setup.indexOf("ensureCollection('marketing_registry'"));
    // Описание поля может занимать несколько строк (списки значений), поэтому
    // берём кусок от объявления поля до объявления следующего.
    for (const field of ['email', 'phone', 'submitted_at', 'consent_type', 'company', 'bitrix_lead_id']) {
      const start = block.indexOf(`'consent_audit_log', '${field}'`);
      expect(start, `${field}: поле не заведено`).toBeGreaterThan(-1);
      const next = block.indexOf('await ensureField(', start + 10);
      const chunk = block.slice(start, next > 0 ? next : undefined);
      expect(chunk, `${field}: нет индекса`).toContain('is_indexed: true');
    }
  });

  it('адрес в реестре уникален — иначе у человека два статуса сразу', () => {
    const block = setup.slice(setup.indexOf("ensureCollection('marketing_registry'"));
    const line = block.split('\n').find((l) => l.includes("'email_normalized'")) || '';
    expect(line).toContain('is_unique: true');
  });
});

describe('заявка не принимается без записи согласия', () => {
  // Что должно произойти ПОСЛЕ фиксации согласия — у каждого обработчика своё:
  // заявка с формы пишется прямо в теле POST, заявка из КП — через
  // recordQuoteLead, объявленный выше по файлу.
  const AFTER: Record<string, string[]> = {
    'src/pages/api/lead.ts': ['await createLeadTolerant(', 'mirrorLeadAndLink(leadId'],
    'src/pages/api/quote.ts': ['recordQuoteLead({', 'generateQuotePdf(', 'sendMail('],
  };

  it.each(Object.keys(AFTER))('%s', (file) => {
    const src = read(file);
    // Смотрим только на тело обработчика: порядок объявлений в файле к
    // порядку выполнения отношения не имеет.
    const handler = src.slice(src.indexOf('export const POST'));
    const intake = handler.indexOf('intakeFormConsents({');
    expect(intake).toBeGreaterThan(0);
    // Сбой журнала — отказ в приёме, а не молчаливое продолжение.
    expect(handler.slice(intake, intake + 1400)).toContain('503');
    for (const call of AFTER[file]) {
      const at = handler.indexOf(call);
      expect(at, `${call}: вызова нет в обработчике`).toBeGreaterThan(-1);
      expect(intake, `согласие должно фиксироваться до ${call}`).toBeLessThan(at);
    }
  });

  it('в CRM уходят идентификатор события и маркетинговый статус', () => {
    const b24 = read('src/lib/bitrix24.ts');
    expect(b24).toContain('consentEventId');
    expect(b24).toContain('marketingStatus');
    expect(b24).toContain('B24_UF_CONSENT_EVENT');
    // Портал прямо назван зеркалом, а не источником доказательства.
    expect(b24).toContain('не портал');
  });
});
