/**
 * JPG коммерческого предложения — то, что скачивает клиент.
 *
 * Решение руководителя 21.08.2026: со страницы и в письме клиенту уходит
 * картинка, PDF отправляет руководитель лично. Картинку нельзя открыть в
 * редакторе, подменить сумму и выдать за наш документ — а именно этим
 * опасен свободно гуляющий редактируемый PDF с реквизитами и печатью.
 *
 * Растеризация без нативных зависимостей: макет складывается в SVG,
 * @resvg/resvg-js (уже в прод-зависимостях) отдаёт сырые пиксели, jpeg-js
 * кодирует их в JPEG. На Alpine нет ни poppler, ни ImageMagick, а Playwright
 * живёт только в dev-зависимостях — этот путь работает на проде как есть.
 */
import jpeg from 'jpeg-js';
import { Resvg } from '@resvg/resvg-js';
import { buildQuoteLayout, PAGE, type QuoteData, type Primitive } from './quote-layout';
import { pdfMeasure, fontPath } from './pdf-quote';

/** Плотность растра: 2× к типографским точкам — читается на экране и в печати. */
export const SCALE = 2;
/** Качество JPEG: 88 — текст без заметных артефактов при вменяемом весе. */
export const QUALITY = 88;

const esc = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const ANCHOR = { left: 'start', right: 'end', center: 'middle' } as const;

/**
 * Примитив в SVG.
 *
 * pdfkit кладёт текст от ВЕРХНЕЙ кромки строки, SVG — от базовой линии,
 * поэтому y смещается на подъём шрифта. Без этой поправки картинка
 * выглядит съехавшей вверх относительно PDF на высоту строки.
 */
const ASCENT = 0.8;

function svgOf(p: Primitive): string {
  if (p.kind === 'rect') {
    return `<rect x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" fill="${p.fill}"/>`;
  }
  if (p.kind === 'line') {
    return `<line x1="${p.x1}" y1="${p.y1}" x2="${p.x2}" y2="${p.y2}" `
      + `stroke="${p.color}" stroke-width="${p.lineWidth}"/>`;
  }
  if (p.kind === 'watermark') {
    return `<g transform="rotate(${p.angle} ${p.x} ${p.y})" opacity="${p.opacity}">`
      + `<text x="${p.x}" y="${p.y}" font-family="DejaVu Sans" font-weight="bold" `
      + `font-size="${p.size}" fill="${p.color}" text-anchor="middle">${esc(p.text)}</text></g>`;
  }
  const y = p.y + p.size * ASCENT;
  let x = p.x;
  let anchor: string = ANCHOR.left;
  if (p.width && p.align === 'right') { x = p.x + p.width; anchor = ANCHOR.right; }
  if (p.width && p.align === 'center') { x = p.x + p.width / 2; anchor = ANCHOR.center; }
  return `<text x="${x}" y="${y}" font-family="DejaVu Sans" `
    + `font-weight="${p.bold ? 'bold' : 'normal'}" font-size="${p.size}" `
    + `fill="${p.color}" text-anchor="${anchor}">${esc(p.text)}</text>`;
}

export function quotePageSvg(items: Primitive[]): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${PAGE.width}" height="${PAGE.height}" `
    + `viewBox="0 0 ${PAGE.width} ${PAGE.height}">`
    + `<rect width="100%" height="100%" fill="#FFFFFF"/>`
    + items.map(svgOf).join('')
    + `</svg>`;
}

interface Raster { width: number; height: number; data: Buffer }

function raster(svg: string): Raster {
  const r = new Resvg(svg, {
    fitTo: { mode: 'width', value: Math.round(PAGE.width * SCALE) },
    font: {
      fontFiles: [fontPath('DejaVuSans.ttf'), fontPath('DejaVuSans-Bold.ttf')],
      loadSystemFonts: false,
      defaultFontFamily: 'DejaVu Sans',
    },
  });
  const img = r.render();
  return { width: img.width, height: img.height, data: Buffer.from(img.pixels) };
}

/**
 * Склейка страниц в одно изображение.
 *
 * Многостраничное КП отдаётся одной вертикальной лентой, а не архивом:
 * клиенту нужно посмотреть документ, а не разбирать вложенные файлы.
 * Между страницами тонкая линия — видно, где кончается одна.
 */
function stack(pages: Raster[]): Raster {
  if (pages.length === 1) return pages[0];
  const width = pages[0].width;
  const gap = 8;
  const height = pages.reduce((s, p) => s + p.height, 0) + gap * (pages.length - 1);
  const out = Buffer.alloc(width * height * 4, 0xEE);
  let y = 0;
  for (const p of pages) {
    p.data.copy(out, y * width * 4);
    y += p.height + gap;
  }
  return { width, height, data: out };
}

/** КП в JPEG. Один файл независимо от числа страниц. */
export function generateQuoteJpg(data: QuoteData): Buffer {
  const pages = buildQuoteLayout(data, pdfMeasure());
  const img = stack(pages.map((p) => raster(quotePageSvg(p.items))));
  return jpeg.encode({ width: img.width, height: img.height, data: img.data }, QUALITY).data;
}
