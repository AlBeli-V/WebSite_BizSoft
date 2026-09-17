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
  /** Экономика сделки из расчёта КП — когда её удалось посчитать. */
  economics?: LeadEconomics;
  /** Ссылки на события журнала согласий, по которым принят запрос КП. */
  consent?: { personalDataEventId: string; marketingEventId: string | null };
}

/**
 * Экономика сделки в заявке (P1, решение руководителя 28.08.2026).
 *
 * Поля перечислены отдельной константой не для красоты: до применения схемы
 * на проде Directus отвергает запись с незнакомыми полями целиком, и заявка
 * терялась бы. По этому списку обработчик повторяет запись без экономики —
 * контакт важнее, чем маржа в карточке.
 */
export const LEAD_ECONOMICS_FIELDS = [
  'quote_cost_rub', 'quote_margin_rub', 'quote_margin_pct', 'quote_fx_rate',
] as const;

export interface LeadEconomics {
  /** Закупка по КП, ₽; null — данных не хватило. */
  costRub: number | null;
  /** Расчётная прибыль, ₽. */
  marginRub: number;
  /** Прибыль, % от выручки. */
  marginPct: number;
  /** Курс ЦБ USD на момент расчёта. */
  fxRate: number | null;
  /** true — закупка посчитана не по всем позициям, прибыль завышена. */
  incomplete: boolean;
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
  /**
   * Полные адреса переходов. Хоста мало: yandex.ru отдаёт и выдачу, и
   * карточку организации в Яндекс Бизнесе, и Дзен — по строке «yandex.ru /
   * referral» эти три источника неразличимы, а руководителю нужен именно
   * этот разбор (решение 10.09.2026).
   */
  first_touch_referrer: string;
  last_touch_referrer: string;
  /**
   * Шаги посетителя по сайту, записанные браузером: «дата и время~страница»
   * через «|». Метрика тот же путь отдаёт с задержкой, а письмо о заявке
   * уходит в ту же секунду — цепочка из браузера закрывает разрыв.
   */
  visit_path: string;
}

/**
 * Поля источника, которых на проде может не быть до прогона
 * ops-directus-schema. Directus отвергает запись с незнакомым полем целиком,
 * поэтому обработчик повторяет её без них: контакт важнее разбора канала.
 */
/**
 * Ссылки на события журнала согласий в карточке заявки.
 *
 * В списке необязательных намеренно: если прод отстал по схеме, заявка
 * должна сохраниться без ссылки, а не потеряться. Само доказательство от
 * этого не страдает — событие уже записано в consent_audit_log до создания
 * заявки, и найти его можно по адресу и времени.
 */
export const LEAD_CONSENT_FIELDS = [
  'consent_event_id', 'marketing_consent', 'marketing_consent_event_id',
] as const;

export const ATTRIBUTION_EXTRA_FIELDS = [
  'first_touch_referrer', 'last_touch_referrer', 'visit_path',
] as const;

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
    // Реферер режется длиннее прочих полей: у выдачи и у карточки организации
    // значащая часть адреса стоит после хоста, и обрезка по 200 символам
    // отрезала бы как раз её.
    first_touch_referrer: typeof first.referrer === 'string' ? first.referrer.slice(0, 500) : '',
    last_touch_referrer: typeof last.referrer === 'string' ? last.referrer.slice(0, 500) : '',
    visit_path: typeof a.visit_path === 'string' ? a.visit_path.slice(0, 1000) : '',
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
  // Экономика — тоже в карточке: менеджер решает «звонить сейчас или нет»
  // по прибыли сделки, а не только по обороту.
  if (q.economics) {
    lines.push('', `Расчётная прибыль: ${rub(q.economics.marginRub)} (${q.economics.marginPct}% от выручки)`
      + (q.economics.incomplete ? ' — закупка посчитана не по всем позициям, прибыль завышена.' : '.'));
  }
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
    // Ссылки на события журнала — те же, что у заявки с обычной формы.
    ...(q.consent ? {
      consent_event_id: q.consent.personalDataEventId,
      marketing_consent: Boolean(q.consent.marketingEventId),
      marketing_consent_event_id: q.consent.marketingEventId,
    } : {}),
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
    ...(q.economics ? {
      quote_cost_rub: q.economics.costRub,
      quote_margin_rub: q.economics.marginRub,
      quote_margin_pct: q.economics.marginPct,
      quote_fx_rate: q.economics.fxRate,
    } : {}),
  };
}
