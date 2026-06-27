/**
 * Клиентское состояние корзины (localStorage). Только для браузера.
 * Любое изменение шлёт window-событие 'cart:change' — слушатели (счётчик в
 * шапке, страница корзины) обновляются реактивно.
 */
import type { CartItem } from './types';

const KEY = 'bizsoft_cart';

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

export function cartTotal(items: CartItem[] = readCart()): number {
  return items.reduce((s, i) => s + i.price * i.qty, 0);
}
