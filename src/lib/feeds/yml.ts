/**
 * Сериализатор YML (Yandex Market Language) — формат, который принимают
 * Яндекс Товары, Яндекс Бизнес и Директ. Один сериализатор на все
 * яндекс-фиды; другие форматы (Google Merchant и т.п.) подключаются
 * отдельными сериализаторами, не трогая этот.
 *
 * Требования формата (справка Яндекса):
 * - корень <yml_catalog date="..."> — дата генерации;
 * - <shop> с name/company/url, <currencies>, <categories> (числовые id);
 * - оффер: name, url, price, currencyId, categoryId; picture и description
 *   обязательны для Товаров; описание — до 3000 символов.
 */
import type { Product, Category } from '../types';
import { effectivePrice } from '../pricing';
import { offerDescription } from './select';
import { hasProductIconImage } from './product-image';
import type { FeedOffer, FeedShopInfo } from './types';

export const YML_DESCRIPTION_LIMIT = 3000;

const escXml = (s: string): string =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&apos;');

const tag = (name: string, value: string | number | null | undefined): string =>
  value === null || value === undefined || value === '' ? '' : `<${name}>${escXml(String(value))}</${name}>`;

function categoryName(p: Product): string {
  const c = typeof p.category === 'object' && p.category ? (p.category as Category) : null;
  return c?.name || 'Программное обеспечение';
}

/**
 * Публичная OG-карточка товара (1200×630, рендерится сервером сайта): название,
 * вендор, цена, бренд BIZSoft. Ассеты Directus наружу не проксируются, поэтому
 * это единственный стабильный публичный источник изображения «как в соцсети».
 */
export const ogPicture = (p: Product, baseUrl: string) => `${baseUrl}/og/product/${p.slug}.png`;

/**
 * Чистый знак товара на белом фоне без надписей и цены
 * (/img/product-icon/<slug>.png). Нужен площадкам, которые показывают
 * изображение как фотографию товара и запрещают надписи и цену на нём:
 * товарные карточки Яндекс Бизнеса и прайс-лист 2ГИС. Знака нет — отдаём
 * OG-карточку, чтобы оффер не остался вовсе без изображения.
 */
export const productMarkPicture = (p: Product, baseUrl: string) =>
  (hasProductIconImage(p.slug, p.vendor)
    ? `${baseUrl}/img/product-icon/${p.slug}.png`
    : ogPicture(p, baseUrl));

/** Дата в формате YML: YYYY-MM-DD hh:mm (локальное время не важно, важна свежесть). */
export function ymlDate(now: Date): string {
  return now.toISOString().slice(0, 16).replace('T', ' ');
}

/**
 * Привести товар к нормализованному офферу для YML.
 *
 * `picture` — функция-резолвер адреса картинки: у площадок разные требования
 * к изображению товара, и подменять сериализатор целиком ради этого не нужно.
 * По умолчанию — публичная OG-карточка (название, вендор, цена, бренд).
 */
export function toFeedOffer(
  p: Product,
  baseUrl: string,
  now: Date,
  picture: (p: Product, baseUrl: string) => string = ogPicture,
): FeedOffer {
  const eff = effectivePrice(p, now);
  return {
    id: p.sku,
    name: p.name,
    url: `${baseUrl}/product/${p.slug}`,
    price: eff.price,
    oldPrice: eff.isPromo ? eff.oldPrice : null,
    currencyId: 'RUR',
    categoryName: categoryName(p),
    picture: picture(p, baseUrl),
    description: offerDescription(p, YML_DESCRIPTION_LIMIT),
    vendor: p.vendor || null,
    vendorCode: p.sku,
    salesNotes: 'Оплата по счёту для юрлиц и ИП. Закрывающие документы.',
  };
}

/**
 * Собрать YML-документ. Числовые id категорий назначаются по алфавиту
 * названий — стабильны при неизменном наборе категорий.
 */
export function buildYml(offers: FeedOffer[], shop: FeedShopInfo, now: Date): string {
  const catNames = [...new Set(offers.map((o) => o.categoryName))].sort((a, b) => a.localeCompare(b, 'ru'));
  const catId = new Map(catNames.map((n, i) => [n, i + 1]));

  const categoriesXml = catNames
    .map((n) => `      <category id="${catId.get(n)}">${escXml(n)}</category>`)
    .join('\n');

  const offersXml = offers
    .map((o) => {
      const parts = [
        tag('name', o.name),
        tag('url', o.url),
        tag('price', o.price),
        o.oldPrice && o.oldPrice > o.price ? tag('oldprice', o.oldPrice) : '',
        tag('currencyId', o.currencyId),
        tag('categoryId', catId.get(o.categoryName)),
        tag('picture', o.picture),
        tag('vendor', o.vendor),
        tag('vendorCode', o.vendorCode),
        tag('description', o.description),
        tag('sales_notes', o.salesNotes),
      ].filter(Boolean);
      return `      <offer id="${escXml(o.id)}" available="true">\n        ${parts.join('\n        ')}\n      </offer>`;
    })
    .join('\n');

  return `<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog date="${ymlDate(now)}">
  <shop>
    ${tag('name', shop.name)}
    ${tag('company', shop.company)}
    ${tag('url', shop.url)}
    <currencies>
      <currency id="RUR" rate="1"/>
    </currencies>
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
