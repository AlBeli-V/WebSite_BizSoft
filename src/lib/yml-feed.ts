/**
 * Прайс-лист YML для Яндекс Бизнеса (карточка организации).
 *
 * Формат — по шаблону Яндекса `pricelisttemplate.xml`: `yml_catalog → shop →
 * categories + offers`, никаких лишних элементов (шаблон здесь и есть спека).
 * Логика чистая (без сети): на вход — товары и категории из Directus,
 * на выходе — строка XML. Используется SSR-маршрутом `/yandex-business.xml`.
 *
 * Соответствие полей:
 *   offer id        → id товара в Directus (целое, стабильное)
 *   name            → название карточки (с брендом, если его нет в названии)
 *   vendor          → поле vendor
 *   price           → эффективная цена (с учётом активной акции), ₽
 *   currencyId      → RUR
 *   categoryId      → id категории (товары без категории → «Прочее ПО»)
 *   picture         → /og/product/<slug>.png (1200×630 PNG, генерится на лету)
 *   description     → description/seo_text, markdown → плоский текст
 *   shortDescription→ short_description
 *   url             → /product/<slug>
 */
import type { Category, Product } from './types';
import { effectivePrice } from './pricing';
import { productNoindex } from './catalog';

/** Лимиты Яндекса на длину текстов в оффере. */
const MAX_DESCRIPTION = 3000;
const MAX_SHORT_DESCRIPTION = 250;
const MAX_NAME = 250;

/** id и название категории-заглушки для товаров без категории. */
export const FALLBACK_CATEGORY_ID = 999;
export const FALLBACK_CATEGORY_NAME = 'Прочее ПО';

export interface YmlFeedOptions {
  /** Базовый URL сайта без завершающего слеша (https://biz-soft.pro). */
  siteUrl: string;
  /** Дата расчёта акций (для тестов). */
  now?: Date;
  /**
   * Включить товары, скрытые от индексации: noindex, плагины JetBrains
   * Marketplace (JB-PLG-...) и личные лицензии (...-IND). По умолчанию
   * выключено — в витрине Яндекса нужен продвигаемый каталог, а не
   * 800+ карточек плагинов.
   */
  includeNoindex?: boolean;
}

export interface YmlOffer {
  id: string;
  name: string;
  vendor: string | null;
  price: number;
  categoryId: number;
  picture: string;
  description: string | null;
  shortDescription: string | null;
  url: string;
}

/** Экранирование текста для XML. */
export function xmlEscape(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

/**
 * Markdown/HTML → плоский текст в одну строку.
 * Описания товаров в Directus хранятся как markdown (input-rich-text-md),
 * Яндекс ждёт обычный текст.
 */
export function plainText(input?: string | null): string {
  if (!input) return '';
  return input
    .replace(/<[^>]+>/g, ' ') // html-теги
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ') // картинки
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1') // ссылки → текст
    .replace(/`{1,3}/g, '')
    .replace(/^\s{0,3}#{1,6}\s+/gm, '') // заголовки
    .replace(/^\s{0,3}[-*+]\s+/gm, '• ') // маркеры списка
    .replace(/\*\*|__/g, '')
    .replace(/(^|\s)[*_]([^*_]+)[*_](?=\s|$)/g, '$1$2')
    .replace(/\r/g, '')
    .replace(/\s*\n\s*/g, ' ')
    .replace(/\u00a0/g, ' ')
    .replace(/[ \t]{2,}/g, ' ')
    .trim();
}

/** Обрезка по границе слова с многоточием. */
export function truncate(value: string, max: number): string {
  if (value.length <= max) return value;
  const cut = value.slice(0, max - 1);
  const space = cut.lastIndexOf(' ');
  return (space > max * 0.6 ? cut.slice(0, space) : cut).trimEnd() + '…';
}

/** Название оффера: бренд впереди, если его ещё нет в названии карточки. */
export function offerName(product: Pick<Product, 'name' | 'vendor'>): string {
  const name = (product.name || '').trim();
  const vendor = (product.vendor || '').replace(/\s*\(.+\)$/, '').trim();
  const withVendor = vendor && !name.toLowerCase().includes(vendor.toLowerCase()) ? `${vendor} ${name}` : name;
  return truncate(withVendor, MAX_NAME);
}

/** Годится ли товар для прайс-листа Яндекса. */
export function isFeedEligible(product: Product, opts: { now?: Date; includeNoindex?: boolean } = {}): boolean {
  if (product.status !== 'published') return false;
  if (product.origin === 'domestic') return false; // отечественное ПО снято с сайта
  if (!opts.includeNoindex && (product.noindex || productNoindex(product.sku))) return false;
  // Яндекс требует цену: карточки «цена по запросу» в прайс-лист не попадают.
  const { price } = effectivePrice(product, opts.now);
  return Number.isFinite(price) && price > 0;
}

/** id категории товара (число) или заглушка. */
function categoryIdOf(product: Product): number {
  const raw = typeof product.category === 'object' && product.category ? product.category.id : product.category;
  const id = Number(raw);
  return Number.isInteger(id) && id > 0 ? id : FALLBACK_CATEGORY_ID;
}

/** Товары Directus → офферы прайс-листа. */
export function feedOffers(products: Product[], opts: YmlFeedOptions): YmlOffer[] {
  const siteUrl = opts.siteUrl.replace(/\/$/, '');
  const offers: YmlOffer[] = [];
  const seenIds = new Set<string>();

  for (const p of products) {
    if (!isFeedEligible(p, opts)) continue;
    // id должен быть уникальным в пределах прайс-листа; id Directus — целое
    // с автоинкрементом, дубликатов не бывает, но подстрахуемся.
    let id = String(p.id);
    if (seenIds.has(id)) id = `${id}-${p.sku}`.slice(0, 40);
    seenIds.add(id);

    const description = truncate(plainText(p.description || p.seo_text), MAX_DESCRIPTION);
    const short = truncate(plainText(p.short_description || p.meta_description), MAX_SHORT_DESCRIPTION);

    offers.push({
      id,
      name: offerName(p),
      vendor: (p.vendor || '').trim() || null,
      price: Math.round(effectivePrice(p, opts.now).price),
      categoryId: categoryIdOf(p),
      picture: `${siteUrl}/og/product/${p.slug}.png`,
      description: description || null,
      shortDescription: short || null,
      url: `${siteUrl}/product/${p.slug}`,
    });
  }
  return offers;
}

/** Категории, реально использованные офферами (Яндекс ругается на пустые). */
export function feedCategories(offers: YmlOffer[], categories: Category[]): { id: number; name: string }[] {
  const used = new Set(offers.map((o) => o.categoryId));
  const out: { id: number; name: string }[] = [];
  for (const c of categories) {
    const id = Number(c.id);
    if (used.has(id)) out.push({ id, name: c.name });
  }
  if (used.has(FALLBACK_CATEGORY_ID) && !out.some((c) => c.id === FALLBACK_CATEGORY_ID)) {
    out.push({ id: FALLBACK_CATEGORY_ID, name: FALLBACK_CATEGORY_NAME });
  }
  return out;
}

function tag(name: string, value: string | number | null | undefined, indent: string): string {
  if (value === null || value === undefined || value === '') return '';
  return `${indent}<${name}>${xmlEscape(String(value))}</${name}>\n`;
}

/** Собрать XML прайс-листа по шаблону Яндекс Бизнеса. */
export function buildYmlCatalog(products: Product[], categories: Category[], opts: YmlFeedOptions): string {
  const offers = feedOffers(products, opts);
  const cats = feedCategories(offers, categories);

  const categoriesXml = cats
    .map((c) => `            <category id="${c.id}">${xmlEscape(c.name)}</category>`)
    .join('\n');

  const offersXml = offers
    .map((o) => {
      const i = '                ';
      return (
        `            <offer id="${xmlEscape(o.id)}">\n` +
        tag('name', o.name, i) +
        tag('vendor', o.vendor, i) +
        tag('price', o.price, i) +
        tag('currencyId', 'RUR', i) +
        tag('categoryId', o.categoryId, i) +
        tag('picture', o.picture, i) +
        tag('description', o.description, i) +
        tag('shortDescription', o.shortDescription, i) +
        tag('url', o.url, i) +
        `            </offer>`
      );
    })
    .join('\n');

  return `<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog>
    <shop>
        <categories>
${categoriesXml}
        </categories>
        <offers>
${offersXml}
        </offers>
    </shop>
</yml_catalog>
`;
}
