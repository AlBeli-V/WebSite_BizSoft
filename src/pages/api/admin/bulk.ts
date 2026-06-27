export const prerender = false;

import type { APIRoute } from 'astro';
import { getAllProductsAdmin, patchProduct } from '../../../lib/directus';
import { previewBulkChange, type BulkChangeOptions } from '../../../lib/pricing';
import { checkAdmin, unauthorized } from '../../../lib/admin-auth';

/**
 * Массовое изменение цен.
 * body: { mode:'preview'|'apply', opts: BulkChangeOptions, skus?: string[] }
 * skus отсутствует/пуст → применяется ко всем товарам.
 */
export const POST: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();

  let body: { mode?: string; opts?: BulkChangeOptions; skus?: string[] };
  try { body = await request.json(); } catch { return new Response('{"error":"bad json"}', { status: 400 }); }

  const opts = body.opts;
  if (!opts || !opts.operation || !opts.mode || typeof opts.amount !== 'number') {
    return new Response(JSON.stringify({ error: 'некорректные параметры' }), { status: 422 });
  }

  let products;
  try { products = await getAllProductsAdmin(); } catch (e) {
    console.error('bulk: load', e);
    return new Response(JSON.stringify({ error: 'не удалось получить товары' }), { status: 502 });
  }

  const skuSet = body.skus && body.skus.length ? new Set(body.skus) : null;
  const scoped = skuSet ? products.filter((p) => skuSet.has(p.sku)) : products;
  const preview = previewBulkChange(scoped, opts);

  if (body.mode === 'preview') {
    return new Response(JSON.stringify({ preview, count: preview.length }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  }

  if (body.mode === 'apply') {
    // группируем изменения по товару
    const byId = new Map<string | number, Record<string, unknown>>();
    const idBySku = new Map(scoped.map((p) => [p.sku, p.id]));
    for (const ch of preview) {
      const id = idBySku.get(ch.sku);
      if (id == null) continue;
      const upd = byId.get(id) || {};
      upd[ch.field] = ch.after;
      byId.set(id, upd);
    }
    let applied = 0;
    const failed: string[] = [];
    for (const [id, upd] of byId) {
      try { await patchProduct(id, upd); applied++; }
      catch (e) { console.error('bulk patch', id, e); failed.push(String(id)); }
    }
    console.log(`[ADMIN][bulk] applied=${applied} changes=${preview.length} failed=${failed.length} opts=${JSON.stringify(opts)}`);
    return new Response(JSON.stringify({ applied, changes: preview.length, failed }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  }

  return new Response(JSON.stringify({ error: 'неизвестный режим' }), { status: 422 });
};
