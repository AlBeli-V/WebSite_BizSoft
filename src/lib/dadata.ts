/**
 * Справочник организаций DaData.
 *
 * Две задачи. Первая — снять с заказчика заполнение реквизитов: он вводит
 * название или ИНН, выбирает свою организацию из списка, остальное
 * подставляется. Ошибиться в десятизначном номере проще, чем не ошибиться,
 * а исправлять придётся уже в счёте.
 *
 * Вторая — дать менеджеру карточку организации до звонка: полное название,
 * руководитель, адрес, статус. Заявка от ликвидированной компании и заявка
 * от действующей выглядят в форме одинаково.
 *
 * Ключ живёт на сервере и в браузер не попадает: запросы идут через наш
 * прокси /api/suggest/party. DaData допускает клиентский ключ с
 * ограничением по домену, но ограничение задаётся в чужом кабинете и
 * незаметно снимается, а утёкший ключ расходует наш суточный лимит.
 */

import { sharedStore, type SharedStore } from './shared-store';

const SUGGEST_URL = 'https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party';
const FIND_URL = 'https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party';

/** Ответ справочника — только те поля, которые мы действительно используем. */
export interface PartyData {
  inn?: string;
  kpp?: string;
  ogrn?: string;
  ogrn_date?: number;
  type?: 'LEGAL' | 'INDIVIDUAL';
  name?: { full_with_opf?: string; short_with_opf?: string };
  address?: { value?: string; unrestricted_value?: string };
  management?: { name?: string; post?: string };
  okved?: string;
  state?: { status?: string; actuality_date?: number; registration_date?: number };
}

export interface Party {
  value: string;
  data: PartyData;
}

/** Организация в виде, пригодном для формы и письма. */
export interface PartyCard {
  name: string;
  fullName: string;
  inn: string;
  kpp: string;
  ogrn: string;
  address: string;
  manager: string;
  status: string;
  /** Действующая ли организация. Ликвидированная — повод не начинать сделку. */
  active: boolean;
  registeredOn: string;
  okved: string;
}

const STATUS_RU: Record<string, string> = {
  ACTIVE: 'действующая',
  LIQUIDATING: 'в процессе ликвидации',
  LIQUIDATED: 'ликвидирована',
  BANKRUPT: 'банкротство',
  REORGANIZING: 'в процессе реорганизации',
};

const asDate = (ms?: number): string =>
  ms ? new Date(ms).toLocaleDateString('ru-RU') : '';

export function toCard(p: Party): PartyCard {
  const d = p.data || {};
  const status = d.state?.status || '';
  return {
    name: d.name?.short_with_opf || p.value || '',
    fullName: d.name?.full_with_opf || p.value || '',
    inn: d.inn || '',
    kpp: d.kpp || '',
    ogrn: d.ogrn || '',
    address: d.address?.unrestricted_value || d.address?.value || '',
    manager: [d.management?.name, d.management?.post].filter(Boolean).join(', '),
    status: STATUS_RU[status] || status.toLowerCase() || 'статус неизвестен',
    active: status === 'ACTIVE',
    registeredOn: asDate(d.state?.registration_date || d.ogrn_date),
    okved: d.okved || '',
  };
}

async function ask(url: string, body: unknown, token: string): Promise<Party[]> {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      Authorization: `Token ${token}`,
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(5000),
  });
  if (!res.ok) throw new Error(`DaData HTTP ${res.status}`);
  const data = await res.json() as { suggestions?: Party[] };
  return data.suggestions || [];
}

/**
 * Подсказки по названию или ИНН.
 *
 * Ликвидированные не предлагаем: подставить в счёт компанию, которой уже нет,
 * — гарантированная переделка документов. Найти её по прямому запросу ИНН
 * по-прежнему можно, и тогда менеджер увидит статус в карточке.
 */
export async function suggestParty(
  query: string,
  token = process.env.DADATA_TOKEN || '',
  count = 7,
): Promise<PartyCard[]> {
  const q = String(query || '').trim();
  if (!token || q.length < 3) return [];
  const parties = await ask(SUGGEST_URL, {
    query: q,
    count: Math.min(20, Math.max(1, count)),
    status: ['ACTIVE'],
  }, token);
  return parties.map(toCard);
}

/**
 * Сколько живёт закэшированный ответ по ИНН.
 *
 * Реквизиты организации меняются раз в годы, а платим мы за каждый запрос.
 * Сутки — компромисс: перевыпуск КП в тот же день не стоит ничего, а
 * смена названия или статуса доедет до нас не позже следующего утра.
 */
const PARTY_TTL_SEC = Number(process.env.DADATA_CACHE_TTL_SEC ?? 24 * 60 * 60);

/** Кэшируем и «не найдено» — иначе перебор несуществующих ИНН платный. */
interface CachedParty { party: Party | null }

/**
 * Организация по ИНН — с кэшем в общем хранилище.
 *
 * Один запрос КП дважды спрашивал справочник об одном и том же ИНН: сверка
 * названия (verifyCompany) и карточка для письма (findParty) ходили каждая
 * своим fetch. Теперь обе идут сюда, и повторное обращение — хоть в том же
 * запросе, хоть завтра с другого инстанса — денег не стоит.
 *
 * Сбой хранилища не мешает: кэш промахивается, справочник отвечает как
 * раньше.
 */
export async function partyByInn(
  inn: string,
  token = process.env.DADATA_TOKEN || '',
  store: SharedStore = sharedStore(),
): Promise<Party | null> {
  const q = String(inn || '').replace(/[\s-]/g, '');
  if (!token || !q) return null;

  const key = `dadata-party-${q}`;
  // Кэш — оптимизация, а не условие работы: его сбой не должен превращаться
  // в отказ справочника, поэтому обе операции хранилища подстрахованы.
  const hit = await store.get<CachedParty>(key).catch(() => null);
  if (hit && typeof hit === 'object' && 'party' in hit) return hit.party;

  const parties = await ask(FIND_URL, { query: q, count: 1 }, token);
  const party = parties.length ? parties[0] : null;
  // Ошибку справочника не кэшируем: она уже улетела исключением выше.
  await store.set(key, { party } satisfies CachedParty, PARTY_TTL_SEC).catch(() => {});
  return party;
}

/** Организация по ИНН или ОГРН. Статус возвращается любой — он и нужен. */
export async function findParty(
  inn: string,
  token = process.env.DADATA_TOKEN || '',
  store: SharedStore = sharedStore(),
): Promise<PartyCard | null> {
  const party = await partyByInn(inn, token, store);
  return party ? toCard(party) : null;
}

/** Карточка организации для письма менеджеру. */
export function cardLines(c: PartyCard): string[] {
  const lines = [
    `Организация: ${c.fullName}`,
    `ИНН/КПП: ${c.inn}${c.kpp ? ` / ${c.kpp}` : ''}${c.ogrn ? `, ОГРН ${c.ogrn}` : ''}`,
  ];
  if (c.address) lines.push(`Адрес: ${c.address}`);
  if (c.manager) lines.push(`Руководитель: ${c.manager}`);
  lines.push(`Статус: ${c.status}${c.registeredOn ? `, в реестре с ${c.registeredOn}` : ''}`);
  if (c.okved) lines.push(`Основной вид деятельности: ${c.okved}`);
  return lines;
}
