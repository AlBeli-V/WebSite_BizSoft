/**
 * Построители JSON-LD разметки. Чистые функции, возвращают объекты,
 * которые сериализуются в <script type="application/ld+json">.
 */
import { site, seller } from '../config/site';
import { effectivePrice } from './pricing';
import type { Product, Category } from './types';

const ORG_ID = `${site.url}/#organization`;

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

export function productSchema(p: Product) {
  const eff = effectivePrice(p);
  const schema: Record<string, unknown> = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: p.name,
    sku: p.sku,
    description: p.short_description || p.meta_description || p.name,
    brand: { '@type': 'Brand', name: p.vendor || seller.brand },
  };
  if (eff.price > 0) {
    // Цена известна — обычное предложение.
    schema.offers = {
      '@type': 'Offer',
      url: `${site.url}/product/${p.slug}/`,
      priceCurrency: p.currency || 'RUB',
      price: eff.price,
      availability: 'https://schema.org/InStock',
      seller: { '@id': ORG_ID },
      ...(eff.isPromo && p.promo_end ? { priceValidUntil: p.promo_end } : {}),
    };
  } else {
    // Цена по запросу — предложение без конкретной цены.
    schema.offers = {
      '@type': 'Offer',
      url: `${site.url}/product/${p.slug}/`,
      priceCurrency: p.currency || 'RUB',
      availability: 'https://schema.org/InStock',
      seller: { '@id': ORG_ID },
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
        url: `${site.url}/product/${p.slug}/`,
        name: p.name,
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
