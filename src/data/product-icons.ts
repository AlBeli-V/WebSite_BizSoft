/**
 * Профильные иконки товарных позиций (пакет владельца; сейчас — 26 позиций
 * Adobe, официальные семейства знаков). Ключ — слаг товара на сайте.
 * Файлы идут через ассет-пайплайн (?url) — хешированные URL в /_astro
 * с годовым immutable-кэшем. Манифест: docs/adobe-product-icons-manifest.json.
 * Паттерн: монохром в плитке, полноцвет при наведении (класс .vi) и рядом
 * с названием на странице товара.
 */
import SLUG_ICON_MAP from './product-icon-map.json';

const colorFiles = import.meta.glob<string>('../assets/product-icons/color/*.svg', { eager: true, query: '?url', import: 'default' });
const monoFiles = import.meta.glob<string>('../assets/product-icons/mono/*.svg', { eager: true, query: '?url', import: 'default' });
// Каталожный пакет (477 уникальных иконок на 1119 позиций; product-icon-map):
// ключ — icon_id, сопоставление со слагом товара — в product-icon-map.json.
// Один комплект файлов намеренно переиспользуется несколькими карточками.
const catColorFiles = import.meta.glob<string>('../assets/product-icons/catalog/color/*.svg', { eager: true, query: '?url', import: 'default' });
const catMonoFiles = import.meta.glob<string>('../assets/product-icons/catalog/mono/*.svg', { eager: true, query: '?url', import: 'default' });

const slugOf = (path: string) => path.slice(path.lastIndexOf('/') + 1, -4);
const COLOR = new Map(Object.entries(colorFiles).map(([p, url]) => [slugOf(p), url]));
const MONO = new Map(Object.entries(monoFiles).map(([p, url]) => [slugOf(p), url]));
const CAT_COLOR = new Map(Object.entries(catColorFiles).map(([p, url]) => [slugOf(p), url]));
const CAT_MONO = new Map(Object.entries(catMonoFiles).map(([p, url]) => [slugOf(p), url]));
const ICON_BY_SLUG = SLUG_ICON_MAP as Record<string, string>;

export interface ProductIconPair { color: string; mono: string }

/** Составные позиции: несколько значков приложений в одной плитке
 * (например, тариф «Фотография» = Lightroom + Photoshop). */
const COMPOSITE: Record<string, string[]> = {
  'adobe-photo': ['adobe-lr', 'adobe-ps'],
};

function pair(slug: string): ProductIconPair | null {
  const color = COLOR.get(slug);
  const mono = MONO.get(slug);
  return color && mono ? { color, mono } : null;
}

function catalogPair(slug: string): ProductIconPair | null {
  const iconId = ICON_BY_SLUG[slug];
  if (!iconId) return null;
  const color = CAT_COLOR.get(iconId);
  const mono = CAT_MONO.get(iconId);
  return color && mono ? { color, mono } : null;
}

export function productIcon(slug: string | undefined): ProductIconPair | null {
  if (!slug) return null;
  return pair(slug) ?? catalogPair(slug);
}

/** Все значки позиции (составные — несколько; обычные — один; нет — пусто).
 * Приоритет: официальный пакет по слагу (Adobe) → составные → каталожный пакет. */
export function productIcons(slug: string | undefined): ProductIconPair[] {
  if (!slug) return [];
  const slugs = COMPOSITE[slug] ?? [slug];
  const direct = slugs.map(pair).filter((p): p is ProductIconPair => p !== null);
  if (direct.length > 0) return direct;
  const cat = catalogPair(slug);
  return cat ? [cat] : [];
}
