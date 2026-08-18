/**
 * Профильные иконки товарных позиций (пакет владельца; сейчас — 26 позиций
 * Adobe, официальные семейства знаков). Ключ — слаг товара на сайте.
 * Файлы идут через ассет-пайплайн (?url) — хешированные URL в /_astro
 * с годовым immutable-кэшем. Манифест: docs/adobe-product-icons-manifest.json.
 * Паттерн: монохром в плитке, полноцвет при наведении (класс .vi) и рядом
 * с названием на странице товара.
 */
const colorFiles = import.meta.glob<string>('../assets/product-icons/color/*.svg', { eager: true, query: '?url', import: 'default' });
const monoFiles = import.meta.glob<string>('../assets/product-icons/mono/*.svg', { eager: true, query: '?url', import: 'default' });

const slugOf = (path: string) => path.slice(path.lastIndexOf('/') + 1, -4);
const COLOR = new Map(Object.entries(colorFiles).map(([p, url]) => [slugOf(p), url]));
const MONO = new Map(Object.entries(monoFiles).map(([p, url]) => [slugOf(p), url]));

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

export function productIcon(slug: string | undefined): ProductIconPair | null {
  if (!slug) return null;
  return pair(slug);
}

/** Все значки позиции (составные — несколько; обычные — один; нет — пусто). */
export function productIcons(slug: string | undefined): ProductIconPair[] {
  if (!slug) return [];
  const slugs = COMPOSITE[slug] ?? [slug];
  return slugs.map(pair).filter((p): p is ProductIconPair => p !== null);
}
