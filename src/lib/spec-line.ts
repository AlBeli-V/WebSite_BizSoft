/**
 * Строка спецификации для подготовки предложения (`/cart`).
 *
 * Постановка руководителя 15.09.2026 по семи образцам договорных
 * формулировок. Ячейка «Описание» собирается из трёх частей:
 *
 *   1. `<Юридическое название производителя> / <название позиции>`
 *   2. `Артикул: <артикул>`
 *   3. договорная фраза — та самая, что уходит в предмет договора.
 *
 * Фраза не сочиняется под каждую позицию: её вид определяют данные —
 * сегменты артикула (вид, план, срок), форма поставки производителя из
 * реестра `src/data/spec-delivery.json` и признак аренды почты, выбранный
 * покупателем в шапке спецификации. Морфология (год/года/лет, месяц/месяца/
 * месяцев, доллар/доллара/долларов) считается, а не пишется руками: «сроком
 * на 2 календарных года» и «сроком на 5 календарных лет» — одна и та же
 * ветка кода.
 *
 * Модуль чистый: ни сети, ни файлов, ни DOM. Он работает и на сервере (КП),
 * и в браузере (страница спецификации), и покрыт tests/spec-line.test.ts.
 */
import DELIVERY from '../data/spec-delivery.json';
import { vendorBySlug } from '../data/vendors';
import { vendorLegal } from './catalog';
import { TERM, termLabel } from './card-display';
import { EMAIL_RENT_MONTHS, emailRentApplies } from './email-rent';
import { moneyFmt, numberWords, pluralForm } from './rub-words';
import { parseSku, type SkuParts } from './sku';
import { vendorSlug } from './vendor-links';

/** Что именно продаётся — от этого зависит предмет договора в фразе. */
export type SpecKind =
  /** Подписка на сервис или ПО со сроком. */
  | 'subscription'
  /** Ключ активации бессрочной лицензии. */
  | 'activation_key'
  /** Дополнение к основному продукту: плагин, надстройка. */
  | 'addon'
  /** Пополнение баланса, API-кредиты. */
  | 'credits'
  /** Подарочная карта, код пополнения. */
  | 'gift_card'
  /** Услуга производителя: внедрение, обучение, сопровождение. */
  | 'service';

/** Форма поставки: доступ к сервису, к ПО или нейтральный «программный продукт». */
export type DeliveryForm = 'web' | 'software' | 'product';

interface DeliveryRegistry {
  defaultByDomain: Record<string, string>;
  byVendor: Record<string, string>;
  bySku: Record<string, string>;
}
const REGISTRY = DELIVERY as unknown as DeliveryRegistry;

export interface SpecInput {
  sku: string;
  name: string;
  /** Марка производителя (поле `vendor` каталога). */
  vendor?: string | null;
  /** Покупатель выбрал аренду адресов почты в шапке спецификации. */
  emailRent?: boolean;
}

export interface SpecLine {
  /** «Anthropic PBC / Claude Team, Standard seat» */
  title: string;
  /** Артикул без подписи — подпись ставит разметка. */
  sku: string;
  /** Договорная фраза. */
  text: string;
  /** Взята ли в позицию аренда почты — по ней считается цена единицы. */
  emailRent: boolean;
}

/**
 * Форма поставки позиции: сначала точечная правка по артикулу, затем
 * поимённое исключение по производителю, затем умолчание его домена.
 * Производитель, которого нет в реестре лендингов, формы поставки не
 * получает: фраза назовёт позицию «программным продуктом» и не соврёт.
 */
export function deliveryForm(vendor: string | null | undefined, sku: string): DeliveryForm {
  const bySku = REGISTRY.bySku[sku];
  if (bySku === 'web' || bySku === 'software') return bySku;
  if (!vendor) return 'product';
  const slug = vendorSlug(vendor);
  const byVendor = REGISTRY.byVendor[slug];
  if (byVendor === 'web' || byVendor === 'software') return byVendor;
  const entry = vendorBySlug(slug);
  const byDomain = entry ? REGISTRY.defaultByDomain[entry.domain] : undefined;
  return byDomain === 'web' || byDomain === 'software' ? byDomain : 'product';
}

/** Вид позиции для фразы. Решают сегменты артикула, а не похожесть названия. */
export function specKind(sku: string, name: string): SpecKind {
  const p = parseSku(sku);
  if (p) {
    if (p.kind === 'GFT') return 'gift_card';
    if (p.kind === 'CRD') return 'credits';
    if (p.kind === 'SVC') return 'service';
    if (p.term === 'PERP') return 'activation_key';
    return p.kind === 'ADD' ? 'addon' : 'subscription';
  }
  // Позиция без системного артикула страницы не имеет (черновик, архив), но
  // в подборку могла попасть по старой ссылке — разбираем по названию.
  if (/подарочн|gift card/i.test(name)) return 'gift_card';
  if (/пополнение баланса|кредит|credits/i.test(name)) return 'credits';
  if (/бессрочн|вечная лицензия|perpetual/i.test(name)) return 'activation_key';
  return 'subscription';
}

/** Маркеры срока и типа плана в названии: в фразе их место занимают данные. */
const NAME_NOISE: RegExp[] = [
  /,\s*(вечная лицензия|бессрочн(ый|ая)|годов(ая|ой)( подписка)?|\d+\s*(год|года|лет|месяц(а|ев)?))(?=,|\s*\(|$)/gi,
  /\s*\((личная|личная лицензия|индивидуальная|подписка)\)/gi,
  /\s+для (организаций|команд)(?=,|$)/gi,
  /\s+\d[YМ]\b/g,
];

/** Словарь тарифных планов: только то, что действительно является планом. */
const PLAN_WORDS = [
  'Enterprise Pro', 'Enterprise Plus', 'Enterprise Max', 'Business Plus', 'Business Standard',
  'Professional Plus', 'Individual Use', 'Free', 'Starter', 'Basic', 'Standard', 'Plus',
  'Pro', 'Professional', 'Premium', 'Premier', 'Business', 'Team', 'Teams', 'Enterprise',
  'Ultimate', 'Advanced', 'Essentials', 'Expert', 'Max', 'Ultra', 'Elite', 'Growth', 'Scale',
  'Individual', 'Personal', 'Education', 'Academic', 'Commercial', 'Studio', 'Organization',
];

/**
 * Производители, у которых «тарифный план» — это сам продукт линейки:
 * у JetBrains покупают доступ к ПО JetBrains в рамках плана подписки Rider
 * (образец руководителя), а не «Rider в рамках плана JetBrains».
 */
const PLAN_FROM_PRODUCT = new Set(['jetbrains']);

export interface NameParts {
  /** Название предмета договора: «Claude», «Microsoft Visual Studio 2026». */
  product: string;
  /** Тарифный план: «Team», «Enterprise Pro», «Professional». Пусто — плана нет. */
  plan: string;
  /** Тип рабочего места: «Standard seat». Пусто — деления мест нет. */
  seat: string;
}

/**
 * Разобрать название позиции на предмет, план и тип рабочего места.
 *
 * Работает по реальному написанию каталога: «Claude Team, Standard seat»,
 * «Perplexity Enterprise Pro», «ManageEngine ADAudit Plus Professional,
 * 2 контроллера домена». Хвост после запятой, не являющийся типом места
 * (объём пакета, число контроллеров), остаётся при названии предмета: он
 * различает позиции и в договоре обязан сохраниться.
 */
export function parseSpecName(name: string, vendor?: string | null): NameParts {
  let clean = name;
  for (const re of NAME_NOISE) clean = clean.replace(re, '');
  clean = clean.replace(/\s{2,}/g, ' ').replace(/\s+([,)])/g, '$1').trim();

  const parts = clean.split(',').map((s) => s.trim()).filter(Boolean);
  let head = parts.shift() || clean;
  let seat = '';
  const last = parts[parts.length - 1];
  if (last && /^[\w+\-.]+(\s+[\w+\-.]+)?\s+seats?$/i.test(last)) {
    seat = last;
    parts.pop();
  }
  // Объём пакета («2 контроллера домена») различает позиции и в предмете
  // договора обязан остаться — но скобками: через запятую он разрывал фразу
  // перед словами «производства компании».
  const tail = parts.length ? ` (${parts.join(', ')})` : '';

  let plan = '';
  const words = head.split(/\s+/);
  for (const size of [2, 1]) {
    if (words.length <= size) continue; // из одного слова предмет не забираем
    const candidate = words.slice(-size).join(' ');
    if (PLAN_WORDS.some((w) => w.toLowerCase() === candidate.toLowerCase())) {
      plan = candidate;
      head = words.slice(0, -size).join(' ');
      break;
    }
  }
  const slug = vendor ? vendorSlug(vendor) : '';
  if (!plan && slug && PLAN_FROM_PRODUCT.has(slug)) {
    const brand = vendorBySlug(slug)?.title || vendorBySlug(slug)?.vendor || '';
    if (brand && head.toLowerCase().startsWith(brand.toLowerCase()) && head.length > brand.length) {
      plan = head.slice(brand.length).trim();
      head = brand;
    }
  }
  return { product: (head + tail).trim(), plan, seat };
}

/** «12 месяцев» → «1 (один) календарный год»; «5 лет» → «5 (пять) календарных лет». */
function periodPhrase(n: number, forms: [string, string, string]): string {
  const one = n % 10 === 1 && n % 100 !== 11;
  return `${n} (${numberWords(n)}) ${one ? 'календарный' : 'календарных'} ${pluralForm(n, forms)}`;
}

const YEAR_FORMS: [string, string, string] = ['год', 'года', 'лет'];
const MONTH_FORMS: [string, string, string] = ['месяц', 'месяца', 'месяцев'];

/** Срок словами договора: «сроком на 1 (один) календарный год». Пусто — срока в фразе нет. */
export function termPhrase(term: string | null | undefined, kind: SpecKind): string {
  if (!term) return '';
  if (term === TERM.balance) return '';
  if (term === TERM.perpetual) {
    // У ключа активации бессрочность — это и есть предмет («ключ активации»),
    // повторять её оговоркой незачем (образец руководителя).
    return kind === 'activation_key' ? '' : 'на условиях бессрочного использования';
  }
  const years = term.match(/^(\d+)\s*(?:год|года|лет)$/i);
  if (years) return `сроком на ${periodPhrase(Number(years[1]), YEAR_FORMS)}`;
  const months = term.match(/^(\d+)\s*(?:месяц|месяца|месяцев)$/i);
  if (months) return `сроком на ${periodPhrase(Number(months[1]), MONTH_FORMS)}`;
  return '';
}

const CURRENCY_FORMS: Record<string, [string, string, string]> = {
  USD: ['доллар США', 'доллара США', 'долларов США'],
  EUR: ['евро', 'евро', 'евро'],
  RUB: ['рубль', 'рубля', 'рублей'],
  KZT: ['тенге', 'тенге', 'тенге'],
  TRY: ['турецкая лира', 'турецкие лиры', 'турецких лир'],
};
const CURRENCY_SIGNS: Record<string, string> = { $: 'USD', '€': 'EUR', '₽': 'RUB' };

/**
 * Денежный номинал из названия: «пополнение баланса на 100 $» → «100,00
 * долларов США», «Apple Gift Card 1000 RUB» → «1 000,00 рублей». Пусто —
 * номинал не назван: выдумывать сумму в предмете договора нельзя.
 */
export function nominalMoney(name: string): string {
  const money = name.match(/(\d[\d\s\u00a0]*(?:[.,]\d+)?)\s*(\$|€|₽|USD|EUR|RUB|KZT|TRY)(?![\w])/i);
  if (!money) return '';
  const value = Number(money[1].replace(/[\s\u00a0]/g, '').replace(',', '.'));
  const code = (CURRENCY_SIGNS[money[2]] || money[2]).toUpperCase();
  const forms = CURRENCY_FORMS[code];
  return Number.isFinite(value) && forms ? `${moneyFmt(value)} ${pluralForm(value, forms)}` : '';
}

/** «16 000 (шестнадцать тысяч) кредитов»; пусто — кредиты в названии не названы. */
export function nominalCredits(name: string): string {
  const credits = name.match(/(\d[\d\s\u00a0]*)\s*кредит/i);
  if (!credits) return '';
  const value = Number(credits[1].replace(/[\s\u00a0]/g, ''));
  if (!Number.isFinite(value)) return '';
  return `${value.toLocaleString('ru-RU')} (${numberWords(value)}) ${pluralForm(value, ['кредит', 'кредита', 'кредитов'])}`;
}

/** Имя сервиса без приписки пакета: «Kling AI — пакет 16 000 кредитов» → «Kling AI». */
export function baseName(name: string): string {
  return name.split(/\s+[—–-]\s+/)[0].trim();
}

/** Приписка об аренде почты — своя для каждой формы поставки (образцы руководителя). */
function rentClause(kind: SpecKind, form: DeliveryForm): string {
  const head = ', включая предоставление доступа к учетной записи электронной почты сроком на '
    + `${periodPhrase(EMAIL_RENT_MONTHS / 12, YEAR_FORMS)} `;
  return form === 'software'
    ? `${head}для целей регистрации на сайте производителя личного кабинета и активации ${kind === 'addon' ? 'дополнения' : 'подписки'}`
    : `${head}для целей регистрации личного кабинета на сайте производителя`;
}

/** «производства компании Anthropic PBC»; пусто — юрлицо неизвестно. */
function madeBy(legal: string): string {
  return legal ? ` производства компании ${legal}` : '';
}

/** Предмет договора по форме поставки: то, к чему даётся доступ. */
function subject(form: DeliveryForm, product: string): string {
  if (form === 'web') return `web-сервису ${product}`;
  if (form === 'software') return `ПО ${product}`;
  return `программному продукту ${product}`;
}

/** Собрать части в предложение, не оставляя двойных пробелов. */
function join(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ').replace(/\s{2,}/g, ' ').replace(/\s+,/g, ',').trim();
}

/**
 * Договорная фраза позиции. Единственное место, где рождается текст предмета
 * договора: и страница спецификации, и КП берут его отсюда.
 */
export function specText(input: SpecInput): string {
  const { sku, name } = input;
  const vendor = input.vendor || '';
  const legal = vendorLegal(vendor);
  const kind = specKind(sku, name);
  const form = deliveryForm(vendor, sku);
  const { product, plan, seat } = parseSpecName(name, vendor);
  const parsed: SkuParts | null = parseSku(sku);
  const term = termLabel({ sku, name }, kind === 'credits' || kind === 'gift_card' ? 'balance_topup' : kind === 'addon' ? 'addon' : 'unit_subscription');
  const period = termPhrase(term, kind);
  const rent = Boolean(input.emailRent) && emailRentApplies(sku);
  const rentText = rent ? rentClause(kind, form) : '';

  // Тип доступа называется только там, где он различает позиции: тип
  // рабочего места — из названия, индивидуальный доступ — из сегмента плана.
  const access = seat
    ? `, (тип рабочего места — ${seat})`
    : parsed?.plan === 'IND' && kind !== 'credits' && kind !== 'gift_card'
      ? ' (тип доступа — Individual Use)'
      : '';
  const planClause = plan
    ? `${form === 'software' && kind === 'subscription' ? 'в рамках плана подписки' : 'в рамках тарифного плана'} ${plan}${access}`
    : access.replace(/^,\s*/, '');

  switch (kind) {
    case 'activation_key':
      return join(
        `Оказание услуг по предоставлению доступа к ключу активации ПО ${product}${madeBy(legal)}`,
        planClause,
      ) + rentText;
    case 'credits': {
      // Предмет — сам сервис, а не название пакета: «Kling AI — пакет 16 000
      // кредитов» в договоре читается как сервис Kling AI и объём зачисления.
      const service = baseName(name);
      const money = nominalMoney(name);
      const credits = nominalCredits(name);
      const isApi = /\bAPI\b/i.test(service);
      const resource = isApi ? 'вычислительным ресурсам API веб-сервиса' : 'вычислительным ресурсам веб-сервиса';
      // «API веб-сервиса OpenAI API» — слово API дважды: в названии сервиса
      // оно уже сказано предметом фразы.
      const serviceName = isApi ? service.replace(/\s*\bAPI\b\s*/i, ' ').trim() || service : service;
      return join(
        `Оказание информационно-технологических услуг по обеспечению доступа к ${resource} ${serviceName}`,
        money ? `путём зачисления API-кредитов номинальной стоимостью ${money} в личный кабинет Заказчика`
          : credits ? `путём пополнения баланса личного кабинета Заказчика на ${credits}`
            : `путём пополнения баланса личного кабинета Заказчика по пакету «${name}»`,
      ) + rentText;
    }
    case 'gift_card': {
      // «Apple Gift Card 1000 RUB, Россия»: номинал и регион уходят из имени
      // карты в свои места фразы — иначе сумма называется дважды.
      const head = name.split(',')[0].replace(/\s*\d[\d\s\u00a0]*\s*(?:RUB|KZT|TRY|USD|EUR|\$|€)\s*$/i, '').trim();
      const region = name.split(',').slice(1).join(',').trim();
      const nominal = nominalMoney(name);
      return join(
        `Оказание услуг по предоставлению доступа к цифровому коду пополнения баланса ${head || product}`,
        nominal && `номинальной стоимостью ${nominal}`,
        region && `(регион — ${region})`,
        'для зачисления в личный кабинет Заказчика',
      ) + rentText;
    }
    case 'service':
      return join(
        `Оказание услуг${legal ? ` компании ${legal}` : ''} по позиции «${name}»`,
        period,
      ) + rentText;
    case 'addon': {
      // У линейки, где план — это сам продукт (JetBrains), именем дополнения
      // становится план, а основой — марка: «дополнение AEM IDE к ПО JetBrains».
      const addonName = plan || product;
      const base = plan ? product : (vendorBySlug(vendorSlug(vendor))?.title || vendor);
      return join(
        `Оказание услуг по предоставлению доступа к дополнению «${addonName}»`,
        base && `к ${subject(form, base)}`,
        madeBy(legal).trim(),
        access.replace(/^,\s*/, ''),
        period,
      ) + rentText;
    }
    default:
      return join(
        `Оказание услуг по предоставлению доступа к ${subject(form, product)}${madeBy(legal)}`,
        planClause,
        period,
      ) + rentText;
  }
}

/** Три части ячейки «Описание» спецификации. */
export function specLine(input: SpecInput): SpecLine {
  const legal = vendorLegal(input.vendor || '');
  return {
    title: legal ? `${legal} / ${input.name}` : input.name,
    sku: input.sku,
    text: specText(input),
    emailRent: Boolean(input.emailRent) && emailRentApplies(input.sku),
  };
}
