/**
 * Тонкий fetch-клиент Directus REST API (без тяжёлого SDK).
 * Чтение каталога — публичной ролью (status=published).
 * Запись (leads/quotes) и инструменты цен — со статическим токеном из .env.
 *
 * Все вызовы — server-side (SSR/эндпоинты). На прод Directus доступен по
 * внутренней docker-сети (http://directus:8055); локально — через SSH-тоннель.
 */
import type { Category, Product, CurrencyRate, PublishStatus } from './types';
import { listValues } from './types';

// Серверные значения читаем из process.env (рантайм) ПЕРЕД import.meta.env,
// чтобы прод-окружение (Docker env) переопределяло любые значения сборки.
const DIRECTUS_URL = (process.env.DIRECTUS_URL || import.meta.env.DIRECTUS_URL || 'http://127.0.0.1:8055').replace(/\/$/, '');
const DIRECTUS_TOKEN = process.env.DIRECTUS_TOKEN || import.meta.env.DIRECTUS_TOKEN || '';

interface FetchOpts {
  auth?: boolean; // подставить служебный токен (для записи/инструментов)
  method?: string;
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
}

export class DirectusError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

/**
 * Потолок ожидания ответа Directus. Без него зависший (а не упавший) Directus
 * держит SSR-запрос открытым бесконечно: соединения Node копятся, и сайт
 * перестаёт отвечать целиком, хотя сам процесс жив. Значение щедрое —
 * выборки идут с limit: -1 и на холодной БД занимают секунды.
 * Настраивается через DIRECTUS_TIMEOUT_MS.
 */
const DIRECTUS_TIMEOUT_MS = Number(process.env.DIRECTUS_TIMEOUT_MS ?? 10_000);

async function dx<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  const url = new URL(DIRECTUS_URL + path);
  if (opts.params) {
    for (const [k, v] of Object.entries(opts.params)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }
  // Весь доступ к Directus — серверный. Сервисный токен шлём всегда (если задан):
  // в этой редакции Directus публичные read-права с фильтром ограничены, поэтому
  // и чтение каталога идёт под сервисной ролью, а фильтр status=published —
  // в самих запросах ниже.
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (DIRECTUS_TOKEN) headers.Authorization = `Bearer ${DIRECTUS_TOKEN}`;

  let res: Response;
  try {
    res = await fetch(url, {
      method: opts.method || 'GET',
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      signal: DIRECTUS_TIMEOUT_MS > 0 ? AbortSignal.timeout(DIRECTUS_TIMEOUT_MS) : undefined,
    });
  } catch (e) {
    // Обрыв и таймаут приводим к тому же типу, что и ошибки Directus, чтобы
    // вызывающий код различал «нет данных» и «источник недоступен» одинаково.
    const timedOut = e instanceof Error && (e.name === 'TimeoutError' || e.name === 'AbortError');
    throw new DirectusError(
      `Directus ${path}: ${timedOut ? `нет ответа за ${DIRECTUS_TIMEOUT_MS} мс` : (e as Error).message}`,
      504,
    );
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j?.errors?.[0]?.message || detail;
    } catch {
      /* ignore */
    }
    throw new DirectusError(`Directus ${path}: ${detail}`, res.status);
  }
  if (res.status === 204) return undefined as T;
  const json = (await res.json()) as { data: T };
  return json.data;
}

/**
 * In-memory кэш публичных чтений каталога (TTL, по умолчанию 60 с).
 * Каждая SSR-страница без кэша тянула из Directus весь каталог (~400 товаров
 * со всеми SEO-полями) — кэш срезает TTFB и нагрузку на БД на порядок.
 * Админ-чтения и записи НЕ кэшируются. Ошибки не кэшируются.
 * Отключение: CATALOG_CACHE_TTL_MS=0.
 */
const CACHE_TTL_MS = Number(process.env.CATALOG_CACHE_TTL_MS ?? 60_000);
// stale-while-revalidate: после истечения TTL устаревшее значение отдаётся
// сразу (без ожидания Directus), а обновление идёт в фоне. Потолок
// устаревания — 10 TTL (10 минут по умолчанию), дальше ждём свежие данные.
const STALE_MAX_MS = CACHE_TTL_MS * 10;
const readCache = new Map<string, { t: number; v: unknown; refreshing?: boolean }>();
async function cached<T>(key: string, fn: () => Promise<T>): Promise<T> {
  if (!(CACHE_TTL_MS > 0)) return fn();
  const hit = readCache.get(key);
  const now = Date.now();
  if (hit && now - hit.t < CACHE_TTL_MS) return hit.v as T;
  if (hit && now - hit.t < STALE_MAX_MS) {
    if (!hit.refreshing) {
      hit.refreshing = true;
      fn()
        .then((v) => readCache.set(key, { t: Date.now(), v }))
        .catch(() => { hit.refreshing = false; });
    }
    return hit.v as T;
  }
  const v = await fn();
  readCache.set(key, { t: now, v });
  // страховка от разрастания (карточек ~сотни, но пусть будет предел)
  if (readCache.size > 2000) readCache.clear();
  return v;
}

const PRODUCT_FIELDS = [
  'id',
  'name',
  'sku',
  'vendor',
  'origin',
  'license_type',
  'slug',
  'short_description',
  'description',
  'seo_text',
  'keywords',
  'meta_title',
  'meta_description',
  'price',
  'price_note',
  'vat_percent',
  'currency',
  'base_price_usd',
  'base_price_eur',
  'peg_currency',
  'peg_to_usd',
  'markup_coeff',
  'markup_percent',
  'price_locked',
  'promo_price',
  'promo_label',
  'promo_start',
  'promo_end',
  'features',
  'faq',
  'sort',
  'status',
  'noindex',
  'date_updated',
  'for_whom',
  'use_cases',
  'former_names',
  'old_slugs',
  'related_products',
  'related_solutions',
  'price_from',
  'category.id',
  'category.name',
  'category.slug',
  'image',
  'images.directus_files_id.id',
  'images.directus_files_id.title',
].join(',');

export interface ProductFilter {
  origin?: 'domestic' | 'foreign';
  categorySlug?: string;
  vendor?: string;
  /** поиск по названию/вендору/ключевым словам */
  q?: string;
}

/** Все опубликованные категории, отсортированные. */
export async function getCategories(): Promise<Category[]> {
  return cached('categories', () => dx<Category[]>('/items/categories', {
    params: {
      filter: JSON.stringify({ status: { _eq: 'published' } }),
      sort: 'sort,name',
      limit: -1,
    },
  }));
}

export async function getCategoryBySlug(slug: string): Promise<Category | null> {
  return cached(`category:${slug}`, async () => {
    const data = await dx<Category[]>('/items/categories', {
      params: {
        filter: JSON.stringify({ slug: { _eq: slug }, status: { _eq: 'published' } }),
        limit: 1,
      },
    });
    return data[0] ?? null;
  });
}

/** Опубликованные товары с фильтрами (origin/категория/вендор/поиск). */
export async function getProducts(opts: ProductFilter = {}): Promise<Product[]> {
  return cached(`products:${JSON.stringify(opts)}`, () => fetchProducts(opts));
}

async function fetchProducts(opts: ProductFilter = {}): Promise<Product[]> {
  const and: Record<string, unknown>[] = [{ status: { _eq: 'published' } }];
  // Отечественное ПО с сайта убрано: показываем только зарубежное.
  // При явном origin используем его (кроме domestic — оно всегда исключается).
  if (opts.origin && opts.origin !== 'domestic') and.push({ origin: { _eq: opts.origin } });
  else and.push({ origin: { _neq: 'domestic' } });
  if (opts.categorySlug) and.push({ category: { slug: { _eq: opts.categorySlug } } });
  if (opts.vendor) and.push({ vendor: { _eq: opts.vendor } });
  if (opts.q) {
    const q = opts.q;
    and.push({ _or: [{ name: { _icontains: q } }, { vendor: { _icontains: q } }, { keywords: { _icontains: q } }, { sku: { _icontains: q } }] });
  }
  return dx<Product[]>('/items/products', {
    params: {
      fields: PRODUCT_FIELDS,
      filter: JSON.stringify({ _and: and }),
      sort: 'sort,name',
      limit: -1,
    },
  });
}

/** Список вендоров (опц. в рамках происхождения) с количеством товаров. */
export async function getVendors(origin?: 'domestic' | 'foreign'): Promise<{ vendor: string; count: number }[]> {
  return cached(`vendors:${origin || ''}`, () => fetchVendors(origin));
}

async function fetchVendors(origin?: 'domestic' | 'foreign'): Promise<{ vendor: string; count: number }[]> {
  const filter: Record<string, unknown> = { status: { _eq: 'published' } };
  // Отечественное ПО исключено из выдачи вендоров.
  if (origin && origin !== 'domestic') filter.origin = { _eq: origin };
  else filter.origin = { _neq: 'domestic' };
  const rows = await dx<{ vendor: string | null }[]>('/items/products', {
    params: { fields: 'vendor', filter: JSON.stringify(filter), limit: -1 },
  });
  const counts = new Map<string, number>();
  for (const r of rows) {
    if (!r.vendor) continue;
    counts.set(r.vendor, (counts.get(r.vendor) || 0) + 1);
  }
  return [...counts.entries()].map(([vendor, count]) => ({ vendor, count })).sort((a, b) => a.vendor.localeCompare(b.vendor, 'ru'));
}

/** Если slug устарел (есть в old_slugs опубликованного товара) — вернуть актуальный slug для 301. */
export async function findCanonicalProductSlug(oldSlug: string): Promise<string | null> {
  return cached(`canonical:${oldSlug}`, async () => {
  const rows = await dx<{ slug: string; old_slugs?: unknown }[]>('/items/products', {
    params: { fields: 'slug,old_slugs', filter: JSON.stringify({ status: { _eq: 'published' } }), limit: -1 },
  });
  for (const r of rows) {
    if (listValues(r.old_slugs).includes(oldSlug)) return r.slug;
  }
  return null;
  });
}

export async function getProductBySlug(slug: string): Promise<Product | null> {
  return cached(`product:${slug}`, async () => {
    const data = await dx<Product[]>('/items/products', {
      params: {
        fields: PRODUCT_FIELDS,
        filter: JSON.stringify({ slug: { _eq: slug }, status: { _eq: 'published' } }),
        limit: 1,
      },
    });
    return data[0] ?? null;
  });
}

/** Товары по списку sku (для пересчёта корзины на сервере при генерации КП). */
export async function getProductsBySkus(skus: string[]): Promise<Product[]> {
  if (skus.length === 0) return [];
  return dx<Product[]>('/items/products', {
    params: {
      fields: PRODUCT_FIELDS,
      filter: JSON.stringify({ sku: { _in: skus }, status: { _eq: 'published' } }),
      limit: -1,
    },
  });
}

/** Опубликованные товары по списку slug (для блоков «связанные товары»). */
export async function getProductsBySlugs(slugs: string[]): Promise<Product[]> {
  if (!slugs.length) return [];
  return cached(`slugs:${[...slugs].sort().join(',')}`, () => dx<Product[]>('/items/products', {
    params: {
      fields: 'id,name,slug,vendor,origin,short_description,price,promo_price,promo_start,promo_end,currency,license_type,image',
      filter: JSON.stringify({ slug: { _in: slugs }, status: { _eq: 'published' } }),
      limit: -1,
    },
  }));
}

/** Все товары для инструментов цен (любой статус) — требует токен. */
export async function getAllProductsAdmin(): Promise<Product[]> {
  return dx<Product[]>('/items/products', {
    auth: true,
    params: { fields: PRODUCT_FIELDS, sort: 'sort,name', limit: -1 },
  });
}

export async function createLead(payload: Record<string, unknown>): Promise<void> {
  await dx('/items/leads', { auth: true, method: 'POST', body: payload });
}

export async function createQuote(payload: Record<string, unknown>): Promise<void> {
  await dx('/items/quotes', { auth: true, method: 'POST', body: payload });
}

export async function patchProduct(id: string | number, payload: Record<string, unknown>): Promise<void> {
  await dx(`/items/products/${id}`, { auth: true, method: 'PATCH', body: payload });
}

export async function createProduct(payload: Record<string, unknown>): Promise<{ id: string | number }> {
  return dx<{ id: string | number }>('/items/products', { auth: true, method: 'POST', body: payload });
}

/** Текущий курс/настройки валюты (singleton-подобная коллекция). */
export async function getCurrencyRate(): Promise<CurrencyRate | null> {
  const data = await dx<CurrencyRate[]>('/items/currency_rate', {
    auth: true,
    params: { limit: 1, sort: '-updated_at' },
  });
  return data[0] ?? null;
}

export async function upsertCurrencyRate(payload: Partial<CurrencyRate>): Promise<CurrencyRate> {
  const existing = await getCurrencyRate();
  if (existing?.id != null) {
    return dx<CurrencyRate>(`/items/currency_rate/${existing.id}`, { auth: true, method: 'PATCH', body: payload });
  }
  return dx<CurrencyRate>('/items/currency_rate', { auth: true, method: 'POST', body: payload });
}

/** URL ассета медиатеки Directus по id файла. */
export function assetUrl(fileId: string, params?: Record<string, string | number>): string {
  const u = new URL(`${DIRECTUS_URL}/assets/${fileId}`);
  if (params) for (const [k, v] of Object.entries(params)) u.searchParams.set(k, String(v));
  return u.toString();
}

/** URL логотипа товара (поле image), если задан. */
export function logoUrl(p: Product, params?: Record<string, string | number>): string | null {
  return p.image ? assetUrl(p.image, params) : null;
}

/** Галерея изображений товара [{url, title}] из M2M images (+ логотип первым). */
export function galleryImages(p: Product): { url: string; title: string }[] {
  const out: { url: string; title: string }[] = [];
  const seen = new Set<string>();
  if (p.image) { out.push({ url: assetUrl(p.image), title: p.name }); seen.add(p.image); }
  for (const ref of p.images || []) {
    const f = ref?.directus_files_id;
    const id = typeof f === 'string' ? f : f?.id;
    if (!id || seen.has(id)) continue;
    seen.add(id);
    const title = typeof f === 'object' && f?.title ? f.title : p.name;
    out.push({ url: assetUrl(id), title });
  }
  return out;
}

export { DIRECTUS_URL, type PublishStatus };
