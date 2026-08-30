/**
 * Ядро механизма фидов: отбор товаров под требования товарных площадок,
 * ранжирование по спросу Вордстата и лимит позиций.
 *
 * Чистые функции без сети и без привязки к конкретному сервису — особенности
 * сервисов подключаются через FeedSelectOptions.extraFilter и сериализаторы.
 */
import type { Product } from '../types';
import { effectivePrice } from '../pricing';
import { productNoindex, productKind } from '../catalog';
import type { FeedSelectOptions } from './types';

/**
 * Базовые требования товарных площадок к карточке (общие для всех фидов):
 * - опубликована и индексируется (noindex-карточки скрыты и от поиска,
 *   и от площадок — те же плагины JB-PLG-*, личные *-IND, продления *-RENEWAL);
 * - есть название, slug (URL) и артикул;
 * - известна точная цена больше нуля («цена по запросу» площадки не принимают;
 *   карточки «от N ₽» идут с этой минимальной ценой — она видна и на сайте).
 */
export function feedEligible(p: Product, now: Date = new Date()): boolean {
  if (!p.name || !p.slug || !p.sku) return false;
  if (p.noindex || productNoindex(p.sku)) return false;
  const eff = effectivePrice(p, now);
  if (!Number.isFinite(eff.price) || eff.price <= 0) return false;
  return true;
}

/**
 * Ключ сортировки: спрос вендора в Вордстате (по убыванию), внутри вендора —
 * основные продукты раньше дополнений, затем витринный sort и имя.
 * Вендор без данных Вордстата получает спрос 0 и уходит в хвост.
 */
export function rankProducts(products: Product[], demand: Record<string, number>): Product[] {
  return [...products].sort((a, b) => {
    const da = demand[a.vendor || ''] || 0;
    const db = demand[b.vendor || ''] || 0;
    if (da !== db) return db - da;
    const va = a.vendor || '';
    const vb = b.vendor || '';
    if (va !== vb) return va.localeCompare(vb, 'ru');
    const ka = productKind(a) === 'main' ? 0 : 1;
    const kb = productKind(b) === 'main' ? 0 : 1;
    if (ka !== kb) return ka - kb;
    const sa = a.sort ?? Number.MAX_SAFE_INTEGER;
    const sb = b.sort ?? Number.MAX_SAFE_INTEGER;
    if (sa !== sb) return sa - sb;
    return a.name.localeCompare(b.name, 'ru');
  });
}

/** Полный конвейер отбора: фильтр требований → фильтр сервиса → ранг → лимит. */
export function selectFeedProducts(products: Product[], opts: FeedSelectOptions): Product[] {
  const now = opts.now ?? new Date();
  let picked = products.filter((p) => feedEligible(p, now));
  if (opts.extraFilter) picked = picked.filter(opts.extraFilter);
  picked = rankProducts(picked, opts.demand);
  if (opts.maxOffers && opts.maxOffers > 0) picked = picked.slice(0, opts.maxOffers);
  return picked;
}

/** Плоский текст из HTML/markdown-полей карточки (для description фида). */
export function plainText(raw: string | null | undefined): string {
  if (!raw) return '';
  return raw
    .replace(/<[^>]+>/g, ' ') // теги
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Описание оффера: первый непустой источник, обрезанный по лимиту сервиса
 * по границе слова. Пустым не бывает — площадки требуют description.
 */
export function offerDescription(p: Product, maxLen: number): string {
  const raw =
    plainText(p.short_description) || plainText(p.meta_description) || plainText(p.seo_text)
    || `${p.name} — лицензия для бизнеса. Оплата по счёту, закрывающие документы.`;
  if (raw.length <= maxLen) return raw;
  const cut = raw.slice(0, maxLen - 1); // −1: многоточие тоже входит в лимит
  const lastSpace = cut.lastIndexOf(' ');
  return (lastSpace > maxLen * 0.6 ? cut.slice(0, lastSpace) : cut).trimEnd() + '…';
}
