/**
 * Единый поиск по каталогу в памяти: страница /catalog?q=… и WebMCP-инструмент
 * search_products обязаны находить одно и то же — поэтому логика одна.
 *
 * Поиск токенный: каждое слово запроса должно встретиться в «стоге»
 * (название + производитель + ключевые слова + sku). Прежний поиск страницы
 * искал запрос как одну подстроку и не находил «Claude для команды», если
 * слова в карточке стоят в другом порядке. Если по И-логике не нашлось
 * ничего, пробуем ИЛИ — лучше показать близкое, чем пустой список.
 */
import type { Product } from './types';
import { effectivePrice } from './pricing';

function haystack(p: Product): string {
  return `${p.name} ${p.vendor || ''} ${p.keywords || ''} ${p.sku}`.toLowerCase();
}

function tokens(q: string): string[] {
  return q.toLowerCase().split(/[^\p{L}\p{N}.+-]+/u).filter((t) => t.length >= 2);
}

/** «Цена по запросу» — всегда в конце списка (как на странице каталога). */
function byRequestLast(a: Product, b: Product): number {
  return Number(!(effectivePrice(a).price > 0)) - Number(!(effectivePrice(b).price > 0));
}

export function searchProducts(products: Product[], query: string): Product[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const toks = tokens(q);
  const scored = products
    .map((p) => {
      const h = haystack(p);
      const phrase = h.includes(q);
      const hit = toks.length ? toks.filter((t) => h.includes(t)).length : 0;
      return { p, phrase, hit };
    });
  let found = scored.filter((s) => s.phrase || (toks.length > 0 && s.hit === toks.length));
  if (found.length === 0) found = scored.filter((s) => s.hit > 0);
  return found
    .sort((a, b) =>
      byRequestLast(a.p, b.p)
      || Number(b.phrase) - Number(a.phrase)
      || b.hit - a.hit
      || (a.p.sort ?? 0) - (b.p.sort ?? 0))
    .map((s) => s.p);
}
