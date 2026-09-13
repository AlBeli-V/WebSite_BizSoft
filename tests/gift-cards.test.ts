/**
 * Подарочные карты (product_type = gift_card): пакет Apple, стратегия цены,
 * порядок номиналов, индексная матрица.
 *
 * Проверяются инварианты задания руководителя от 05.09.2026: 28 вариантов
 * (RU 14, TR 10, KZ 4), контрольное соответствие «номинал → закупка»
 * (1000 RUB = 13.83, 900 RUB = 13.65), цена = закупка × курс × 3,00 (ровно ×3,
 * не ×4), номиналы внутри региона по убыванию независимо от порядка в базе,
 * цены, наличия и артикула; вариант не индексируется, родитель — индексируется;
 * закупка в ответ агенту не попадает.
 */
import { describe, expect, it } from 'vitest';
import { parseSku } from '../src/lib/sku';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { computePegRub, defaultMarkupCoeff, markupCoeffOf } from '../src/lib/pricing';
import { DEFAULT_MARKUP_COEFF, GIFT_CARD_MARKUP_COEFF, type Product } from '../src/lib/types';
import { productNoindex, isGiftCard, isVariant, listingProducts } from '../src/lib/catalog';
import { groupGiftCardVariants, giftCardPriceRange, pickInitialVariant, formatDenomination, REGION_ORDER } from '../src/lib/gift-cards';
import { giftCardProductSchema } from '../src/lib/seo';
import { toAgentProductFull } from '../src/webmcp/adapters';
import { VENDORS } from '../src/data/vendors';
import { GIFT_CARD_CONTENT } from '../src/data/gift-cards';
import { buildPlan } from '../src/lib/bulk-import';

interface PkgProduct {
  sku: string; slug: string; name: string; status: string; category: string;
  product_type?: string; parent_sku?: string; region_code?: string; region_name?: string;
  denomination?: number; denomination_currency?: string; base_price_usd?: number; markup_coeff?: number;
  short_description?: string; price_from?: boolean;
}
const pkg = JSON.parse(readFileSync(resolve(__dirname, '../scripts/catalog/apple.json'), 'utf8')) as {
  vendor_entry: { slug: string; vendor: string }; products: PkgProduct[];
};
const parent = pkg.products.find((p) => !p.parent_sku)!;
const variants = pkg.products.filter((p) => p.parent_sku);

// Таблица задания: регион → [номинал, закупка USD].
const EXPECTED: Record<string, [number, number][]> = {
  RU: [[9000, 138.88], [8000, 123.32], [7000, 107.77], [6000, 92.21], [5000, 69.26], [4000, 55.42], [3000, 42.18],
    [2000, 27.30], [1500, 20.47], [1000, 13.83], [900, 13.65], [800, 12.33], [700, 10.72], [500, 7.02]],
  TR: [[2000, 41.76], [1750, 36.51], [1500, 30.87], [1250, 25.72], [1000, 20.58], [799, 17.40], [750, 15.45],
    [600, 12.36], [500, 10.29], [400, 8.24]],
  KZ: [[10000, 36.36], [5000, 16.16], [3000, 10.10], [2000, 7.58]],
};

/** Пакетная позиция → объект Product, как он приходит из Directus (цена при курсе 80). */
function asProduct(p: PkgProduct, over: Partial<Product> = {}): Product {
  const price = computePegRub(
    { peg_to_usd: true, peg_currency: 'USD', base_price_usd: p.base_price_usd ?? null, base_price_eur: null, markup_coeff: p.markup_coeff ?? null },
    { usd: 80, eur: null },
  ) ?? 0;
  return {
    id: p.sku, name: p.name, sku: p.sku, slug: p.slug, vendor: 'Apple', category: null, price, currency: 'RUB', status: 'published',
    product_type: 'gift_card', parent_sku: p.parent_sku ?? null, region_code: p.region_code ?? null, region_name: p.region_name ?? null,
    denomination: p.denomination ?? null, denomination_currency: p.denomination_currency ?? null, availability: 'in_stock',
    base_price_usd: p.base_price_usd ?? null, markup_coeff: p.markup_coeff ?? null, peg_to_usd: true, peg_currency: 'USD',
    ...over,
  } as Product;
}

describe('пакет Apple: вендор и родитель', () => {
  it('вендор Apple заведён в VENDORS и совпадает с пакетом', () => {
    const entry = VENDORS.find((v) => v.slug === 'apple');
    expect(entry?.vendor).toBe('Apple');
    expect(pkg.vendor_entry.vendor).toBe('Apple');
    expect(entry?.catSeg).toBe('gift-cards');
  });

  it('один родитель со страницей app-store-itunes-gift-card, тип gift_card, цена «от»', () => {
    expect(parent.slug).toBe('app-store-itunes-gift-card');
    expect(parent.sku).toBe('APPL-GFT-APPSTORE-UNI-BAL-NOM');
    expect(parent.name).toBe('Apple App Store & iTunes Gift Card');
    expect(parent.product_type).toBe('gift_card');
    expect(parent.price_from).toBe(true);
    expect(parent.status).toBe('published');
    // Закупка родителя — минимальная закупка варианта: цена «от» переоценивается вместе с ними.
    expect(parent.base_price_usd).toBe(Math.min(...variants.map((v) => v.base_price_usd!)));
    expect(parent.markup_coeff).toBe(GIFT_CARD_MARKUP_COEFF);
    expect(GIFT_CARD_CONTENT[parent.slug], 'нет редакторского контента страницы').toBeTruthy();
  });
});

describe('пакет Apple: 28 вариантов', () => {
  it('RU = 14, TR = 10, KZ = 4, все опубликованы и ссылаются на родителя', () => {
    expect(variants.length).toBe(28);
    const by = (code: string) => variants.filter((v) => v.region_code === code);
    expect(by('RU').length).toBe(14);
    expect(by('TR').length).toBe(10);
    expect(by('KZ').length).toBe(4);
    for (const v of variants) {
      expect(v.parent_sku).toBe(parent.sku);
      expect(v.product_type).toBe('gift_card');
      expect(v.status).toBe('published');
      expect(v.category).toBe('gift-cards');
      expect(v.sku).toBe(`${parent.sku}-${v.region_code}${v.denomination}`);
    }
  });

  it('каждый номинал несёт закупку из таблицы задания (1000 RUB = 13.83, 900 RUB = 13.65)', () => {
    for (const [code, rows] of Object.entries(EXPECTED)) {
      for (const [denomination, cost] of rows) {
        const v = variants.find((x) => x.region_code === code && x.denomination === denomination);
        expect(v, `${code} ${denomination}`).toBeTruthy();
        expect(v!.base_price_usd, `${code} ${denomination}`).toBe(cost);
        expect(v!.markup_coeff).toBe(GIFT_CARD_MARKUP_COEFF);
      }
    }
    const ru1000 = variants.find((v) => v.region_code === 'RU' && v.denomination === 1000)!;
    const ru900 = variants.find((v) => v.region_code === 'RU' && v.denomination === 900)!;
    expect(ru1000.base_price_usd).toBe(13.83);
    expect(ru900.base_price_usd).toBe(13.65);
  });

  it('валюта номинала соответствует региону, названия и краткие описания различимы', () => {
    const cur: Record<string, string> = { RU: 'RUB', TR: 'TRY', KZ: 'KZT' };
    for (const v of variants) expect(v.denomination_currency).toBe(cur[v.region_code!]);
    expect(new Set(variants.map((v) => v.name)).size).toBe(28);
    expect(new Set(variants.map((v) => v.short_description)).size).toBe(28);
  });
});

describe('стратегия цены gift_card', () => {
  it('коэффициент по умолчанию: подарочные карты ×3,00, остальное ×1,85', () => {
    expect(defaultMarkupCoeff({ product_type: 'gift_card' })).toBe(3);
    expect(defaultMarkupCoeff({ product_type: null })).toBe(DEFAULT_MARKUP_COEFF);
    expect(defaultMarkupCoeff(undefined)).toBe(DEFAULT_MARKUP_COEFF);
    expect(markupCoeffOf({ product_type: 'gift_card', markup_coeff: null })).toBe(3);
    expect(markupCoeffOf({ product_type: 'gift_card', markup_coeff: 2.5 })).toBe(2.5);
  });

  it('price_rub = cost_usd × курс × 3 (не ×4), номинал в расчёте не участвует', () => {
    const rate = 80;
    const tr2000 = variants.find((v) => v.region_code === 'TR' && v.denomination === 2000)!;
    const rub = computePegRub(
      { peg_to_usd: true, peg_currency: 'USD', base_price_usd: tr2000.base_price_usd!, base_price_eur: null, markup_coeff: tr2000.markup_coeff! },
      { usd: rate, eur: null },
    );
    expect(rub).toBe(Math.round(41.76 * rate * 3)); // 10022
    expect(rub).not.toBe(Math.round(41.76 * rate * 4));
    expect(rub).not.toBe(Math.round(2000 * rate));
    // При курсе 80 ₽: 1000 RUB = 13.83 × 80 × 3 = 3319 ₽; 900 RUB = 3276 ₽.
    const ru1000 = asProduct(variants.find((v) => v.region_code === 'RU' && v.denomination === 1000)!);
    const ru900 = asProduct(variants.find((v) => v.region_code === 'RU' && v.denomination === 900)!);
    expect(ru1000.price).toBe(3319);
    expect(ru900.price).toBe(3276);
  });

  it('импорт строки gift_card без markup_coeff считает цену по ×3', () => {
    const plan = buildPlan(
      [{ sku: 'X-GIFT-CARD-RU-100', name: 'X 100', product_type: 'gift_card', base_price_usd: '10', region_code: 'RU', denomination: '100', availability: 'limited' }],
      [], () => null, { rates: { usd: 80, eur: null } },
    );
    expect(plan.items[0].errors).toEqual([]);
    expect(plan.items[0].payload.price).toBe(2400);
    expect(plan.items[0].payload.product_type).toBe('gift_card');
    expect(plan.items[0].payload.availability).toBe('limited');
    expect(plan.items[0].payload.denomination).toBe(100);
    // Обычная строка — прежний коэффициент 1,85.
    const usual = buildPlan([{ sku: 'Y', name: 'Y', base_price_usd: '10' }], [], () => null, { rates: { usd: 80, eur: null } });
    expect(usual.items[0].payload.price).toBe(1480);
  });
});

describe('группировка и порядок номиналов', () => {
  const shuffled = [...variants].sort((a, b) => a.sku.localeCompare(b.sku)); // алфавит ≠ номинал
  const products = shuffled.map((v, i) => asProduct(v, { id: 1000 - i, sort: i % 3 }));
  const regions = groupGiftCardVariants(products);

  it('регионы в порядке задания: Россия, Казахстан, Турция', () => {
    expect(regions.map((r) => r.code)).toEqual(REGION_ORDER);
    expect(regions.map((r) => r.name)).toEqual(['Россия', 'Казахстан', 'Турция']);
  });

  it('внутри региона denomination DESC — независимо от id, sort, цены и наличия', () => {
    for (const r of regions) {
      const d = r.variants.map((v) => v.denomination);
      expect(d, r.code).toEqual([...d].sort((a, b) => b - a));
    }
    expect(regions[0].variants.map((v) => v.denomination)).toEqual([9000, 8000, 7000, 6000, 5000, 4000, 3000, 2000, 1500, 1000, 900, 800, 700, 500]);
    // Наличие и цена порядок не меняют.
    const withSoldOut = groupGiftCardVariants(products.map((p, i) => ({ ...p, availability: i % 2 ? 'out_of_stock' : 'in_stock', price: 1 })));
    expect(withSoldOut[2].variants.map((v) => v.denomination)).toEqual([2000, 1750, 1500, 1250, 1000, 799, 750, 600, 500, 400]);
  });

  it('вариант без региона или номинала в витрину не попадает', () => {
    const broken = groupGiftCardVariants([asProduct(variants[0], { region_code: null }), asProduct(variants[1], { denomination: 0 })]);
    expect(broken).toEqual([]);
  });

  it('диапазон цен, начальный вариант по ?sku и подпись номинала', () => {
    const range = giftCardPriceRange(regions)!;
    expect(range.count).toBe(28);
    expect(range.low).toBe(asProduct(variants.find((v) => v.base_price_usd === 7.02)!).price);
    expect(range.high).toBe(asProduct(variants.find((v) => v.base_price_usd === 138.88)!).price);
    expect(pickInitialVariant(regions, 'appl-gft-appstore-uni-bal-nom-tr2000')?.sku).toBe('APPL-GFT-APPSTORE-UNI-BAL-NOM-TR2000');
    expect(pickInitialVariant(regions, null)?.denomination).toBe(9000);
    // Intl ставит между разрядами узкий неразрывный пробел — сравниваем без него.
    const plain = (s: string) => s.replace(/[\s\u00a0\u202f]/g, '');
    expect(plain(formatDenomination({ denomination: 9000, currency: 'RUB' }))).toBe('9000₽');
    expect(plain(formatDenomination({ denomination: 2000, currency: 'TRY' }))).toBe('2000₺');
    expect(plain(formatDenomination({ denomination: 10000, currency: 'KZT' }))).toBe('10000₸');
  });
});

describe('индексная матрица и списки', () => {
  it('варианты не индексируются, родитель индексируется', () => {
    for (const v of variants) expect(productNoindex(v.sku), v.sku).toBe(true);
    expect(productNoindex(parent.sku)).toBe(false);
    expect(productNoindex('STM-GFT-WALLET-UNI-BAL-NOM-RU1000')).toBe(true);
    expect(productNoindex('STM-GFT-WALLET-UNI-BAL-NOM')).toBe(false);
    // Регион Global и вариант-подписка (код тарифа вместо номинала).
    expect(productNoindex('DISC-GFT-NITRO-UNI-12M-NOM-GL')).toBe(true);
    expect(productNoindex('BNCE-GFT-USDT-UNI-BAL-NOM-GL500')).toBe(true);
    expect(productNoindex('DISC-GFT-NITRO-UNI-BAL-NOM')).toBe(false);
    expect(productNoindex('BNCE-GFT-USDT-UNI-BAL-NOM')).toBe(false);
  });

  it('isGiftCard / isVariant / listingProducts', () => {
    const all = [asProduct(parent), ...variants.map((v) => asProduct(v))];
    expect(all.every(isGiftCard)).toBe(true);
    expect(isVariant(all[0])).toBe(false);
    expect(all.slice(1).every(isVariant)).toBe(true);
    expect(listingProducts(all).map((p) => p.sku)).toEqual([parent.sku]);
  });
});

describe('разметка и ответ агенту', () => {
  it('Product + AggregateOffer с диапазоном витрины; без диапазона — null', () => {
    const p = asProduct(parent);
    const ld = giftCardProductSchema(p, { low: 1000, high: 9000, count: 28 })!;
    expect(ld['@type']).toBe('Product');
    const offers = ld.offers as Record<string, unknown>;
    expect(offers['@type']).toBe('AggregateOffer');
    expect(offers.lowPrice).toBe(1000);
    expect(offers.highPrice).toBe(9000);
    expect(offers.offerCount).toBe(28);
    expect(offers.url).toBe('https://biz-soft.pro/product/app-store-itunes-gift-card');
    expect(giftCardProductSchema(p, null)).toBeNull();
    expect(giftCardProductSchema(p, { low: 0, high: 0, count: 0 })).toBeNull();
  });

  it('закупка варианта не уходит агенту', () => {
    const full = toAgentProductFull(asProduct(variants[0]));
    const json = JSON.stringify(full);
    for (const secret of ['base_price', 'markup', 'peg_']) expect(json).not.toContain(secret);
    expect(full.price).toBeGreaterThan(0);
  });
});

/**
 * Общие инварианты всех пакетов подарочных карт (Apple, Airalo, Binance,
 * Discord): родитель со страницей и ценой «от», варианты — с регионом,
 * номиналом и закупкой, подпись у не денежных вариантов, мета родителя в
 * партии описаний, редакторский контент страницы.
 */
describe('все пакеты подарочных карт', () => {
  const dir = resolve(__dirname, '../scripts/catalog');
  const batch = JSON.parse(readFileSync(resolve(__dirname, '../data/seo/product-descriptions.json'), 'utf8')) as { products: Record<string, unknown> };
  const packages = ['apple', 'airalo', 'binance', 'discord'].map((slug) => ({
    slug,
    pkg: JSON.parse(readFileSync(resolve(dir, `${slug}.json`), 'utf8')) as { vendor_entry: { vendor: string; slug: string }; products: PkgProduct[] },
  }));

  it('вендоры заведены в VENDORS с разделом gift-cards', () => {
    for (const { slug, pkg } of packages) {
      const entry = VENDORS.find((v) => v.slug === slug);
      expect(entry?.vendor, slug).toBe(pkg.vendor_entry.vendor);
      expect(entry?.catSeg, slug).toBe('gift-cards');
      expect(entry?.domain, slug).toBe('gift');
    }
  });

  it('родители: страница, цена «от» от минимальной закупки, мета и контент', () => {
    for (const { slug, pkg } of packages) {
      const parents = pkg.products.filter((p) => !p.parent_sku);
      expect(parents.length, slug).toBeGreaterThan(0);
      for (const parent of parents) {
        const kids = pkg.products.filter((p) => p.parent_sku === parent.sku);
        expect(kids.length, parent.sku).toBeGreaterThan(0);
        expect(parent.sku, parent.sku).toMatch(/^[A-Z0-9]{2,4}-GFT-[A-Z0-9]+-UNI-BAL-NOM$/);
        expect(productNoindex(parent.sku), parent.sku).toBe(false);
        expect(parent.price_from, parent.sku).toBe(true);
        expect(parent.markup_coeff, parent.sku).toBe(GIFT_CARD_MARKUP_COEFF);
        expect(parent.base_price_usd, parent.sku).toBe(Math.min(...kids.map((k) => k.base_price_usd!)));
        expect(GIFT_CARD_CONTENT[parent.slug], `нет контента страницы ${parent.slug}`).toBeTruthy();
        expect(batch.products[parent.slug], `нет меты ${parent.slug} в product-descriptions.json`).toBeTruthy();
      }
    }
  });

  it('варианты: регион, номинал, закупка, ×3, подпись у подписок, noindex', () => {
    for (const { slug, pkg } of packages) {
      for (const v of pkg.products.filter((p) => p.parent_sku)) {
        // Вариант — GFT с различителем; подписка на срок несёт свой срок, а не BAL родителя.
        expect(parseSku(v.sku)?.kind, v.sku).toBe('GFT');
        expect(parseSku(v.sku)?.variant, v.sku).toBeTruthy();
        expect(productNoindex(v.sku), v.sku).toBe(true);
        expect(v.region_code, v.sku).toMatch(/^[A-Z]{2,6}$/);
        expect(String(v.region_name || '').length, v.sku).toBeGreaterThan(2);
        expect(v.denomination, v.sku).toBeGreaterThan(0);
        expect(v.base_price_usd, v.sku).toBeGreaterThan(0);
        expect(v.markup_coeff, v.sku).toBe(GIFT_CARD_MARKUP_COEFF);
        expect(v.product_type, v.sku).toBe('gift_card');
        const monetary = /^[A-Z]{3}$/.test(String(v.denomination_currency)) && v.denomination_currency !== 'MON';
        if (v.denomination_currency === 'MONTH') expect(String((v as { variant_label?: string }).variant_label || '').length, `${v.sku}: подпись подписки`).toBeGreaterThan(5);
        else expect(monetary, `${v.sku}: валюта номинала ${v.denomination_currency}`).toBe(true);
      }
      expect(new Set(pkg.products.map((p) => p.slug)).size, slug).toBe(pkg.products.length);
    }
  });

  it('группировка: у Global-карт один регион, номиналы по убыванию, подпись из variant_label', () => {
    const discord = packages.find((p) => p.slug === 'discord')!.pkg.products.filter((p) => p.parent_sku);
    const regions = groupGiftCardVariants(discord.map((v) => asProduct(v, { variant_label: (v as { variant_label?: string }).variant_label ?? null })));
    expect(regions.length).toBe(1);
    expect(regions[0].code).toBe('GLOBAL');
    expect(regions[0].variants[0].label).toBe('Discord Nitro, 12 месяцев');
    expect(regions[0].variants.map((v) => v.denomination)).toEqual([12, 1, 1]);
  });
});
