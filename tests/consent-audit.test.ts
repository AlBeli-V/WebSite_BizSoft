/**
 * Журнал согласий и рассылочный реестр: сценарии приёмки (ТЗ 16.09.2026, п. 11).
 *
 * Здесь проверяется не «работает ли код», а выполняются ли обещания, данные
 * в документах: что рекламное согласие отдельное и необязательное, что
 * отозвавший не попадёт в рассылку, что версия документа берётся с сервера,
 * а не от клиента.
 *
 * Directus подменён хранилищем в памяти — проверять нужно логику согласий,
 * а не доступность базы.
 */
import { describe, expect, it, beforeEach, vi } from 'vitest';

interface Row { [k: string]: unknown }
const journal: Row[] = [];
const registry: (Row & { id: number; email_normalized: string; status: string })[] = [];
let nextId = 1;

vi.mock('../src/lib/directus', () => ({
  createConsentEvent: async (row: Row) => { journal.push({ ...row }); },
  queryConsentEvents: async () => [...journal],
  findMarketingEntry: async (email: string) => registry.find((r) => r.email_normalized === email) || null,
  createMarketingEntry: async (row: Row) => {
    registry.push({ id: nextId++, ...(row as { email_normalized: string; status: string }) });
  },
  patchMarketingEntry: async (id: number, patch: Row) => {
    const row = registry.find((r) => r.id === id);
    if (row) Object.assign(row, patch);
  },
  queryMarketingRegistry: async (filter: Record<string, string> = {}) => {
    const want = filter['filter[status][_eq]'];
    return registry.filter((r) => !want || r.status === want);
  },
  createAdminAuditEntry: async () => {},
  queryAdminAudit: async () => [],
  kvGet: async () => null,
  kvPut: async () => {},
  DirectusError: class extends Error { status = 0 },
}));

const { logConsentEvent, logFormConsents, normalizeEmail, subjectIdFor } = await import('../src/lib/consent-log');
const { subscribe, unsubscribe, allowedAudience, isMailable, marketingStatusOf } =
  await import('../src/lib/marketing-registry');
const { intakeFormConsents } = await import('../src/lib/consent-intake');
const { LEGAL_MANIFEST } = await import('../src/lib/legal');
const { CONSENT_UI } = await import('../src/config/legal');

beforeEach(() => {
  journal.length = 0;
  registry.length = 0;
  nextId = 1;
});

const SUBJECT = { name: 'Кувшинова Екатерина', email: 'K@Romashka.RU', phone: '+79167898651', company: 'ООО «Ромашка»' };

const form = (marketing: boolean, extra: Record<string, unknown> = {}) =>
  intakeFormConsents({
    body: { marketing_consent: marketing, consent_form_id: 'lead-form', consent_page_url: '/pricing', ...extra },
    subject: SUBJECT,
    fallbackFormId: 'lead-form',
    purpose: 'Обработка обращения',
    ip: '203.0.113.10',
    userAgent: 'Mozilla/5.0',
  });

describe('события формы', () => {
  it('без рекламной галочки пишется одно событие — согласие на ПДн', async () => {
    const out = await form(false);
    expect(journal).toHaveLength(1);
    expect(journal[0].consent_type).toBe('personal_data');
    expect(journal[0].consent_action).toBe('granted');
    expect(out.marketingEventId).toBeNull();
    expect(out.marketingStatus).toBe('not_requested');
  });

  it('с рекламной галочкой — два независимых события, а не одно общее', async () => {
    const out = await form(true);
    expect(journal).toHaveLength(2);
    const types = journal.map((e) => e.consent_type);
    expect(types).toEqual(['personal_data', 'marketing']);
    // У каждого свой идентификатор, свой документ и свой снимок текста.
    expect(journal[0].event_id).not.toBe(journal[1].event_id);
    expect(journal[0].document_sha256).not.toBe(journal[1].document_sha256);
    expect(journal[0].consent_text_snapshot).toBe(CONSENT_UI.personalData.text);
    expect(journal[1].consent_text_snapshot).toBe(CONSENT_UI.marketing.text);
    expect(out.marketingEventId).toBeTruthy();
  });

  it('оба события одной отправки связаны общим request_id', async () => {
    await form(true);
    expect(journal[0].request_id).toBe(journal[1].request_id);
  });

  it('«Подтвердить оба» сохраняется способом ввода, а не отдельным согласием', async () => {
    await form(true, { consent_source_action: 'bulk_control_all' });
    expect(journal.map((e) => e.source_action)).toEqual(['bulk_control_all', 'bulk_control_all']);
    // Никакого события «ALL_CONSENTS» в журнале нет и быть не может.
    expect(journal.map((e) => e.consent_type)).not.toContain('all');
  });

  it('«Только необходимое» не создаёт маркетингового события', async () => {
    await form(false, { consent_source_action: 'bulk_control_required_only' });
    expect(journal).toHaveLength(1);
    expect(journal[0].source_action).toBe('bulk_control_required_only');
  });

  it('снятая после bulk галочка не оставляет действующего согласия на рекламу', async () => {
    // Интерфейс возвращает способ ввода к обычному, а флаг приходит false.
    await form(false, { consent_source_action: 'checkbox' });
    expect(journal.filter((e) => e.consent_type === 'marketing')).toHaveLength(0);
    expect(registry).toHaveLength(0);
  });

  it('незнакомый способ ввода приводится к обычному чекбоксу, а не пишется как есть', async () => {
    await form(false, { consent_source_action: 'whatever_client_sent' });
    expect(journal[0].source_action).toBe('checkbox');
  });

  it('без согласия на ПДн событие не пишется вовсе', async () => {
    await expect(logFormConsents({
      personalData: false,
      marketing: true,
      sourceAction: 'checkbox',
      source: 'lead-form',
      formId: 'lead-form',
      requestId: 'r1',
      subject: SUBJECT,
      texts: { personalData: 'a', marketing: 'b' },
    })).rejects.toThrow();
    expect(journal).toHaveLength(0);
  });
});

describe('версия и хэш документа — только с сервера', () => {
  it('значения берутся из манифеста', async () => {
    await form(true);
    expect(journal[0].document_version).toBe(LEGAL_MANIFEST['personal-data-consent'].version);
    expect(journal[0].document_sha256).toBe(LEGAL_MANIFEST['personal-data-consent'].sha256);
    expect(journal[1].document_version).toBe(LEGAL_MANIFEST['marketing-consent'].version);
    expect(journal[1].document_sha256).toBe(LEGAL_MANIFEST['marketing-consent'].sha256);
  });

  it('присланные клиентом версия и хэш игнорируются', async () => {
    await form(false, {
      document_version: '1999-01-01',
      document_sha256: '0'.repeat(64),
      consent_text_snapshot: 'я согласен на всё',
    });
    expect(journal[0].document_version).toBe(LEGAL_MANIFEST['personal-data-consent'].version);
    expect(journal[0].document_sha256).not.toBe('0'.repeat(64));
    expect(journal[0].consent_text_snapshot).toBe(CONSENT_UI.personalData.text);
  });
});

describe('состав записи', () => {
  it('адрес нормализуется, субъект выводится из него детерминированно', async () => {
    await form(false);
    expect(journal[0].email).toBe('k@romashka.ru');
    expect(journal[0].subject_id).toBe(subjectIdFor('K@ROMASHKA.ru'));
    expect(String(journal[0].subject_id)).toMatch(/^[0-9a-f-]{36}$/);
  });

  it('ФИО разбирается без догадок: фамилия и имя, отчество не выдумывается', async () => {
    await form(false);
    expect(journal[0].last_name).toBe('Кувшинова');
    expect(journal[0].first_name).toBe('Екатерина');
  });

  it('технические реквизиты и страница сохраняются', async () => {
    await form(false);
    expect(journal[0].ip_address).toBe('203.0.113.10');
    expect(journal[0].user_agent).toBe('Mozilla/5.0');
    expect(journal[0].page_url).toBe('/pricing');
    expect(journal[0].form_id).toBe('lead-form');
  });
});

describe('рассылочный реестр', () => {
  it('маркетинговое согласие подписывает адрес и ссылается на событие', async () => {
    const out = await form(true);
    expect(registry).toHaveLength(1);
    expect(registry[0].status).toBe('subscribed');
    expect(registry[0].consent_event_id).toBe(out.marketingEventId);
  });

  it('отправка формы без галочки в рассылку не подписывает', async () => {
    await form(false);
    expect(registry).toHaveLength(0);
    expect(await marketingStatusOf(SUBJECT.email)).toBe('unknown');
  });

  it('подписка без ссылки на событие невозможна', async () => {
    await expect(subscribe({ email: 'a@b.ru', consentEventId: '', source: 'test' })).rejects.toThrow();
  });

  it('отписка меняет статус, но не удаляет адрес', async () => {
    await form(true);
    await unsubscribe({ email: SUBJECT.email, reason: 'link' });
    expect(registry).toHaveLength(1);
    expect(registry[0].status).toBe('unsubscribed');
    expect(registry[0].unsubscribed_at).toBeTruthy();
  });

  it('отписавшийся никогда не попадает в разрешённую аудиторию', async () => {
    await form(true);
    expect(await allowedAudience()).toHaveLength(1);
    await unsubscribe({ email: SUBJECT.email, reason: 'link' });
    expect(await allowedAudience()).toHaveLength(0);
  });

  it('повторная отписка идемпотентна: сканер письма не ломает состояние', async () => {
    await form(true);
    expect((await unsubscribe({ email: SUBJECT.email, reason: 'link' })).changed).toBe(true);
    expect((await unsubscribe({ email: SUBJECT.email, reason: 'link' })).changed).toBe(false);
    expect(registry).toHaveLength(1);
  });

  it('повторная подписка возможна только новым событием granted', async () => {
    await form(true);
    await unsubscribe({ email: SUBJECT.email, reason: 'link' });
    const out = await form(true);
    expect(registry[0].status).toBe('subscribed');
    expect(registry[0].consent_event_id).toBe(out.marketingEventId);
    expect(registry[0].unsubscribed_at).toBeNull();
    expect(await allowedAudience()).toHaveLength(1);
  });

  it('жалоба и недоставляемый адрес формой не снимаются', async () => {
    await form(true);
    await unsubscribe({ email: SUBJECT.email, reason: 'complaint', status: 'suppressed' });
    await form(true);
    expect(registry[0].status).toBe('suppressed');
    expect(await allowedAudience()).toHaveLength(0);
  });

  it('владелец может снять блокировку явным флагом — и только так', async () => {
    await form(true);
    await unsubscribe({ email: SUBJECT.email, reason: 'bounce', status: 'bounced' });
    await subscribe({ email: SUBJECT.email, consentEventId: 'e-1', source: 'admin-unblock', allowBlocked: true });
    expect(registry[0].status).toBe('subscribed');
  });

  it('адрес со статусом subscribed, но без события согласия, в аудиторию не идёт', async () => {
    registry.push({ id: 99, email_normalized: 'ghost@b24.ru', status: 'subscribed', consent_event_id: null });
    expect(isMailable(registry[0])).toBe(false);
    expect(await allowedAudience()).toHaveLength(0);
  });

  it('аудитория дедуплицируется по адресу', async () => {
    await form(true);
    registry.push({ ...registry[0], id: 100 });
    expect(await allowedAudience()).toHaveLength(1);
  });

  it('отписка адреса, которого не было в реестре, заводит запись в suppression', async () => {
    await unsubscribe({ email: 'never@seen.ru', reason: 'manual_entry' });
    expect(registry).toHaveLength(1);
    expect(registry[0].status).toBe('unsubscribed');
    // И следующая подписка уже видит эту запись, а не заводит вторую.
    await subscribe({ email: 'never@seen.ru', consentEventId: 'e-2', source: 'lead-form' });
    expect(registry).toHaveLength(1);
  });
});

describe('отзыв как доказательство', () => {
  it('событие withdrawn пишется тем же журналом и с тем же документом', async () => {
    await form(true);
    journal.length = 0;
    await logConsentEvent({
      type: 'marketing',
      action: 'withdrawn',
      sourceAction: 'unsubscribe_link',
      source: 'unsubscribe',
      requestId: 'r-2',
      subject: { email: SUBJECT.email },
      textSnapshot: CONSENT_UI.marketing.text,
    });
    expect(journal).toHaveLength(1);
    expect(journal[0].consent_action).toBe('withdrawn');
    expect(journal[0].document_sha256).toBe(LEGAL_MANIFEST['marketing-consent'].sha256);
    expect(journal[0].email).toBe(normalizeEmail(SUBJECT.email));
  });

  it('исходные события отзывом не стираются', async () => {
    await form(true);
    const before = journal.length;
    await unsubscribe({ email: SUBJECT.email, reason: 'link' });
    expect(journal.length).toBeGreaterThanOrEqual(before);
    expect(journal.filter((e) => e.consent_action === 'granted')).toHaveLength(2);
  });
});
