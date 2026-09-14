/**
 * Зеркало заявки в Bitrix24.
 *
 * Проверяется не «умеем ли мы слать POST», а три обещания из
 * docs/rules/crm-mirror.md, которые дорого стоят при нарушении: зеркало не
 * роняет заявку, код вебхука не попадает в лог, выключенное зеркало ведёт
 * себя как отсутствующее, а не как сбой.
 */
import { describe, expect, it, vi, afterEach, beforeEach } from 'vitest';
import { b24Configured, b24LeadFields, maskWebhook, mirrorLeadToB24 } from '../src/lib/bitrix24';

const WEBHOOK = 'https://b24-test.bitrix24.ru/rest/1/abcdef123456/';

const lead = (over: Record<string, unknown> = {}) => ({
  title: 'Заявка с сайта — ООО «Ромашка»',
  name: 'Иванов Иван Иванович',
  company: 'ООО «Ромашка»',
  inn: '7707083893',
  email: 'ivanov@romashka.ru',
  phone: '+7 900 000-00-00',
  comments: 'Нужны 10 лицензий',
  formSource: 'product',
  channel: 'yandex / cpc',
  productRef: 'JB-SUB-IDEA-ULT-1Y-SEAT',
  utm: { utm_source: 'yandex', utm_medium: 'cpc', utm_campaign: 'brand' },
  ...over,
});

const ok = (id: number) => ({ ok: true, status: 200, json: async () => ({ result: id }) });

beforeEach(() => { process.env.B24_WEBHOOK_URL = WEBHOOK; });
afterEach(() => {
  delete process.env.B24_WEBHOOK_URL;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('поля лида', () => {
  it('контакты уходят массивами, как ждёт портал', () => {
    const f = b24LeadFields(lead());
    expect(f.EMAIL).toEqual([{ VALUE: 'ivanov@romashka.ru', VALUE_TYPE: 'WORK' }]);
    expect(f.PHONE).toEqual([{ VALUE: '+7 900 000-00-00', VALUE_TYPE: 'WORK' }]);
  });

  it('пустой телефон не создаёт пустого поля', () => {
    const f = b24LeadFields(lead({ phone: '' }));
    expect(f).not.toHaveProperty('PHONE');
  });

  it('ИНН и товар видны в комментарии — отдельного поля ИНН в лиде нет', () => {
    const c = String(b24LeadFields(lead()).COMMENTS);
    expect(c).toContain('ИНН: 7707083893');
    expect(c).toContain('JB-SUB-IDEA-ULT-1Y-SEAT');
    expect(c).toContain('Нужны 10 лицензий');
  });

  it('метки кампании переносятся в штатные поля Битрикса', () => {
    const f = b24LeadFields(lead());
    expect(f.UTM_SOURCE).toBe('yandex');
    expect(f.UTM_CAMPAIGN).toBe('brand');
    expect(f).not.toHaveProperty('UTM_TERM');
  });

  it('стадия у зеркала всегда начальная: воронку ведёт Directus', () => {
    expect(b24LeadFields(lead()).STATUS_ID).toBe('NEW');
  });
});

describe('обращение к порталу', () => {
  it('лид заведён — возвращается его номер', async () => {
    const fetchMock = vi.fn(async () => ok(42));
    vi.stubGlobal('fetch', fetchMock);
    await expect(mirrorLeadToB24(lead())).resolves.toEqual({ status: 'created', id: 42 });
    expect(fetchMock.mock.calls[0][0]).toBe(`${WEBHOOK}crm.lead.add.json`);
  });

  it('портал ответил ошибкой — исход возвращается, исключение не летит', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: false,
      status: 400,
      json: async () => ({ error: 'INVALID_CREDENTIALS', error_description: 'Invalid request credentials' }),
    })));
    const r = await mirrorLeadToB24(lead());
    expect(r.status).toBe('failed');
    expect(r).toHaveProperty('reason', expect.stringContaining('INVALID_CREDENTIALS'));
  });

  it('портал недоступен — заявка этого не замечает', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('timeout'); }));
    await expect(mirrorLeadToB24(lead())).resolves.toMatchObject({ status: 'failed' });
  });

  it('вебхук не задан — зеркало пропущено, а не сломано', async () => {
    delete process.env.B24_WEBHOOK_URL;
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    expect(b24Configured()).toBe(false);
    await expect(mirrorLeadToB24(lead())).resolves.toMatchObject({ status: 'skipped' });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('адрес без завершающей косой черты не склеивает метод с кодом', async () => {
    process.env.B24_WEBHOOK_URL = WEBHOOK.slice(0, -1);
    const fetchMock = vi.fn(async () => ok(7));
    vi.stubGlobal('fetch', fetchMock);
    await mirrorLeadToB24(lead());
    expect(fetchMock.mock.calls[0][0]).toBe(`${WEBHOOK}crm.lead.add.json`);
  });
});

describe('код вебхука не утекает в лог', () => {
  it('маскируется и точное значение, и любой адрес вида /rest/<id>/<код>/', () => {
    expect(maskWebhook(`отказ по ${WEBHOOK}crm.lead.add.json`)).not.toContain('abcdef123456');
    expect(maskWebhook('см. https://other.bitrix24.ru/rest/9/zzz999/')).not.toContain('zzz999');
  });

  it('причина сбоя, собранная из ответа портала, уже промаскирована', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: false,
      status: 401,
      json: async () => ({ error: 'NO_AUTH_FOUND', error_description: `Wrong handler ${WEBHOOK}` }),
    })));
    const r = await mirrorLeadToB24(lead());
    expect(JSON.stringify(r)).not.toContain('abcdef123456');
  });
});
