/**
 * Заявка из скачивания КП.
 *
 * Скачивание КП — самый тёплый контакт на сайте: человек назвал организацию,
 * ИНН, телефон и собрал корзину. До сих пор это уходило в коллекцию quotes и
 * письмом менеджеру, а в воронке не появлялось вовсе — канал был невидим.
 *
 * Модуль живёт на стороне сайта, а не в src/crm: фиксация контакта — дело
 * сайта, работа с ним — дело CRM. Граница между ними не нарушается.
 */
import { defaultLeadOwner } from '../config/site';

export interface QuoteLineForLead { sku: string; name: string; qty: number; sum: number }

export interface QuoteForLead {
  attribution?: AttributionFields;
  quoteNo: string;
  buyerCompany: string;
  buyerInn: string;
  contactName: string;
  email: string;
  phone?: string;
  items: QuoteLineForLead[];
  total: number;
  validUntil?: string;
  /**
   * Итог проверки ИНН: сходится ли он с названием организации.
   *
   * Попадает в текст заявки, потому что менеджеру это нужно видеть в самой
   * карточке, а не искать в почте: расхождение имени и номера — первое,
   * о чём спрашивают в звонке.
   */
  innCheck?: string;
}

const rub = (n: number) => `${n.toLocaleString('ru-RU')} ₽`;

/**
 * Поля источника, попадающие в запись заявки.
 *
 * Тип перечислен явно, а не сведён к Record<string, string>: заявка собирается
 * spread-ом, и при безымянном типе поля теряют имена — их нельзя ни прочитать
 * в письме менеджеру, ни проверить компилятором.
 */
export interface AttributionFields {
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  utm_content: string;
  utm_term: string;
  yclid: string;
  gclid: string;
  first_touch_source: string;
  first_touch_ts: string;
  last_touch_source: string;
  landing_path: string;
  ym_client_id: string;
  ga_client_id: string;
}

/** Одно поле касания: строка разумной длины или пусто. */
function touchField(v: unknown): string {
  return typeof v === 'string' ? v.slice(0, 200) : '';
}

/**
 * Источник обращения из тела запроса — общий разбор для заявок и КП.
 *
 * Живёт здесь, а не в каждом обработчике: канал заявки обязан определяться
 * одинаково независимо от того, пришла она из формы или из скачивания КП.
 * Иначе два канала с одним именем окажутся посчитаны по-разному.
 */
export function attributionFields(body: Record<string, unknown>): AttributionFields {
  const a = (body.attribution ?? {}) as Record<string, unknown>;
  const first = (a.first ?? {}) as Record<string, unknown>;
  const last = (a.last ?? {}) as Record<string, unknown>;
  const channel = (t: Record<string, unknown>): string => {
    const src = touchField(t.utm_source);
    const med = touchField(t.utm_medium);
    if (src) return med ? `${src} / ${med}` : src;
    if (t.yclid) return 'yandex / cpc';
    if (t.gclid) return 'google / cpc';
    const ref = touchField(t.referrer);
    if (ref) { try { return `${new URL(ref).hostname} / referral`; } catch { return 'referral'; } }
    return '';
  };
  return {
    utm_source: touchField(last.utm_source),
    utm_medium: touchField(last.utm_medium),
    utm_campaign: touchField(last.utm_campaign),
    utm_content: touchField(last.utm_content),
    utm_term: touchField(last.utm_term),
    yclid: touchField(last.yclid),
    gclid: touchField(last.gclid),
    first_touch_source: channel(first),
    first_touch_ts: touchField(first.ts),
    last_touch_source: channel(last),
    landing_path: touchField(first.landing_path) || touchField(last.landing_path),
    ym_client_id: touchField(a.ym_client_id),
    ga_client_id: touchField(a.ga_client_id),
  };
}

/** Короткая строка состава для колонки «Запрос» в списке заявок. */
export function summarizeItems(items: QuoteLineForLead[]): string {
  if (!items.length) return 'КП без позиций';
  const first = items[0].name;
  return items.length === 1 ? first : `${first} и ещё ${items.length - 1}`;
}

/** Полный состав корзины — его менеджер видит в карточке. */
export function describeQuote(q: QuoteForLead): string {
  const lines = [
    `Клиенту отправлено коммерческое предложение № ${q.quoteNo}.`,
    '',
    'Состав корзины:',
    ...q.items.map((i) => `— ${i.name} (${i.sku}) × ${i.qty} = ${rub(i.sum)}`),
    '',
    `Итого: ${rub(q.total)}.`,
  ];
  if (q.validUntil) lines.push(`Предложение действует до ${q.validUntil}.`);
  // Достоверность заявки — в самой карточке: расхождение имени и номера
  // первое, о чём спрашивают в звонке, и искать это в почте неудобно.
  if (q.innCheck) lines.push('', `Проверка ИНН: ${q.innCheck}`);
  return lines.join('\n');
}

/**
 * Запись для коллекции leads.
 *
 * Стадия — «новая», хотя КП у клиента уже на руках. Так и есть: документ ушёл
 * автоматически, живой человек с заявкой ещё не работал, а срок реакции на
 * новую заявку — два часа, что для скачавшего КП ровно то, что нужно. Двинуть
 * её на «Отправлено КП» менеджер может одним нажатием.
 */
export function leadFromQuote(q: QuoteForLead): Record<string, unknown> {
  return {
    name: q.contactName,
    company: q.buyerCompany,
    inn: q.buyerInn,
    email: q.email,
    phone: q.phone || '',
    message: describeQuote(q),
    product_ref: summarizeItems(q.items),
    consent: true,
    form_source: 'quote',
    source: 'quote',
    ...(q.attribution || {}),
    status: 'new',
    // Ответственный проставляется сразу: заявка без владельца ничья, и о ней
    // забывают. Распоряжение руководителя 21.08.2026 — всегда Беляев Алексей.
    owner: defaultLeadOwner,
    // Сумма известна из корзины: менеджер сразу видит вес сделки в списке.
    amount: q.total,
    quote_no: q.quoteNo,
  };
}
