/**
 * Справочник организаций: подстановка реквизитов и карточка для менеджера.
 *
 * Проверяется главное: подсказки — удобство, а не условие работы формы.
 * Справочник молчит или отвечает мусором — заявка всё равно принимается,
 * человек заполняет поля руками, как раньше.
 */
import { describe, expect, it, vi, afterEach } from 'vitest';
import { toCard, cardLines, suggestParty, findParty, type Party } from '../src/lib/dadata';

const sber: Party = {
  value: 'ПАО СБЕРБАНК',
  data: {
    inn: '7707083893', kpp: '773601001', ogrn: '1027700132195', type: 'LEGAL',
    name: { short_with_opf: 'ПАО СБЕРБАНК', full_with_opf: 'ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО "СБЕРБАНК РОССИИ"' },
    address: { value: 'г Москва, ул Вавилова, д 19' },
    management: { name: 'Греф Герман Оскарович', post: 'ПРЕЗИДЕНТ, ПРЕДСЕДАТЕЛЬ ПРАВЛЕНИЯ' },
    okved: '64.19', state: { status: 'ACTIVE', registration_date: 1027000000000 },
  },
};

const reply = (items: Party[]) => ({ ok: true, json: async () => ({ suggestions: items }) });
afterEach(() => vi.unstubAllGlobals());

describe('карточка организации', () => {
  it('собирает реквизиты, руководителя и статус', () => {
    const c = toCard(sber);
    expect(c.inn).toBe('7707083893');
    expect(c.kpp).toBe('773601001');
    expect(c.manager).toContain('Греф');
    expect(c.active).toBe(true);
    expect(c.status).toBe('действующая');
  });

  it('статус переводится на русский, а не остаётся кодом', () => {
    const dead = { ...sber, data: { ...sber.data, state: { status: 'LIQUIDATED' } } };
    const c = toCard(dead);
    expect(c.status).toBe('ликвидирована');
    expect(c.active).toBe(false);
  });

  it('неизвестный статус не выдаётся за действующую организацию', () => {
    const odd = { ...sber, data: { ...sber.data, state: { status: 'СТРАННОЕ' } } };
    expect(toCard(odd).active).toBe(false);
  });

  it('пустые поля не превращаются в пустые строки письма', () => {
    const bare = toCard({ value: 'ООО РОМАШКА', data: { inn: '7707083893' } });
    const lines = cardLines(bare);
    expect(lines.some((l) => l.startsWith('Адрес:'))).toBe(false);
    expect(lines.some((l) => l.startsWith('Руководитель:'))).toBe(false);
    expect(lines.join(' ')).toContain('7707083893');
  });
});

describe('подсказки', () => {
  it('короткий запрос не идёт в справочник — лимит общий на все подсказки', async () => {
    const spy = vi.fn();
    vi.stubGlobal('fetch', spy);
    expect(await suggestParty('ро', 'ключ')).toEqual([]);
    expect(spy).not.toHaveBeenCalled();
  });

  it('без ключа подсказки просто не работают, а не падают', async () => {
    const spy = vi.fn();
    vi.stubGlobal('fetch', spy);
    expect(await suggestParty('ромашка', '')).toEqual([]);
    expect(spy).not.toHaveBeenCalled();
  });

  it('ликвидированные не предлагаются к подстановке', async () => {
    // Подставить в счёт компанию, которой уже нет, — гарантированная
    // переделка документов.
    const spy = vi.fn(async () => reply([sber]));
    vi.stubGlobal('fetch', spy);
    await suggestParty('сбербанк', 'ключ');
    const body = JSON.parse((spy.mock.calls[0] as any[])[1].body);
    expect(body.status).toEqual(['ACTIVE']);
  });

  it('поиск по ИНН возвращает организацию с любым статусом', async () => {
    // Здесь статус как раз и нужен: менеджер должен увидеть, что она мертва.
    const spy = vi.fn(async () => reply([{ ...sber, data: { ...sber.data, state: { status: 'LIQUIDATED' } } }]));
    vi.stubGlobal('fetch', spy);
    const c = await findParty('7707083893', 'ключ');
    expect(c?.active).toBe(false);
    const body = JSON.parse((spy.mock.calls[0] as any[])[1].body);
    expect(body.status).toBeUndefined();
  });

  it('пробелы и дефисы в ИНН не мешают поиску', async () => {
    const spy = vi.fn(async () => reply([sber]));
    vi.stubGlobal('fetch', spy);
    await findParty(' 7707-083-893 ', 'ключ');
    expect(JSON.parse((spy.mock.calls[0] as any[])[1].body).query).toBe('7707083893');
  });

  it('ошибка справочника не роняет вызов', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('таймаут'); }));
    await expect(suggestParty('ромашка', 'ключ')).rejects.toThrow();
    // Вызывающий код обязан ловить: проверяем, что он это делает.
    const api = (await import('node:fs')).readFileSync('src/pages/api/suggest/party.ts', 'utf8');
    expect(api).toContain('catch');
    expect(api).toContain('unavailable');
  });
});

describe('форма заявки', () => {
  const page = require('node:fs').readFileSync('src/components/QuoteDialog.astro', 'utf8');

  it('подставленные реквизиты остаются доступны для правки', () => {
    // Филиал, недавнее переименование, работа под другим названием —
    // справочник знает это хуже, чем сам заказчик.
    expect(page).not.toMatch(/data-inn[^>]*readonly/);
    expect(page).not.toMatch(/data-company[^>]*readonly/);
    expect(page).toContain('Проверьте и при необходимости поправьте поля');
  });

  it('запрос идёт через наш прокси, а ключ не попадает в браузер', () => {
    expect(page).toContain('/api/suggest/party');
    expect(page).not.toMatch(/suggestions\.dadata\.ru/);
    expect(page).not.toMatch(/Authorization|Token /);
  });

  it('запрос не уходит на каждую букву', () => {
    expect(page).toMatch(/setTimeout\(async/);
    expect(page).toMatch(/clearTimeout/);
  });

  it('ответ на устаревший запрос не перезатирает свежий', () => {
    expect(page).toContain('if (mine !== seq) return;');
  });
});
