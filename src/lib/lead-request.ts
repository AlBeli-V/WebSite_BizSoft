/**
 * Разбор обращения: что именно человек просит, и есть ли это у нас.
 *
 * Зачем. Заявка приходит свободным текстом («Требуется закупка 3-х лицензий
 * Perplexity Personal PRO на 6 месяцев»), а форма кладёт в заявку одну
 * строку вида «количество: 3». Ни менеджер в своём письме, ни заказчик в
 * подтверждении не видят из этого ни производителя, ни продукта, ни срока.
 * Здесь обращение сопоставляется с каталогом — и результат делится на две
 * части: подтверждённое (его можно показать заказчику) и наблюдения
 * (они уходят менеджеру).
 *
 * Главное правило: **молчание лучше ошибки**. Письмо заказчику называет
 * позицию только тогда, когда совпадение однозначно. Разбор 21.09.2026 на
 * настоящей заявке показал цену обратного: в каталоге нет Perplexity
 * Personal Pro, есть Enterprise Pro и Enterprise Max, и нестрогий поиск
 * (`searchProducts` с ИЛИ-фолбэком) уверенно «находит» Enterprise Pro по
 * двум общим словам. Заказчик получил бы письмо, подтверждающее заказ
 * продукта, которого он не просил и который стоит кратно дороже.
 *
 * Разбор детерминированный и локальный: реестр вендоров, каталог и словари
 * сроков. Ни одной внешней службы — текст обращения содержит персональные
 * данные и за периметр не уходит; ни одной ссылки из самого текста —
 * адреса берутся только по найденному в каталоге слагу.
 */
import { VENDORS, vendorByName } from '../data/vendors';
import { isVariant } from './catalog';
import type { LeadCartItem } from './quote-lead';
import { parseSku } from './sku';
import { searchProducts } from './product-search';
import type { Product } from './types';

/** Тип лицензии для письма — из сегмента ПЛАН артикула, не из названия. */
export type RequestPlan = 'team' | 'individual' | 'universal';

export interface RequestTerm {
  /** Срок в месяцах, как его назвал клиент. */
  months: number;
  /** Та же величина словами для письма: «6 месяцев». */
  label: string;
}

export interface LeadRequestSource {
  /** Скрытое поле формы: «количество: 3», «Creative Cloud Pro · количество: 5». */
  productRef?: string;
  /** Текст обращения. */
  message?: string;
  /**
   * Состав подборки на момент обращения. Главный источник: артикулы уже
   * названы самим покупателем, и гадать по тексту поверх них незачем.
   */
  cart?: LeadCartItem[];
}

export interface IdentifiedRequest {
  /** Производитель — только если он есть в нашем реестре. */
  vendor?: string;
  /** Название позиции каталога. */
  product?: string;
  /** Тип лицензии найденной позиции. */
  plan?: RequestPlan;
  /** Количество: из поля формы, иначе из текста. */
  qty?: string;
  /** Найденная позиция — источник ссылок письма. */
  matched?: Product;
  /** Другой план того же продукта: командный против личного. */
  alternative?: Product;
}

export interface LeadRequestReview {
  /** Разобранное однозначно — это и уходит заказчику. */
  request: IdentifiedRequest;
  /**
   * Что менеджеру нужно знать до расчёта: близкие, но не подтверждённые
   * позиции, запрошенный срок вне номенклатуры, расхождение типа плана,
   * прямой вопрос в обращении. Заказчику ничего из этого не показывается.
   */
  notes: string[];
  /** Близкие позиции, которыми нельзя подтвердить запрос. */
  candidates: Product[];
  /** Срок, названный клиентом. */
  term?: RequestTerm;
  /** В обращении есть прямой вопрос — на него отвечает человек. */
  hasQuestion: boolean;
}

const norm = (s: string) => s.toLowerCase().replace(/ё/g, 'е').replace(/\s+/g, ' ').trim();

/**
 * Слова, которые в названии позиции ничего не различают. Без их отсева
 * «3 лицензии Perplexity» требовало бы слова «лицензия» в карточке.
 */
const STOP = new Set([
  'лицензия', 'лицензии', 'лицензий', 'подписка', 'подписки', 'подписку',
  'тариф', 'план', 'план;', 'продукт', 'сервис', 'доступ', 'для', 'на', 'по',
  'шт', 'штук', 'мест', 'место', 'пользователей', 'пользователя',
]);

/** Хвост названия: слова, которые могут стоять после имени вендора. */
const NAME_WORD = /^[A-Za-z][A-Za-z0-9+.-]*$/;

/** Производитель из реестра — по названию или слагу, целым словом. */
export function detectVendor(text: string): string | undefined {
  const hay = norm(text);
  // Длинные имена проверяются раньше коротких: «Adobe Express» не должен
  // опознаваться как «Adobe», когда в реестре есть обе марки.
  const byLength = [...VENDORS].sort((a, b) => b.vendor.length - a.vendor.length);
  for (const v of byLength) {
    for (const needle of [v.vendor, v.slug]) {
      const n = norm(needle);
      if (n.length < 3) continue;
      const re = new RegExp(`(^|[^\\p{L}\\p{N}])${n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}([^\\p{L}\\p{N}]|$)`, 'u');
      if (re.test(hay)) return v.vendor;
    }
  }
  return undefined;
}

/**
 * Кандидат-название из текста: имя вендора и следующие за ним латинские
 * слова («Perplexity Personal PRO»). Дальше русского слова или числа
 * название не тянется — там уже условия заказа, а не имя продукта.
 */
export function productPhrase(text: string, vendor: string): string | undefined {
  const words = text.split(/\s+/);
  const i = words.findIndex((w) => norm(w).replace(/[^\p{L}\p{N}]/gu, '').startsWith(norm(vendor).split(' ')[0]));
  if (i < 0) return undefined;
  const tail: string[] = [];
  for (const w of words.slice(i + 1, i + 5)) {
    // Точка и дефис внутри слова осмысленны («v1.2», «Add-on»), но хвостовые
    // — это пунктуация предложения: без их отсечения «Pro.» уходит в поиск
    // отдельным токеном и не находит ничего.
    const clean = w.replace(/[^\p{L}\p{N}+.-]/gu, '').replace(/[.\-]+$/, '');
    if (!clean || !NAME_WORD.test(clean)) break;
    tail.push(clean);
  }
  return [vendor, ...tail].join(' ');
}

/**
 * Название продукта без имени марки: в письме марка уже стоит строкой выше,
 * и «Perplexity Perplexity Personal PRO» читалось бы как опечатка.
 */
export function withoutVendor(phrase: string, vendor: string): string {
  const cut = phrase.replace(new RegExp(`^${vendor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*`, 'iu'), '');
  return cut.trim() || phrase;
}

/** Срок из текста: «на 6 месяцев», «на год», «12 мес». */
export function detectTerm(text: string): RequestTerm | undefined {
  const hay = norm(text);
  const m = hay.match(/(\d{1,2})\s*(?:мес|месяц)/);
  if (m) {
    const months = Number(m[1]);
    const word = months === 1 ? 'месяц' : months < 5 ? 'месяца' : 'месяцев';
    return { months, label: `${months} ${word}` };
  }
  if (/(^|[^\p{L}])(на\s+год|годов(ая|ую|ой)|12\s*мес)([^\p{L}]|$)/u.test(hay)) {
    return { months: 12, label: '1 год' };
  }
  return undefined;
}

/**
 * Тип лицензии по словам обращения.
 *
 * Это не догадка по названию, а чтение того, что человек написал: «Personal
 * PRO» и «для команд» — различитель плана, который вендоры ставят в имя
 * тарифа сами. Подтверждённая позиция каталога всё равно главнее: там тип
 * берётся из сегмента ПЛАН артикула.
 */
export function detectPlanWords(text: string): RequestPlan | undefined {
  const hay = norm(text);
  const has = (re: string) => new RegExp(`(^|[^\\p{L}])(${re})`, 'u').test(hay);
  if (has('personal|individual|индивидуальн|персональн|личн')) return 'individual';
  if (has('team|business|enterprise|командн|корпоративн|для команд')) return 'team';
  return undefined;
}

/** Количество: поле формы главнее текста — его посетитель выставлял руками. */
export function detectQty(source: LeadRequestSource): string | undefined {
  const ref = source.productRef || '';
  const fromRef = ref.match(/кол(?:ичество|-во)\s*:?\s*(\d+)/i);
  if (fromRef) return fromRef[1];
  const text = source.message || '';
  const m = text.match(/(\d{1,4})\s*[- ]?х?\s*(?:лиценз|подписк|мест|польз|шт)/i);
  return m?.[1];
}

/** План позиции по сегменту артикула. */
export function planOf(p: Product): RequestPlan | undefined {
  const parsed = parseSku(p.sku || '');
  if (!parsed) return undefined;
  return parsed.plan === 'TEAM' ? 'team' : parsed.plan === 'IND' ? 'individual' : 'universal';
}

/**
 * Строгое совпадение: каждое значимое слово запроса стоит в карточке.
 *
 * `searchProducts` при неудаче отдаёт близкое по одному слову — для
 * страницы поиска это правильно, для письма недопустимо. Поэтому результат
 * поиска здесь ещё раз просеивается по И-логике.
 */
function strictMatches(products: Product[], phrase: string): Product[] {
  const toks = norm(phrase).split(/[^\p{L}\p{N}.+-]+/u).filter((t) => t.length >= 2 && !STOP.has(t));
  if (!toks.length) return [];
  return searchProducts(products, phrase).filter((p) => {
    const hay = norm(`${p.name} ${p.vendor || ''} ${p.keywords || ''} ${p.sku}`);
    return toks.every((t) => hay.includes(t));
  });
}

/**
 * Позиция подборки в каталоге. Совпадение по артикулу, а не по названию:
 * название клиент видел на витрине, но в письмо должно попасть то, что
 * каталог отдаёт сейчас — цена, план и страница берутся из карточки.
 */
function pickFromCart(products: Product[], cart?: LeadCartItem[]): Product | undefined {
  for (const item of cart || []) {
    const found = products.find((p) => p.sku && item.sku && p.sku === item.sku);
    if (found) return found;
  }
  return undefined;
}

/** Другой план того же продукта: тот же вендор и код продукта, иной ПЛАН. */
function findAlternative(products: Product[], matched: Product): Product | undefined {
  const base = parseSku(matched.sku || '');
  if (!base) return undefined;
  return products.find((p) => {
    if (p.slug === matched.slug) return false;
    const s = parseSku(p.sku || '');
    return !!s && s.vendor === base.vendor && s.product === base.product && s.plan !== base.plan;
  });
}

/**
 * Разбор обращения по каталогу.
 *
 * Возвращает подтверждённую часть (для письма заказчику) и наблюдения
 * (для письма менеджеру). Пустой разбор — штатный исход, а не сбой:
 * заявка из общей формы часто не называет продукт вовсе.
 */
export function identifyRequest(all: Product[], source: LeadRequestSource): LeadRequestReview {
  // Из письма нельзя вести только туда, где страницы нет: вариант-номинал
  // подарочной карты отдаёт 301 на родителя. Снятые с витрины сюда не
  // доходят — каталог читается фильтром status=published.
  //
  // `productNoindex` здесь намеренно не применяется. Он закрывает от
  // поисковиков индивидуальные планы (все, кроме TryHackMe) — но письмо не
  // поисковик, страница жива и по ней покупают. Фильтруя по нему, мы
  // отрезали бы ровно те личные лицензии, за которыми человек и пришёл:
  // заявка 21.09.2026 просила именно личный план.
  const products = all.filter((p) => !isVariant(p));
  const text = `${source.productRef || ''} ${source.message || ''}`.trim();
  const review: LeadRequestReview = {
    request: {},
    notes: [],
    candidates: [],
    term: detectTerm(text),
    hasQuestion: /\?/.test(source.message || ''),
  };
  const qty = detectQty(source);
  if (qty) review.request.qty = qty;

  // Источник первый: подборка. Позиция из неё не нуждается в разборе —
  // покупатель положил её сам, артикул точный.
  const picked = pickFromCart(products, source.cart);
  if (picked) {
    review.request.vendor = picked.vendor || detectVendor(text);
    review.request.product = picked.name;
    review.request.matched = picked;
    review.request.plan = planOf(picked) || detectPlanWords(text);
    review.request.alternative = findAlternative(products, picked);
    if (!review.request.qty) {
      const line = (source.cart || []).find((i) => i.sku === picked.sku);
      if (line?.qty) review.request.qty = String(line.qty);
    }
    if ((source.cart || []).length > 1) {
      review.notes.push(`В подборке ${source.cart!.length} позиции — письмо называет первую.`);
    }
    if (review.hasQuestion) {
      review.notes.push('В обращении есть прямой вопрос — нужен ответ человека.');
    }
    return review;
  }

  const vendor = detectVendor(text);
  if (!vendor) {
    if (text) review.notes.push('Производитель в обращении не назван или его нет в реестре.');
    return review;
  }
  review.request.vendor = vendor;

  // Самый надёжный признак — название карточки дословно в тексте: человек
  // скопировал его со страницы или из прайса. Из нескольких подошедших
  // берётся самое длинное: «Creative Cloud Pro для команд» точнее, чем
  // «Creative Cloud Pro», которое является его частью.
  const quoted = products
    .filter((p) => p.name && norm(p.name).length >= 6 && norm(text).includes(norm(p.name)))
    .sort((a, b) => b.name.length - a.name.length);

  const phrase = productPhrase(text, vendor) || vendor;
  const strict = quoted.length ? [quoted[0]] : strictMatches(products, phrase);
  // Название позиции бывает началом другого, более длинного («… для одного
  // пользователя»), и по И-логике подходят обе. Дословное совпадение имени
  // разрешает это однозначно — и без порогов похожести, которые пришлось бы
  // подбирать на глаз.
  const exact = strict.filter((p) => norm(p.name) === norm(phrase));
  const matches = exact.length === 1 ? exact : strict;

  if (matches.length === 1) {
    const matched = matches[0];
    review.request.product = matched.name;
    review.request.matched = matched;
    review.request.plan = planOf(matched) || detectPlanWords(text);
    review.request.alternative = findAlternative(products, matched);

    // Срок клиента против срока позиции: «на 6 месяцев» при годовой
    // подписке — это не мелочь, а предмет разговора до счёта.
    const parsed = parseSku(matched.sku || '');
    if (review.term && parsed?.term === '1Y' && review.term.months !== 12) {
      review.notes.push(`Запрошен срок ${review.term.label}, у позиции — 1 год.`);
    }
    if (/person|личн|индивидуальн/i.test(text) && review.request.plan === 'team') {
      review.notes.push('В обращении назван личный план, найденная позиция — командная.');
    }
  } else {
    // Позиция в каталоге не подтверждена — но клиент назвал её сам, и блок
    // «Ваше обращение» показывает именно его слова: это сверка того, что мы
    // поняли, а не подтверждение заказа. Подтверждение нужно для ссылок —
    // их без найденной карточки не будет (решение руководителя 21.09.2026).
    if (phrase !== vendor) review.request.product = withoutVendor(phrase, vendor);
    review.request.plan = detectPlanWords(text);
    review.candidates = strictMatches(products, vendor).slice(0, 5);
    review.notes.push(matches.length
      ? `Обращению отвечают ${matches.length} позиции — точная не определена: «${phrase}».`
      : `Позиция «${phrase}» в каталоге не найдена.`);
    if (review.candidates.length) {
      review.notes.push(`Позиции ${vendor} в каталоге: `
        + review.candidates.map((p) => p.name).join(', ') + '.');
    }
  }

  const inText = (source.message || '').match(/(\d{1,4})\s*[- ]?х?\s*(?:лиценз|подписк|мест|польз|шт)/i);
  if (qty && inText && inText[1] !== qty) {
    review.notes.push(`Количество в поле формы (${qty}) и в тексте (${inText[1]}) расходятся.`);
  }

  if (review.hasQuestion) {
    review.notes.push('В обращении есть прямой вопрос — нужен ответ человека.');
  }
  return review;
}

/**
 * Ссылки письма по результату разбора: страница позиции, другой её план и
 * раздел производителя. Собираются здесь, а не в обработчике заявки, чтобы
 * адрес страницы строился в одном месте и проверялся тестом.
 */
export function leadLinks(review: LeadRequestReview, siteUrl: string): {
  product?: { name: string; url: string };
  alternative?: { name: string; url: string };
  catalog?: { name: string; url: string };
} {
  const { matched, alternative } = review.request;
  const vendor = matched ? vendorByName(matched.vendor) : undefined;
  return {
    ...(matched?.slug ? { product: { name: matched.name, url: `${siteUrl}/product/${matched.slug}` } } : {}),
    ...(alternative?.slug
      ? { alternative: { name: alternative.name, url: `${siteUrl}/product/${alternative.slug}` } }
      : {}),
    ...(vendor ? { catalog: { name: `Каталог ${vendor.vendor}`, url: `${siteUrl}/vendors/${vendor.slug}` } } : {}),
  };
}
