/**
 * Построители JSON-LD разметки. Чистые функции, возвращают объекты,
 * которые сериализуются в <script type="application/ld+json">.
 */
import { site, seller, sellerAddress, workingHours, sameAs, knowsAbout, expert } from '../config/site';
import { effectivePrice } from './pricing';
import type { Product, Category } from './types';

export const ORG_ID = `${site.url}/#organization`;
const WEBSITE_ID = `${site.url}/#website`;
/** Публичный эксперт: один узел Person на весь сайт, как ORG_ID у организации. */
export const EXPERT_ID = `${site.url}/authors/${expert.slug}#person`;

/**
 * Дата регистрации в формате schema.org (ISO). В реквизитах она хранится
 * по-русски (`07.11.2022`) — так её видит человек на /documents.
 */
function foundingDateIso(): string | undefined {
  const m = seller.registrationDate.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
  return m ? `${m[3]}-${m[2]}-${m[1]}` : undefined;
}

/** Единый почтовый адрес организации (тот же, что видим на /contacts). */
function postalAddress() {
  return { '@type': 'PostalAddress', ...sellerAddress };
}

/**
 * Единый канонический URL: https://biz-soft.pro + путь без завершающего слеша,
 * кроме главной ("/"). Принимает путь или абсолютный URL.
 */
export function canonicalUrl(input: string): string {
  let path = input || '/';
  if (path.startsWith('http')) {
    try { path = new URL(path).pathname; } catch { /* ignore */ }
  }
  // отбрасываем query/hash для canonical
  path = path.split('?')[0].split('#')[0];
  if (path !== '/') path = path.replace(/\/+$/, '');
  if (!path.startsWith('/')) path = '/' + path;
  return path === '/' ? `${site.url}/` : `${site.url}${path}`;
}

/** WebSite schema (site-wide). */
export function websiteSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    '@id': WEBSITE_ID,
    name: site.name,
    url: site.url,
    inLanguage: 'ru-RU',
    publisher: { '@id': ORG_ID },
  };
}

export function organizationSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    '@id': ORG_ID,
    name: seller.brand,
    legalName: seller.legalName,
    url: site.url,
    logo: `${site.url}/brand/bizsoft-logo-lockup.png`,
    email: seller.email,
    telephone: seller.phone,
    taxID: seller.inn,
    description: site.description,
    address: postalAddress(),
    // Внешние подтверждения существования организации. Пустой массив в
    // разметку не выводится: `sameAs: []` — не сигнал, а шум (ENT-001).
    ...(sameAs.length > 0 ? { sameAs: [...sameAs] } : {}),
    ...(foundingDateIso() ? { foundingDate: foundingDateIso() } : {}),
    founder: { '@id': EXPERT_ID },
    knowsAbout: [...knowsAbout],
    areaServed: { '@type': 'Country', name: 'RU' },
    currenciesAccepted: 'RUB',
    contactPoint: {
      '@type': 'ContactPoint',
      telephone: seller.phone,
      email: seller.email,
      contactType: 'sales',
      areaServed: 'RU',
      availableLanguage: ['Russian'],
    },
  };
}

/**
 * Публичный эксперт как сущность. Отдельный узел Person со своим `@id`:
 * на него ссылаются `founder` организации и `author` статей, поэтому
 * описывается он один раз, а не копируется в каждую разметку.
 */
export function expertSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Person',
    '@id': EXPERT_ID,
    name: expert.fullName,
    alternateName: expert.name,
    jobTitle: expert.jobTitle,
    description: expert.bio,
    email: expert.email,
    url: `${site.url}/authors/${expert.slug}`,
    worksFor: { '@id': ORG_ID },
    knowsAbout: [...knowsAbout],
    ...(sameAs.length > 0 ? { sameAs: [...sameAs] } : {}),
  };
}

/**
 * Та же организация с локальным профилем (график работы, ценовой диапазон,
 * картинка) — расширение базового узла, а не второй узел рядом с ним.
 *
 * Раньше страницы «Главная» и «Контакты» выводили этот узел дополнительно к
 * Organization из BaseLayout под тем же @id. Потребитель, который сливает
 * узлы по идентификатору (так делает Google), получал name/url/telephone/
 * email/address по два раза — ровно тот же дефект, что «Поле "brand"
 * дублируется» на карточке товара. Поэтому узел один: BaseLayout выводит
 * либо Organization, либо это расширение (проп localBusiness).
 */
export function localBusinessSchema() {
  return {
    ...organizationSchema(),
    '@type': ['Organization', 'LocalBusiness'],
    image: `${site.url}/og-default.png`,
    priceRange: '₽₽',
    openingHoursSpecification: workingHours.schema,
  };
}

export interface Crumb {
  name: string;
  url: string;
}

export function breadcrumbSchema(crumbs: Crumb[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: crumbs.map((c, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: c.name,
      item: c.url.startsWith('http') ? c.url : `${site.url}${c.url}`,
    })),
  };
}

/**
 * Политика возврата и доставки для цифровых лицензий/подписок.
 * Экспортируется: те же значения выводит microdata-слой карточки
 * (компонент OfferLogisticsMicrodata) — источник у слоёв один.
 * Товар — электронный доступ: физической доставки нет (бесплатно, моментально),
 * возврат активированной лицензии не предусмотрен. Значения фактические —
 * закрывают рекомендованные поля Merchant listings в Search Console.
 */
export function offerLogistics(currency: string) {
  return {
    hasMerchantReturnPolicy: {
      '@type': 'MerchantReturnPolicy',
      applicableCountry: 'RU',
      returnPolicyCategory: 'https://schema.org/MerchantReturnNotPermitted',
    },
    shippingDetails: {
      '@type': 'OfferShippingDetails',
      shippingRate: { '@type': 'MonetaryAmount', value: 0, currency },
      shippingDestination: { '@type': 'DefinedRegion', addressCountry: 'RU' },
      deliveryTime: {
        '@type': 'ShippingDeliveryTime',
        handlingTime: { '@type': 'QuantitativeValue', minValue: 0, maxValue: 1, unitCode: 'DAY' },
        transitTime: { '@type': 'QuantitativeValue', minValue: 0, maxValue: 0, unitCode: 'DAY' },
      },
    },
  };
}

/**
 * Product + Offer карточки товара.
 *
 * «Цена по запросу» (price <= 0) возвращает null — страница выходит без
 * товарной разметки: и Яндекс, и Google требуют у Offer цену, а Offer без
 * price (как было раньше) Google считает invalid item. Подставлять 0 или
 * условную цену запрещено — разметка обязана совпадать с видимой страницей.
 */
export function productSchema(p: Product, opts?: { images?: string[] }): Record<string, unknown> | null {
  const eff = effectivePrice(p);
  if (eff.price <= 0) return null;
  const cat = typeof p.category === 'object' && p.category ? p.category : null;
  const currency = p.currency || 'RUB';
  // Без завершающего слеша: canonical карточки и фиды используют форму
  // /product/<slug>, и Offer.url обязан совпадать с ними, иначе робот
  // видит два разных URL одного предложения.
  const url = `${site.url}/product/${p.slug}`;
  // image — обязательное поле Product. Берём галерею товара; если её нет,
  // подставляем брендовое изображение по умолчанию (то же, что в og:image),
  // чтобы поле всегда присутствовало.
  const images = opts?.images?.length ? opts.images : [`${site.url}/og-default.png`];
  return {
    '@context': 'https://schema.org',
    '@type': 'Product',
    '@id': `${url}#product`,
    url,
    name: p.name,
    sku: p.sku,
    image: images,
    description: p.short_description || p.meta_description || p.name,
    // brand — только реальный производитель; BIZSoft — продавец, не бренд.
    ...(p.vendor ? { brand: { '@type': 'Brand', name: p.vendor } } : {}),
    ...(cat ? { category: cat.name } : {}),
    offers: {
      '@type': 'Offer',
      url,
      priceCurrency: currency,
      price: eff.price,
      availability: 'https://schema.org/InStock',
      seller: { '@id': ORG_ID },
      ...offerLogistics(currency),
      ...(eff.isPromo && p.promo_end ? { priceValidUntil: p.promo_end } : {}),
    },
  };
}

/**
 * Product + AggregateOffer родительской карточки подарочной карты.
 *
 * У карты нет одной цены: номиналы одного продукта продаются по разным ценам,
 * и Google для такого случая предписывает AggregateOffer (lowPrice/highPrice/
 * offerCount) на одном Product — вместо отдельного Product на каждый номинал,
 * то есть без отдельных страниц-дублей. Диапазон считается из тех же данных,
 * что и витрина (effectivePrice вариантов); без доступных вариантов разметки
 * нет (null) — Offer без цены запрещён так же, как у обычной карточки.
 */
export function giftCardProductSchema(
  p: Product,
  range: { low: number; high: number; count: number } | null,
  opts?: { images?: string[] },
): Record<string, unknown> | null {
  if (!range || range.low <= 0) return null;
  const cat = typeof p.category === 'object' && p.category ? p.category : null;
  const currency = p.currency || 'RUB';
  const url = `${site.url}/product/${p.slug}`;
  const images = opts?.images?.length ? opts.images : [`${site.url}/og-default.png`];
  return {
    '@context': 'https://schema.org',
    '@type': 'Product',
    '@id': `${url}#product`,
    url,
    name: p.name,
    sku: p.sku,
    image: images,
    description: p.short_description || p.meta_description || p.name,
    ...(p.vendor ? { brand: { '@type': 'Brand', name: p.vendor } } : {}),
    ...(cat ? { category: cat.name } : {}),
    offers: {
      '@type': 'AggregateOffer',
      url,
      priceCurrency: currency,
      lowPrice: range.low,
      highPrice: range.high,
      offerCount: range.count,
      availability: 'https://schema.org/InStock',
      seller: { '@id': ORG_ID },
      ...offerLogistics(currency),
    },
  };
}

export function itemListSchema(category: Category, products: Product[], pagePath?: string) {
  return {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: category.meta_title || category.name,
    description: category.meta_description || category.seo_text || '',
    ...(pagePath ? { url: canonicalUrl(pagePath) } : {}),
    isPartOf: { '@id': WEBSITE_ID },
    mainEntity: {
      '@type': 'ItemList',
      itemListElement: products.map((p, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        url: `${site.url}/product/${p.slug}`,
        name: p.name,
      })),
    },
  };
}

/** CollectionPage + ItemList для посадочной (напр. /vendors/zoom). */
export function collectionPageSchema(opts: { name: string; description: string; url: string; items: { name: string; slug: string }[] }) {
  return {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: opts.name,
    description: opts.description,
    url: canonicalUrl(opts.url),
    inLanguage: 'ru-RU',
    isPartOf: { '@id': `${site.url}/#website` },
    about: { '@id': ORG_ID },
    mainEntity: {
      '@type': 'ItemList',
      itemListElement: opts.items.map((it, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        url: `${site.url}/product/${it.slug}`,
        name: it.name,
      })),
    },
  };
}

/**
 * CollectionPage + ItemList для страницы-раздела, элементы которой — не
 * карточки товара, а произвольные страницы сайта (`/alternatives`, `/compare`).
 * Отличается от collectionPageSchema только этим: там URL элемента всегда
 * строится как `/product/<slug>`.
 */
export function sectionListSchema(opts: {
  name: string;
  description: string;
  url: string;
  items: { name: string; url: string }[];
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: opts.name,
    description: opts.description,
    url: canonicalUrl(opts.url),
    inLanguage: 'ru-RU',
    isPartOf: { '@id': WEBSITE_ID },
    about: { '@id': ORG_ID },
    mainEntity: {
      '@type': 'ItemList',
      itemListElement: opts.items.map((it, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        url: canonicalUrl(it.url),
        name: it.name,
      })),
    },
  };
}

export function faqSchema(faq: { q: string; a: string }[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faq.map((f) => ({
      '@type': 'Question',
      name: f.q,
      acceptedAnswer: { '@type': 'Answer', text: f.a },
    })),
  };
}
