/**
 * WebMCP-адаптеры: существующая доменная модель → ответ для AI-агента.
 *
 * Единственный источник данных — те же модули, что кормят витрину и разметку:
 * Directus (через lib/directus), effectivePrice (lib/pricing), реестр
 * вендоров (data/vendors) и слаги лендингов (lib/vendor-links). Никакой
 * собственной базы товаров/цен у WebMCP-слоя нет и быть не должно.
 *
 * Поля отдаются ТОЛЬКО по белому списку. Внутренняя экономика
 * (base_price_usd/eur, markup_coeff, purchase_source и т.п.) в ответы
 * не попадает — как и в HTML, и в фиды. Тест: tests/webmcp-adapters.test.ts.
 */
import type { Category, Product } from '../lib/types';
import type { PolicyItem } from '../data/policies';
import { LICENSE_LABEL } from '../lib/types';
import { effectivePrice } from '../lib/pricing';
import { productKind, PRODUCT_KIND_LABEL, vendorLegal } from '../lib/catalog';
import { vendorSlug } from '../lib/vendor-links';
import { VENDORS } from '../data/vendors';
import { site, taxation } from '../config/site';

/** Краткая карточка для списков (поиск, товары вендора). */
export interface AgentProductBrief {
  name: string;
  vendor: string | null;
  sku: string;
  /** Абсолютный адрес карточки на сайте. */
  url: string;
  /** Цена в рублях с НДС; null — «цена по запросу». */
  price: number | null;
  currency: string;
  price_note: string | null;
  kind: string;
  license: string | null;
}

export interface AgentProductFull extends AgentProductBrief {
  slug: string;
  category: string | null;
  vendor_legal: string | null;
  description: string | null;
  promo: { label: string; old_price: number; valid_until: string | null } | null;
  features: string[];
  for_whom: string | null;
  /** Условия приобретения — те же формулировки, что видит человек на сайте. */
  purchase_terms: string[];
}

export interface AgentCategory {
  name: string;
  slug: string;
  url: string;
  products_count: number;
}

/** Ответ об условиях работы: тот же текст, что человек читает на странице. */
export interface AgentPolicy {
  id: string;
  question: string;
  answer: string;
  /** Страница сайта с этим ответом — агенту есть куда отправить человека. */
  url: string;
}

export interface AgentVendor {
  vendor: string;
  title: string;
  url: string;
  legal_name: string | null;
  products_count: number;
  about: string | null;
}

const BY_REQUEST_NOTE = 'Цена по запросу: рассчитывается по заявке со страницы товара.';

export function productUrl(slug: string): string {
  return `${site.url}/product/${slug}`;
}

export function vendorUrl(vendorName: string): string {
  return `${site.url}/vendors/${vendorSlug(vendorName)}`;
}

export function categoryUrl(slug: string): string {
  return `${site.url}/catalog/${slug}`;
}

export function toAgentCategory(c: Category, productsCount: number): AgentCategory {
  return {
    name: c.name,
    slug: c.slug,
    url: categoryUrl(c.slug),
    products_count: productsCount,
  };
}

export function toAgentPolicy(p: PolicyItem): AgentPolicy {
  return {
    id: p.id,
    question: p.question,
    answer: p.answer,
    url: `${site.url}${p.path}`,
  };
}

export function toAgentProductBrief(p: Product): AgentProductBrief {
  const eff = effectivePrice(p);
  const byRequest = !(eff.price > 0);
  return {
    name: p.name,
    vendor: p.vendor || null,
    sku: p.sku,
    url: productUrl(p.slug),
    price: byRequest ? null : eff.price,
    currency: p.currency || 'RUB',
    price_note: byRequest ? BY_REQUEST_NOTE : (p.price_from ? 'Цена «от»: итог зависит от конфигурации.' : null),
    kind: PRODUCT_KIND_LABEL[productKind(p)],
    license: p.license_type ? LICENSE_LABEL[p.license_type] : null,
  };
}

/** Единые условия приобретения (собраны из констант сайта, не дублируются руками). */
export function purchaseTerms(): string[] {
  return [
    'Оформление на юридическое лицо или ИП: договор и оплата по счёту.',
    taxation.priceLine,
    taxation.docsLine,
    `Коммерческое предложение действует ${site.quoteValidDays} дней с даты выставления.`,
  ];
}

export function toAgentProductFull(p: Product): AgentProductFull {
  const eff = effectivePrice(p);
  const brief = toAgentProductBrief(p);
  const cat = typeof p.category === 'object' && p.category ? p.category.name : null;
  return {
    ...brief,
    slug: p.slug,
    category: cat,
    vendor_legal: p.vendor ? vendorLegal(p.vendor) : null,
    description: p.short_description || null,
    promo: eff.isPromo && eff.oldPrice != null
      ? { label: eff.promoLabel || 'Акция', old_price: eff.oldPrice, valid_until: p.promo_end || null }
      : null,
    features: (p.features || []).slice(0, 12),
    for_whom: p.for_whom || null,
    purchase_terms: purchaseTerms(),
  };
}

/**
 * Карточка вендора для агента. Имя вендора приходит и человеческое
 * («JetBrains»), и слагом («jetbrains») — сравниваем по обоим.
 */
export function resolveVendorName(
  input: string,
  known: { vendor: string; count: number }[],
): { vendor: string; count: number } | null {
  const needle = input.trim().toLowerCase();
  if (!needle) return null;
  return (
    known.find((v) => v.vendor.toLowerCase() === needle)
    || known.find((v) => vendorSlug(v.vendor) === needle)
    // Отображаемое имя из реестра лендингов (например «Magnific» → «Magnific (Freepik)»)
    || known.find((v) => {
      const entry = VENDORS.find((e) => e.vendor === v.vendor);
      return entry ? (entry.title || '').toLowerCase() === needle || entry.slug === needle : false;
    })
    || null
  );
}

export function toAgentVendor(v: { vendor: string; count: number }): AgentVendor {
  const entry = VENDORS.find((e) => e.vendor === v.vendor);
  return {
    vendor: v.vendor,
    title: entry?.title || v.vendor,
    url: vendorUrl(v.vendor),
    legal_name: entry?.legalName || vendorLegal(v.vendor) || null,
    products_count: v.count,
    about: entry?.tagline || null,
  };
}
