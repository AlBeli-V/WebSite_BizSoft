/**
 * Обратный канал Bitrix24 → Directus.
 *
 * Канал трогает то, по чему считают конверсию и выручку, и приходит снаружи,
 * с публичного адреса. Проверяется поэтому не «доходит ли стадия», а границы:
 * подделка не проходит, чужой лид не сопоставляется догадкой, неизвестная
 * стадия ничего не меняет, а даты стадий считаются тем же правилом, что в
 * кабинете.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { ALL_STATUSES } from '../src/crm/stages';
import { mapB24Status, mappedStatuses } from '../src/lib/b24-stages';

const patchLead = vi.fn(async () => {});
const createLeadEvent = vi.fn(async () => {});
const findLeadByB24Id = vi.fn(async (): Promise<Record<string, unknown> | null> => null);

vi.mock('../src/lib/directus', () => ({
  patchLead: (...a: unknown[]) => patchLead(...(a as [])),
  createLeadEvent: (...a: unknown[]) => createLeadEvent(...(a as [])),
  findLeadByB24Id: (...a: unknown[]) => findLeadByB24Id(...(a as [])),
  DirectusError: class extends Error { status = 0 },
}));

const { POST } = await import('../src/pages/api/b24/hook');

const TOKEN = 'app-token-12345';
const WEBHOOK = 'https://b24-test.bitrix24.ru/rest/1/abcdef123456/';

/** Событие в том виде, в каком его шлёт портал: форма с ключами data[FIELDS][…]. */
function event(over: Record<string, string> = {}): Request {
  const form = new URLSearchParams({
    event: 'ONCRMLEADUPDATE',
    'data[FIELDS][ID]': '77',
    'auth[application_token]': TOKEN,
    ...over,
  });
  return new Request('https://biz-soft.pro/api/b24/hook', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form.toString(),
  });
}

/** Ответ портала на crm.lead.get. */
const portalLead = (statusId: string, opportunity = 0) => vi.fn(async () => ({
  ok: true, status: 200, json: async () => ({ result: { STATUS_ID: statusId, OPPORTUNITY: opportunity, TITLE: 'Заявка' } }),
}));

const call = (req: Request) => POST({ request: req } as never) as Promise<Response>;

beforeEach(() => {
  process.env.B24_APP_TOKEN = TOKEN;
  process.env.B24_WEBHOOK_URL = WEBHOOK;
  findLeadByB24Id.mockResolvedValue({ id: 5, status: 'new', amount: null, qualified_at: null });
});
afterEach(() => {
  delete process.env.B24_APP_TOKEN;
  delete process.env.B24_WEBHOOK_URL;
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe('карта стадий', () => {
  it('каждая стадия карты существует в воронке', () => {
    for (const s of mappedStatuses()) expect(ALL_STATUSES).toContain(s);
  });

  it('неизвестный код соответствия не получает', () => {
    expect(mapB24Status('UC_НЕТ_ТАКОГО')).toBeNull();
    expect(mapB24Status('')).toBeNull();
  });
});

describe('граница приёмника', () => {
  it('чужой application_token — 403, к базе не ходим', async () => {
    vi.stubGlobal('fetch', portalLead('IN_PROCESS'));
    const res = await call(event({ 'auth[application_token]': 'подделка' }));
    expect(res.status).toBe(403);
    expect(findLeadByB24Id).not.toHaveBeenCalled();
    expect(patchLead).not.toHaveBeenCalled();
  });

  it('ключ не настроен — 503, а не молчаливое «принято»', async () => {
    delete process.env.B24_APP_TOKEN;
    const res = await call(event());
    expect(res.status).toBe(503);
    expect(patchLead).not.toHaveBeenCalled();
  });

  it('чужое событие пропускается без правок', async () => {
    const res = await call(event({ event: 'ONCRMLEADADD' }));
    expect(res.status).toBe(200);
    expect(patchLead).not.toHaveBeenCalled();
  });

  it('лид, заведённый в портале руками, к заявке не привязывается', async () => {
    vi.stubGlobal('fetch', portalLead('IN_PROCESS'));
    findLeadByB24Id.mockResolvedValue(null);
    const res = await call(event());
    expect(res.status).toBe(200);
    expect(patchLead).not.toHaveBeenCalled();
  });
});

describe('перенос стадии', () => {
  it('стадия портала доезжает до заявки', async () => {
    vi.stubGlobal('fetch', portalLead('IN_PROCESS'));
    const res = await call(event());
    expect(res.status).toBe(200);
    expect(patchLead).toHaveBeenCalledWith(5, expect.objectContaining({ status: 'in_progress' }));
    expect(createLeadEvent).toHaveBeenCalledWith(expect.objectContaining({ kind: 'stage', author: 'Bitrix24' }));
  });

  it('дата квалификации ставится тем же правилом, что в кабинете', async () => {
    vi.stubGlobal('fetch', portalLead('PROCESSED'));
    await call(event());
    const patch = patchLead.mock.calls[0][1] as Record<string, unknown>;
    expect(patch.status).toBe('qualified');
    expect(patch.qualified_at).toEqual(expect.any(String));
  });

  it('отказ закрывает заявку датой', async () => {
    vi.stubGlobal('fetch', portalLead('JUNK'));
    await call(event());
    const patch = patchLead.mock.calls[0][1] as Record<string, unknown>;
    expect(patch.status).toBe('lost');
    expect(patch.closed_at).toEqual(expect.any(String));
  });

  it('повтор того же события заявку не трогает', async () => {
    vi.stubGlobal('fetch', portalLead('IN_PROCESS'));
    findLeadByB24Id.mockResolvedValue({ id: 5, status: 'in_progress', amount: null, qualified_at: null });
    const res = await call(event());
    expect(res.status).toBe(200);
    expect(patchLead).not.toHaveBeenCalled();
  });

  it('неописанная стадия портала заявку не меняет, но оставляет след в истории', async () => {
    vi.stubGlobal('fetch', portalLead('UC_ЧТО_ТО_СВОЁ'));
    const res = await call(event());
    expect(res.status).toBe(200);
    expect(patchLead).not.toHaveBeenCalled();
    expect(createLeadEvent).toHaveBeenCalledWith(expect.objectContaining({
      subject: expect.stringContaining('UC_ЧТО_ТО_СВОЁ'),
    }));
  });
});

describe('сумма', () => {
  it('сумма портала заполняет пустое поле', async () => {
    vi.stubGlobal('fetch', portalLead('IN_PROCESS', 120000));
    await call(event());
    expect((patchLead.mock.calls[0][1] as Record<string, unknown>).amount).toBe(120000);
  });

  it('сумма, введённая у нас, порталом не перебивается', async () => {
    vi.stubGlobal('fetch', portalLead('IN_PROCESS', 120000));
    findLeadByB24Id.mockResolvedValue({ id: 5, status: 'new', amount: 99000, qualified_at: null });
    await call(event());
    expect((patchLead.mock.calls[0][1] as Record<string, unknown>).amount).toBeUndefined();
  });
});

describe('сбой портала и базы', () => {
  it('портал не отдал лид — 502, заявка не тронута', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('timeout'); }));
    const res = await call(event());
    expect(res.status).toBe(502);
    expect(patchLead).not.toHaveBeenCalled();
  });

  it('база не приняла правку — 502, а не «ок»', async () => {
    vi.stubGlobal('fetch', portalLead('IN_PROCESS'));
    patchLead.mockRejectedValueOnce(new Error('directus down'));
    const res = await call(event());
    expect(res.status).toBe(502);
  });
});
