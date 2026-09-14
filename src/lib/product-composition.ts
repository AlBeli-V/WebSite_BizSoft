/**
 * Какой композицией показывать позицию каталога.
 *
 * Композиция, утверждённая руководителем 12.09.2026 на карточке Red Giant, —
 * эталон для подписки, продаваемой за расчётную единицу: цена за место,
 * счётчик количества, минимальный заказ, единый пул администрирования.
 * На пополнения баланса, номиналы и дополнения она не переносится: там
 * покупают не количество мест, а номинал или надстройку к уже купленному
 * продукту, и счётчик рабочих мест в такой карточке — просто неверный
 * вопрос.
 *
 * Вид позиции берётся из данных (product_type, parent_sku, артикул), а не из
 * того, что позиция «похожа на подписку»: правило Data Before UI. Чего в
 * данных нет — конфигурируемых составных продуктов, — здесь не выводится
 * ни из чего, это DATA GAP (см. навык bizsoft-product-conversion-flow).
 */
import { isGiftCard, isVariant, productKind } from './catalog';
import type { Product } from './types';

export type CardComposition =
  /** Подписка за расчётную единицу — эталонная композиция. */
  | 'unit_subscription'
  /** Пополнение баланса, номинал, подарочная карта. */
  | 'balance_topup'
  /** Дополнение к основному продукту: плагин, надстройка, пакет кредитов. */
  | 'addon'
  /** Договорная позиция: цены нет, объём считается под задачу. */
  | 'quote_only';

/**
 * Первая плашка над заголовком карточки. Правило
 * `docs/rules/product-markers.md`: она называет вид позиции, а не свойство
 * товара — покупатель по ней понимает, что вообще покупает.
 *
 * Тип плана (командный или индивидуальный) сюда не попадает: он считается
 * отдельно и только для подписок, потому что у пополнения и дополнения
 * плана нет вовсе.
 */
export const KIND_MARKER: Partial<Record<CardComposition, string>> = {
  balance_topup: 'Универсальный продукт',
  addon: 'Дополнение к продукту',
};

export const COMPOSITION_LABEL: Record<CardComposition, string> = {
  unit_subscription: 'Подписка за расчётную единицу',
  balance_topup: 'Пополнение, номинал или подарочная карта',
  addon: 'Дополнение к основному продукту',
  quote_only: 'Договорная позиция',
};

type Input = Pick<Product, 'sku' | 'price'> & Pick<Product, 'product_type' | 'parent_sku'>;

/**
 * Порядок проверок важен: номинал подарочной карты — тоже позиция с ценой,
 * и без первой ветки он получил бы композицию подписки со счётчиком мест.
 */
export function cardComposition(p: Input): CardComposition {
  if (isGiftCard(p) || isVariant(p)) return 'balance_topup';
  if (productKind(p) === 'addon') return 'addon';
  if (!(p.price > 0)) return 'quote_only';
  return 'unit_subscription';
}

/** Применима ли к позиции эталонная композиция подписки. */
export function isUnitSubscription(p: Input): boolean {
  return cardComposition(p) === 'unit_subscription';
}
