export const prerender = false;

import type { APIRoute } from 'astro';
import { getCurrencyRate, upsertCurrencyRate, getProductsForReprice, patchProductsBatch } from '../../../lib/directus';
import { fetchCbrRates } from '../../../lib/currency';
import { computePegRub, type RoundingRule, type Rates } from '../../../lib/pricing';
import { checkAdmin, unauthorized } from '../../../lib/admin-auth';
import { DEFAULT_MARKUP_COEFF, type Product } from '../../../lib/types';

const ROUNDING: RoundingRule = 'to1';

interface Scope { type: 'all' | 'imported' | 'origin' | 'category' | 'vendor'; value?: string }
interface RepricePreview { sku: string; name: string; before: number; after: number; coeff: number; locked: boolean }

function inScope(p: Product, scope: Scope): boolean {
  switch (scope.type) {
    case 'all': return true;
    case 'imported': return p.origin === 'foreign';
    case 'origin': return p.origin === scope.value;
    case 'category': return typeof p.category === 'object' && p.category ? p.category.slug === scope.value : false;
    case 'vendor': return p.vendor === scope.value;
    default: return false;
  }
}

/** Построить предпросмотр переоценки привязанных к валюте товаров. */
function buildReprice(products: Product[], rates: Rates, scope: Scope, coeff: number | null, includeLocked: boolean): RepricePreview[] {
  const out: RepricePreview[] = [];
  for (const p of products) {
    if (!p.peg_to_usd) continue;
    if (!inScope(p, scope)) continue;
    if (p.price_locked && !includeLocked) continue;
    const effCoeff = coeff != null && coeff > 0 ? coeff : (p.markup_coeff ?? DEFAULT_MARKUP_COEFF);
    const after = computePegRub({ ...p, markup_coeff: effCoeff }, rates, DEFAULT_MARKUP_COEFF, ROUNDING);
    if (after == null) continue;
    if (after !== p.price || (coeff != null && coeff !== p.markup_coeff)) {
      out.push({ sku: p.sku, name: p.name, before: p.price, after, coeff: effCoeff, locked: !!p.price_locked });
    }
  }
  return out;
}

/**
 * Записать пересчитанные цены.
 *
 * Наценка считается как и прежде: себестоимость в валюте × курс ЦБ ×
 * коэффициент, округление по правилу витрины. Меняется только способ
 * записи — пачками вместо запроса на каждую позицию: с позициями
 * конфигуратора ManageEngine в каталоге около шести тысяч товаров, и
 * последовательный цикл в ночное окно уже не помещается.
 */
async function applyReprice(products: Product[], preview: RepricePreview[], setCoeff: boolean): Promise<{ applied: number; failed: string[] }> {
  const idBySku = new Map(products.map((p) => [p.sku, p.id]));
  const failed: string[] = [];
  const items: { id: string | number; payload: Record<string, unknown>; key: string }[] = [];
  for (const ch of preview) {
    const id = idBySku.get(ch.sku);
    if (id == null) { failed.push(ch.sku); continue; }
    items.push({
      id,
      key: ch.sku,
      payload: setCoeff ? { price: ch.after, markup_coeff: ch.coeff } : { price: ch.after },
    });
  }
  const res = await patchProductsBatch(items);
  for (const f of res.failed) { console.error('reprice patch', f.key, f.error); failed.push(f.key); }
  return { applied: res.ok, failed };
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
  let body: {
    action?: string; usd_rate?: number; eur_rate?: number; auto_recalc?: boolean; mode?: 'manual' | 'auto';
    scope?: Scope; coeff?: number | null; includeLocked?: boolean;
  };
  try { body = await request.json(); } catch { return new Response('{"error":"bad json"}', { status: 400 }); }
  const action = body.action;

  try {
    if (action === 'refresh') {
      let cbr;
      try { cbr = await fetchCbrRates(); }
      catch (e) {
        console.error('CBR fetch failed', e);
        const current = await getCurrencyRate();
        return new Response(JSON.stringify({ ok: false, error: 'Не удалось получить курс ЦБ. Сохранён прежний.', rate: current }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      const prev = await getCurrencyRate();
      const rate = await upsertCurrencyRate({
        usd_rate: cbr.usd ?? prev?.usd_rate,
        eur_rate: cbr.eur ?? prev?.eur_rate,
        rate_date: cbr.date ? cbr.date.split('.').reverse().join('-') : undefined,
        source: 'cbr.ru',
        updated_at: new Date().toISOString(),
      });
      let recalc = null;
      if (prev?.auto_recalc) {
        const products = await getProductsForReprice();
        const rates: Rates = { usd: rate.usd_rate ?? null, eur: rate.eur_rate ?? null };
        const preview = buildReprice(products, rates, { type: 'all' }, null, false); // не трогаем зафиксированные
        const res = await applyReprice(products, preview, false);
        recalc = { applied: res.applied, changes: preview.length };
        console.log(`[ADMIN][currency] auto-recalc applied=${res.applied}`);
      }
      console.log(`[ADMIN][currency] refresh usd=${cbr.usd} eur=${cbr.eur} date=${cbr.date}`);
      return new Response(JSON.stringify({ ok: true, rate, recalc }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    if (action === 'set-manual') {
      const patch: Record<string, unknown> = { mode: 'manual', source: 'manual', rate_date: new Date().toISOString().slice(0, 10), updated_at: new Date().toISOString() };
      if (typeof body.usd_rate === 'number' && body.usd_rate > 0) patch.usd_rate = body.usd_rate;
      if (typeof body.eur_rate === 'number' && body.eur_rate > 0) patch.eur_rate = body.eur_rate;
      if (body.auto_recalc != null) patch.auto_recalc = body.auto_recalc;
      const rate = await upsertCurrencyRate(patch);
      return new Response(JSON.stringify({ ok: true, rate }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    if (action === 'set-mode') {
      const rate = await upsertCurrencyRate({ mode: body.mode || 'manual', auto_recalc: body.auto_recalc ?? false, updated_at: new Date().toISOString() });
      return new Response(JSON.stringify({ ok: true, rate }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    if (action === 'reprice-preview' || action === 'reprice-apply') {
      const cur = await getCurrencyRate();
      const rates: Rates = { usd: cur?.usd_rate ?? null, eur: cur?.eur_rate ?? null };
      if (!rates.usd && !rates.eur) return new Response(JSON.stringify({ error: 'курс не задан — сначала обновите курс ЦБ' }), { status: 422 });
      const scope: Scope = body.scope || { type: 'all' };
      const coeff = body.coeff != null && body.coeff > 0 ? body.coeff : null;
      const includeLocked = !!body.includeLocked;
      const products = await getProductsForReprice();
      const preview = buildReprice(products, rates, scope, coeff, includeLocked);
      if (action === 'reprice-preview') {
        return new Response(JSON.stringify({ preview, count: preview.length, rates, skippedLocked: products.filter((p) => p.peg_to_usd && inScope(p, scope) && p.price_locked && !includeLocked).length }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      const res = await applyReprice(products, preview, coeff != null);
      console.log(`[ADMIN][currency] reprice scope=${scope.type}:${scope.value || ''} coeff=${coeff} locked=${includeLocked} applied=${res.applied}`);
      return new Response(JSON.stringify({ ok: true, applied: res.applied, changes: preview.length, failed: res.failed }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    return new Response(JSON.stringify({ error: 'неизвестное действие' }), { status: 422 });
  } catch (e) {
    console.error('currency action', e);
    return new Response(JSON.stringify({ error: 'ошибка обработки' }), { status: 500 });
  }
};
