// Генерирует src/data/logos.ts из пакета simple-icons.
// Берём только бренды, которые есть в наборе (официальные SVG-глифы).
// Отсутствующие (Adobe, OpenAI, Canva и т.п.) рендерятся буквенным знаком в компоненте.
// Запуск: node scripts/build-logos.mjs
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dir, '../src/data/logos.ts');

const all = await import('simple-icons');
const byTitle = {};
for (const k of Object.keys(all)) {
  const ic = all[k];
  if (ic && ic.title && ic.path) byTitle[ic.title.toLowerCase()] = ic;
}

// Наш slug → возможные названия в simple-icons (первое найденное используется).
const MAP = {
  figma: ['Figma'],
  jetbrains: ['JetBrains'],
  zoom: ['Zoom'],
  miro: ['Miro'],
  autodesk: ['Autodesk'],
  framer: ['Framer'],
  sketch: ['Sketch'],
  unity: ['Unity'],
  'unreal-engine': ['Unreal Engine'],
  blackmagic: ['DaVinci Resolve', 'Blackmagic Design'],
  runway: ['Runway'],
  descript: ['Descript'],
  elevenlabs: ['ElevenLabs'],
  heygen: ['HeyGen'],
  freepik: ['Freepik'],
  shutterstock: ['Shutterstock'],
  envato: ['Envato'],
  procreate: ['Procreate'],
  coreldraw: ['CorelDRAW'],
  maxon: ['Maxon'],
  houdini: ['Houdini'],
  perforce: ['Perforce'],
  wondershare: ['Wondershare Filmora', 'Wondershare'],
  spine: ['Spine'],
  rive: ['Rive'],
  clip_studio_paint: ['Clip Studio Paint'],
  'clip-studio-paint': ['Clip Studio Paint'],
  topaz_labs: ['Topaz Labs'],
  midjourney: ['Midjourney'],
  recraft: ['Recraft'],
};

const out = {};
const found = [];
const missing = [];
for (const [slug, titles] of Object.entries(MAP)) {
  const ic = titles.map((t) => byTitle[t.toLowerCase()]).find(Boolean);
  if (ic) {
    out[slug] = { title: ic.title, hex: '#' + ic.hex, path: ic.path };
    found.push(slug);
  } else {
    missing.push(slug);
  }
}

const body = `/**
 * Данные брендовых логотипов (path SVG 24×24) — АВТОГЕНЕРАЦИЯ из simple-icons.
 * Не править руками: node scripts/build-logos.mjs
 * Отсутствующие бренды рендерятся буквенным знаком в VendorLogo.astro.
 */
export interface BrandLogo { title: string; hex: string; path: string }
export const LOGOS: Record<string, BrandLogo> = ${JSON.stringify(out, null, 2)};

export function brandLogo(slug: string): BrandLogo | undefined {
  return LOGOS[slug];
}
`;
writeFileSync(OUT, body);
console.log(`logos.ts: ${found.length} найдено (${found.join(', ')})`);
console.log(`не в наборе: ${missing.join(', ') || '—'}`);
