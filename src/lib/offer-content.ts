/**
 * Ссылки предложения: позиции и разделы каталога.
 *
 * Письмо и страница предложения показывают не абстрактный список товаров, а
 * ссылки на те же карточки сайта, откуда клиент их выбрал: вернуться к
 * составу он должен одним кликом, а не поиском по каталогу.
 *
 * Раздел определяется по производителю из реестра вендоров, а не угадывается
 * по названию: реестр — единственный источник, где у марки записаны её
 * раздел и посадочная страница (`docs/rules/catalog.md`).
 */
import { VENDORS } from '../data/vendors';
import type { Product } from './types';
import type { QuoteItem } from './types';

export interface OfferProductLink {
  vendor: string;
  name: string;
  url: string;
  sku: string;
}

export interface OfferCategoryLink {
  label: string;
  url: string;
}

/** Метки кампании ставятся только на переходе «письмо → сайт». */
export function withEmailUtm(url: string, content: string): string {
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}utm_source=bizsoft_email&utm_medium=email`
    + `&utm_campaign=commercial_offer&utm_content=${encodeURIComponent(content)}`;
}

/**
 * Позиции предложения со ссылками на карточки.
 *
 * Позиция без карточки в каталоге (снята с витрины, переехала) ссылки не
 * получает и в письмо не идёт: битая ссылка в коммерческом предложении хуже
 * её отсутствия.
 */
export function offerProductLinks(
  items: readonly QuoteItem[],
  products: readonly Product[],
  siteUrl: string,
  utm = true,
): OfferProductLink[] {
  const bySku = new Map(products.map((p) => [p.sku, p]));
  const out: OfferProductLink[] = [];
  for (const it of items) {
    const p = bySku.get(it.sku);
    if (!p?.slug) continue;
    const url = `${siteUrl.replace(/\/$/, '')}/product/${p.slug}`;
    out.push({
      vendor: String(p.vendor || it.vendor || '').trim(),
      name: p.name || it.name,
      sku: it.sku,
      url: utm ? withEmailUtm(url, 'product') : url,
    });
  }
  return out;
}

/**
 * Разделы каталога по составу предложения — не больше трёх.
 *
 * Больше трёх превращает письмо в каталог: задача блока — показать, что у
 * нас есть смежное, а не перечислить весь сайт.
 */
export function offerCategoryLinks(
  items: readonly QuoteItem[],
  products: readonly Product[],
  siteUrl: string,
  limit = 3,
): OfferCategoryLink[] {
  const bySku = new Map(products.map((p) => [p.sku, p]));
  const vendorNames = new Set<string>();
  for (const it of items) {
    const name = String(bySku.get(it.sku)?.vendor || it.vendor || '').trim();
    if (name) vendorNames.add(name);
  }
  const base = siteUrl.replace(/\/$/, '');
  const seen = new Set<string>();
  const out: OfferCategoryLink[] = [];
  for (const name of vendorNames) {
    const entry = VENDORS.find((v) => v.vendor === name);
    if (!entry || seen.has(entry.catSeg)) continue;
    seen.add(entry.catSeg);
    out.push({
      label: entry.catLabel,
      url: withEmailUtm(`${base}/catalog/${entry.catSeg}`, 'category'),
    });
    if (out.length >= limit) break;
  }
  return out;
}
