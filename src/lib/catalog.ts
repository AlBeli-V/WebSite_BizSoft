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
/**
 * Пакеты дополнительных кредитов вендора: <VENDOR>-CREDITS-<объём>.
 * Покупаются поверх подписки и без неё не имеют смысла — это дополнение,
 * а не самостоятельный продукт: так они и подписаны в фасете каталога,
 * в порядке выгрузок и в ответах агентам.
 */
const CREDITS_PACK = /-CREDITS-\d+$/;
/**
 * Вариант подарочной карты: <РОДИТЕЛЬ>-GIFT-CARD-<регион>-<номинал>, например
 * APP-STORE-ITUNES-GIFT-CARD-RU-1000. Родитель заканчивается на -GIFT-CARD и
 * является страницей; варианты — номиналы одного продукта, страниц не имеют.
 */
const GIFT_CARD_VARIANT = /-GIFT-CARD-[A-Z]{2}-\d+$/;

/** Классифицировать товар по контексту (sku). */
export function productKind(p: Pick<Product, 'sku'>): ProductKind {
  const sku = (p.sku || '').toUpperCase();
  if (sku.startsWith('JB-PLG-')) return 'addon';
  if (ZOOM_ADDON.test(sku)) return 'addon';
  if (CREDITS_PACK.test(sku)) return 'addon';
  return 'main';
}

/**
 * Сколько опубликованных товаров в каждом разделе (ключ — slug категории).
 *
 * Один расчёт на страницу каталога и на инструмент list_categories: раздел,
 * который человек видит в каталоге, и раздел, который агент предлагает как
 * фильтр, обязаны совпадать. Пустые разделы отбрасывает уже потребитель —
 * фильтр по разделу без товаров выглядит как поломка.
 */
export function countByCategory(products: Pick<Product, 'category'>[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const p of products) {
    const slug = typeof p.category === 'object' && p.category ? p.category.slug : '';
    if (slug) counts[slug] = (counts[slug] || 0) + 1;
  }
  return counts;
}

/** Полное юридическое название производителя для отображения в карточке. */
export const VENDOR_LEGAL: Record<string, string> = {
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
  return VENDOR_LEGAL[vendor] || vendor;
}

/**
 * Индексная матрица: какие товары НЕ индексировать (noindex + вне sitemap и фидов).
 * Сейчас: плагины JetBrains Marketplace (JB-PLG-*), личные лицензии любого
 * вендора (*-IND), бессрочные дубли ManageEngine (ME-*-PERP), карточки
 * продлений (*-RENEWAL) и пакеты кредитов (*-CREDITS-<объём>).
 * Основные продукты для организаций, AI и командные инструменты — индексируются.
 */
export function productNoindex(sku?: string | null): boolean {
  const s = (sku || '').toUpperCase();
  if (s.startsWith('JB-PLG-')) return true;               // 867 плагинов Marketplace
  // Личные лицензии (*-IND) любого вендора: сайт продаёт юрлицам, а срез
  // покрытия 03.09.2026 показал, что Яндекс исключил 6 из 7 таких карточек
  // как малоценные (Bitdefender, Monotype, Marmoset). Правило было только для
  // JetBrains — теперь для всех.
  if (s.endsWith('-IND')) return true;
  // Бессрочные лицензии ManageEngine (ME-*-PERP): у каждой из 81 карточки есть
  // парная годовая подписка с тем же текстом, отличие — «вечная лицензия» в
  // названии. Google держал их в очереди «обнаружена, не сканирована»,
  // Яндекс исключал как малоценные (разбор 03.09.2026). Бессрочный вариант
  // остаётся на витрине и в КП, в поиск идёт карточка подписки.
  if (s.startsWith('ME-') && s.endsWith('-PERP')) return true;
  // Карточки продления (у вендора цена продления выше первого года): живут на
  // витрине и в КП, но в поиск не идут — иначе конкурируют со страницей
  // первой покупки того же тарифа (решение руководителя 29.08.2026).
  if (s.endsWith('-RENEWAL')) return true;
  // Пакеты кредитов (<VENDOR>-CREDITS-<объём>): линейка отличается только числом,
  // а замер Вордстата 02.09.2026 даёт на весь покупательский интент около сотни
  // показов в месяц («купить кредиты kling» — 37, «kling ai купить кредиты» — 27,
  // «пополнить kling ai» — 39). Восемь почти одинаковых страниц под один интент —
  // это малоценные страницы и каннибализация вендорской страницы, которая уже
  // держит брендовый спрос («kling ai купить» — 312). Карточки живут на витрине,
  // в корзине и в КП; интент «купить кредиты <вендор>» держит страница вендора.
  if (CREDITS_PACK.test(s)) return true;
  // Варианты подарочных карт (<…>-GIFT-CARD-<регион>-<номинал>): регион и
  // номинал — варианты одного продукта, а не отдельные страницы. Отдельная
  // индексируемая страница на каждый номинал — те же дубли, что у пакетов
  // кредитов. Страница варианта отдаёт 301 на родительскую карточку; в поиск
  // идёт только она.
  if (GIFT_CARD_VARIANT.test(s)) return true;
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
