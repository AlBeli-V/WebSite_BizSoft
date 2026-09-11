/**
 * Вторая привязка товара к разделу каталога.
 *
 * У товара в Directus одна категория, и вокруг неё собран весь сайт: витрина,
 * фильтры, крошки, микроразметка, карта сайта, слой для агентов. Перенос между
 * разделами каталог не наполняет — он забирает позицию у соседа. Тонкие разделы
 * пусты не потому, что товары лежат не там, а потому что один продукт закрывает
 * две задачи, а показан в одной.
 *
 * Механизм не новый: так с самого начала живут «Корпоративные AI» — раздел
 * собирается явным списком товаров из других веток, и схему базы для этого
 * менять не пришлось. Здесь он обобщён на любой раздел.
 *
 * Домашний раздел (`category`) остаётся у товара один: он задаёт крошки,
 * канонический адрес и подпись в карточке. Вторая привязка добавляет товар в
 * выдачу раздела и в его счётчик — новых адресов и дублей страниц не возникает.
 *
 * ВАЖНО для тех, кто добавляет новый слой: любой код, который считает или
 * фильтрует товары по `category`, обязан пройти через `categoryMembers` или
 * `countByCategory`. Счётчик, не знающий про реестр, подписывает живой раздел
 * как пустой — так хаб каталога до 11.09.2026 объявлял «в подготовке» раздел
 * с десятком тарифов.
 */
import registry from '../../data/catalog/cross-listing.json';
import { aiEnterpriseSlugs } from '../data/ai-hub';
import type { Product } from './types';

/** Артикул (в верхнем регистре) → разделы, где товар показывается дополнительно. */
export const CROSS_LISTING: Record<string, string[]> = Object.fromEntries(
  Object.entries((registry as { also: Record<string, string[]> }).also).map(
    ([sku, cats]) => [sku.toUpperCase(), cats],
  ),
);

/**
 * «Корпоративные AI» — кросс-коллекция, заведённая раньше реестра и по слагам,
 * а не по артикулам (см. data/ai-hub.ts). Держим её вторым источником, а не
 * переписываем вслепую: артикулы этих тарифов в репозитории не лежат, и
 * угаданный ключ молча выключил бы живой раздел. Переносится в общий реестр,
 * когда выгрузка ops-export-catalog-map даст артикулы.
 */
const LEGACY_BY_SLUG: Record<string, string[]> = Object.fromEntries(
  aiEnterpriseSlugs.map((slug) => [slug, ['ai-enterprise']]),
);

/** Слаг домашнего раздела товара. */
export function homeCategory(p: Pick<Product, 'category'>): string {
  return typeof p.category === 'object' && p.category ? p.category.slug : '';
}

/** Разделы, в которых товар показывается дополнительно к домашнему. */
export function extraCategories(p: Pick<Product, 'sku' | 'slug' | 'category'>): string[] {
  const home = homeCategory(p);
  const listed = [
    ...(CROSS_LISTING[(p.sku || '').toUpperCase()] || []),
    ...(LEGACY_BY_SLUG[p.slug] || []),
  ];
  // Домашний раздел в списке — ошибка реестра (её ловит тест), но повторно
  // показывать товар в его же разделе нельзя в любом случае.
  return [...new Set(listed)].filter((c) => c && c !== home);
}

/** Все разделы товара: домашний первым, затем вторые привязки. */
export function productCategories(p: Pick<Product, 'sku' | 'slug' | 'category'>): string[] {
  const home = homeCategory(p);
  return home ? [home, ...extraCategories(p)] : extraCategories(p);
}

/** Показывается ли товар в разделе — с учётом второй привязки. */
export function inCategory(p: Pick<Product, 'sku' | 'slug' | 'category'>, slug: string): boolean {
  return homeCategory(p) === slug || extraCategories(p).includes(slug);
}

/**
 * Товары раздела: сначала свои, затем пришедшие второй привязкой.
 *
 * Порядок не случаен: раздел должен начинаться с того, что в нём живёт, —
 * иначе «Сайты и хостинг» открывались бы карточкой Cloudflare, а не WordPress.
 */
export function categoryMembers<T extends Pick<Product, 'sku' | 'slug' | 'category'>>(
  products: T[],
  slug: string,
): T[] {
  const own: T[] = [];
  const extra: T[] = [];
  for (const p of products) {
    if (homeCategory(p) === slug) own.push(p);
    else if (extraCategories(p).includes(slug)) extra.push(p);
  }
  return [...own, ...extra];
}

/** Сколько товаров пришло в раздел второй привязкой (для подписи «+N»). */
export function crossListedCount<T extends Pick<Product, 'sku' | 'slug' | 'category'>>(
  products: T[],
  slug: string,
): number {
  return products.filter((p) => homeCategory(p) !== slug && extraCategories(p).includes(slug)).length;
}
