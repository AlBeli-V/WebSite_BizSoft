export const prerender = false;

import type { APIRoute } from 'astro';
import { getCurrencyRate, upsertCurrencyRate, getAllProductsAdmin, patchProduct } from '../../../lib/directus';
import { fetchCbrUsd } from '../../../lib/currency';
import { pegPrice, type RoundingRule } from '../../../lib/pricing';
import { checkAdmin, unauthorized } from '../../../lib/admin-auth';

const ROUNDING: RoundingRule = 'to1';

interface PegPreview { sku: string; name: string; before: number; after: number }

async function recalcPreview(usdRate: number): Promise<PegPreview[]> {
  const products = await getAllProductsAdmin();
  const out: PegPreview[] = [];
  for (const p of products) {
    if (!p.peg_to_usd || !p.base_price_usd) continue;
    const after = pegPrice(p.base_price_usd, usdRate, p.markup_percent || 0, ROUNDING);
    if (after !== p.price) out.push({ sku: p.sku, name: p.name, before: p.price, after });
  }
  return out;
}

export const GET: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();
  try {
    const rate = await getCurrencyRate();
    return new Response(JSON.stringify({ rate }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  } catch (e) {
    console.error('currency get', e);
    return new Response(JSON.stringify({ error: 'не удалось получить курс' }), { status: 502 });
  }
};

export const POST: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();
  let body: { action?: string; usd_rate?: number; auto_recalc?: boolean };
  try { body = await request.json(); } catch { return new Response('{"error":"bad json"}', { status: 400 }); }

  const action = body.action;

  try {
    if (action === 'refresh') {
      // Тянем курс ЦБ. При сбое — НЕ перезатираем последний удачный курс.
      let cbr;
      try { cbr = await fetchCbrUsd(); }
      catch (e) {
        console.error('CBR fetch failed', e);
        const current = await getCurrencyRate();
        return new Response(JSON.stringify({ ok: false, error: 'Не удалось получить курс ЦБ. Сохранён прежний курс.', rate: current }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      const prev = await getCurrencyRate();
      const rate = await upsertCurrencyRate({
        usd_rate: cbr.rate,
        rate_date: cbr.date ? cbr.date.split('.').reverse().join('-') : undefined,
        source: 'cbr.ru',
        updated_at: new Date().toISOString(),
      });
      let recalc = null;
      if (prev?.auto_recalc) {
        const preview = await recalcPreview(cbr.rate);
        const idBySku = new Map((await getAllProductsAdmin()).map((p) => [p.sku, p.id]));
        let applied = 0;
        for (const ch of preview) { const id = idBySku.get(ch.sku); if (id != null) { await patchProduct(id, { price: ch.after }); applied++; } }
        recalc = { applied, changes: preview.length };
        console.log(`[ADMIN][currency] auto-recalc applied=${applied}`);
      }
      console.log(`[ADMIN][currency] refresh rate=${cbr.rate} date=${cbr.date}`);
      return new Response(JSON.stringify({ ok: true, rate, recalc }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    if (action === 'set-manual') {
      if (typeof body.usd_rate !== 'number' || body.usd_rate <= 0) return new Response(JSON.stringify({ error: 'некорректный курс' }), { status: 422 });
      const rate = await upsertCurrencyRate({ mode: 'manual', usd_rate: body.usd_rate, source: 'manual', rate_date: new Date().toISOString().slice(0, 10), auto_recalc: body.auto_recalc ?? false, updated_at: new Date().toISOString() });
      return new Response(JSON.stringify({ ok: true, rate }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    if (action === 'set-mode') {
      const rate = await upsertCurrencyRate({ mode: (body as { mode?: 'manual' | 'auto' }).mode || 'manual', auto_recalc: body.auto_recalc ?? false, updated_at: new Date().toISOString() });
      return new Response(JSON.stringify({ ok: true, rate }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    if (action === 'recalc-preview' || action === 'recalc-apply') {
      const current = await getCurrencyRate();
      const usd = current?.usd_rate;
      if (!usd) return new Response(JSON.stringify({ error: 'курс не задан' }), { status: 422 });
      const preview = await recalcPreview(usd);
      if (action === 'recalc-preview') return new Response(JSON.stringify({ preview, count: preview.length, usd }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      const idBySku = new Map((await getAllProductsAdmin()).map((p) => [p.sku, p.id]));
      let applied = 0;
      for (const ch of preview) { const id = idBySku.get(ch.sku); if (id != null) { await patchProduct(id, { price: ch.after }); applied++; } }
      console.log(`[ADMIN][currency] manual recalc applied=${applied}`);
      return new Response(JSON.stringify({ ok: true, applied, changes: preview.length }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    return new Response(JSON.stringify({ error: 'неизвестное действие' }), { status: 422 });
  } catch (e) {
    console.error('currency action', e);
    return new Response(JSON.stringify({ error: 'ошибка обработки' }), { status: 500 });
  }
};
