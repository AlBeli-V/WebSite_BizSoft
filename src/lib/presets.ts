/**
 * Разворачивание наборов в позиции с ценами.
 *
 * Главная и спецификация показывают одни и те же наборы, и считать их состав
 * дважды нельзя: два одинаковых по смыслу куска кода расходятся при первой
 * правке — на одной витрине набор уже без позиции, на другой ещё с ней.
 *
 * Набор с одной позицией не набор: такие отсеиваются. Позиции без цены в
 * состав не берутся — сумма «от» должна складываться из того, что видно.
 */
import { PRESETS, type Preset } from '../data/presets';
import { getProductsBySlugs } from './directus';
import { effectivePrice } from './pricing';
import type { Product } from './types';

export interface PresetItem {
  sku: string;
  slug: string;
  name: string;
  vendor: string;
  price: number;
}

export interface ResolvedPreset extends Preset {
  items: PresetItem[];
  total: number;
}

export async function getPresets(): Promise<ResolvedPreset[]> {
  const all = await getProductsBySlugs(PRESETS.flatMap((p) => p.slugs));
  return PRESETS.map((pr) => {
    const items = pr.slugs
      .map((sl) => all.find((x) => x.slug === sl))
      .filter((x): x is Product => Boolean(x))
      .map((x) => ({
        sku: x.sku,
        slug: x.slug,
        name: x.name,
        vendor: x.vendor || '',
        price: effectivePrice(x).price,
      }))
      .filter((x) => Number.isFinite(x.price) && x.price > 0);
    return { ...pr, items, total: items.reduce((a, x) => a + x.price, 0) };
  }).filter((pr) => pr.items.length >= 2);
}
