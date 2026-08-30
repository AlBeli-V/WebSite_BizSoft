/**
 * Товарные картинки для фидов площадок, запрещающих «маркетинговые» изображения.
 *
 * 2ГИС не принимает картинки с ценой, названием магазина и надписями — наша
 * og-карточка (/og/product/*.png) с ценой и брендом BIZSoft не подходит.
 * Здесь — чистый PNG: официальный знак продукта (или вендора) по центру
 * на белом фоне, без единой надписи.
 *
 * SVG-знаки берутся из тех же комплектов, что и витрина (см.
 * src/data/product-icons.ts / vendor-icons.ts), но сырым содержимым через
 * ленивые glob-загрузчики: содержимое нужно рендереру resvg, а не браузеру,
 * и eager-импорт полутысячи файлов раздул бы серверный бандл.
 */
import { Resvg } from '@resvg/resvg-js';
import SLUG_ICON_MAP from '../../data/product-icon-map.json';
import { vendorSlug } from '../vendor-links';

type RawLoader = () => Promise<string>;

const ownColor = import.meta.glob<string>('../../assets/product-icons/color/*.svg', { query: '?raw', import: 'default' }) as Record<string, RawLoader>;
const catColor = import.meta.glob<string>('../../assets/product-icons/catalog/color/*.svg', { query: '?raw', import: 'default' }) as Record<string, RawLoader>;
const vendorColor = import.meta.glob<string>('../../assets/vendor-icons/color/*.svg', { query: '?raw', import: 'default' }) as Record<string, RawLoader>;

const nameOf = (path: string) => path.slice(path.lastIndexOf('/') + 1, -4);
const OWN = new Map(Object.entries(ownColor).map(([p, l]) => [nameOf(p), l]));
const CAT = new Map(Object.entries(catColor).map(([p, l]) => [nameOf(p), l]));
const VEND = new Map(Object.entries(vendorColor).map(([p, l]) => [nameOf(p), l]));
const ICON_BY_SLUG = SLUG_ICON_MAP as Record<string, string>;

function loaderFor(slug: string, vendor?: string | null): RawLoader | null {
  const own = OWN.get(slug);
  if (own) return own;
  const iconId = ICON_BY_SLUG[slug];
  const cat = iconId ? CAT.get(iconId) : undefined;
  if (cat) return cat;
  const vend = vendor ? VEND.get(vendorSlug(vendor)) : undefined;
  return vend ?? null;
}

/** Есть ли у товара картинка для фида (синхронно, по известным ключам глобов). */
export function hasProductIconImage(slug: string, vendor?: string | null): boolean {
  return loaderFor(slug, vendor) !== null;
}

/** Содержимое SVG-знака товара (продуктовый знак → каталожный → знак вендора). */
export async function loadProductIconSvg(slug: string, vendor?: string | null): Promise<string | null> {
  const loader = loaderFor(slug, vendor);
  return loader ? loader() : null;
}

/** Размер PNG: ≥600 px по меньшей стороне рекомендует 2ГИС, ≤3500 — предел. */
export const ICON_PNG_SIZE = 800;
/** Знак занимает ~65% холста — остальное белые поля. */
const ICON_INNER = 520;

/**
 * Отрендерить квадратный PNG: знак по центру на белом фоне, без надписей.
 * SVG вкладывается через data:-URI — resvg растрирует вложенный SVG сам,
 * не требуя разбора viewBox исходника.
 */
export function renderIconPng(svgContent: string, size: number = ICON_PNG_SIZE): Buffer {
  const inner = Math.round((ICON_INNER / ICON_PNG_SIZE) * size);
  const offset = Math.round((size - inner) / 2);
  const dataUri = `data:image/svg+xml;base64,${Buffer.from(svgContent, 'utf8').toString('base64')}`;
  const wrapper = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${size}" height="${size}">
  <rect width="${size}" height="${size}" fill="#ffffff"/>
  <image x="${offset}" y="${offset}" width="${inner}" height="${inner}" xlink:href="${dataUri}"/>
</svg>`;
  return new Resvg(wrapper, { fitTo: { mode: 'width', value: size } }).render().asPng();
}
