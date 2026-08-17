// Генерирует src/data/logos.ts из пакета simple-icons.
// Автоматически подбирает глиф для КАЖДОГО вендора (VENDORS + bespoke) по названию.
// Отсутствующие в наборе бренды рендерятся буквенным знаком в VendorLogo.astro.
// Запуск: node scripts/build-logos.mjs
import { readFileSync, writeFileSync, readdirSync, existsSync, copyFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dir, '../src/data/logos.ts');
const VENDORS_TS = resolve(__dir, '../src/data/vendors.ts');
// Официальные логотипы правообладателей: положите <slug>.svg сюда — они имеют
// приоритет над встроенным набором и рендерятся как есть (с фирменными цветами).
const BRAND_DIR = resolve(__dir, '../public/brand-logos');

// ── Все бренды сайта: bespoke + записи из VENDORS (парсим слаги/названия) ──
const targets = [
  { slug: 'jetbrains', names: ['JetBrains'] },
  { slug: 'zoom', names: ['Zoom'] },
  { slug: 'openai', names: ['OpenAI'] },
  { slug: 'figma', names: ['Figma'] },
  // AI-вендоры каталога (лендингов пока нет — логотипы нужны для /vendors и карточек)
  { slug: 'anthropic', names: ['Anthropic', 'Claude'] },
  { slug: 'github', names: ['GitHub'] },
  { slug: 'cursor', names: ['Cursor'] },
  { slug: 'microsoft', names: ['Microsoft'] },
  { slug: 'google', names: ['Google'] },
  { slug: 'perplexity', names: ['Perplexity'] },
  { slug: 'notion', names: ['Notion'] },
  { slug: 'gamma', names: ['Gamma'] },
  { slug: 'grammarly', names: ['Grammarly'] },
  { slug: 'jasper', names: ['Jasper'] },
  { slug: 'heygen', names: ['HeyGen'] },
  { slug: 'descript', names: ['Descript'] },
  { slug: 'runway', names: ['Runway', 'RunwayML'] },
  { slug: 'recraft', names: ['Recraft'] },
];
const src = readFileSync(VENDORS_TS, 'utf8');
const re = /\{\s*slug:\s*'([^']+)',\s*vendor:\s*'([^']+)'(?:,\s*title:\s*'([^']+)')?/g;
let m;
while ((m = re.exec(src)) !== null) {
  const [, slug, vendor, title] = m;
  targets.push({ slug, names: [title, vendor].filter(Boolean) });
}

// ── Индекс simple-icons по нормализованному названию ──
const all = await import('simple-icons');
const norm = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
const byName = {};
for (const k of Object.keys(all)) {
  const ic = all[k];
  if (ic && ic.title && ic.path) byName[norm(ic.title)] = ic;
}
// Ручные соответствия, где название вендора не совпадает с simple-icons.
const ALIAS = {
  blackmagic: 'davinciresolve',
  'sidefx-houdini': 'houdini',
  'magix-vegas': 'vegaspro',
  wondershare: 'wondersharefilmora',
  audiokinetic: 'audiokinetic',
};

const out = {};
const found = [];
const missing = [];
for (const t of targets) {
  if (out[t.slug]) continue;
  let ic = null;
  const aliasName = ALIAS[t.slug];
  if (aliasName && byName[norm(aliasName)]) ic = byName[norm(aliasName)];
  if (!ic) for (const n of t.names) { if (byName[norm(n)]) { ic = byName[norm(n)]; break; } }
  if (ic) { out[t.slug] = { title: ic.title, hex: '#' + ic.hex, path: ic.path }; found.push(t.slug); }
  else missing.push(t.slug);
}

// ── Экспорт цветных SVG-файлов брендов (SEO-имена: <slug>-logo.svg) ──
// Дизайн-калибровка: глифы simple-icons оптически нормированы на сетке 24px —
// единый визуальный размер по построению. Цвет — официальный hex бренда;
// слишком светлые знаки затемняем до читаемого на белой карточке.
function visibleHex(hex) {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  const lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  return lum > 0.82 ? '#1d1d1f' : '#' + h;
}
const generated = {};

// ── Официальные логотипы правообладателей: public/brand-logos/<slug>.<svg|png|webp> ──
// Высший приоритет: копируются под SEO-именем <slug>-logo.<ext> и попадают в
// LOGO_FILE вместо глифа/монограммы. Достаточно положить файл и пересобрать сайт.
const fileLogos = [];
if (existsSync(BRAND_DIR)) {
  for (const f of readdirSync(BRAND_DIR)) {
    const mExt = f.toLowerCase().match(/^(.+)\.(svg|png|webp)$/);
    if (!mExt || mExt[1].endsWith('-logo')) continue;
    const [, slug, ext] = mExt;
    copyFileSync(resolve(BRAND_DIR, f), resolve(BRAND_DIR, `${slug}-logo.${ext}`));
    generated[slug] = `/brand-logos/${slug}-logo.${ext}`;
    fileLogos.push(slug);
  }
}
fileLogos.sort();

for (const [slug, ic] of Object.entries(out)) {
  if (generated[slug]) continue;
  const fill = visibleHex(ic.hex);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" role="img" aria-label="${ic.title}">` +
    `<title>${ic.title} — логотип</title><path fill="${fill}" d="${ic.path}"/></svg>\n`;
  const fname = `${slug}-logo.svg`;
  writeFileSync(resolve(BRAND_DIR, fname), svg);
  generated[slug] = `/brand-logos/${fname}`;
}

// ── Монограммы для брендов без глифа (simple-icons удалил ряд марок) ──
// Единая система: скруглённый квадрат в фирменном цвете + белая литера.
// Фирменные цвета: из VENDORS.brandColor + ручная карта для новых вендоров.
const BRAND_COLORS = {
  openai: '#10A37F', adobe: '#FA0F00', canva: '#00C4CC', microsoft: '#0078D4',
  midjourney: '#1a1a2e', runway: '#1F1F1F', descript: '#001DFF', heygen: '#6D4AFF',
  gamma: '#7C3AED', jasper: '#8B5CF6', recraft: '#111111',
};
const colorRe = /slug:\s*'([^']+)'[^}]*?brandColor:\s*'([^']+)'/g;
let cm;
while ((cm = colorRe.exec(src)) !== null) {
  if (!BRAND_COLORS[cm[1]]) BRAND_COLORS[cm[1]] = cm[2];
}
const PALETTE = ['#f2591d', '#2563eb', '#0f766e', '#7c3aed', '#b45309', '#be185d', '#334155'];
const hashColor = (s) => PALETTE[[...s].reduce((a, c) => a + c.charCodeAt(0), 0) % PALETTE.length];

for (const t of targets) {
  if (generated[t.slug]) continue;
  const name = t.names[0] || t.slug;
  const letter = name.trim().charAt(0).toUpperCase();
  const color = visibleHex(BRAND_COLORS[t.slug] || hashColor(t.slug));
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" role="img" aria-label="${name}">` +
    `<title>${name} — логотип</title>` +
    `<rect x="1" y="1" width="22" height="22" rx="5.5" fill="${color}"/>` +
    `<text x="12" y="12.5" text-anchor="middle" dominant-baseline="central" ` +
    `font-family="-apple-system,'Segoe UI',Roboto,Arial,sans-serif" font-size="12.5" font-weight="800" fill="#ffffff">${letter}</text></svg>\n`;
  const fname = `${t.slug}-logo.svg`;
  writeFileSync(resolve(BRAND_DIR, fname), svg);
  generated[t.slug] = `/brand-logos/${fname}`;
}

const body = `/**
 * Данные брендовых логотипов — АВТОГЕНЕРАЦИЯ: node scripts/build-logos.mjs
 * 1) FILE_LOGOS — официальные SVG из public/brand-logos/<slug>.svg (приоритет).
 * 2) LOGOS — встроенные глифы из simple-icons.
 * 3) иначе — буквенный знак в VendorLogo.astro.
 */
export interface BrandLogo { title: string; hex: string; path: string }
export const LOGOS: Record<string, BrandLogo> = ${JSON.stringify(out, null, 2)};

/** Слаги, для которых есть официальный файл public/brand-logos/<slug>.svg. */
export const FILE_LOGOS: string[] = ${JSON.stringify(fileLogos)};

/** Сгенерированные цветные SVG-файлы брендов (SEO-имена <slug>-logo.svg). */
export const LOGO_FILE: Record<string, string> = ${JSON.stringify(generated, null, 2)};

export function brandLogo(slug: string): BrandLogo | undefined {
  return LOGOS[slug];
}
export function hasFileLogo(slug: string): boolean {
  return FILE_LOGOS.includes(slug);
}
/** Путь к цветному SVG-файлу логотипа бренда (если сгенерирован). */
export function logoFile(slug: string): string | undefined {
  return LOGO_FILE[slug];
}
`;
writeFileSync(OUT, body);
console.log(`logos.ts: ${found.length} глифов simple-icons; ${fileLogos.length} официальных файлов (${fileLogos.join(', ') || '—'})`);
console.log(`буквенный знак: ${missing.filter((s) => !fileLogos.includes(s)).join(', ') || '—'}`);
