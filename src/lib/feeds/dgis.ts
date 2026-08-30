/**
 * Спецификация фида 2ГИС поверх общего YML-сериализатора.
 *
 * Отличия от яндекс-фидов — по «Инструкции по подготовке прайс-листа» 2ГИС
 * (получена руководителем 29.08.2026):
 * - id оффера: только цифры и латиница, максимум 20 символов — sku с
 *   дефисами не проходят, берём числовой id товара из Directus;
 * - картинка: без цены, названия магазина и надписей — вместо og-карточки
 *   чистый знак продукта (/img/product-icon/<slug>.png); нет знака — оффер
 *   идёт без картинки (поле необязательное);
 * - описание: без URL-ссылок (правило 2ГИС), лимит 5000 — наш лимит 3000
 *   укладывается;
 * - без oldprice и sales_notes: скидочные механики и условия продажи в
 *   формате 2ГИС не описаны, упоминания акций в тексте запрещены.
 */
import type { Product } from '../types';
import { buildYml, toFeedOffer } from './yml';
import { hasProductIconImage } from './product-image';
import type { FeedOffer, FeedShopInfo } from './types';

/** id для 2ГИС: цифры/латиница, ≤20 символов. */
export function dgisOfferId(p: Pick<Product, 'id' | 'sku'>): string {
  const fromId = String(p.id).replace(/[^0-9A-Za-z]/g, '');
  if (fromId) return fromId.slice(0, 20);
  return p.sku.replace(/[^0-9A-Za-z]/g, '').slice(0, 20);
}

/** Убрать URL из текста описания (2ГИС запрещает любые ссылки). */
export function stripUrls(text: string): string {
  return text.replace(/\bhttps?:\/\/\S+|\bwww\.\S+/gi, '').replace(/\s+/g, ' ').trim();
}

export function toDgisOffer(p: Product, baseUrl: string, now: Date): FeedOffer {
  const base = toFeedOffer(p, baseUrl, now);
  return {
    ...base,
    id: dgisOfferId(p),
    oldPrice: null,
    picture: hasProductIconImage(p.slug, p.vendor) ? `${baseUrl}/img/product-icon/${p.slug}.png` : '',
    description: stripUrls(base.description),
    salesNotes: undefined,
  };
}

export function buildDgisYml(products: Product[], baseUrl: string, shop: FeedShopInfo, now: Date): string {
  return buildYml(products.map((p) => toDgisOffer(p, baseUrl, now)), shop, now);
}
