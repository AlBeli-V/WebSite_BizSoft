/**
 * Интеграция WebMCP: инструмент → обработчик → адаптер → каталог (мок
 * Directus) → нормализованный ответ. Плюс поведение HTTP-эндпоинта,
 * включая рубильник PUBLIC_WEBMCP=0.
 */
import { describe, expect, it, vi, afterEach } from 'vitest';
import type { Product } from '../src/lib/types';

const P = (over: Partial<Product>): Product => ({
  id: over.sku || 'id',
  name: 'X',
  sku: 'X-1',
  vendor: 'Zoom',
  category: null,
  slug: 'x',
  price: 1000,
  currency: 'RUB',
  status: 'published',
  ...over,
});

const CATALOG: Product[] = [
  P({ name: 'Zoom Workplace Pro', sku: 'ZOOM-PRO', slug: 'zoom-workplace-pro', vendor: 'Zoom', price: 25_000, keywords: 'видеосвязь конференции' }),
  P({ name: 'Zoom Workplace Business', sku: 'ZOOM-BIZ', slug: 'zoom-workplace-business', vendor: 'Zoom', price: 31_000 }),
  P({ name: 'Claude Team', sku: 'INT-AI-CLAUDE-TEAM', slug: 'claude-team', vendor: 'Anthropic', price: 42_000, keywords: 'AI ассистент команда' }),
  P({ name: 'Claude Enterprise', sku: 'INT-AI-CLAUDE-ENT', slug: 'claude-enterprise', vendor: 'Anthropic', price: 0 }),
];

vi.mock('../src/lib/directus', () => ({
  getProducts: vi.fn(async (opts?: { vendor?: string }) =>
    opts?.vendor ? CATALOG.filter((p) => p.vendor === opts.vendor) : CATALOG),
  getProductBySlug: vi.fn(async (slug: string) => CATALOG.find((p) => p.slug === slug) ?? null),
  getVendors: vi.fn(async () => [
    { vendor: 'Anthropic', count: 2 },
    { vendor: 'Zoom', count: 2 },
  ]),
  DirectusError: class extends Error { status = 0 },
}));

const { runTool } = await import('../src/webmcp/handlers');
const { GET } = await import('../src/pages/api/agent/[tool]');

type Ok = { ok: true; data: Record<string, never> & Record<string, unknown> };

afterEach(() => {
  delete process.env.PUBLIC_WEBMCP;
});

describe('runTool: search_products', () => {
  it('находит по словам в любом порядке («Claude для команды» → Claude Team)', async () => {
    const r = await runTool('search_products', { query: 'Claude команда' });
    expect(r.status).toBe(200);
    const data = (r.body as Ok).data as { items: { sku: string }[] };
    expect(data.items[0].sku).toBe('INT-AI-CLAUDE-TEAM');
  });

  it('«цена по запросу» — в конце выдачи', async () => {
    const r = await runTool('search_products', { query: 'Claude' });
    const data = (r.body as Ok).data as { items: { sku: string; price: number | null }[] };
    expect(data.items.at(-1)?.price).toBeNull();
  });

  it('фильтр по вендору сужает выдачу, неизвестный вендор — 404', async () => {
    const ok = await runTool('search_products', { query: 'Workplace', vendor: 'Zoom' });
    expect(((ok.body as Ok).data as { total: number }).total).toBe(2);
    const bad = await runTool('search_products', { query: 'x1', vendor: 'Никто' });
    expect(bad.status).toBe(404);
  });

  it('limit ограничивает выдачу, total сообщает полное число', async () => {
    const r = await runTool('search_products', { query: 'Zoom Workplace', limit: 1 });
    const data = (r.body as Ok).data as { total: number; items: unknown[] };
    expect(data.total).toBe(2);
    expect(data.items).toHaveLength(1);
  });

  it('мусорный вход отклоняется схемой: лишнее поле, кривой limit', async () => {
    expect((await runTool('search_products', { query: 'x1', hack: '1' })).status).toBe(400);
    expect((await runTool('search_products', { query: 'x1', limit: -5 })).status).toBe(400);
    expect((await runTool('search_products', {})).status).toBe(400);
  });
});

describe('runTool: get_product', () => {
  it('по slug и по sku (регистр sku не важен)', async () => {
    const bySlug = await runTool('get_product', { slug: 'claude-team' });
    expect(((bySlug.body as Ok).data as { sku: string }).sku).toBe('INT-AI-CLAUDE-TEAM');
    const bySku = await runTool('get_product', { sku: 'zoom-pro' });
    expect(((bySku.body as Ok).data as { name: string }).name).toBe('Zoom Workplace Pro');
  });

  it('без идентификаторов — 400, неизвестный slug/sku — 404 с подсказкой', async () => {
    expect((await runTool('get_product', {})).status).toBe(400);
    const r = await runTool('get_product', { slug: 'no-such' });
    expect(r.status).toBe(404);
    expect((r.body as { ok: false; error: string }).error).toContain('search_products');
  });
});

describe('runTool: вендоры', () => {
  it('list_vendors отдаёт всех с ссылками', async () => {
    const r = await runTool('list_vendors', {});
    const data = (r.body as Ok).data as { total: number; items: { url: string }[] };
    expect(data.total).toBe(2);
    expect(data.items[0].url).toMatch(/^https:\/\/biz-soft\.pro\/vendors\//);
  });

  it('get_vendor по имени и слагу; list_vendor_products по точному полю vendor', async () => {
    const v = await runTool('get_vendor', { vendor: 'anthropic' });
    expect(((v.body as Ok).data as { vendor: string }).vendor).toBe('Anthropic');
    const lp = await runTool('list_vendor_products', { vendor: 'Anthropic' });
    const data = (lp.body as Ok).data as { total: number; items: { vendor: string }[] };
    expect(data.total).toBe(2);
    expect(data.items.every((i) => i.vendor === 'Anthropic')).toBe(true);
  });

  it('неизвестный вендор — 404 с подсказкой про list_vendors', async () => {
    const r = await runTool('get_vendor', { vendor: 'Роскосмос' });
    expect(r.status).toBe(404);
    expect((r.body as { ok: false; error: string }).error).toContain('list_vendors');
  });
});

describe('runTool: реестр', () => {
  it('несуществующий инструмент — 404 (в т.ч. product-specific имена)', async () => {
    expect((await runTool('get_chatgpt', {})).status).toBe(404);
  });
});

const call = (tool: string, qs = '') =>
  (GET as (ctx: { params: { tool: string }; url: URL }) => Promise<Response>)({
    params: { tool },
    url: new URL(`https://biz-soft.pro/api/agent/${tool}${qs}`),
  });

describe('GET /api/agent/[tool]', () => {
  it('успех: JSON с данными, noindex и короткий кэш', async () => {
    const res = await call('get_product', '?slug=claude-team');
    expect(res.status).toBe(200);
    expect(res.headers.get('X-Robots-Tag')).toContain('noindex');
    expect(res.headers.get('Cache-Control')).toContain('max-age=60');
    const body = await res.json();
    expect(body.ok).toBe(true);
    expect(body.data.url).toBe('https://biz-soft.pro/product/claude-team');
  });

  it('ошибки валидации и незнакомые инструменты не кэшируются', async () => {
    const res = await call('search_products', '?query=x&limit=999');
    expect(res.status).toBe(400);
    expect(res.headers.get('Cache-Control')).toBe('no-store');
    expect((await call('unknown_tool')).status).toBe(404);
  });

  it('рубильник PUBLIC_WEBMCP=0 гасит API: 404 + X-Agent-Api: disabled', async () => {
    process.env.PUBLIC_WEBMCP = '0';
    const res = await call('list_vendors');
    expect(res.status).toBe(404);
    expect(res.headers.get('X-Agent-Api')).toBe('disabled');
  });
});
