/**
 * Построители JSON-LD разметки. Чистые функции, возвращают объекты,
 * которые сериализуются в <script type="application/ld+json">.
 */
import { site, seller, workingHours } from '../config/site';
import { effectivePrice } from './pricing';
import type { Product, Category } from './types';

const ORG_ID = `${site.url}/#organization`;
const WEBSITE_ID = `${site.url}/#website`;

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
    email: seller.email,
    telephone: seller.phone,
    taxID: seller.inn,
    description: site.description,
    address: {
      '@type': 'PostalAddress',
      streetAddress: 'Каширское шоссе 80К1, 378',
      addressLocality: 'Москва',
      postalCode: '115569',
      addressCountry: 'RU',
    },
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

export function localBusinessSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'LocalBusiness',
    '@id': `${site.url}/#localbusiness`,
    name: seller.brand,
    image: `${site.url}/og-default.png`,
    url: site.url,
    telephone: seller.phone,
    email: seller.email,
    priceRange: '₽₽',
    openingHoursSpecification: workingHours.schema,
    address: {
      '@type': 'PostalAddress',
      streetAddress: 'Каширское шоссе 80К1, 378',
      addressLocality: 'Москва',
      postalCode: '115569',
      addressCountry: 'RU',
    },
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
 * Товар — электронный доступ: физической доставки нет (бесплатно, моментально),
 * возврат активированной лицензии не предусмотрен. Значения фактические —
 * закрывают рекомендованные поля Merchant listings в Search Console.
 */
function offerLogistics(currency: string) {
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

export function productSchema(p: Product, opts?: { images?: string[] }) {
  const eff = effectivePrice(p);
  const cat = typeof p.category === 'object' && p.category ? p.category : null;
  const currency = p.currency || 'RUB';
  // image — обязательное поле Product. Берём галерею товара; если её нет,
  // подставляем брендовое изображение по умолчанию, чтобы поле всегда присутствовало.
  const images = opts?.images?.length ? opts.images : [`${site.url}/og-default.png`];
  const schema: Record<string, unknown> = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: p.name,
    sku: p.sku,
    image: images,
    description: p.short_description || p.meta_description || p.name,
    brand: { '@type': 'Brand', name: p.vendor || seller.brand },
    ...(cat ? { category: cat.name } : {}),
  };
  if (eff.price > 0) {
    // Цена известна — обычное предложение.
    schema.offers = {
      '@type': 'Offer',
      // Без завершающего слеша: canonical карточки и фиды используют форму
      // /product/<slug>, и Offer.url обязан совпадать с ними, иначе робот
      // видит два разных URL одного предложения.
      url: `${site.url}/product/${p.slug}`,
      priceCurrency: currency,
      price: eff.price,
      availability: 'https://schema.org/InStock',
      seller: { '@id': ORG_ID },
      ...offerLogistics(currency),
      ...(eff.isPromo && p.promo_end ? { priceValidUntil: p.promo_end } : {}),
    };
  } else {
    // Цена по запросу — предложение без конкретной цены.
    schema.offers = {
      '@type': 'Offer',
      url: `${site.url}/product/${p.slug}`,
      priceCurrency: currency,
      availability: 'https://schema.org/InStock',
      seller: { '@id': ORG_ID },
      ...offerLogistics(currency),
    };
  }
  return schema;
}

export function itemListSchema(category: Category, products: Product[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: category.meta_title || category.name,
    description: category.meta_description || category.seo_text || '',
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
