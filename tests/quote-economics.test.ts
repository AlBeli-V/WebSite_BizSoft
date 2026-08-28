/**
 * Экономика сделки: базы расходов — решения руководителя 28.08.2026.
 *
 * Проверяются именно базы, а не только арифметика: налог 7% — от полной
 * выручки с НДС, резерв 10% — от закупки, НДС — изнутри цены (5/105).
 * Перепутанная база тут не «неточность», а неверная цена сделки.
 */
import { describe, expect, it } from 'vitest';
import { buildQuoteEconomics, usdReference } from '../src/lib/quote-economics';
import type { Product } from '../src/lib/types';

const fx = { usd: 85, eur: 92, date: '28.08.2026' };

const product = (sku: string, extra: Partial<Product> = {}): Product => ({
  id: 1, name: sku, sku, vendor: 'v', origin: '', slug: sku.toLowerCase(),
  price: 0, currency: 'RUB', status: 'published', ...extra,
} as unknown as Product);

const items = [
  { sku: 'A', name: 'Товар А', qty: 10, price: 105000, sum: 1050000 },
];

describe('экономика сделки', () => {
  const eco = buildQuoteEconomics(items,
    [product('A', { base_price_usd: 700 })], fx);

  it('закупка — по курсу ЦБ: $700 × 10 × 85 = 595 000 ₽', () => {
    expect(eco.purchaseRub).toBe(595000);
    expect(eco.purchaseByCurrency.USD).toBe(7000);
    expect(eco.complete).toBe(true);
  });

  it('НДС выделен изнутри цены: 1 050 000 × 5/105 = 50 000', () => {
    expect(eco.vat).toBe(50000);
  });

  it('налог 7% — от полной выручки с НДС (решение 28.08.2026)', () => {
    expect(eco.tax).toBe(73500);
  });

  it('резерв 10% — от закупки, не от выручки', () => {
    // От выручки было бы 105 000: при наценке выше закупки процент от
    // продажи приписывает конвертации расходы, которых не будет.
    expect(eco.fxReserve).toBe(59500);
  });

  it('прибыль: выручка − НДС − закупка − резерв − налог', () => {
    expect(eco.profit).toBe(1050000 - 50000 - 595000 - 59500 - 73500);
    expect(eco.profit).toBe(272000);
    expect(eco.profitPercent).toBeCloseTo(25.9, 1);
  });

  it('валовая маржа: выручка − закупка', () => {
    expect(eco.grossMargin).toBe(455000);
  });

  it('справка в долларах — по курсу ЦБ', () => {
    expect(usdReference(eco.profit, fx)).toBe(3200);
    expect(usdReference(100, { usd: null, eur: null, date: null })).toBeNull();
  });
});

describe('неполные данные закупки', () => {
  it('позиция без закупочной цены помечается, а не считается бесплатной', () => {
    const eco = buildQuoteEconomics(
      [...items, { sku: 'B', name: 'Без закупки', qty: 1, price: 50000, sum: 50000 }],
      [product('A', { base_price_usd: 700 }), product('B')], fx);
    expect(eco.missingPurchase).toEqual(['B']);
    expect(eco.complete).toBe(false);
    // Итоги закупки — только по позициям с данными.
    expect(eco.purchaseRub).toBe(595000);
    // Выручка и налоги — по всем: они от продажи, а не от закупки.
    expect(eco.revenue).toBe(1100000);
  });

  it('закупка в евро идёт по курсу евро', () => {
    const eco = buildQuoteEconomics(
      [{ sku: 'C', name: 'Евро', qty: 2, price: 100000, sum: 200000 }],
      [product('C', { peg_currency: 'EUR', base_price_eur: 500 })], fx);
    expect(eco.lines[0].purchaseCurrency).toBe('EUR');
    expect(eco.purchaseRub).toBe(2 * 500 * 92);
  });

  it('правдоподобное соотношение продажи и закупки помечается ok', () => {
    const eco = buildQuoteEconomics(items, [product('A', { base_price_usd: 700 })], fx);
    expect(eco.lines[0].flag).toBe('ok');
    expect(eco.suspectMonthly).toEqual([]);
    expect(eco.aboveSale).toEqual([]);
  });

  it('продажа в 6+ раз дороже закупки — подозрение на месячную закупку', () => {
    // Поручение руководителя 28.08.2026: ошибка «закупка за месяц при годовой
    // продаже» уже случалась. $100 × 85 = 8 500 ₽ закупки при продаже 105 000 ₽
    // честной наценкой (~1.85) не объясняется, а месячной ценой — ровно.
    const eco = buildQuoteEconomics(
      [{ sku: 'M', name: 'Месячная закупка', qty: 1, price: 105000, sum: 105000 }],
      [product('M', { base_price_usd: 100 })], fx);
    expect(eco.lines[0].flag).toBe('suspect_monthly');
    expect(eco.suspectMonthly).toEqual(['M']);
  });

  it('закупка дороже продажи — отдельный флаг', () => {
    const eco = buildQuoteEconomics(
      [{ sku: 'X', name: 'Перепутан период', qty: 1, price: 10000, sum: 10000 }],
      [product('X', { base_price_usd: 700 })], fx);
    expect(eco.lines[0].flag).toBe('above_sale');
    expect(eco.aboveSale).toEqual(['X']);
  });

  it('закупочная цена старше 90 дней помечается устаревшей', () => {
    const eco = buildQuoteEconomics(items,
      [product('A', { base_price_usd: 700, purchase_updated_at: '2026-01-01T00:00:00Z' })], fx);
    expect(eco.stalePurchase).toEqual(['A']);
    expect(eco.lines[0].purchaseUpdatedAt).toBe('2026-01-01T00:00:00Z');
    const fresh = buildQuoteEconomics(items,
      [product('A', { base_price_usd: 700, purchase_updated_at: new Date().toISOString() })], fx);
    expect(fresh.stalePurchase).toEqual([]);
  });

  it('без курса ЦБ позиция попадает в «нет данных», а не в ноль', () => {
    const eco = buildQuoteEconomics(items,
      [product('A', { base_price_usd: 700 })], { usd: null, eur: null, date: null });
    expect(eco.missingPurchase).toEqual(['A']);
    expect(eco.purchaseRub).toBe(0);
  });
});
