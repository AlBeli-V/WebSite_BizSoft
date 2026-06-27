/**
 * Чистая ценовая логика (без сети, без chrome/DOM) — покрыта юнит-тестами.
 * Используется и на витрине (эффективная цена), и в инструментах цен
 * (массовое изменение, привязка к курсу ЦБ).
 */
import type { Product } from './types';

export type RoundingRule = 'none' | 'to1' | 'to10' | 'to100' | 'psychological99';

/** Округление по выбранному правилу. */
export function roundPrice(value: number, rule: RoundingRule): number {
  if (!isFinite(value)) return 0;
  const v = Math.max(0, value);
  switch (rule) {
    case 'to1':
      return Math.round(v);
    case 'to10':
      return Math.round(v / 10) * 10;
    case 'to100':
      return Math.round(v / 100) * 100;
    case 'psychological99': {
      // ближайшее значение вида N99 (например 1999, 2999)
      const base = Math.max(0, Math.floor(v / 100) * 100 - 1);
      return base < 99 ? 99 : base;
    }
    case 'none':
    default:
      return v;
  }
}

/**
 * Активна ли акция у товара на заданную дату.
 * Акция активна, если задан promo_price и текущая дата в окне promo_start..promo_end
 * (пустые границы означают «без ограничения» с соответствующей стороны).
 */
export function isPromoActive(p: Pick<Product, 'promo_price' | 'promo_start' | 'promo_end'>, now: Date = new Date()): boolean {
  if (p.promo_price == null || p.promo_price <= 0) return false;
  const t = now.getTime();
  if (p.promo_start) {
    const start = new Date(p.promo_start).getTime();
    if (!isNaN(start) && t < start) return false;
  }
  if (p.promo_end) {
    const end = new Date(p.promo_end).getTime();
    // включительно до конца суток даты окончания
    if (!isNaN(end) && t > end + 24 * 60 * 60 * 1000 - 1) return false;
  }
  return true;
}

export interface EffectivePrice {
  /** Цена к показу/оплате. */
  price: number;
  /** Базовая (зачёркнутая) цена, если есть активная акция. */
  oldPrice: number | null;
  isPromo: boolean;
  promoLabel: string | null;
}

/** Итоговая цена товара для витрины с учётом акции. */
export function effectivePrice(p: Product, now: Date = new Date()): EffectivePrice {
  if (isPromoActive(p, now)) {
    return {
      price: p.promo_price as number,
      oldPrice: p.price,
      isPromo: true,
      promoLabel: p.promo_label ?? 'Акция',
    };
  }
  return { price: p.price, oldPrice: null, isPromo: false, promoLabel: null };
}

/**
 * Цена товара, привязанного к курсу доллара (устаревшая формула с процентом):
 * base_price_usd × usd_rate × (1 + markup_percent/100). Оставлена для совместимости.
 */
export function pegPrice(
  basePriceUsd: number,
  usdRate: number,
  markupPercent: number,
  rule: RoundingRule = 'to1',
): number {
  const raw = basePriceUsd * usdRate * (1 + markupPercent / 100);
  return roundPrice(raw, rule);
}

/**
 * Рублёвая цена по коэффициенту наценки:
 * себестоимость(в валюте) × курс_валюты × коэффициент, затем округление.
 */
export function pegPriceCoeff(
  baseInCurrency: number,
  rate: number,
  coeff: number,
  rule: RoundingRule = 'to1',
): number {
  return roundPrice(baseInCurrency * rate * coeff, rule);
}

export interface Rates { usd: number | null; eur: number | null }

/**
 * Вычислить рублёвую цену привязанного к валюте товара по текущим курсам.
 * Возвращает null, если товар не привязан или нет нужного курса/себестоимости.
 */
export function computePegRub(
  p: Pick<Product, 'peg_to_usd' | 'peg_currency' | 'base_price_usd' | 'base_price_eur' | 'markup_coeff'>,
  rates: Rates,
  defaultCoeff = 1.85,
  rule: RoundingRule = 'to1',
): number | null {
  if (!p.peg_to_usd) return null;
  const cur = p.peg_currency === 'EUR' ? 'EUR' : 'USD';
  const base = cur === 'EUR' ? p.base_price_eur : p.base_price_usd;
  const rate = cur === 'EUR' ? rates.eur : rates.usd;
  if (!base || base <= 0 || !rate || rate <= 0) return null;
  const coeff = p.markup_coeff != null && p.markup_coeff > 0 ? p.markup_coeff : defaultCoeff;
  return pegPriceCoeff(base, rate, coeff, rule);
}

export type BulkOperation = 'increase' | 'decrease';
export type BulkMode = 'percent' | 'fixed';
export type BulkTarget = 'base' | 'promo' | 'both';

export interface BulkChangeOptions {
  operation: BulkOperation;
  mode: BulkMode;
  amount: number; // % или фикс. сумма ₽
  target: BulkTarget;
  rounding: RoundingRule;
}

export interface PriceChangePreview {
  sku: string;
  name: string;
  field: 'price' | 'promo_price';
  before: number;
  after: number;
}

/** Применить операцию к одному числовому значению. */
export function applyBulkValue(value: number, opts: BulkChangeOptions): number {
  const sign = opts.operation === 'increase' ? 1 : -1;
  let next: number;
  if (opts.mode === 'percent') {
    next = value * (1 + (sign * opts.amount) / 100);
  } else {
    next = value + sign * opts.amount;
  }
  return roundPrice(Math.max(0, next), opts.rounding);
}

/**
 * Построить предпросмотр «было → станет» для массового изменения цен.
 * Меняет price и/или promo_price согласно target. promo_price трогаем,
 * только если он задан у товара.
 */
export function previewBulkChange(products: Product[], opts: BulkChangeOptions): PriceChangePreview[] {
  const out: PriceChangePreview[] = [];
  for (const p of products) {
    if (opts.target === 'base' || opts.target === 'both') {
      const after = applyBulkValue(p.price, opts);
      if (after !== p.price) {
        out.push({ sku: p.sku, name: p.name, field: 'price', before: p.price, after });
      }
    }
    if ((opts.target === 'promo' || opts.target === 'both') && p.promo_price != null && p.promo_price > 0) {
      const after = applyBulkValue(p.promo_price, opts);
      if (after !== p.promo_price) {
        out.push({ sku: p.sku, name: p.name, field: 'promo_price', before: p.promo_price, after });
      }
    }
  }
  return out;
}

/** Форматирование цены в рублях для UI. */
export function formatRub(value: number): string {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0,
  }).format(value);
}
