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
import { getProducts, getProductBySlug, getVendors } from '../lib/directus';
import { searchProducts } from '../lib/product-search';
import {
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

const handlers: Record<string, Handler> = {
  async search_products(input) {
    const query = String(input.query);
    const limit = Number(input.limit ?? 10);
    let products = await getProducts();
    if (input.vendor) {
      const match = resolveVendorName(String(input.vendor), await getVendors());
      if (!match) return errResult(404, `производитель «${input.vendor}» не найден в каталоге`);
      products = products.filter((p) => p.vendor === match.vendor);
    }
    const found = searchProducts(products, query);
    return okResult({
      total: found.length,
      items: found.slice(0, limit).map(toAgentProductBrief),
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
