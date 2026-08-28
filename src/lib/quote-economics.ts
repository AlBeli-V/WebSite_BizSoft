/**
 * Экономика сделки по КП: продажа, закупка, налоги, прибыль.
 *
 * Считается в момент формирования КП и уходит руководителю (блок в письме
 * и Excel-вложение). Клиент этих цифр не видит никогда: модуль подключён
 * только к внутренней части обработчика.
 *
 * Источники данных:
 * - продажа — позиции КП (уже пересчитанные по базе);
 * - закупка — поля товара base_price_usd / base_price_eur («закупочная
 *   себестоимость в валюте с сайта производителя») и peg_currency;
 * - курс — ЦБ РФ на дату формирования, фиксируется в результате.
 *
 * Позиция без закупочной цены не считается «бесплатной»: она попадает в
 * список missingPurchase, а итоги закупки и прибыли помечаются неполными.
 * Молчаливый ноль в себестоимости завысил бы прибыль — хуже, чем честное
 * «нет данных».
 */
import { economics as cfg } from '../config/site';
import { vatOfItems } from './rub-words';
import { VAT_PERCENT } from './quote-layout';
import type { Product, QuoteItem } from './types';
import type { CbrRates } from './currency';

const r2 = (n: number) => Math.round(n * 100) / 100;

export interface EconomicsLine {
  sku: string;
  name: string;
  qty: number;
  /** Продажа за единицу, ₽ (из КП). */
  price: number;
  /** Продажа по позиции, ₽. */
  sum: number;
  /** Валюта закупки; null — закупочная цена у товара не заполнена. */
  purchaseCurrency: 'USD' | 'EUR' | null;
  /** Закупка за единицу в валюте. */
  purchaseUnit: number | null;
  /** Закупка по позиции в валюте. */
  purchaseSum: number | null;
  /** Закупка по позиции в рублях по курсу ЦБ. */
  purchaseRub: number | null;
  /** Валовая маржа по позиции, ₽ (продажа − закупка). */
  grossMargin: number | null;
  /** Валовая маржа, % от продажи позиции. */
  grossMarginPercent: number | null;
}

export interface QuoteEconomics {
  lines: EconomicsLine[];
  /** Курс ЦБ, зафиксированный в момент расчёта. */
  fx: CbrRates;
  /** Выручка по КП, ₽ (с НДС). */
  revenue: number;
  /** НДС к уплате, выделенный из цены (5/105 по позициям). */
  vat: number;
  /** Налоговая нагрузка (cfg.taxPercent% от полной выручки — решение 28.08.2026). */
  tax: number;
  /** Закупка в рублях по курсу ЦБ — только позиции с данными. */
  purchaseRub: number;
  /** Закупка в валюте по валютам (для справки в отчёте). */
  purchaseByCurrency: { USD: number; EUR: number };
  /** Резерв на конвертацию и платёж: cfg.fxReservePercent% от закупки. */
  fxReserve: number;
  /** Валовая маржа: выручка − закупка. */
  grossMargin: number;
  /** Прибыль: выручка − НДС − закупка − резерв − налог. */
  profit: number;
  /** Прибыль, % от выручки. */
  profitPercent: number;
  /** Артикулы без закупочной цены: итоги по ним неполные. */
  missingPurchase: string[];
  /** true, когда закупка посчитана по всем позициям. */
  complete: boolean;
}

/** Закупочная цена и валюта единицы товара; null — данных нет. */
function purchaseOf(p: Product | undefined): { unit: number; currency: 'USD' | 'EUR' } | null {
  if (!p) return null;
  // Валюту называет peg_currency; без него заполненное base_price_usd
  // трактуется как доллары — так же, как в переоценке цен (pricing.ts).
  if (p.peg_currency === 'EUR') {
    return p.base_price_eur && p.base_price_eur > 0
      ? { unit: p.base_price_eur, currency: 'EUR' } : null;
  }
  if (p.base_price_usd && p.base_price_usd > 0) return { unit: p.base_price_usd, currency: 'USD' };
  if (p.base_price_eur && p.base_price_eur > 0) return { unit: p.base_price_eur, currency: 'EUR' };
  return null;
}

export function buildQuoteEconomics(
  items: QuoteItem[],
  products: Product[],
  fx: CbrRates,
): QuoteEconomics {
  const bySku = new Map(products.map((p) => [p.sku, p]));
  const missingPurchase: string[] = [];
  const purchaseByCurrency = { USD: 0, EUR: 0 };
  let purchaseRub = 0;

  const lines: EconomicsLine[] = items.map((it) => {
    const buy = purchaseOf(bySku.get(it.sku));
    const rate = buy ? (buy.currency === 'EUR' ? fx.eur : fx.usd) : null;
    if (!buy || !rate) {
      missingPurchase.push(it.sku);
      return { sku: it.sku, name: it.name, qty: it.qty, price: it.price, sum: it.sum,
               purchaseCurrency: buy?.currency ?? null, purchaseUnit: buy?.unit ?? null,
               purchaseSum: buy ? r2(buy.unit * it.qty) : null,
               purchaseRub: null, grossMargin: null, grossMarginPercent: null };
    }
    const purchaseSum = r2(buy.unit * it.qty);
    const rub = r2(purchaseSum * rate);
    purchaseByCurrency[buy.currency] += purchaseSum;
    purchaseRub += rub;
    const gross = r2(it.sum - rub);
    return { sku: it.sku, name: it.name, qty: it.qty, price: it.price, sum: it.sum,
             purchaseCurrency: buy.currency, purchaseUnit: buy.unit, purchaseSum,
             purchaseRub: rub, grossMargin: gross,
             grossMarginPercent: it.sum > 0 ? r2((gross / it.sum) * 100) : null };
  });

  const revenue = items.reduce((s, i) => s + i.sum, 0);
  const vat = vatOfItems(items, VAT_PERCENT);
  // База налога — полная выручка с НДС: решение руководителя 28.08.2026.
  const tax = r2(revenue * cfg.taxPercent / 100);
  // Резерв — от закупки, не от выручки: при высокой наценке процент от
  // продажи приписал бы конвертации расходы, которых не будет.
  const fxReserve = r2(purchaseRub * cfg.fxReservePercent / 100);
  const grossMargin = r2(revenue - purchaseRub);
  const profit = r2(revenue - vat - purchaseRub - fxReserve - tax);

  return {
    lines, fx, revenue, vat, tax,
    purchaseRub: r2(purchaseRub),
    purchaseByCurrency: { USD: r2(purchaseByCurrency.USD), EUR: r2(purchaseByCurrency.EUR) },
    fxReserve, grossMargin, profit,
    profitPercent: revenue > 0 ? r2((profit / revenue) * 100) : 0,
    missingPurchase,
    complete: missingPurchase.length === 0,
  };
}

/** Справка в долларах по курсу ЦБ; null — курса нет. */
export function usdReference(rub: number, fx: CbrRates): number | null {
  return fx.usd && fx.usd > 0 ? r2(rub / fx.usd) : null;
}
