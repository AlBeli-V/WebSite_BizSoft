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

/**
 * Поля закупки, добавленные схемой 28.08.2026 (purchase_updated_at,
 * purchase_source). Запрашиваются отдельным списком с откатом: Directus
 * отвечает 400 на ВЕСЬ запрос, если хоть одно поле из fields не существует,
 * и до прогона ops-directus-schema на проде каталог и КП падали бы целиком
 * из-за не доехавшей миграции. Каталог важнее свежести даты закупки.
 *
 * Тем же списком идут поля вариантов и типа товара (схема 05.09.2026,
 * подарочные карты): product_type, parent_sku, region_code, region_name,
 * denomination, denomination_currency, availability — с тем же откатом.
 */
const VARIANT_FIELDS = 'product_type,parent_sku,region_code,region_name,denomination,denomination_currency,availability,variant_label';
const PRODUCT_FIELDS_EXTRA = `${PRODUCT_FIELDS},purchase_updated_at,purchase_source,content_updated_at,${VARIANT_FIELDS}`;
let extraFieldsMissing = false;

async function productsQuery(params: Record<string, unknown>, auth = false): Promise<Product[]> {
  if (!extraFieldsMissing) {
    try {
      return await dx<Product[]>('/items/products', {
        auth,
        params: { ...params, fields: PRODUCT_FIELDS_EXTRA },
      });
    } catch (e) {
      // Запоминаем до перезапуска процесса: после применения схемы поля
      // появятся, и новый деплой снова начнёт их запрашивать.
      extraFieldsMissing = true;
      console.warn('products: поля схемы 28.08/03.09/05.09 недоступны, запрос без них', e);
    }
  }
  return dx<Product[]>('/items/products', { auth, params: { ...params, fields: PRODUCT_FIELDS } });
}

/**
 * Поля, правка которых не меняет страницу для поисковика: цены и наценки
 * (их ежедневно двигает переоценка по курсу ЦБ), дата и источник закупки,
 * порядок сортировки. Любая другая правка — содержательная: она ставит
 * content_updated_at, из которого sitemap берёт lastmod.
 *
 * date_updated для lastmod не годится: Directus сдвигает его при любом
 * PATCH, и после переоценки 02.09.2026 у 537 карточек из 593 стоял один и
 * тот же lastmod — сигнал свежести для Google обесценился (разбор 03.09.2026).
 */
const CONTENT_NEUTRAL_FIELDS = new Set([
  'id', 'price', 'markup_coeff', 'markup_percent', 'base_price_usd', 'base_price_eur',
  'peg_currency', 'peg_to_usd', 'price_locked', 'purchase_updated_at', 'purchase_source',
  'sort', 'content_updated_at',
]);

export function isContentChange(payload: Record<string, unknown>): boolean {
  return Object.keys(payload).some((k) => !CONTENT_NEUTRAL_FIELDS.has(k));
}

/**
 * Дополнить payload штампом содержательного изменения. Пока схема без поля
 * (ops-directus-schema ещё не прогнан), штамп не ставится: Directus
 * отклоняет PATCH с неизвестным полем целиком, а каталог важнее даты.
 */
export function withContentStamp<T extends Record<string, unknown>>(payload: T, now = new Date()): T {
  if (extraFieldsMissing || 'content_updated_at' in payload || !isContentChange(payload)) return payload;
  return { ...payload, content_updated_at: now.toISOString() };
}

/** Записать со штампом; если Directus отверг именно штамп — повторить без него. */
async function writeWithStamp(
  write: (body: Record<string, unknown>) => Promise<unknown>,
  payload: Record<string, unknown>,
): Promise<unknown> {
  const stamped = withContentStamp(payload);
  if (stamped === payload) return write(payload);
  try {
    return await write(stamped);
  } catch (e) {
    // Откат только на отказ самого Directus (4xx: неизвестное поле, нет прав
    // на него). Сеть, таймаут и 5xx — не про схему: повтор без штампа лишь
    // задвоил бы запись, а флаг ложно отключил бы штампы до перезапуска.
    if (!(e instanceof DirectusError) || e.status >= 500) throw e;
    extraFieldsMissing = true;
    console.warn('products: content_updated_at не принят схемой, запись без штампа', e);
    return write(payload);
  }
}

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

/**
 * Срез каталога для счётчиков витрины: по одному вендору и слагу категории
 * на позицию.
 *
 * Главной нужны только числа — сколько всего позиций, сколько вендоров и
 * сколько товаров в каждом направлении. Раньше она брала их из полной
 * выборки getProducts(), то есть тянула на каждую позицию описание, SEO-текст,
 * характеристики и вопросы. После истечения кэша первый запрос оплачивал эту
 * выгрузку целиком, и главная проваливалась по времени ответа: три подряд
 * замера Lighthouse на одном и том же коде дали 52, 73 и 95 баллов, тогда как
 * раздел каталога с узкой выборкой держал 90 стабильно.
 *
 * Два поля вместо полусотни: объём ответа падает примерно в сто раз.
 */
export async function getCatalogFacets(): Promise<{ vendor: string | null; category: { slug: string } | null }[]> {
  return cached('facets', () => dx<{ vendor: string | null; category: { slug: string } | null }[]>('/items/products', {
    params: {
      fields: 'vendor,category.slug',
      // Те же условия, что у витрины: опубликованное и не отечественное.
      filter: JSON.stringify({ _and: [{ status: { _eq: 'published' } }, { origin: { _neq: 'domestic' } }] }),
      limit: -1,
    },
  }));
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
/**
 * Варианты товара (номиналы подарочной карты) по артикулу родителя.
 * Опубликованные, в порядке базы — порядок для витрины задаёт
 * lib/gift-cards.ts (denomination DESC), а не sort и не id.
 */
export async function getProductVariants(parentSku: string): Promise<Product[]> {
  return cached(`variants:${parentSku}`, () => productsQuery({
    filter: JSON.stringify({ _and: [{ status: { _eq: 'published' } }, { parent_sku: { _eq: parentSku } }] }),
    limit: -1,
  }));
}

export async function getProductsBySkus(skus: string[]): Promise<Product[]> {
  if (skus.length === 0) return [];
  // С полями закупки: выборку по артикулам использует расчёт экономики КП.
  return productsQuery({
    filter: JSON.stringify({ sku: { _in: skus }, status: { _eq: 'published' } }),
    limit: -1,
  });
}

/**
 * Позиции конфигуратора ManageEngine: и опубликованные карточки, и скрытые.
 *
 * Скрытые позиции живут в базе со статусом draft — у них есть артикул и
 * рублёвая цена, которую пересчитывает ежедневная переоценка, но нет ни
 * страницы, ни места в каталоге и в sitemap. Конфигуратору и расчёту КП они
 * нужны, иначе спецификацию нечем оценить.
 *
 * Фильтр по префиксу артикула — не украшение: без него любой черновик в
 * базе, включая неготовые карточки других вендоров, стало бы можно
 * подставить в корзину по угаданному sku.
 */
const ZOHO_SKU_PREFIX = /^(ME-|MANAGEENGINE-)/;

export function isZohoConfiguratorSku(sku: string): boolean {
  return ZOHO_SKU_PREFIX.test(sku);
}

export async function getZohoPositionsBySkus(skus: string[]): Promise<Product[]> {
  const allowed = skus.filter(isZohoConfiguratorSku);
  if (allowed.length === 0) return [];
  return productsQuery({
    filter: JSON.stringify({
      sku: { _in: allowed },
      status: { _in: ['published', 'draft'] },
    }),
    limit: -1,
  });
}

/** Опубликованные товары по списку slug (для блоков «связанные товары»). */
export async function getProductsBySlugs(slugs: string[]): Promise<Product[]> {
  if (!slugs.length) return [];
  return cached(`slugs:${[...slugs].sort().join(',')}`, () => dx<Product[]>('/items/products', {
    params: {
      // sku, price_note и promo_label добавлены для карточек витрины:
      // ProductCard печатает артикул и приписку к цене, effectivePrice —
      // подпись акции. Без них главная не смогла бы обойтись этой выборкой.
      fields: 'id,name,sku,slug,vendor,origin,short_description,price,price_note,promo_price,promo_label,promo_start,promo_end,currency,license_type,image',
      filter: JSON.stringify({ slug: { _in: slugs }, status: { _eq: 'published' } }),
      limit: -1,
    },
  }));
}

/** Все товары для инструментов цен (любой статус) — требует токен. */
/**
 * Поля, которых достаточно для переоценки по курсу ЦБ.
 *
 * Полная выборка тянет описания, тексты SEO, характеристики и вопросы —
 * килобайты на позицию. На шести тысячах товаров это десятки мегабайт
 * впустую: пересчёт смотрит только на себестоимость, коэффициент и текущую
 * цену, а пишет одно поле.
 */
const REPRICE_FIELDS = [
  // vendor и category.slug нужны не для расчёта, а для выбора области
  // переоценки: без них переоценка «по вендору» тихо не нашла бы ни одного
  // товара и отчиталась бы нулём изменений.
  'id', 'sku', 'name', 'vendor', 'origin', 'status',
  'price', 'base_price_usd', 'base_price_eur',
  'peg_currency', 'peg_to_usd', 'markup_coeff', 'price_locked',
  'category.slug',
].join(',');

/** Товары в объёме, достаточном для пересчёта цен. */
export async function getProductsForReprice(): Promise<Product[]> {
  return dx<Product[]>('/items/products', {
    auth: true,
    params: { fields: REPRICE_FIELDS, sort: 'id', limit: -1 },
  });
}

export async function getAllProductsAdmin(): Promise<Product[]> {
  // Через productsQuery: чтение с расширенным списком полей заодно выясняет,
  // знает ли схема content_updated_at, — до первой записи импорта.
  return productsQuery({ sort: 'sort,name', limit: -1 }, true);
}

export interface Lead {
  id: string | number;
  created_at?: string;
  updated_at?: string;
  name?: string;
  company?: string;
  email?: string;
  phone?: string;
  message?: string;
  product_ref?: string;
  source?: string;
  inn?: string;
  quote_no?: string;
  status?: string;
  owner?: string;
  amount?: number | null;
  qualified_at?: string | null;
  closed_at?: string | null;
  lost_reason?: string | null;
  next_action_at?: string | null;
  note?: string | null;
}

export async function createLead(payload: Record<string, unknown>): Promise<void> {
  await dx('/items/leads', { auth: true, method: 'POST', body: payload });
}

/** Заявки для админ-страницы воронки: свежие сверху. */
export async function getLeads(limit = 200): Promise<Lead[]> {
  return dx<Lead[]>('/items/leads', {
    auth: true,
    params: { limit, sort: '-created_at' },
  });
}

export async function patchLead(id: string | number, payload: Record<string, unknown>): Promise<void> {
  await dx(`/items/leads/${id}`, { auth: true, method: 'PATCH', body: payload });
}

export async function deleteLead(id: string | number): Promise<void> {
  await dx(`/items/leads/${id}`, { auth: true, method: 'DELETE' });
}

export interface LeadEvent {
  id: string | number;
  created_at?: string;
  lead?: number;
  kind?: string;
  author?: string;
  subject?: string;
  text?: string;
}

/** История работы по всем заявкам: письма, звонки, заметки, смены стадии. */
export async function getLeadEvents(limit = 1000): Promise<LeadEvent[]> {
  return dx<LeadEvent[]>('/items/lead_events', {
    auth: true,
    params: { limit, sort: '-created_at' },
  });
}

export async function createLeadEvent(payload: Record<string, unknown>): Promise<void> {
  await dx('/items/lead_events', { auth: true, method: 'POST', body: payload });
}

export interface Quote {
  id: string | number;
  created_at?: string;
  quote_no?: string;
  buyer_company?: string;
  buyer_inn?: string;
  contact_name?: string;
  email?: string;
  phone?: string;
  items?: { sku: string; name: string; qty: number; sum: number }[];
  total?: number;
}

/** Скачанные коммерческие предложения — источник фактической истории обращений. */
export async function getQuotes(limit = 500): Promise<Quote[]> {
  return dx<Quote[]>('/items/quotes', { auth: true, params: { limit, sort: '-created_at' } });
}

export async function createQuote(payload: Record<string, unknown>): Promise<void> {
  await dx('/items/quotes', { auth: true, method: 'POST', body: payload });
}

export async function patchProduct(id: string | number, payload: Record<string, unknown>): Promise<void> {
  await writeWithStamp((body) => dx(`/items/products/${id}`, { auth: true, method: 'PATCH', body }), payload);
}

/** Новая карточка — всегда содержательное событие: штамп ставится при создании. */
export async function createProduct(payload: Record<string, unknown>): Promise<{ id: string | number }> {
  return (await writeWithStamp(
    (body) => dx<{ id: string | number }>('/items/products', { auth: true, method: 'POST', body }),
    payload,
  )) as { id: string | number };
}

/**
 * Пакетная запись товаров.
 *
 * Раньше и импорт, и ежедневная переоценка писали по одному запросу на
 * позицию. Пока в каталоге была тысяча товаров, это укладывалось; с
 * позициями конфигуратора ManageEngine их около шести тысяч, и
 * последовательный цикл перестаёт помещаться в отведённое время.
 *
 * Directus принимает массив в теле: POST создаёт все объекты разом, PATCH
 * обновляет их по первичному ключу внутри каждого объекта. Одна сотня
 * позиций уходит одним запросом вместо ста.
 *
 * Размер пакета — компромисс: слишком крупный упирается в лимит тела
 * запроса и в таймаут самого Directus, слишком мелкий не даёт выигрыша.
 */
export const WRITE_BATCH = 100;

export function chunk<T>(items: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
}

export interface BatchResult { ok: number; failed: { key: string; error: string }[] }

/**
 * Создать товары пачками. При ошибке пачки повторяем её по одному, чтобы
 * из-за единственной плохой строки не потерять остальные девяносто девять.
 */
export async function createProductsBatch(
  payloads: Record<string, unknown>[],
  keyOf: (p: Record<string, unknown>) => string,
): Promise<BatchResult> {
  const result: BatchResult = { ok: 0, failed: [] };
  for (const part of chunk(payloads, WRITE_BATCH)) {
    try {
      await dx('/items/products', { auth: true, method: 'POST', body: part.map((p) => withContentStamp(p)) });
      result.ok += part.length;
    } catch (e) {
      for (const one of part) {
        try { await createProduct(one); result.ok += 1; }
        catch (inner) { result.failed.push({ key: keyOf(one), error: String(inner) }); }
      }
    }
  }
  return result;
}

/** Обновить товары пачками. Каждый объект обязан нести свой id. */
export async function patchProductsBatch(
  items: { id: string | number; payload: Record<string, unknown>; key: string }[],
): Promise<BatchResult> {
  const result: BatchResult = { ok: 0, failed: [] };
  for (const part of chunk(items, WRITE_BATCH)) {
    try {
      await dx('/items/products', {
        auth: true,
        method: 'PATCH',
        body: part.map((i) => ({ id: i.id, ...withContentStamp(i.payload) })),
      });
      result.ok += part.length;
    } catch (e) {
      for (const one of part) {
        try { await patchProduct(one.id, one.payload); result.ok += 1; }
        catch (inner) { result.failed.push({ key: one.key, error: String(inner) }); }
      }
    }
  }
  return result;
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

// ── app_kv: общее хранилище счётчиков и кэша ──
// Счётчик лимита, лежащий в памяти процесса, считает каждый инстанс свой:
// при двух контейнерах порог удваивается, при рестарте обнуляется. Общая
// таблица в той же базе, что и заявки, лишена обоих недостатков и не тянет
// в проект ещё одну зависимость (Redis) ради трёх ключей.

export interface KvRecord {
  key: string;
  value: unknown;
  /** ISO-время, после которого запись считается отсутствующей. */
  expires_at: string;
}

/**
 * Запись по ключу или null, если её нет. Просроченную не возвращаем.
 *
 * Выборка списком с фильтром, а не обращение к /items/app_kv/<key>: на
 * отсутствующую запись Directus отвечает тем же 403, что и на отсутствие
 * прав или коллекции, и «счёт нулевой» становится неотличимо от «считать
 * нечем». Для лимита это разные вещи: первое означает «пропускай», второе —
 * «защита не работает». Список отвечает пустым массивом на первое и ошибкой
 * на второе, поэтому ошибку отсюда мы пробрасываем, а не гасим.
 */
export async function kvGet(key: string): Promise<KvRecord | null> {
  const rows = await dx<KvRecord[]>('/items/app_kv', {
    auth: true,
    params: { 'filter[key][_eq]': key, limit: 1 },
  });
  const rec = rows?.[0];
  if (!rec) return null;
  if (rec.expires_at && Date.parse(rec.expires_at) <= Date.now()) return null;
  return rec;
}

/** Создать или перезаписать запись. Ключ — первичный, поэтому upsert по нему. */
export async function kvPut(rec: KvRecord): Promise<void> {
  try {
    await dx(`/items/app_kv/${encodeURIComponent(rec.key)}`, {
      auth: true, method: 'PATCH', body: { value: rec.value, expires_at: rec.expires_at },
    });
  } catch (e) {
    if (e instanceof DirectusError && (e.status === 403 || e.status === 404)) {
      await dx('/items/app_kv', { auth: true, method: 'POST', body: rec });
      return;
    }
    throw e;
  }
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
