/**
 * Тонкий fetch-клиент Directus REST API (без тяжёлого SDK).
 * Чтение каталога — публичной ролью (status=published).
 * Запись (leads/quotes) и инструменты цен — со статическим токеном из .env.
 *
 * Все вызовы — server-side (SSR/эндпоинты). На прод Directus доступен по
 * внутренней docker-сети (http://directus:8055); локально — через SSH-тоннель.
 */
import type { Category, Product, CurrencyRate, PublishStatus } from './types';

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

  const res = await fetch(url, {
    method: opts.method || 'GET',
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });

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

const PRODUCT_FIELDS = [
  'id',
  'name',
  'sku',
  'slug',
  'short_description',
  'description',
  'seo_text',
  'meta_title',
  'meta_description',
  'price',
  'currency',
  'base_price_usd',
  'peg_to_usd',
  'markup_percent',
  'promo_price',
  'promo_label',
  'promo_start',
  'promo_end',
  'features',
  'faq',
  'sort',
  'status',
  'category.id',
  'category.name',
  'category.slug',
  'images.directus_files_id',
].join(',');

/** Все опубликованные категории, отсортированные. */
export async function getCategories(): Promise<Category[]> {
  return dx<Category[]>('/items/categories', {
    params: {
      filter: JSON.stringify({ status: { _eq: 'published' } }),
      sort: 'sort,name',
      limit: -1,
    },
  });
}

export async function getCategoryBySlug(slug: string): Promise<Category | null> {
  const data = await dx<Category[]>('/items/categories', {
    params: {
      filter: JSON.stringify({ slug: { _eq: slug }, status: { _eq: 'published' } }),
      limit: 1,
    },
  });
  return data[0] ?? null;
}

/** Опубликованные товары (опционально — по категории). */
export async function getProducts(opts: { categorySlug?: string } = {}): Promise<Product[]> {
  const filter: Record<string, unknown> = { status: { _eq: 'published' } };
  if (opts.categorySlug) filter.category = { slug: { _eq: opts.categorySlug } };
  return dx<Product[]>('/items/products', {
    params: {
      fields: PRODUCT_FIELDS,
      filter: JSON.stringify(filter),
      sort: 'sort,name',
      limit: -1,
    },
  });
}

export async function getProductBySlug(slug: string): Promise<Product | null> {
  const data = await dx<Product[]>('/items/products', {
    params: {
      fields: PRODUCT_FIELDS,
      filter: JSON.stringify({ slug: { _eq: slug }, status: { _eq: 'published' } }),
      limit: 1,
    },
  });
  return data[0] ?? null;
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

export { DIRECTUS_URL, type PublishStatus };
