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

export function productIcon(slug: string | undefined): ProductIconPair | null {
  if (!slug) return null;
  const color = COLOR.get(slug);
  const mono = MONO.get(slug);
  if (!color || !mono) return null;
  return { color, mono };
}
