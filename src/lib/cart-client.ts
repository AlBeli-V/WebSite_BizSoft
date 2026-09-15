/**
 * Клиентское состояние корзины (localStorage). Только для браузера.
 * Любое изменение шлёт window-событие 'cart:change' — слушатели (счётчик в
 * шапке, страница корзины) обновляются реактивно.
 */
import type { CartItem } from './types';
import { emailRentApplies, EMAIL_RENT_PRICE } from './email-rent';

const KEY = 'bizsoft_cart';
/**
 * Аренда адресов почты — выбор покупателя на всю подборку, а не свойство
 * позиции (постановка руководителя 15.09.2026): вопрос «есть ли у вас почта
 * вне зоны .ru» задаётся один раз в шапке спецификации. Поэтому флаг живёт
 * рядом с корзиной и входит в её итог — счётчик в шапке, полка и КП обязаны
 * показывать одну сумму.
 */
const RENT_KEY = 'bizsoft_email_rent';

export function readCart(): CartItem[] {
  try {
    const raw = localStorage.getItem(KEY);
    const data = raw ? JSON.parse(raw) : [];
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

function writeCart(items: CartItem[]): void {
  localStorage.setItem(KEY, JSON.stringify(items));
  window.dispatchEvent(new CustomEvent('cart:change', { detail: items }));
}

export function addToCart(item: Omit<CartItem, 'qty'>, qty = 1): void {
  const items = readCart();
  const existing = items.find((i) => i.sku === item.sku);
  if (existing) {
    existing.qty += qty;
    // обновляем цену на актуальную (на случай изменения акции)
    existing.price = item.price;
  } else {
    items.push({ ...item, qty });
  }
  writeCart(items);
}

export function setQty(sku: string, qty: number): void {
  const items = readCart();
  const it = items.find((i) => i.sku === sku);
  if (!it) return;
  if (qty <= 0) {
    writeCart(items.filter((i) => i.sku !== sku));
  } else {
    it.qty = qty;
    writeCart(items);
  }
}

export function removeFromCart(sku: string): void {
  writeCart(readCart().filter((i) => i.sku !== sku));
}

export function clearCart(): void {
  writeCart([]);
}

export function cartCount(items: CartItem[] = readCart()): number {
  return items.reduce((s, i) => s + i.qty, 0);
}

/** Выбрана ли аренда адресов почты. */
export function readEmailRent(): boolean {
  try {
    return localStorage.getItem(RENT_KEY) === '1';
  } catch {
    return false;
  }
}

/** Переключить аренду; слушатели корзины пересчитываются тем же событием. */
export function setEmailRent(on: boolean): void {
  try {
    localStorage.setItem(RENT_KEY, on ? '1' : '0');
  } catch { /* приватный режим — считаем выбор разовым */ }
  window.dispatchEvent(new CustomEvent('cart:change', { detail: readCart() }));
}

/** Есть ли в подборке позиции, которым аренда почты вообще применима. */
export function hasRentable(items: CartItem[] = readCart()): boolean {
  return items.some((i) => emailRentApplies(i.sku));
}

/** Цена единицы с учётом аренды — она же цена в колонке ЦЕНА РУБ. */
export function lineUnitPrice(it: CartItem, rent = readEmailRent()): number {
  return rent && emailRentApplies(it.sku) ? it.price + EMAIL_RENT_PRICE : it.price;
}

/** Сумма строки: ЦЕНА × КОЛ-ВО — в спецификации она обязана сходиться. */
export function lineSum(it: CartItem, rent = readEmailRent()): number {
  return lineUnitPrice(it, rent) * it.qty;
}

export function cartTotal(items: CartItem[] = readCart(), rent = readEmailRent()): number {
  return items.reduce((s, i) => s + lineSum(i, rent), 0);
}
