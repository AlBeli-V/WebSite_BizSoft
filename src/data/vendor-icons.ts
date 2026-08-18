/**
 * Унифицированные иконки производителей (пакет владельца, 64 бренда):
 * src/assets/vendor-icons/{color,mono}/<slug>.svg — холст 512×512, прозрачный фон.
 * Файлы идут через ассет-пайплайн Vite (?url) — получают хешированные URL в
 * /_astro с годовым immutable-кэшем (вместо max-age=0 у public/).
 * Паттерн отображения: монохром по умолчанию, полноцвет при наведении
 * (класс .vi в global.css); в меню «Топ-запросы» — сразу цветные.
 * Манифест пакета с источниками: docs/vendor-icons-manifest.json.
 */
const colorFiles = import.meta.glob<string>('../assets/vendor-icons/color/*.svg', { eager: true, query: '?url', import: 'default' });
const monoFiles = import.meta.glob<string>('../assets/vendor-icons/mono/*.svg', { eager: true, query: '?url', import: 'default' });

const slugOf = (path: string) => path.slice(path.lastIndexOf('/') + 1, -4);
const COLOR = new Map(Object.entries(colorFiles).map(([p, url]) => [slugOf(p), url]));
const MONO = new Map(Object.entries(monoFiles).map(([p, url]) => [slugOf(p), url]));

export const VENDOR_ICON_SLUGS = new Set<string>(COLOR.keys());

/** Слаги сайта → слаги пакета иконок (различия в неймингах). */
const ALIAS: Record<string, string> = {
  freepik: 'magnific',
  houdini: 'sidefx-houdini',
  photon: 'photon-engine',
  blackmagic: 'blackmagic-design',
  vegas: 'magix-vegas',
  gaea: 'quadspinner-gaea',
  wwise: 'audiokinetic',
};

export interface VendorIconPair { color: string; mono: string }

export function vendorIcon(slug: string | undefined): VendorIconPair | null {
  if (!slug) return null;
  const s = COLOR.has(slug) ? slug : ALIAS[slug];
  if (!s) return null;
  const color = COLOR.get(s);
  const mono = MONO.get(s);
  if (!color || !mono) return null;
  return { color, mono };
}
