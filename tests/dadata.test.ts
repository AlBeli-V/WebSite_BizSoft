import { describe, expect, it, vi, afterEach } from 'vitest';
import { verifyCompany } from '../src/lib/inn';

/** Ответ DaData в реальном формате — по документации findById/party. */
const reply = (value: string) => ({
  ok: true,
  json: async () => ({ suggestions: [{ value, data: { inn: '7707083893' } }] }),
});

afterEach(() => vi.unstubAllGlobals());

describe('сверка с ЕГРЮЛ на живом формате ответа', () => {
  it('название сходится', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => reply('ПАО СБЕРБАНК')));
    const r = await verifyCompany('7707083893', 'ПАО «Сбербанк»', 'ключ');
    expect(r.nameMatch).toBe('match');
    expect(r.verdict).toContain('сходятся');
  });

  it('заказчик назвался чужой компанией', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => reply('ПАО СБЕРБАНК')));
    const r = await verifyCompany('7707083893', 'ООО «Ромашка»', 'ключ');
    expect(r.nameMatch).toBe('mismatch');
    expect(r.verdict).toContain('не сходится');
    expect(r.verdict).toContain('ПАО СБЕРБАНК');
  });

  it('ИНН действителен, но в реестре не найден', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({ suggestions: [] }) })));
    const r = await verifyCompany('7707083893', 'ООО «Ромашка»', 'ключ');
    expect(r.verdict).toContain('не найден');
  });

  it('справочник недоступен — говорим об этом, а не молчим', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('timeout'); }));
    const r = await verifyCompany('7707083893', 'ООО «Ромашка»', 'ключ');
    expect(r.nameMatch).toBe('not_checked');
    expect(r.verdict).toContain('не ответил');
  });

  it('форма собственности не мешает совпадению', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => reply('ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "РОМАШКА"')));
    const r = await verifyCompany('7707083893', 'ООО Ромашка', 'ключ');
    expect(r.nameMatch).toBe('match');
  });
});
