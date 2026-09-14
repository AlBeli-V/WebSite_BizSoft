/**
 * Единая система артикулов biz-soft.pro (правило docs/rules/sku-system.md).
 *
 * Артикул — семь сегментов через дефис, фиксированные позиции:
 *
 *   <ВЕНДОР>-<ВИД>-<ПРОДУКТ>-<ПЛАН>-<СРОК>-<ЕДИНИЦА>[-<ВАРИАНТ>]
 *
 *   ADBE-LIC-PS-TEAM-1Y-USER            Adobe Photoshop, командный план, год, за пользователя
 *   JB-ADD-AEMIDE-IND-1Y-USER           плагин JetBrains AEM IDE, индивидуальный, год
 *   OPAI-CRD-API-UNI-BAL-NOM-100        пополнение баланса OpenAI API на 100 $
 *   APPL-GFT-APPSTORE-UNI-BAL-NOM-RU1000 подарочная карта App Store 1000 ₽, Россия
 *   ZOHO-LIC-ADAUDITPRO-TEAM-PERP-PACK-2DC  ADAudit Plus Professional, бессрочно, пакет на 2 DC
 *
 * Сегменты — из закрытых словарей (ниже), кроме кода продукта и варианта:
 * код продукта берётся из реестра data/catalog/sku-products.json (для
 * вендора уникален), вариант — различитель позиций с одинаковыми остальными
 * сегментами (регион и номинал, тип места, платформа, объём пакета).
 *
 * Модуль чистый: ни сети, ни файлов. Разбор артикула — единственный
 * источник вида позиции, типа плана, срока и единицы для карточки
 * (catalog.ts, plan-type.ts, card-display.ts).
 */

/** Вид позиции: что именно покупают. */
export const SKU_KINDS = {
  LIC: 'Основной продукт: подписка или лицензия',
  ADD: 'Дополнение к продукту: плагин, надстройка, add-on',
  CRD: 'Кредиты и пополнение баланса (API, генерации)',
  GFT: 'Подарочная карта, ваучер',
  SVC: 'Услуга вендора: сопровождение, внедрение, обучение',
} as const;
export type SkuKind = keyof typeof SKU_KINDS;

/** Тип плана — то же деление, что в плашке карточки (docs/rules/product-markers.md). */
export const SKU_PLANS = {
  TEAM: 'Командный план (для организаций, пул мест)',
  IND: 'Индивидуальный план (один специалист)',
  UNI: 'Универсальный: деления на командный и индивидуальный нет',
} as const;
export type SkuPlan = keyof typeof SKU_PLANS;

/** Единица расчёта — за что платят. */
export const SKU_UNITS = {
  USER: 'Пользователь, рабочее место, именованная лицензия',
  DEV: 'Устройство, компьютер, комната',
  SRV: 'Сервер, хост, виртуальная машина',
  CCU: 'Плавающая (конкурентная) лицензия',
  ORG: 'Организация, аккаунт, домен или сайт целиком',
  PROJ: 'Проект (игровое middleware)',
  PACK: 'Фиксированный пакет объёма (объём — в варианте)',
  NOM: 'Номинал: сумма или количество кредитов (в варианте)',
} as const;
export type SkuUnit = keyof typeof SKU_UNITS;

/** Срок: `<n>M`, `<n>Y`, PERP — бессрочно, BAL — до истечения баланса. */
export const SKU_TERM_RE = /^(?:[1-9]\d?[MY]|PERP|BAL)$/;
export const SKU_VENDOR_RE = /^[A-Z][A-Z0-9]{1,3}$/;
export const SKU_PRODUCT_RE = /^[A-Z0-9]{2,12}$/;
export const SKU_VARIANT_RE = /^[A-Z0-9]{1,12}$/;

export interface SkuParts {
  vendor: string;
  kind: SkuKind;
  product: string;
  plan: SkuPlan;
  term: string;
  unit: SkuUnit;
  variant?: string | null;
}

const KINDS = new Set(Object.keys(SKU_KINDS));
const PLANS = new Set(Object.keys(SKU_PLANS));
const UNITS = new Set(Object.keys(SKU_UNITS));

/** Ошибки сегментов; пустой список — артикул можно собирать. */
export function validateSkuParts(p: Partial<SkuParts>): string[] {
  const errs: string[] = [];
  if (!p.vendor || !SKU_VENDOR_RE.test(p.vendor)) errs.push(`вендор: код 2–4 знака A–Z/0–9, начинается с буквы («${p.vendor ?? ''}»)`);
  if (!p.kind || !KINDS.has(p.kind)) errs.push(`вид: один из ${[...KINDS].join('/')} («${p.kind ?? ''}»)`);
  if (!p.product || !SKU_PRODUCT_RE.test(p.product)) errs.push(`продукт: код 2–12 знаков A–Z/0–9 («${p.product ?? ''}»)`);
  if (!p.plan || !PLANS.has(p.plan)) errs.push(`план: один из ${[...PLANS].join('/')} («${p.plan ?? ''}»)`);
  if (!p.term || !SKU_TERM_RE.test(p.term)) errs.push(`срок: <n>M, <n>Y, PERP или BAL («${p.term ?? ''}»)`);
  if (!p.unit || !UNITS.has(p.unit)) errs.push(`единица: одна из ${[...UNITS].join('/')} («${p.unit ?? ''}»)`);
  if (p.variant && !SKU_VARIANT_RE.test(p.variant)) errs.push(`вариант: 1–12 знаков A–Z/0–9 («${p.variant}»)`);
  // Согласованность словарей: у кредитов и карт нет плана и мест, есть номинал.
  if (p.kind && (p.kind === 'CRD' || p.kind === 'GFT')) {
    if (p.plan && p.plan !== 'UNI') errs.push(`план у ${p.kind} — только UNI`);
    if (p.unit && p.unit !== 'NOM') errs.push(`единица у ${p.kind} — только NOM`);
  } else if (p.unit === 'NOM') {
    errs.push('единица NOM — только у CRD и GFT');
  }
  if (p.term === 'BAL' && p.kind && p.kind !== 'CRD' && p.kind !== 'GFT') errs.push('срок BAL — только у CRD и GFT');
  return errs;
}

/** Собрать артикул; бросает при ошибке сегментов. */
export function buildSku(p: SkuParts): string {
  const errs = validateSkuParts(p);
  if (errs.length) throw new Error(`артикул не собран: ${errs.join('; ')}`);
  const base = [p.vendor, p.kind, p.product, p.plan, p.term, p.unit].join('-');
  return p.variant ? `${base}-${p.variant}` : base;
}

/**
 * Разобрать артикул новой системы; null — артикул старой схемы или мусор.
 * Разбор строгий: семь или восемь сегментов, каждый — по своему словарю.
 * Артикулы старой схемы (`JB-PLG-log-ORG`, `OPENAI-CREDITS-100`) сюда не
 * проходят: у них нет сегментов вида и срока. Такие остались только у
 * черновиков и архива, страниц не имеющих.
 */
export function parseSku(sku: string | null | undefined): SkuParts | null {
  if (!sku) return null;
  const seg = sku.split('-');
  if (seg.length < 6 || seg.length > 7) return null;
  const [vendor, kind, product, plan, term, unit, variant] = seg;
  const parts: SkuParts = { vendor, kind: kind as SkuKind, product, plan: plan as SkuPlan, term, unit: unit as SkuUnit, variant: variant ?? null };
  return validateSkuParts(parts).length ? null : parts;
}

/** Артикул новой системы? */
export function isSystemSku(sku: string | null | undefined): boolean {
  return parseSku(sku) !== null;
}

/** Число месяцев по сегменту срока; null — бессрочно или баланс. */
export function termMonths(term: string): number | null {
  const m = term.match(/^(\d+)([MY])$/);
  if (!m) return null;
  return m[2] === 'Y' ? 12 * Number(m[1]) : Number(m[1]);
}

/**
 * Код продукта из названия: латиница и цифры без пробелов и знаков, до 12
 * знаков. Длиннее — первое слово (до 6 знаков) плюс начальные буквы
 * остальных, затем обрезка. Это предложение для реестра, а не сам реестр:
 * столкновения внутри вендора разводятся там, добавлением цифры к
 * позднее заведённому коду.
 */
export function proposeProductCode(name: string): string {
  const words = name
    .normalize('NFKD')
    .replace(/[^\x00-\x7F]/g, '')
    .toUpperCase()
    .split(/[^A-Z0-9]+/)
    .filter(Boolean);
  if (words.length === 0) return '';
  const joined = words.join('');
  if (joined.length <= 12 || words.length === 1) return joined.slice(0, 12);
  const head = words[0].slice(0, 6);
  const tail = words.slice(1).map((w) => w[0]).join('');
  return (head + tail).slice(0, 12);
}

/** Уникален ли код продукта в наборе (без учёта самого артикула). */
export function findDuplicateSkus(skus: string[]): string[] {
  const seen = new Set<string>();
  const dups = new Set<string>();
  for (const s of skus) {
    if (seen.has(s)) dups.add(s); else seen.add(s);
  }
  return [...dups].sort();
}
