/**
 * Состав предложения для письма: производители и их позиции со ссылками.
 *
 * Письмо показывает не абстрактный список товаров, а ссылки на те же
 * карточки сайта, откуда клиент их выбрал: вернуться к составу он должен
 * одним кликом, а не поиском по каталогу.
 *
 * Производитель определяется из реестра вендоров, а не угадывается по
 * названию: реестр — единственный источник, где у марки записаны её раздел и
 * посадочная страница (`docs/rules/catalog.md`).
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

/** Производитель из состава КП и его позиции — блок «Состав предложения». */
export interface OfferVendorGroup {
  vendor: string;
  /** Раздел производителя на сайте; пусто — марки нет в реестре. */
  url: string;
  products: OfferProductLink[];
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
 * Состав предложения по производителям: марка, её раздел, её позиции.
 *
 * Порядок как в документе — производитель, его позиции, следующий
 * производитель: читатель сверяет письмо с КП сверху вниз, и другой порядок
 * заставил бы его искать.
 *
 * Ссылка на раздел марки берётся из реестра вендоров. Марки в реестре нет —
 * строка остаётся без ссылки: битая ссылка в коммерческом предложении хуже
 * её отсутствия (то же правило, что у позиций без карточки).
 */
export function offerVendorGroups(
  links: readonly OfferProductLink[],
  siteUrl: string,
): OfferVendorGroup[] {
  const base = siteUrl.replace(/\/$/, '');
  const order: string[] = [];
  const byVendor = new Map<string, OfferProductLink[]>();
  for (const link of links) {
    const name = link.vendor || '';
    if (!byVendor.has(name)) { byVendor.set(name, []); order.push(name); }
    byVendor.get(name)!.push(link);
  }
  return order.map((name) => {
    const entry = name ? VENDORS.find((v) => v.vendor === name) : undefined;
    return {
      vendor: name,
      url: entry ? withEmailUtm(`${base}/vendors/${entry.slug}`, 'vendor') : '',
      products: byVendor.get(name) || [],
    };
  });
}
