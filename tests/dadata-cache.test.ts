/**
 * Кэш справочника организаций по ИНН.
 *
 * Каждое обращение к DaData платное, а один запрос КП спрашивал справочник
 * об одном и том же ИНН дважды: сверка названия (verifyCompany) и карточка
 * для письма менеджеру (findParty) ходили каждая своим запросом. Проверяем
 * не наличие кэша, а его смысл — второй раз за тот же ИНН мы не платим.
 */
import { describe, expect, it, vi, afterEach } from 'vitest';
import { findParty, partyByInn, type Party } from '../src/lib/dadata';
import { verifyCompany } from '../src/lib/inn';
import { createMemoryStore } from '../src/lib/shared-store';

const sber: Party = {
  value: 'ПАО СБЕРБАНК',
  data: {
    inn: '7707083893', kpp: '773601001', ogrn: '1027700132195', type: 'LEGAL',
    name: { short_with_opf: 'ПАО СБЕРБАНК', full_with_opf: 'ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО "СБЕРБАНК РОССИИ"' },
    address: { value: 'г Москва, ул Вавилова, д 19' },
    management: { name: 'Греф Герман Оскарович', post: 'ПРЕЗИДЕНТ' },
    state: { status: 'ACTIVE' },
  },
};

const reply = (items: Party[]) => ({ ok: true, json: async () => ({ suggestions: items }) });
const stubDadata = (items: Party[] = [sber]) => {
  const spy = vi.fn(async () => reply(items));
  vi.stubGlobal('fetch', spy);
  return spy;
};

afterEach(() => vi.unstubAllGlobals());

describe('кэш по ИНН', () => {
  it('повторный запрос того же ИНН не стоит денег', async () => {
    const spy = stubDadata();
    const store = createMemoryStore();
    expect((await findParty('7707083893', 'ключ', store))?.inn).toBe('7707083893');
    expect((await findParty('7707083893', 'ключ', store))?.inn).toBe('7707083893');
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it('один запрос КП спрашивает справочник об ИНН один раз, а не два', async () => {
    // Так ходит /api/quote: сначала сверка названия, потом карточка в письмо.
    const spy = stubDadata();
    const store = createMemoryStore();

    const check = await verifyCompany('7707083893', 'ПАО СБЕРБАНК', 'ключ', store);
    const card = await findParty('7707083893', 'ключ', store);

    expect(spy).toHaveBeenCalledTimes(1);
    // Вердикт и карточка при этом остались прежними — кэш ничего не «упростил».
    expect(check.nameMatch).toBe('match');
    expect(check.registryName).toBe('ПАО СБЕРБАНК');
    expect(card?.manager).toContain('Греф');
    expect(card?.active).toBe(true);
  });

  it('разные ИНН кэш не смешивает', async () => {
    const spy = stubDadata();
    const store = createMemoryStore();
    await findParty('7707083893', 'ключ', store);
    await findParty('7736050003', 'ключ', store);
    expect(spy).toHaveBeenCalledTimes(2);
  });

  it('пробелы и дефисы не создают второй ключ на ту же организацию', async () => {
    const spy = stubDadata();
    const store = createMemoryStore();
    await findParty('7707083893', 'ключ', store);
    await findParty(' 7707-083-893 ', 'ключ', store);
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it('«не найдено» тоже запоминается — перебор несуществующих ИНН платный', async () => {
    const spy = stubDadata([]);
    const store = createMemoryStore();
    expect(await findParty('7728168971', 'ключ', store)).toBeNull();
    expect(await findParty('7728168971', 'ключ', store)).toBeNull();
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it('ошибка справочника не кэшируется — иначе сбой минуты запомнился бы на сутки', async () => {
    const store = createMemoryStore();
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('таймаут'); }));
    await expect(partyByInn('7707083893', 'ключ', store)).rejects.toThrow();

    const spy = stubDadata();
    expect((await partyByInn('7707083893', 'ключ', store))?.value).toBe('ПАО СБЕРБАНК');
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it('сбой хранилища не ломает справочник — просто нет экономии', async () => {
    const spy = stubDadata();
    const broken = {
      get: async () => null,
      set: async () => { throw new Error('база недоступна'); },
      incr: async () => null,
    };
    // Хранилище недоступно — справочник обязан ответить как раньше, просто
    // без экономии: каждый вызов снова платный.
    expect((await findParty('7707083893', 'ключ', broken))?.inn).toBe('7707083893');
    expect((await findParty('7707083893', 'ключ', broken))?.inn).toBe('7707083893');
    expect(spy).toHaveBeenCalledTimes(2);
  });
});
