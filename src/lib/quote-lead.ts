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
    source: 'quote',
    status: 'new',
    // Ответственный проставляется сразу: заявка без владельца ничья, и о ней
    // забывают. Распоряжение руководителя 21.08.2026 — всегда Беляев Алексей.
    owner: defaultLeadOwner,
    // Сумма известна из корзины: менеджер сразу видит вес сделки в списке.
    amount: q.total,
    quote_no: q.quoteNo,
  };
}
