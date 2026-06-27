export const prerender = false;

import type { APIRoute } from 'astro';
import { getAllProductsAdmin, patchProduct } from '../../../lib/directus';
import { productsToCsv, parseCsv, diffCsvImport } from '../../../lib/csv';
import { checkAdmin, unauthorized } from '../../../lib/admin-auth';

/** GET — экспорт CSV (опц. ?skus=a,b). */
export const GET: APIRoute = async ({ request, url }) => {
  if (!checkAdmin(request)) return unauthorized();
  let products;
  try { products = await getAllProductsAdmin(); } catch (e) {
    console.error('csv export load', e);
    return new Response(JSON.stringify({ error: 'не удалось получить товары' }), { status: 502 });
  }
  const skusParam = url.searchParams.get('skus');
  if (skusParam) {
    const set = new Set(skusParam.split(',').map((s) => s.trim()).filter(Boolean));
    products = products.filter((p) => set.has(p.sku));
  }
  const csv = productsToCsv(products);
  return new Response(csv, {
    status: 200,
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': `attachment; filename="bizsoft-prices-${new Date().toISOString().slice(0, 10)}.csv"`,
    },
  });
};

/** POST — импорт: { csv:string, apply?:boolean }. dry-run по умолчанию. */
export const POST: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();
  let body: { csv?: string; apply?: boolean };
  try { body = await request.json(); } catch { return new Response('{"error":"bad json"}', { status: 400 }); }
  if (!body.csv || typeof body.csv !== 'string') return new Response(JSON.stringify({ error: 'нет данных CSV' }), { status: 422 });

  let products;
  try { products = await getAllProductsAdmin(); } catch (e) {
    console.error('csv import load', e);
    return new Response(JSON.stringify({ error: 'не удалось получить товары' }), { status: 502 });
  }

  const rows = parseCsv(body.csv);
  const result = diffCsvImport(rows, products);

  if (!body.apply) {
    return new Response(JSON.stringify({ dryRun: true, ...result }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  }

  // применение
  const idBySku = new Map(products.map((p) => [p.sku, p.id]));
  let applied = 0;
  const failed: string[] = [];
  for (const [sku, upd] of Object.entries(result.updates)) {
    const id = idBySku.get(sku);
    if (id == null) { failed.push(sku); continue; }
    try { await patchProduct(id, upd); applied++; }
    catch (e) { console.error('csv patch', sku, e); failed.push(sku); }
  }
  console.log(`[ADMIN][csv-import] applied=${applied} changes=${result.changes.length} errors=${result.errors.length} failed=${failed.length}`);
  return new Response(JSON.stringify({ applied, changes: result.changes.length, errors: result.errors, failed }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
};
