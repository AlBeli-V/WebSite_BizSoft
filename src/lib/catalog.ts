/**
 * Каталожные хелперы: тип товара (основной/дополнение) и юр. название вендора.
 * Тип товара выводится из sku (плагины JetBrains: JB-PLG-*; дополнения Zoom:
 * Phone/Webinars/Rooms/Large Meeting/Events/AI Companion). Остальное — основной продукт.
 */
import type { Product } from './types';

export type ProductKind = 'main' | 'addon';

export const PRODUCT_KIND_LABEL: Record<ProductKind, string> = {
  main: 'Основной продукт',
  addon: 'Плагин или дополнение',
};

const ZOOM_ADDON = /^ZOOM-(PHONE|WEBINARS|ROOMS|LARGE-MEETING|EVENTS|AI-COMPANION)/i;

/** Классифицировать товар по контексту (sku). */
export function productKind(p: Pick<Product, 'sku'>): ProductKind {
  const sku = (p.sku || '').toUpperCase();
  if (sku.startsWith('JB-PLG-')) return 'addon';
  if (ZOOM_ADDON.test(sku)) return 'addon';
  return 'main';
}

/** Полное юридическое название производителя для отображения в карточке. */
export const VENDOR_LEGAL: Record<string, string> = {
  JetBrains: 'JetBrains s.r.o.',
  'JetBrains Marketplace': 'JetBrains s.r.o.',
  Zoom: 'Zoom Communications, Inc.',
};

export function vendorLegal(vendor?: string | null): string {
  if (!vendor) return '';
  return VENDOR_LEGAL[vendor] || vendor;
}

/**
 * Индексная матрица: какие товары временно НЕ индексировать (noindex + вне sitemap).
 * Сейчас: все плагины JetBrains Marketplace (JB-PLG-*) и личные лицензии JetBrains (JB-…-IND).
 * Основные продукты для организаций, AI и командные инструменты — индексируются.
 */
export function productNoindex(sku?: string | null): boolean {
  const s = (sku || '').toUpperCase();
  if (s.startsWith('JB-PLG-')) return true;               // 867 плагинов Marketplace
  if (s.startsWith('JB-') && s.endsWith('-IND')) return true; // личные лицензии JetBrains
  return false;
}
