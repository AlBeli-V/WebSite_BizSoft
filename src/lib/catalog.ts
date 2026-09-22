/**
 * Каталожные хелперы: вид позиции (основной продукт или дополнение), индексная
 * матрица и юр. название вендора. Вид и матрица читаются из сегментов
 * артикула единой системы (docs/rules/sku-system.md, `parseSku`).
 */
import { productCategories } from './cross-listing';
import { vendorBySlug } from '../data/vendors';
import { vendorSlug } from './vendor-links';
import { parseSku } from './sku';
import type { Product } from './types';

export type ProductKind = 'main' | 'addon';

export const PRODUCT_KIND_LABEL: Record<ProductKind, string> = {
  main: 'Основной продукт',
  addon: 'Плагин или дополнение',
};

/**
 * Классифицировать товар по артикулу: сегмент вида (docs/rules/sku-system.md)
 * ADD, SVC и номинал CRD — дополнение; LIC, GFT и родитель линейки CRD —
 * основной продукт. Позиция без системного артикула (черновик, архив) —
 * основной продукт: у неё нет страницы, и вопрос вида не встаёт.
 */
export function productKind(p: Pick<Product, 'sku'>): ProductKind {
  const parsed = parseSku(p.sku);
  if (!parsed) return 'main';
  if (parsed.kind === 'ADD' || parsed.kind === 'SVC') return 'addon';
  // Номинал кредитов (с вариантом) — дополнение; родитель линейки без
  // варианта — страница пополнения баланса, самостоятельная позиция.
  if (parsed.kind === 'CRD') return parsed.variant ? 'addon' : 'main';
  return 'main';
}

/**
 * Сколько опубликованных товаров в каждом разделе (ключ — slug категории).
 *
 * Один расчёт на страницу каталога и на инструмент list_categories: раздел,
 * который человек видит в каталоге, и раздел, который агент предлагает как
 * фильтр, обязаны совпадать. Пустые разделы отбрасывает уже потребитель —
 * фильтр по разделу без товаров выглядит как поломка.
 *
 * Считает и вторые привязки (lib/cross-listing): товар, показанный в разделе,
 * обязан в нём же считаться. Счётчик по одному полю `category` подписывал живой
 * раздел как пустой — так «Корпоративные AI» с десятком тарифов годами стояли
 * на витрине как «в подготовке».
 */
export function countByCategory(
  products: Pick<Product, 'sku' | 'slug' | 'category'>[],
): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const p of products) {
    for (const slug of productCategories(p)) {
      counts[slug] = (counts[slug] || 0) + 1;
    }
  }
  return counts;
}

/** Полное юридическое название производителя для отображения в карточке. */
export const VENDOR_LEGAL: Record<string, string> = {
  // Подарочные карты (docs/gift-cards.md)
  Apple: 'Apple Inc.',
  Airalo: 'Airalo Technologies Inc.',
  Binance: 'Binance Holdings Ltd.',
  Discord: 'Discord Inc.',
  JetBrains: 'JetBrains s.r.o.',
  'JetBrains Marketplace': 'JetBrains s.r.o.',
  Zoom: 'Zoom Communications, Inc.',
  // Блок 1 — графический дизайн / AI-графика
  Canva: 'Canva Pty Ltd',
  CorelDRAW: 'Corel Corporation (Alludo)',
  Sketch: 'Sketch B.V.',
  Framer: 'Framer B.V.',
  Miro: 'RealtimeBoard, Inc. dba Miro',
  Zeplin: 'Zeplin, Inc.',
  'Clip Studio Paint': 'CELSYS, Inc.',
  Procreate: 'Savage Interactive Pty Ltd',
  'Astute Graphics': 'Astute Graphics Ltd',
  Freepik: 'Freepik Company S.L.U.',
  // Сервис Freepik переименован в Magnific; юрлицо-правообладатель прежнее.
  'Magnific (Freepik)': 'Freepik Company S.L.U.',
  Magnific: 'Freepik Company S.L.U.',
  Envato: 'Envato Pty Ltd',
  Shutterstock: 'Shutterstock, Inc.',
  Depositphotos: 'Depositphotos Inc.',
  Monotype: 'Monotype Imaging Holdings Inc.',
  Midjourney: 'Midjourney, Inc.',
  Recraft: 'Recraft, Inc.',
  // Блок 2 — игры / 3D
  Unity: 'Unity Technologies',
  'Unreal Engine': 'Epic Games, Inc.',
  Autodesk: 'Autodesk, Inc.',
  Maxon: 'Maxon Computer GmbH',
  'SideFX Houdini': 'Side Effects Software Inc.',
  SpeedTree: 'Unity Technologies (IDV Inc.)',
  Marmoset: 'Marmoset LLC',
  'Marvelous Designer': 'CLO Virtual Fashion Inc.',
  Reallusion: 'Reallusion Inc.',
  Perforce: 'Perforce Software, Inc.',
  Audiokinetic: 'Audiokinetic Inc.',
  FMOD: 'Firelight Technologies Pty Ltd',
  Spine: 'Esoteric Software LLC',
  Rive: 'Rive App, Inc.',
  'QuadSpinner Gaea': 'QuadSpinner Inc.',
  RizomUV: 'Rizom-Lab',
  'Photon Engine': 'Exit Games GmbH',
  // Блок 3 — видео / VFX / аудио
  'Blackmagic Design': 'Blackmagic Design Pty Ltd',
  Avid: 'Avid Technology, Inc.',
  Foundry: 'The Foundry Visionmongers Ltd',
  'Boris FX': 'Boris FX, Inc.',
  'Topaz Labs': 'Topaz Labs LLC',
  Wondershare: 'Wondershare Technology Group Co., Ltd.',
  'MAGIX Vegas': 'MAGIX Software GmbH',
  Telestream: 'Telestream, LLC',
  'Native Instruments': 'Native Instruments GmbH',
  'Epidemic Sound': 'Epidemic Sound AB',
  Artlist: 'Artlist Ltd',
  'Motion Array': 'Motion Array LLC',
  Runway: 'Runway AI, Inc.',
  ElevenLabs: 'ElevenLabs Inc.',
  Descript: 'Descript, Inc.',
  HeyGen: 'HeyGen, Inc.',
};

export function vendorLegal(vendor?: string | null): string {
  if (!vendor) return '';
  // Первый источник — профиль производителя: поле legalName заполнено у всех
  // записей реестра, тогда как словарь ниже покрывал сорок с небольшим имён,
  // и карточки OpenAI, Anthropic, Figma показывали марку вместо юрлица
  // (постановка руководителя 14.09.2026). Словарь остаётся для имён, которых
  // в реестре лендингов нет: он ведётся по написанию поля `vendor` каталога.
  const entry = vendorBySlug(vendorSlug(vendor));
  return entry?.legalName || VENDOR_LEGAL[vendor] || vendor;
}

/**
 * Индексная матрица: какие товары НЕ индексировать (noindex + вне sitemap и
 * фидов) — по сегментам артикула единой системы (docs/rules/sku-system.md):
 *
 * - плагины JetBrains Marketplace (`JB` + `ADD`): сотни карточек, отличающихся
 *   одним словом;
 * - личные планы (план `IND`) любого вендора: сайт продаёт юрлицам, а срез
 *   покрытия 03.09.2026 показал, что Яндекс исключал такие карточки как
 *   малоценные (Bitdefender, Monotype, Marmoset). Исключение —
 *   `IND_INDEXABLE_VENDORS` ниже: вендор, у которого личный план и есть
 *   основной товар, а не хвост командной линейки;
 * - бессрочные дубли ManageEngine (`ZOHO` + `PERP`): у каждой есть парная
 *   годовая подписка с тем же текстом (разбор 03.09.2026) — в поиск идёт
 *   подписка, бессрочная остаётся на витрине и в КП;
 * - продления (вариант `RENEWAL`): иначе конкурируют со страницей первой
 *   покупки того же тарифа (решение руководителя 29.08.2026);
 * - номиналы кредитов и подарочных карт (`CRD`/`GFT` с вариантом): линейка
 *   отличается только числом, интент держит родитель линейки или страница
 *   вендора (замер Вордстата 02.09.2026, правило подарочных карт 05.09.2026).
 *
 * Основные продукты для организаций, AI и командные инструменты индексируются.
 * Позиция без системного артикула страницы не имеет и в матрицу не попадает.
 */
/**
 * Вендоры, у которых личный план индексируется вопреки общему правилу.
 *
 * Правило `IND` → noindex заведено против хвостов командных линеек: у
 * Bitdefender или Monotype личная лицензия — младший вариант того же
 * продукта, и её карточка дублирует командную. У TryHackMe наоборот: личные
 * Premium и MAX — основной товар вендора, командный тариф всего один, и
 * дублировать личным карточкам нечего (решение руководителя 15.09.2026).
 * У Perplexity (решение руководителя 22.09.2026) личные Pro и Max — не
 * младшая ступень Enterprise Pro, а другой продукт: без консоли организации,
 * единого входа и поиска по внутренним файлам, с собственными текстами и
 * метой. Дублировать командным карточкам им нечем, а запросы «Perplexity Pro
 * купить» и «Perplexity Max цена» без этих страниц не ловятся вовсе.
 *
 * Код вендора — из `data/catalog/sku-vendors.json`. Список пополняется
 * только решением руководителя: каждая запись — страницы, которые сайт
 * предъявляет поиску.
 */
const IND_INDEXABLE_VENDORS = new Set(['THM', 'PPLX']);

export function productNoindex(sku?: string | null): boolean {
  const p = parseSku(sku);
  if (!p) return false;
  if (p.vendor === 'JB' && p.kind === 'ADD') return true;
  if (p.plan === 'IND' && !IND_INDEXABLE_VENDORS.has(p.vendor)) return true;
  if (p.vendor === 'ZOHO' && p.term === 'PERP') return true;
  if (p.variant === 'RENEWAL') return true;
  if ((p.kind === 'CRD' || p.kind === 'GFT') && p.variant) return true;
  return false;
}

/** Товар — подарочная карта (родитель или вариант). */
export function isGiftCard(p: Pick<Product, 'product_type'>): boolean {
  return p.product_type === 'gift_card';
}

/** Товар — вариант другого товара (номинал, регион): страницы не имеет. */
export function isVariant(p: Pick<Product, 'parent_sku'>): boolean {
  return Boolean(p.parent_sku);
}

/**
 * Позиции для витринных списков (каталог, лендинг вендора, поиск на сайте):
 * варианты скрыты — их представляет родительская карточка с выбором
 * региона и номинала. В корзине, КП и WebMCP варианты остаются: там нужен
 * конкретный артикул с ценой.
 */
export function listingProducts<T extends Pick<Product, 'parent_sku'>>(products: T[]): T[] {
  return products.filter((p) => !isVariant(p));
}
