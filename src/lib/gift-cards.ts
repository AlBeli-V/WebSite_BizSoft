/**
 * Подарочные карты (product_type = gift_card): чистая логика без сети.
 *
 * Модель: один родительский товар (страница /product/<slug>) и варианты —
 * строки Directus с parent_sku, регионом и номиналом. Вариант несёт свою
 * закупку в USD (base_price_usd) и рублёвую цену, которую считает тот же
 * ежедневный механизм переоценки, что и у подписок (коэффициент ×3,00 —
 * GIFT_CARD_MARKUP_COEFF). Здесь — группировка по регионам и порядок
 * номиналов для витрины, разметки и тестов.
 *
 * Механика не привязана к Apple: любая цифровая карта с регионом и номиналом
 * ложится в ту же модель (docs/gift-cards.md).
 */
import type { Product, Availability } from './types';
import { effectivePrice } from './pricing';

/** Порядок регионов на витрине: как в задании руководителя, а не по алфавиту;
 *  прочие коды (GLOBAL, MENA…) — после известных, по алфавиту. */
export const REGION_ORDER: string[] = ['RU', 'KZ', 'TR'];

/** Названия валют номинала для подписи «1 000 ₽ / 2 000 ₸ / 500 ₺». */
export const DENOMINATION_CURRENCY_SYMBOL: Record<string, string> = {
  RUB: '₽',
  KZT: '₸',
  TRY: '₺',
  USD: '$',
  EUR: '€',
};

export interface GiftCardVariant {
  sku: string;
  slug: string;
  name: string;
  regionCode: string;
  regionName: string;
  currency: string;
  denomination: number;
  /** Подпись варианта, когда номинал — не сумма в валюте (подписка, тариф). */
  label: string | null;
  /** Итоговая цена BIZSoft в рублях (effectivePrice); закупка сюда не попадает. */
  price: number;
  availability: Availability;
}

export interface GiftCardRegion {
  code: string;
  name: string;
  currency: string;
  /** Номиналы по убыванию (denomination DESC) — всегда, независимо от
   *  порядка в базе, цены, наличия и даты создания. */
  variants: GiftCardVariant[];
}

function availabilityOf(p: Product): Availability {
  const a = p.availability;
  return a === 'limited' || a === 'out_of_stock' ? a : 'in_stock';
}

/** Строка Directus → вариант витрины. Возвращает null, если у строки нет
 *  региона или номинала: такая запись заведена с ошибкой, и показывать её
 *  как вариант нельзя. */
export function toGiftCardVariant(p: Product): GiftCardVariant | null {
  const denomination = Number(p.denomination);
  if (!p.region_code || !Number.isFinite(denomination) || denomination <= 0) return null;
  return {
    sku: p.sku,
    slug: p.slug,
    name: p.name,
    regionCode: String(p.region_code).toUpperCase(),
    regionName: p.region_name || String(p.region_code).toUpperCase(),
    currency: (p.denomination_currency || '').toUpperCase(),
    denomination,
    label: p.variant_label ? String(p.variant_label) : null,
    price: effectivePrice(p).price,
    availability: availabilityOf(p),
  };
}

/** Сортировка вариантов внутри региона: номинал по убыванию, при равном —
 *  по артикулу (детерминированно). */
export function sortByDenominationDesc(variants: GiftCardVariant[]): GiftCardVariant[] {
  return [...variants].sort((a, b) => b.denomination - a.denomination || a.sku.localeCompare(b.sku));
}

/**
 * Сгруппировать варианты по регионам в порядке REGION_ORDER (неизвестные
 * регионы — после известных, по коду). Внутри региона — denomination DESC.
 */
export function groupGiftCardVariants(products: Product[]): GiftCardRegion[] {
  const byRegion = new Map<string, GiftCardRegion>();
  for (const p of products) {
    const v = toGiftCardVariant(p);
    if (!v) continue;
    const region = byRegion.get(v.regionCode) ?? { code: v.regionCode, name: v.regionName, currency: v.currency, variants: [] };
    region.variants.push(v);
    byRegion.set(v.regionCode, region);
  }
  const rank = (code: string) => {
    const i = REGION_ORDER.indexOf(code);
    return i === -1 ? REGION_ORDER.length : i;
  };
  return [...byRegion.values()]
    .sort((a, b) => rank(a.code) - rank(b.code) || a.code.localeCompare(b.code))
    .map((r) => ({ ...r, variants: sortByDenominationDesc(r.variants) }));
}

/** Подпись номинала: «1 000 ₽», «2 000 ₸», «500 ₺»; без известного символа — код валюты. */
export function formatDenomination(v: Pick<GiftCardVariant, 'denomination' | 'currency'>): string {
  const num = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(v.denomination);
  const sym = DENOMINATION_CURRENCY_SYMBOL[v.currency];
  return sym ? `${num} ${sym}` : `${num} ${v.currency}`;
}

/** Подпись варианта на витрине: своя (тариф, срок) либо номинал в валюте. */
export function variantLabel(v: Pick<GiftCardVariant, 'denomination' | 'currency' | 'label'>): string {
  return v.label || formatDenomination(v);
}

/** Диапазон цен доступных вариантов (для AggregateOffer и «от N ₽»). */
export function giftCardPriceRange(regions: GiftCardRegion[]): { low: number; high: number; count: number } | null {
  const prices = regions.flatMap((r) => r.variants)
    .filter((v) => v.availability !== 'out_of_stock' && v.price > 0)
    .map((v) => v.price);
  if (prices.length === 0) return null;
  return { low: Math.min(...prices), high: Math.max(...prices), count: prices.length };
}

/** Вариант, который надо показать выбранным при открытии страницы (?sku=…). */
export function pickInitialVariant(regions: GiftCardRegion[], sku?: string | null): GiftCardVariant | null {
  const all = regions.flatMap((r) => r.variants);
  if (sku) {
    const wanted = sku.toUpperCase();
    const hit = all.find((v) => v.sku.toUpperCase() === wanted);
    if (hit) return hit;
  }
  return all.find((v) => v.availability !== 'out_of_stock') ?? all[0] ?? null;
}
