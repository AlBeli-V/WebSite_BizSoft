/**
 * Адаптеры WebMCP: единственный источник цены — effectivePrice, поля —
 * только по белому списку (внутренняя экономика не утекает агентам).
 */
import { describe, expect, it } from 'vitest';
import {
  toAgentProductBrief,
  toAgentProductFull,
  toAgentVendor,
  resolveVendorName,
  purchaseTerms,
} from '../src/webmcp/adapters';
import type { Product } from '../src/lib/types';

const product = (over: Partial<Product> = {}): Product => ({
  id: 1,
  name: 'Zoom Workplace Pro',
  sku: 'ZOOM-PRO',
  vendor: 'Zoom',
  category: { id: 1, name: 'Видеосвязь', slug: 'communications', status: 'published' },
  slug: 'zoom-workplace-pro',
  price: 25_000,
  currency: 'RUB',
  status: 'published',
  license_type: 'org',
  // внутренняя экономика — не должна попадать в ответы
  base_price_usd: 120,
  base_price_eur: null,
  peg_currency: 'USD',
  peg_to_usd: true,
  markup_coeff: 1.85,
  purchase_source: 'https://zoom.us/pricing',
  ...over,
});

describe('toAgentProductBrief / toAgentProductFull', () => {
  it('цена — из effectivePrice: активная акция даёт промо-цену и старую цену', () => {
    const p = product({ promo_price: 19_990, promo_label: 'Скидка', promo_start: null, promo_end: null });
    const full = toAgentProductFull(p);
    expect(full.price).toBe(19_990);
    expect(full.promo).toEqual({ label: 'Скидка', old_price: 25_000, valid_until: null });
  });

  it('«цена по запросу» (price <= 0) — price null и пояснение, без выдуманных цифр', () => {
    const b = toAgentProductBrief(product({ price: 0 }));
    expect(b.price).toBeNull();
    expect(b.price_note).toContain('по запросу');
  });

  it('внутренняя экономика не утекает: ни закупки, ни коэффициентов, ни источников', () => {
    const json = JSON.stringify(toAgentProductFull(product()));
    for (const secret of ['base_price', 'markup', 'peg_', 'purchase_source', 'price_locked']) {
      expect(json, `утечка поля ${secret}`).not.toContain(secret);
    }
    expect(json).not.toContain('120'); // сама закупочная цифра
    expect(json).not.toContain('1.85');
  });

  it('url абсолютные и в формате canonical (без завершающего слеша)', () => {
    const full = toAgentProductFull(product());
    expect(full.url).toBe('https://biz-soft.pro/product/zoom-workplace-pro');
  });

  it('лицензия и тип товара — человеческими метками витрины', () => {
    const b = toAgentProductBrief(product());
    expect(b.license).toBe('Для организаций');
    expect(b.kind).toBe('Основной продукт');
    const addon = toAgentProductBrief(product({ sku: 'JB-PLG-RUBY' }));
    expect(addon.kind).toBe('Плагин или дополнение');
  });

  it('условия приобретения собраны из констант сайта (НДС, документы, срок КП)', () => {
    const terms = purchaseTerms().join(' ');
    expect(terms).toContain('НДС');
    expect(terms).toContain('счёт');
    expect(terms).toContain('7 дней');
  });
});

describe('resolveVendorName / toAgentVendor', () => {
  const known = [
    { vendor: 'Zoom', count: 12 },
    { vendor: 'Magnific (Freepik)', count: 4 },
  ];

  it('находит по точному имени без учёта регистра', () => {
    expect(resolveVendorName('zoom', known)?.vendor).toBe('Zoom');
  });

  it('находит по слагу лендинга и по отображаемому имени', () => {
    expect(resolveVendorName('freepik', known)?.vendor).toBe('Magnific (Freepik)');
    expect(resolveVendorName('Magnific', known)?.vendor).toBe('Magnific (Freepik)');
  });

  it('неизвестный вендор — null, без исключений', () => {
    expect(resolveVendorName('НетТакого', known)).toBeNull();
    expect(resolveVendorName('', known)).toBeNull();
  });

  it('карточка вендора: ссылка на лендинг и юрлицо', () => {
    const v = toAgentVendor({ vendor: 'Zoom', count: 12 });
    expect(v.url).toBe('https://biz-soft.pro/vendors/zoom');
    expect(v.legal_name).toContain('Zoom');
    expect(v.products_count).toBe(12);
  });
});
