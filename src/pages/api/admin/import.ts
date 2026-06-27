export const prerender = false;

import type { APIRoute } from 'astro';
import * as XLSX from 'xlsx';
import { getAllProductsAdmin, getCategories, createProduct, patchProduct } from '../../../lib/directus';
import { checkAdmin, unauthorized } from '../../../lib/admin-auth';
import { buildPlan, canonRow, type RawRow } from '../../../lib/bulk-import';
import { parseCsv } from '../../../lib/csv';

/**
 * Пакетное добавление/обновление товаров из Excel/CSV (upsert по sku).
 * body: { format:'csv'|'xlsx', csv?:string, xlsxBase64?:string, apply?:boolean }
 */
export const POST: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();

  let body: { format?: string; csv?: string; xlsxBase64?: string; apply?: boolean };
  try { body = await request.json(); } catch { return new Response('{"error":"bad json"}', { status: 400 }); }

  // 1) получить строки
  let rows: Record<string, string>[] = [];
  try {
    if (body.format === 'xlsx' && body.xlsxBase64) {
      const wb = XLSX.read(body.xlsxBase64, { type: 'base64' });
      // лист «Товары» если есть, иначе первый
      const sheetName = wb.SheetNames.find((n) => /товар|product/i.test(n)) || wb.SheetNames[0];
      const json = XLSX.utils.sheet_to_json<RawRow>(wb.Sheets[sheetName], { defval: '', raw: false });
      rows = json.map(canonRow).filter((r) => r.sku);
    } else if (body.csv) {
      rows = parseCsv(body.csv).map((r) => canonRow(r as RawRow)).filter((r) => r.sku);
    } else {
      return new Response(JSON.stringify({ error: 'нет данных (csv или xlsxBase64)' }), { status: 422 });
    }
  } catch (e) {
    console.error('import parse', e);
    return new Response(JSON.stringify({ error: 'не удалось разобрать файл' }), { status: 422 });
  }
  if (rows.length === 0) return new Response(JSON.stringify({ error: 'нет строк с заполненным sku' }), { status: 422 });

  // 2) контекст: категории и существующие товары
  let categories, products;
  try {
    categories = await getCategories();
    products = await getAllProductsAdmin();
  } catch (e) {
    console.error('import context', e);
    return new Response(JSON.stringify({ error: 'не удалось получить данные каталога' }), { status: 502 });
  }
  const catById = new Map<string, string | number>();
  for (const c of categories) {
    catById.set(c.slug.toLowerCase(), c.id);
    catById.set(c.name.toLowerCase(), c.id);
  }
  const resolver = (key: string) => catById.get(String(key).trim().toLowerCase()) ?? null;

  // 3) план
  const plan = buildPlan(rows, products, resolver);

  if (!body.apply) {
    return new Response(JSON.stringify({ dryRun: true, ...plan }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  }

  // 4) применение
  const idBySku = new Map(products.map((p) => [p.sku, p.id]));
  let created = 0, updated = 0;
  const failed: { sku: string; error: string }[] = [];
  for (const item of plan.items) {
    try {
      if (item.mode === 'create') { await createProduct(item.payload); created++; }
      else if (item.mode === 'update') {
        const id = idBySku.get(item.sku);
        if (id == null) { failed.push({ sku: item.sku, error: 'не найден id' }); continue; }
        await patchProduct(id, item.payload); updated++;
      }
    } catch (e) {
      failed.push({ sku: item.sku, error: (e as Error).message.slice(0, 160) });
    }
  }
  console.log(`[ADMIN][import] created=${created} updated=${updated} failed=${failed.length} skipped=${plan.items.filter(i=>i.mode==='skip'&&!i.errors.length).length}`);
  return new Response(JSON.stringify({ applied: true, created, updated, failed, summary: plan.summary }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
};
