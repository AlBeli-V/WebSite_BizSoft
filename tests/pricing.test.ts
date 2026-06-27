import { describe, it, expect } from 'vitest';
import {
  roundPrice,
  isPromoActive,
  effectivePrice,
  pegPrice,
  applyBulkValue,
  previewBulkChange,
} from '../src/lib/pricing';
import type { Product } from '../src/lib/types';

function product(overrides: Partial<Product> = {}): Product {
  return {
    id: 1,
    name: 'Test',
    sku: 'SKU-1',
    category: null,
    slug: 'test',
    price: 1000,
    currency: 'RUB',
    status: 'published',
    ...overrides,
  };
}

describe('roundPrice', () => {
  it('rounds to nearest 1/10/100', () => {
    expect(roundPrice(1234.6, 'to1')).toBe(1235);
    expect(roundPrice(1234, 'to10')).toBe(1230);
    expect(roundPrice(1250, 'to100')).toBe(1300);
    expect(roundPrice(1234, 'none')).toBe(1234);
  });
  it('psychological .99 style', () => {
    expect(roundPrice(2000, 'psychological99')).toBe(1999);
    expect(roundPrice(50, 'psychological99')).toBe(99);
  });
  it('never negative', () => {
    expect(roundPrice(-5, 'to1')).toBe(0);
  });
});

describe('isPromoActive', () => {
  const now = new Date('2026-06-27T12:00:00Z');
  it('active within window', () => {
    expect(isPromoActive({ promo_price: 800, promo_start: '2026-06-01', promo_end: '2026-07-31' }, now)).toBe(true);
  });
  it('inactive before start', () => {
    expect(isPromoActive({ promo_price: 800, promo_start: '2026-07-01', promo_end: '2026-07-31' }, now)).toBe(false);
  });
  it('inactive after end', () => {
    expect(isPromoActive({ promo_price: 800, promo_start: '2026-05-01', promo_end: '2026-06-10' }, now)).toBe(false);
  });
  it('inactive without promo_price', () => {
    expect(isPromoActive({ promo_price: null, promo_start: '2026-06-01', promo_end: '2026-07-31' }, now)).toBe(false);
  });
  it('open-ended window', () => {
    expect(isPromoActive({ promo_price: 800 }, now)).toBe(true);
  });
});

describe('effectivePrice', () => {
  const now = new Date('2026-06-27T12:00:00Z');
  it('returns promo when active', () => {
    const p = product({ price: 1000, promo_price: 800, promo_label: '−20%', promo_start: '2026-06-01', promo_end: '2026-07-31' });
    const eff = effectivePrice(p, now);
    expect(eff.price).toBe(800);
    expect(eff.oldPrice).toBe(1000);
    expect(eff.isPromo).toBe(true);
    expect(eff.promoLabel).toBe('−20%');
  });
  it('returns base when no promo', () => {
    const eff = effectivePrice(product({ price: 1000 }), now);
    expect(eff.price).toBe(1000);
    expect(eff.oldPrice).toBeNull();
    expect(eff.isPromo).toBe(false);
  });
});

describe('pegPrice', () => {
  it('computes base*rate*(1+markup)', () => {
    // 100 * 90 * 1.15 = 10350
    expect(pegPrice(100, 90, 15, 'to1')).toBe(10350);
  });
  it('rounds result', () => {
    expect(pegPrice(95, 90.5, 12, 'to10')).toBe(9630); // 95*90.5*1.12=9629.2 → 9630
  });
});

describe('applyBulkValue', () => {
  it('increase percent', () => {
    expect(applyBulkValue(1000, { operation: 'increase', mode: 'percent', amount: 10, target: 'base', rounding: 'to1' })).toBe(1100);
  });
  it('decrease fixed', () => {
    expect(applyBulkValue(1000, { operation: 'decrease', mode: 'fixed', amount: 250, target: 'base', rounding: 'to1' })).toBe(750);
  });
  it('clamps to zero', () => {
    expect(applyBulkValue(100, { operation: 'decrease', mode: 'fixed', amount: 500, target: 'base', rounding: 'to1' })).toBe(0);
  });
});

describe('previewBulkChange', () => {
  it('changes base and promo when target both', () => {
    const products = [product({ sku: 'A', price: 1000, promo_price: 800 })];
    const preview = previewBulkChange(products, { operation: 'increase', mode: 'percent', amount: 10, target: 'both', rounding: 'to1' });
    expect(preview).toHaveLength(2);
    expect(preview.find((p) => p.field === 'price')?.after).toBe(1100);
    expect(preview.find((p) => p.field === 'promo_price')?.after).toBe(880);
  });
  it('skips promo when not set', () => {
    const products = [product({ sku: 'A', price: 1000, promo_price: null })];
    const preview = previewBulkChange(products, { operation: 'increase', mode: 'percent', amount: 10, target: 'both', rounding: 'to1' });
    expect(preview).toHaveLength(1);
    expect(preview[0].field).toBe('price');
  });
  it('omits unchanged', () => {
    const products = [product({ sku: 'A', price: 1000 })];
    const preview = previewBulkChange(products, { operation: 'increase', mode: 'percent', amount: 0, target: 'base', rounding: 'to1' });
    expect(preview).toHaveLength(0);
  });
});
