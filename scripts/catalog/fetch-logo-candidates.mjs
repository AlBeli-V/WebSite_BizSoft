/**
 * Кандидаты знаков продуктов — сбор на раннере (в сессии внешней сети нет).
 * Вход: data/catalog/logo-requests.json (scripts/catalog/logo-requests.ts).
 * Выход: assets/incoming/logos/<id>/cand-N.<ext> + candidates.json и
 * contact.png — лист превью с номерами, по которому в сессии выбирают знак.
 *
 * Источники по порядку (правило docs/rules/product-logos.md):
 *   1. JetBrains Marketplace API — иконка плагина от издателя;
 *   2. официальные адреса из заявки (official);
 *   3. Google Custom Search (картинки) — при наличии GOOGLE_CSE_KEY и
 *      GOOGLE_CSE_CX; без ключа этот шаг пропускается, и заявка помечается
 *      needs_key.
 *
 * Google-квота (100 запросов в сутки бесплатно) расходуется только на
 * заявки без официального источника; LIMIT ограничивает число запросов
 * за прогон, чтобы не упереться в квоту молча.
 */
import { mkdirSync, writeFileSync, readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import sharp from 'sharp';

const REQUESTS = process.env.REQUESTS_FILE || 'data/catalog/logo-requests.json';
const OUT = process.env.OUT_DIR || 'assets/incoming/logos';
const LIMIT = Number(process.env.GOOGLE_LIMIT || 90);
const ONLY = (process.env.ONLY || '').split(',').map((s) => s.trim()).filter(Boolean);
const KEY = process.env.GOOGLE_CSE_KEY;
const CX = process.env.GOOGLE_CSE_CX;
const MAX_BYTES = 3 * 1024 * 1024;
const UA = 'Mozilla/5.0 (compatible; bizsoft-logo-fetch/1.0; +https://biz-soft.pro)';

async function download(url) {
  const res = await fetch(url, { headers: { 'User-Agent': UA, Accept: 'image/*,*/*;q=0.8' }, redirect: 'follow', signal: AbortSignal.timeout(20000) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const type = (res.headers.get('content-type') || '').toLowerCase();
  const buf = Buffer.from(await res.arrayBuffer());
  if (buf.length > MAX_BYTES) throw new Error('слишком большой файл');
  const ext = type.includes('svg') || buf.subarray(0, 300).toString().includes('<svg') ? 'svg'
    : type.includes('png') ? 'png' : type.includes('jpeg') || type.includes('jpg') ? 'jpg'
    : type.includes('webp') ? 'webp' : type.includes('gif') ? 'gif' : type.includes('x-icon') || type.includes('vnd.microsoft.icon') ? 'ico' : null;
  if (!ext) throw new Error(`не картинка: ${type || 'без типа'}`);
  return { buf, ext, type };
}

async function marketplace(term) {
  const url = `https://plugins.jetbrains.com/api/searchPlugins?search=${encodeURIComponent(term)}&max=4`;
  const res = await fetch(url, { headers: { 'User-Agent': UA }, signal: AbortSignal.timeout(20000) });
  if (!res.ok) throw new Error(`Marketplace HTTP ${res.status}`);
  const data = await res.json();
  return (data.plugins || []).filter((p) => p.icon).map((p) => ({
    url: `https://plugins.jetbrains.com${p.icon}`, kind: 'jetbrains-marketplace',
    note: `${p.name} — ${p.vendor?.name || ''} (id ${p.id})`,
  }));
}

async function google(query) {
  const u = new URL('https://www.googleapis.com/customsearch/v1');
  u.search = new URLSearchParams({ key: KEY, cx: CX, q: query, searchType: 'image', num: '8', safe: 'active', imgSize: 'medium' }).toString();
  const res = await fetch(u, { signal: AbortSignal.timeout(20000) });
  if (!res.ok) throw new Error(`Google CSE HTTP ${res.status}: ${(await res.text()).slice(0, 200)}`);
  const data = await res.json();
  return (data.items || []).map((it) => ({ url: it.link, kind: 'google-cse', note: `${it.displayLink} — ${it.title}` }));
}

/** Лист превью: до 8 кандидатов по 160px с номером — один взгляд на заявку. */
async function contactSheet(dir, items) {
  const cell = 176; const cols = Math.min(4, items.length || 1); const rows = Math.ceil(items.length / cols) || 1;
  const composites = [];
  for (let i = 0; i < items.length; i++) {
    const it = items[i];
    try {
      const src = it.ext === 'ico' ? null : join(dir, it.file);
      if (!src) continue;
      const thumb = await sharp(src, { density: 300 }).resize(144, 144, { fit: 'contain', background: { r: 255, g: 255, b: 255, alpha: 0 } }).png().toBuffer();
      const x = (i % cols) * cell + 16; const y = Math.floor(i / cols) * cell + 16;
      composites.push({ input: thumb, left: x, top: y });
      const label = Buffer.from(`<svg width="40" height="22"><rect width="40" height="22" rx="4" fill="#1d1d1f"/><text x="20" y="16" font-family="sans-serif" font-size="14" font-weight="700" fill="#fff" text-anchor="middle">${i + 1}</text></svg>`);
      composites.push({ input: label, left: x, top: y });
      it.thumb = true;
    } catch (e) { it.thumb = false; it.error = `превью: ${e.message}`; }
  }
  const sheet = sharp({ create: { width: cols * cell + 16, height: rows * cell + 16, channels: 4, background: '#f4f4f5' } });
  await sheet.composite(composites).png().toFile(join(dir, 'contact.png'));
}

const requests = JSON.parse(readFileSync(REQUESTS, 'utf8')).filter((r) => !ONLY.length || ONLY.includes(r.id));
let googleUsed = 0; const summary = { done: 0, needs_key: 0, empty: 0, google_calls: 0 };
for (const req of requests) {
  const dir = join(OUT, req.id);
  if (existsSync(join(dir, 'candidates.json')) && !process.env.REFRESH) { continue; }
  mkdirSync(dir, { recursive: true });
  const sources = [];
  const log = [];
  if (req.marketplace) {
    try { sources.push(...await marketplace(req.marketplace)); } catch (e) { log.push(`marketplace: ${e.message}`); }
  }
  for (const url of req.official || []) sources.push({ url, kind: 'official', note: new URL(url).hostname });
  let needsKey = false;
  if (!sources.length) {
    if (KEY && CX && googleUsed < LIMIT) {
      try { sources.push(...await google(req.query)); googleUsed++; summary.google_calls++; } catch (e) { log.push(`google: ${e.message}`); }
    } else needsKey = true;
  }
  const items = [];
  for (const s of sources.slice(0, 8)) {
    try {
      const { buf, ext, type } = await download(s.url);
      const file = `cand-${items.length + 1}.${ext}`;
      writeFileSync(join(dir, file), buf);
      let width = null, height = null;
      try { const m = await sharp(buf).metadata(); width = m.width ?? null; height = m.height ?? null; } catch { /* svg без размера */ }
      items.push({ file, ext, type, width, height, source: s.url, kind: s.kind, note: s.note });
    } catch (e) { log.push(`${s.url}: ${e.message}`); }
  }
  if (items.length) await contactSheet(dir, items);
  const status = items.length ? 'candidates' : needsKey ? 'needs_key' : 'empty';
  summary[status === 'candidates' ? 'done' : status]++;
  writeFileSync(join(dir, 'candidates.json'), JSON.stringify({ id: req.id, vendor: req.vendor, family: req.family, query: req.query, status, items, log, fetched_at: new Date().toISOString() }, null, 1));
  console.log(`${req.id}: ${status} (${items.length})${log.length ? ' — ' + log.join('; ') : ''}`);
}
console.log(`\nитог: с кандидатами ${summary.done}, ждут ключ Google ${summary.needs_key}, пусто ${summary.empty}, запросов Google ${summary.google_calls}`);
