// Генерирует src/data/logos.ts из пакета simple-icons.
// Автоматически подбирает глиф для КАЖДОГО вендора (VENDORS + bespoke) по названию.
// Отсутствующие в наборе бренды рендерятся буквенным знаком в VendorLogo.astro.
// Запуск: node scripts/build-logos.mjs
import { readFileSync, writeFileSync, readdirSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, basename } from 'node:path';

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

// ── Официальные файлы логотипов из public/brand-logos/<slug>.svg ──
// Имеют приоритет: рендерятся как <img> с фирменными цветами.
const fileLogos = [];
if (existsSync(BRAND_DIR)) {
  for (const f of readdirSync(BRAND_DIR)) {
    if (f.toLowerCase().endsWith('.svg')) fileLogos.push(basename(f, '.svg'));
  }
}
fileLogos.sort();

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

export function brandLogo(slug: string): BrandLogo | undefined {
  return LOGOS[slug];
}
export function hasFileLogo(slug: string): boolean {
  return FILE_LOGOS.includes(slug);
}
`;
writeFileSync(OUT, body);
console.log(`logos.ts: ${found.length} глифов simple-icons; ${fileLogos.length} официальных файлов (${fileLogos.join(', ') || '—'})`);
console.log(`буквенный знак: ${missing.filter((s) => !fileLogos.includes(s)).join(', ') || '—'}`);
