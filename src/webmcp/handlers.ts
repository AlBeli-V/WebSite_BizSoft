/**
 * Серверные обработчики WebMCP-инструментов.
 *
 * Цепочка одна для любого вызова:
 *   вход → схема (validate.ts) → нормализация → бизнес-проверки →
 *   существующие функции каталога (lib/directus) → адаптер (adapters.ts).
 *
 * Обработчики НЕ читают Request и не пишут Response — это делает эндпоинт
 * /api/agent/[tool]. Так их можно вызывать из юнит-тестов без HTTP.
 * Все обработчики v1 — только чтение; записи (заявки, КП) сознательно
 * не открыты агентам, см. docs/webmcp/security.md.
 */
import { getCategories, getProducts, getProductBySlug, getVendors } from '../lib/directus';
import type { ProductFilter } from '../lib/directus';
import type { Product } from '../lib/types';
import { countByCategory } from '../lib/catalog';
import { effectivePrice } from '../lib/pricing';
import { searchProducts } from '../lib/product-search';
import { searchPolicies } from '../lib/policy-search';
import { ALL_POLICIES } from '../data/policies';
import { site } from '../config/site';
import {
  toAgentCategory,
  toAgentPolicy,
  toAgentProductBrief,
  toAgentProductFull,
  toAgentVendor,
  resolveVendorName,
  vendorUrl,
} from './adapters';
import { toolByName } from './definitions';
import { validateInput } from './validate';

export interface ToolResult {
  /** HTTP-статус для эндпоинта; 200 — успех. */
  status: number;
  /** Тело ответа: data при успехе, error с причиной при отказе. */
  body: { ok: true; data: unknown } | { ok: false; error: string };
}

const okResult = (data: unknown): ToolResult => ({ status: 200, body: { ok: true, data } });
const errResult = (status: number, error: string): ToolResult => ({ status, body: { ok: false, error } });

type Handler = (input: Record<string, string | number>) => Promise<ToolResult>;

/** Цена товара для фильтра и сортировки; 0 — «цена по запросу». */
const priceOf = (p: Product): number => {
  const v = effectivePrice(p).price;
  return v > 0 ? v : 0;
};

const handlers: Record<string, Handler> = {
  async search_products(input) {
    const query = input.query ? String(input.query) : '';
    const limit = Number(input.limit ?? 10);
    // Бизнес-проверка сверх схемы: пустой вызов вернул бы весь каталог.
    if (!query && !input.vendor && !input.category) {
      return errResult(400, 'укажите query, vendor или category — хотя бы одно');
    }
    const min = input.min_price != null ? Number(input.min_price) : null;
    const max = input.max_price != null ? Number(input.max_price) : null;
    if (min != null && max != null && min > max) {
      return errResult(400, `min_price (${min}) больше max_price (${max})`);
    }

    // Фильтры вендора и раздела — те же параметры каталога, что у страниц:
    // выборку делает Directus, а не перебор всего каталога в памяти.
    const filter: ProductFilter = {};
    if (input.vendor) {
      const match = resolveVendorName(String(input.vendor), await getVendors());
      if (!match) return errResult(404, `производитель «${input.vendor}» не найден в каталоге. Список — list_vendors.`);
      filter.vendor = match.vendor;
    }
    if (input.category) {
      const needle = String(input.category).toLowerCase();
      const cats = await getCategories();
      const cat = cats.find((c) => c.slug === needle) ?? cats.find((c) => c.name.toLowerCase() === needle);
      if (!cat) return errResult(404, `раздел «${input.category}» не найден. Список — list_categories.`);
      filter.categorySlug = cat.slug;
    }

    let products = await getProducts(filter);
    if (input.license) products = products.filter((p) => p.license_type === input.license);
    if (min != null || max != null) {
      // «Цена по запросу» из ценового диапазона уходит: сравнивать нечего,
      // а показать её внутри «до 50 000 ₽» — соврать о цене.
      products = products.filter((p) => {
        const price = priceOf(p);
        return price > 0 && (min == null || price >= min) && (max == null || price <= max);
      });
    }

    const found = query ? searchProducts(products, query) : products;
    const sort = input.sort ? String(input.sort) : 'relevance';
    // Порядок задаём копией: searchProducts уже вернул отсортированный
    // по релевантности массив, и его переворачивать на месте нельзя.
    const items = sort === 'relevance'
      ? found
      : [...found].sort((a, b) => {
        // «Цена по запросу» остаётся в конце при любой сортировке — как в каталоге.
        const pa = priceOf(a);
        const pb = priceOf(b);
        if (pa === 0 || pb === 0) return Number(pa === 0) - Number(pb === 0);
        return sort === 'price_asc' ? pa - pb : pb - pa;
      });
    return okResult({
      total: items.length,
      items: items.slice(0, limit).map(toAgentProductBrief),
    });
  },

  async list_categories() {
    const [categories, products] = await Promise.all([getCategories(), getProducts()]);
    const counts = countByCategory(products);
    // Пустые разделы не показываем: фильтр по ним вернул бы пусто, и агент
    // решил бы, что сломан каталог. Ровно так же поступает страница /catalog.
    const items = categories
      .filter((c) => (counts[c.slug] || 0) > 0)
      .map((c) => toAgentCategory(c, counts[c.slug]));
    return okResult({ total: items.length, items });
  },

  async search_policies(input) {
    const limit = Number(input.limit ?? 5);
    const found = searchPolicies(ALL_POLICIES, String(input.query));
    if (found.length === 0) {
      return errResult(404, `по этому вопросу условий в базе нет. Не додумывайте ответ: отправьте человека на ${site.url}/faq или к менеджеру через форму на сайте.`);
    }
    return okResult({
      total: found.length,
      items: found.slice(0, limit).map(toAgentPolicy),
    });
  },

  async get_product(input) {
    const slug = input.slug ? String(input.slug) : '';
    const sku = input.sku ? String(input.sku) : '';
    // Бизнес-проверка сверх схемы: нужен хотя бы один идентификатор.
    if (!slug && !sku) return errResult(400, 'укажите slug или sku товара');
    let product = null;
    if (slug) product = await getProductBySlug(slug.toLowerCase());
    if (!product && sku) {
      const all = await getProducts();
      const needle = sku.toUpperCase();
      product = all.find((p) => (p.sku || '').toUpperCase() === needle) ?? null;
    }
    if (!product) {
      return errResult(404, `товар не найден (${slug ? `slug «${slug}»` : `sku «${sku}»`}). Попробуйте search_products.`);
    }
    return okResult(toAgentProductFull(product));
  },

  async list_vendors() {
    const vendors = await getVendors();
    return okResult({
      total: vendors.length,
      items: vendors.map(toAgentVendor),
    });
  },

  async get_vendor(input) {
    const vendors = await getVendors();
    const match = resolveVendorName(String(input.vendor), vendors);
    if (!match) return errResult(404, `производитель «${input.vendor}» не найден. Список — list_vendors.`);
    return okResult(toAgentVendor(match));
  },

  async list_vendor_products(input) {
    const vendors = await getVendors();
    const match = resolveVendorName(String(input.vendor), vendors);
    if (!match) return errResult(404, `производитель «${input.vendor}» не найден. Список — list_vendors.`);
    const limit = Number(input.limit ?? 50);
    // Точное значение поля vendor — как на лендингах (никаких префиксов sku).
    const products = await getProducts({ vendor: match.vendor });
    return okResult({
      vendor: match.vendor,
      vendor_url: vendorUrl(match.vendor),
      total: products.length,
      items: products.slice(0, limit).map(toAgentProductBrief),
    });
  },
};

/** Выполнить инструмент по имени с недоверенным входом. */
export async function runTool(name: string, rawInput: unknown): Promise<ToolResult> {
  const def = toolByName(name);
  if (!def) return errResult(404, `инструмент «${String(name).slice(0, 64)}» не существует`);
  const v = validateInput(def.inputSchema, rawInput);
  if (!v.ok) return errResult(400, `неверный вход: ${v.errors.join('; ')}`);
  return handlers[name](v.value);
}
