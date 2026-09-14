/**
 * Инварианты слоя Schema.org (src/lib/seo.ts).
 *
 * Правила, которые закрепляются навсегда:
 * - разметка отражает видимую страницу: цена = effectivePrice (та же
 *   функция, что у витрины), никаких Offer без цены;
 * - «цена по запросу» — товарной разметки нет вовсе (null), а не Offer
 *   с выдуманной ценой;
 * - сущности связаны по @id и не плодят копий BIZSoft;
 * - URL абсолютные, canonical без завершающего слеша, валюта RUB.
 */
import { describe, expect, it } from 'vitest';
import {
  canonicalUrl,
  organizationSchema,
  localBusinessSchema,
  websiteSchema,
  productSchema,
  breadcrumbSchema,
  itemListSchema,
  collectionPageSchema,
  faqSchema,
  ORG_ID,
} from '../src/lib/seo';
import type { Product, Category } from '../src/lib/types';

const category: Category = { id: 1, name: 'AI-сервисы', slug: 'ai', status: 'published' } as Category;

function product(over: Partial<Product> = {}): Product {
  return {
    id: 1,
    name: 'ChatGPT Business',
    sku: 'OPAI-LIC-CHATGPTBUS-TEAM-1Y-USER-STD',
    vendor: 'OpenAI',
    slug: 'chatgpt-business',
    category,
    price: 24900,
    currency: 'RUB',
    status: 'published',
    ...over,
  } as Product;
}

describe('canonicalUrl', () => {
  it('абсолютный, без завершающего слеша, кроме главной', () => {
    expect(canonicalUrl('/')).toBe('https://biz-soft.pro/');
    expect(canonicalUrl('/catalog/')).toBe('https://biz-soft.pro/catalog');
    expect(canonicalUrl('/product/chatgpt-business')).toBe('https://biz-soft.pro/product/chatgpt-business');
  });
});

describe('productSchema', () => {
  it('обычная цена: Offer с price/priceCurrency/availability, url = canonical', () => {
    const s = productSchema(product())!;
    expect(s).not.toBeNull();
    expect(s['@type']).toBe('Product');
    expect(s['@id']).toBe('https://biz-soft.pro/product/chatgpt-business#product');
    expect(s.url).toBe('https://biz-soft.pro/product/chatgpt-business');
    const offer = s.offers as Record<string, unknown>;
    expect(offer.price).toBe(24900);
    expect(offer.priceCurrency).toBe('RUB');
    expect(offer.url).toBe(s.url);
    expect(offer.availability).toBe('https://schema.org/InStock');
    expect(offer.seller).toEqual({ '@id': ORG_ID });
  });

  it('цена по запросу (price <= 0): разметки нет вовсе', () => {
    expect(productSchema(product({ price: 0 }))).toBeNull();
    expect(productSchema(product({ price: -1 }))).toBeNull();
  });

  it('акция: цена — промо, priceValidUntil — конец акции', () => {
    const s = productSchema(product({ promo_price: 19900, promo_end: '2099-12-31' }))!;
    const offer = s.offers as Record<string, unknown>;
    expect(offer.price).toBe(19900);
    expect(offer.priceValidUntil).toBe('2099-12-31');
  });

  it('brand — только реальный производитель, без фолбэка на BIZSoft', () => {
    const withVendor = productSchema(product())!;
    expect(withVendor.brand).toEqual({ '@type': 'Brand', name: 'OpenAI' });
    const noVendor = productSchema(product({ vendor: null }))!;
    expect(noVendor.brand).toBeUndefined();
    expect(JSON.stringify(noVendor)).not.toContain('"Brand","name":"BIZSoft"');
  });

  it('image всегда присутствует (галерея либо брендовый фолбэк)', () => {
    const fallback = productSchema(product())!;
    expect(fallback.image).toEqual(['https://biz-soft.pro/og-default.png']);
    const gallery = productSchema(product(), { images: ['https://biz-soft.pro/img/1.png'] })!;
    expect(gallery.image).toEqual(['https://biz-soft.pro/img/1.png']);
  });

  it('цена совпадает с витриной (effectivePrice), а не с сырым полем', () => {
    // Промо активно — витрина показывает промо-цену, разметка обязана тоже.
    const s = productSchema(product({ price: 100, promo_price: 90 }))!;
    expect((s.offers as Record<string, unknown>).price).toBe(90);
  });
});

describe('сущности организации и сайта', () => {
  it('Organization и LocalBusiness — один узел (@id совпадает)', () => {
    const org = organizationSchema();
    const lb = localBusinessSchema();
    expect(org['@id']).toBe(ORG_ID);
    expect(lb['@id']).toBe(ORG_ID);
    expect(lb['@type']).toContain('Organization');
  });

  it('адреса организации совпадают между узлами и не содержат непубличного офиса', () => {
    const org = organizationSchema();
    const lb = localBusinessSchema();
    expect(org.address).toEqual(lb.address);
    expect(JSON.stringify(org.address)).not.toContain('378');
  });

  it('локальный профиль — расширение того же узла, а не второй узел рядом', () => {
    // Два узла с одним @id потребитель склеивает, и каждое общее поле
    // приходит дважды (ошибка Google «Поле … дублируется»). Поэтому
    // localBusinessSchema — надмножество Organization: страница выводит
    // ровно один узел организации, полный по составу.
    const org = organizationSchema();
    const lb = localBusinessSchema();
    for (const key of Object.keys(org)) {
      if (key === '@type') continue;
      expect(lb[key as keyof typeof lb]).toEqual(org[key as keyof typeof org]);
    }
    expect(lb['@type']).toEqual(['Organization', 'LocalBusiness']);
    expect(lb.openingHoursSpecification).toBeTruthy();
    expect(lb.priceRange).toBeTruthy();
    expect(lb.image).toBeTruthy();
  });

  it('WebSite ссылается на Organization по @id', () => {
    const w = websiteSchema();
    expect(w.publisher).toEqual({ '@id': ORG_ID });
  });
});

describe('списки и цепочки', () => {
  it('breadcrumbSchema: позиции с 1, абсолютные URL', () => {
    const b = breadcrumbSchema([
      { name: 'Главная', url: '/' },
      { name: 'Каталог', url: '/catalog' },
    ]);
    const items = b.itemListElement as { position: number; item: string }[];
    expect(items[0].position).toBe(1);
    for (const it2 of items) expect(String(it2.item)).toMatch(/^https:\/\/biz-soft\.pro/);
  });

  it('itemListSchema: связь с сайтом и canonical url страницы', () => {
    const s = itemListSchema(category, [product()], '/catalog/ai');
    expect(s.isPartOf).toEqual({ '@id': 'https://biz-soft.pro/#website' });
    expect(s.url).toBe('https://biz-soft.pro/catalog/ai');
  });

  it('collectionPageSchema: абсолютные url элементов', () => {
    const s = collectionPageSchema({ name: 'X', description: 'Y', url: '/vendors/zoom', items: [{ name: 'A', slug: 'a' }] });
    expect(s.url).toBe('https://biz-soft.pro/vendors/zoom');
    const el = (s.mainEntity as { itemListElement: { url: string }[] }).itemListElement;
    expect(el[0].url).toBe('https://biz-soft.pro/product/a');
  });

  it('faqSchema: вопрос-ответ без пустых значений', () => {
    const s = faqSchema([{ q: 'Вопрос?', a: 'Ответ.' }]);
    const m = s.mainEntity as { name: string; acceptedAnswer: { text: string } }[];
    expect(m[0].name).toBe('Вопрос?');
    expect(m[0].acceptedAnswer.text).toBe('Ответ.');
  });
});
