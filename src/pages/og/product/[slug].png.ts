export const prerender = false;

/**
 * Б12 аудита: уникальная OG-картинка карточки товара (1200×630 PNG).
 * Рендер на лету: SVG → PNG через resvg; шрифты DejaVu (в комплекте).
 * Ссылка на товар в Telegram/почте показывает название, вендора и цену.
 */
import type { APIRoute } from 'astro';
import { Resvg } from '@resvg/resvg-js';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { getProductBySlug } from '../../../lib/directus';
import { isSourceUnavailable, serviceUnavailable } from '../../../lib/http';
import { effectivePrice } from '../../../lib/pricing';

const require = createRequire(import.meta.url);
const fontRegular = require.resolve('dejavu-fonts-ttf/ttf/DejaVuSans.ttf');
const fontBold = require.resolve('dejavu-fonts-ttf/ttf/DejaVuSans-Bold.ttf');

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const fmt = (n: number) => new Intl.NumberFormat('ru-RU').format(Math.round(n)) + ' ₽';

/** Перенос названия на строки ≤ limit символов (максимум 2 строки). */
function wrap(text: string, limit = 26): string[] {
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let cur = '';
  for (const w of words) {
    if ((cur + ' ' + w).trim().length > limit && cur) {
      lines.push(cur.trim());
      cur = w;
    } else cur = (cur + ' ' + w).trim();
  }
  if (cur) lines.push(cur);
  if (lines.length > 2) {
    lines.length = 2;
    lines[1] = lines[1].slice(0, limit - 1) + '…';
  }
  return lines;
}

export const GET: APIRoute = async ({ params }) => {
  const slug = params.slug || '';
  let product = null;
  try {
    product = await getProductBySlug(slug);
  } catch (e) {
    // Соцсеть повторит запрос по 503; по 404 закэширует отсутствие картинки.
    if (isSourceUnavailable(e)) return serviceUnavailable();
  }
  if (!product) return new Response(null, { status: 404 });

  const eff = effectivePrice(product);
  const hasPrice = Number.isFinite(eff.price) && eff.price > 0;
  const priceLine = hasPrice ? `от ${fmt(eff.price)} в год` : 'Цена по запросу';
  const vendor = (product.vendor || '').replace(/\s*\(.+\)$/, '');
  const nameLines = wrap(product.name);
  const nameSvg = nameLines
    .map((l, i) => `<text x="80" y="${300 + i * 74}" font-family="DejaVu Sans" font-weight="bold" font-size="58" fill="#1d1d1f">${esc(l)}</text>`)
    .join('');

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630">
  <rect width="1200" height="630" fill="#ffffff"/>
  <rect x="0" y="0" width="1200" height="12" fill="#f2591d"/>
  <text x="80" y="120" font-family="DejaVu Sans" font-weight="bold" font-size="40" fill="#1d1d1f">BIZ<tspan fill="#f2591d">Soft</tspan></text>
  <text x="80" y="160" font-family="DejaVu Sans" font-size="22" fill="#565660">Единая точка доступа к ПО и AI-сервисам</text>
  ${vendor ? `<text x="80" y="236" font-family="DejaVu Sans" font-weight="bold" font-size="26" fill="#f2591d">${esc(vendor.toUpperCase())}</text>` : ''}
  ${nameSvg}
  <text x="80" y="${nameLines.length > 1 ? 494 : 430}" font-family="DejaVu Sans" font-weight="bold" font-size="44" fill="#f2591d">${esc(priceLine)}</text>
  <text x="80" y="566" font-family="DejaVu Sans" font-size="24" fill="#565660">Для юрлиц · договор и счёт в рублях · закрывающие через ЭДО</text>
</svg>`;

  const png = new Resvg(svg, {
    fitTo: { mode: 'width', value: 1200 },
    font: { fontFiles: [fontRegular, fontBold], loadSystemFonts: false, defaultFontFamily: 'DejaVu Sans' },
  }).render().asPng();

  return new Response(new Uint8Array(png), {
    status: 200,
    headers: {
      'Content-Type': 'image/png',
      'Cache-Control': 'public, max-age=86400, stale-while-revalidate=604800',
    },
  });
};
