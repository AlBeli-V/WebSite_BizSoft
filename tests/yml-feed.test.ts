import { describe, it, expect } from 'vitest';
import {
  buildYmlCatalog,
  feedCategories,
  feedOffers,
  isFeedEligible,
  offerName,
  plainText,
  truncate,
  xmlEscape,
  FALLBACK_CATEGORY_ID,
} from '../src/lib/yml-feed';
import type { Category, Product } from '../src/lib/types';

function product(overrides: Partial<Product> = {}): Product {
  return {
    id: 1,
    name: 'Test Pro (годовая)',
    sku: 'TEST-PRO',
    vendor: 'Test',
    origin: 'foreign',
    category: 5,
    slug: 'test-pro',
    price: 1000,
    currency: 'RUB',
    status: 'published',
    ...overrides,
  };
}

const categories: Category[] = [
  { id: 5, name: 'Дизайн', slug: 'design', status: 'published' },
  { id: 7, name: 'Разработка', slug: 'dev', status: 'published' },
];

const opts = { siteUrl: 'https://biz-soft.pro' };

describe('xmlEscape', () => {
  it('escapes xml special chars', () => {
    expect(xmlEscape('Tools & "Co" <b> \'x\'')).toBe('Tools &amp; &quot;Co&quot; &lt;b&gt; &apos;x&apos;');
  });
});

describe('plainText', () => {
  it('flattens markdown to a single line', () => {
    const md = '# Заголовок\n\nТекст с **жирным** и [ссылкой](https://example.com).\n\n- пункт один\n- пункт два';
    expect(plainText(md)).toBe('Заголовок Текст с жирным и ссылкой. • пункт один • пункт два');
  });

  it('drops html tags and images', () => {
    expect(plainText('<p>Абзац</p> ![alt](/img.png) конец')).toBe('Абзац конец');
  });

  it('returns empty string for empty input', () => {
    expect(plainText(null)).toBe('');
    expect(plainText(undefined)).toBe('');
  });
});

describe('truncate', () => {
  it('keeps short strings as is', () => {
    expect(truncate('коротко', 20)).toBe('коротко');
  });

  it('cuts on a word boundary and adds ellipsis', () => {
    expect(truncate('один два три четыре пять', 15)).toBe('один два три…');
  });
});

describe('offerName', () => {
  it('prefixes the vendor when the name lacks it', () => {
    expect(offerName({ name: 'Team (годовая)', vendor: 'Anthropic' })).toBe('Anthropic Team (годовая)');
  });

  it('keeps the name when the vendor is already there', () => {
    expect(offerName({ name: 'Zoom Pro (годовая)', vendor: 'Zoom' })).toBe('Zoom Pro (годовая)');
  });

  it('ignores the legal suffix in the vendor', () => {
    expect(offerName({ name: 'Magnific Premium', vendor: 'Magnific (Freepik)' })).toBe('Magnific Premium');
  });
});

describe('isFeedEligible', () => {
  it('accepts a published foreign product with a price', () => {
    expect(isFeedEligible(product())).toBe(true);
  });

  it('rejects products without a price (цена по запросу)', () => {
    expect(isFeedEligible(product({ price: 0 }))).toBe(false);
  });

  it('rejects drafts, domestic software and noindex cards', () => {
    expect(isFeedEligible(product({ status: 'draft' }))).toBe(false);
    expect(isFeedEligible(product({ origin: 'domestic' }))).toBe(false);
    expect(isFeedEligible(product({ noindex: true }))).toBe(false);
  });

  it('rejects JetBrains plugins and personal licenses by sku', () => {
    expect(isFeedEligible(product({ sku: 'JB-PLG-SONARLINT' }))).toBe(false);
    expect(isFeedEligible(product({ sku: 'JB-IDEA-IND' }))).toBe(false);
  });

  it('includes hidden cards when asked explicitly', () => {
    expect(isFeedEligible(product({ sku: 'JB-PLG-SONARLINT' }), { includeNoindex: true })).toBe(true);
  });

  it('accepts a price-by-request product with an active promo price', () => {
    const p = product({ price: 0, promo_price: 500, promo_start: '2026-01-01', promo_end: '2026-12-31' });
    expect(isFeedEligible(p, { now: new Date('2026-06-01') })).toBe(true);
  });
});

describe('feedOffers', () => {
  it('maps a product to the yandex offer fields', () => {
    const p = product({
      id: 42,
      short_description: 'Короткое описание',
      description: '## Описание\n\nПодробности **тут**.',
    });
    expect(feedOffers([p], opts)).toEqual([
      {
        id: '42',
        name: 'Test Pro (годовая)',
        vendor: 'Test',
        price: 1000,
        categoryId: 5,
        picture: 'https://biz-soft.pro/og/product/test-pro.png',
        description: 'Описание Подробности тут.',
        shortDescription: 'Короткое описание',
        url: 'https://biz-soft.pro/product/test-pro',
      },
    ]);
  });

  it('uses the promo price while the promo is active', () => {
    const p = product({ promo_price: 700, promo_start: '2026-01-01', promo_end: '2026-12-31' });
    expect(feedOffers([p], { ...opts, now: new Date('2026-06-01') })[0].price).toBe(700);
    expect(feedOffers([p], { ...opts, now: new Date('2027-06-01') })[0].price).toBe(1000);
  });

  it('falls back to the placeholder category when the product has none', () => {
    expect(feedOffers([product({ category: null })], opts)[0].categoryId).toBe(FALLBACK_CATEGORY_ID);
  });

  it('reads the category id from an expanded m2o object', () => {
    const category: Category = { id: 7, name: 'Разработка', slug: 'dev', status: 'published' };
    expect(feedOffers([product({ category })], opts)[0].categoryId).toBe(7);
  });

  it('omits empty descriptions instead of emitting blank tags', () => {
    const [offer] = feedOffers([product()], opts);
    expect(offer.description).toBeNull();
    expect(offer.shortDescription).toBeNull();
  });
});

describe('feedCategories', () => {
  it('keeps only categories used by offers', () => {
    const offers = feedOffers([product()], opts);
    expect(feedCategories(offers, categories)).toEqual([{ id: 5, name: 'Дизайн' }]);
  });

  it('adds the placeholder category when needed', () => {
    const offers = feedOffers([product({ category: null })], opts);
    expect(feedCategories(offers, categories)).toEqual([{ id: FALLBACK_CATEGORY_ID, name: 'Прочее ПО' }]);
  });
});

describe('buildYmlCatalog', () => {
  const xml = buildYmlCatalog(
    [
      product({ id: 42, short_description: 'ПО «для всех» & прочее' }),
      product({ id: 43, sku: 'JB-PLG-X', slug: 'plugin' }), // скрытый — не попадёт
      product({ id: 44, sku: 'NO-PRICE', slug: 'no-price', price: 0 }), // без цены — не попадёт
    ],
    categories,
    opts,
  );

  it('renders the template structure', () => {
    expect(xml.startsWith('<?xml version="1.0" encoding="UTF-8"?>\n<yml_catalog>\n    <shop>')).toBe(true);
    expect(xml).toContain('<categories>');
    expect(xml).toContain('<category id="5">Дизайн</category>');
    expect(xml).toContain('</yml_catalog>');
  });

  it('renders one offer per eligible product only', () => {
    expect(xml.match(/<offer /g)?.length).toBe(1);
    expect(xml).toContain('<offer id="42">');
    expect(xml).not.toContain('/product/plugin');
    expect(xml).not.toContain('/product/no-price');
  });

  it('fills the offer fields and escapes text', () => {
    expect(xml).toContain('<name>Test Pro (годовая)</name>');
    expect(xml).toContain('<vendor>Test</vendor>');
    expect(xml).toContain('<price>1000</price>');
    expect(xml).toContain('<currencyId>RUR</currencyId>');
    expect(xml).toContain('<categoryId>5</categoryId>');
    expect(xml).toContain('<picture>https://biz-soft.pro/og/product/test-pro.png</picture>');
    expect(xml).toContain('<url>https://biz-soft.pro/product/test-pro</url>');
    expect(xml).toContain('<shortDescription>ПО «для всех» &amp; прочее</shortDescription>');
  });
});
