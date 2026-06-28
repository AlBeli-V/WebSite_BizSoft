// Генерирует public/og-default.png (1200×630) из SVG со встроенным шрифтом.
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const require = createRequire(import.meta.url);
const __dir = dirname(fileURLToPath(import.meta.url));
// sharp — транзитивная зависимость astro; ищем её в pnpm-сторе.
import { readdirSync } from 'node:fs';
function loadSharp() {
  try { return require('sharp'); } catch { /* not hoisted */ }
  const store = resolve(__dir, '../node_modules/.pnpm');
  const dir = readdirSync(store).find((d) => d.startsWith('sharp@'));
  if (!dir) throw new Error('sharp not found in pnpm store');
  return require(resolve(store, dir, 'node_modules/sharp'));
}
const sharp = loadSharp();
const PUB = resolve(__dir, '../public');

const fontReg = readFileSync(require.resolve('dejavu-fonts-ttf/ttf/DejaVuSans.ttf')).toString('base64');
const fontBold = readFileSync(require.resolve('dejavu-fonts-ttf/ttf/DejaVuSans-Bold.ttf')).toString('base64');

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <style>
      @font-face { font-family: 'DJ'; font-weight: 400; src: url(data:font/ttf;base64,${fontReg}) format('truetype'); }
      @font-face { font-family: 'DJB'; font-weight: 700; src: url(data:font/ttf;base64,${fontBold}) format('truetype'); }
      .t { font-family: 'DJ'; fill: #8A8F98; }
      .b { font-family: 'DJB'; fill: #F2F3F5; }
      .a { font-family: 'DJB'; fill: #FF763C; }
    </style>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FF763C" stop-opacity="0.12"/>
      <stop offset="1" stop-color="#0E0F12" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="#0E0F12"/>
  <rect width="1200" height="630" fill="url(#g)"/>
  <text x="90" y="250" font-size="92"><tspan class="b">Biz</tspan><tspan class="a">Soft</tspan></text>
  <text x="92" y="330" class="t" font-size="40">Легальное ПО для бизнеса</text>
  <text x="92" y="392" class="t" font-size="40">по договору и счёту</text>
  <text x="92" y="560" class="a" font-size="30">Договор · Счёт · ЭДО · Закрывающие документы</text>
</svg>`;

const buf = await sharp(Buffer.from(svg)).png().toBuffer();
writeFileSync(resolve(PUB, 'og-default.png'), buf);
console.log('✓ og-default.png written:', buf.length, 'bytes');
