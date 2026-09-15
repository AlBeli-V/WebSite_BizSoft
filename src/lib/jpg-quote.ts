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
import { pdfMeasure, docFonts, logoBuffer } from './pdf-quote';

/** Начертания документа — те же файлы, что у PDF (шрифт сайта Raleway). */
const FONTS = docFonts();

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
  if (p.kind === 'image') {
    // Растр встраивается data-URI: resvg не ходит по файловой системе за
    // внешними ссылками, а отдельный слой картинки поверх SVG рассыпал бы
    // единый порядок отрисовки.
    const b64 = logoBuffer(p.file).toString('base64');
    return `<image x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" `
      + `preserveAspectRatio="xMinYMid meet" href="data:image/png;base64,${b64}"/>`;
  }
  if (p.kind === 'bullet') {
    return `<circle cx="${p.x}" cy="${p.y}" r="${p.size}" fill="${p.color}"/>`;
  }
  if (p.kind === 'rect') {
    return `<rect x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" fill="${p.fill}"/>`;
  }
  if (p.kind === 'line') {
    return `<line x1="${p.x1}" y1="${p.y1}" x2="${p.x2}" y2="${p.y2}" `
      + `stroke="${p.color}" stroke-width="${p.lineWidth}"/>`;
  }
  if (p.kind === 'band') {
    const cx = p.x + p.w / 2;
    const cy = p.y + p.h / 2;
    const inner = p.x < PAGE.width / 2 ? p.x + p.w : p.x;
    // Замок: дужка линией и корпус скруглённым прямоугольником — те же
    // пропорции, что в PDF-драйвере, иначе картинка разойдётся с PDF.
    const lock = (top: number) => {
      const size = p.lock;
      const bodyY = top + size * 0.34;
      return `<g fill="${p.textColor}" stroke="${p.textColor}" opacity="${p.textOpacity}">`
        + `<path d="M ${cx - size * 0.26} ${bodyY} L ${cx - size * 0.26} ${bodyY - size * 0.16} `
        + `C ${cx - size * 0.26} ${top} ${cx + size * 0.26} ${top} ${cx + size * 0.26} ${bodyY - size * 0.16} `
        + `L ${cx + size * 0.26} ${bodyY}" fill="none" stroke-width="${size * 0.15}"/>`
        + `<rect x="${cx - size * 0.43}" y="${bodyY}" width="${size * 0.86}" height="${size * 0.66}" `
        + `rx="${size * 0.16}" ry="${size * 0.16}" stroke="none"/>`
        + `</g>`;
    };
    return `<g>`
      + `<rect x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" fill="${p.fill}" `
      + `opacity="${p.fillOpacity}"/>`
      + `<line x1="${inner}" y1="${p.y}" x2="${inner}" y2="${p.y + p.h}" stroke="${p.edge}" `
      + `stroke-width="0.8" opacity="${p.fillOpacity * 3}"/>`
      + `<text x="${cx}" y="${cy}" font-family="${FONTS.family}" font-weight="bold" `
      + `font-size="${p.size}" letter-spacing="${p.spacing}" fill="${p.textColor}" `
      + `opacity="${p.textOpacity}" text-anchor="middle" dominant-baseline="central" `
      + `transform="rotate(-90 ${cx} ${cy})">${esc(p.text)}</text>`
      + lock(p.y + p.lock * 2.6)
      + lock(p.y + p.h - p.lock * 3.6)
      + `</g>`;
  }
  const y = p.y + p.size * ASCENT;
  let x = p.x;
  let anchor: string = ANCHOR.left;
  if (p.width && p.align === 'right') { x = p.x + p.width; anchor = ANCHOR.right; }
  if (p.width && p.align === 'center') { x = p.x + p.width / 2; anchor = ANCHOR.center; }
  return `<text x="${x}" y="${y}" font-family="${FONTS.family}" `
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
      fontFiles: FONTS.files,
      loadSystemFonts: false,
      defaultFontFamily: FONTS.family,
    },
  });
  const img = r.render();
  return { width: img.width, height: img.height, data: Buffer.from(img.pixels) };
}

/**
 * КП в JPEG — по файлу на лист.
 *
 * Раньше страницы склеивались в одну вертикальную ленту: на экране это
 * читалось, но распечатать такой файл нельзя — лента ложится на один лист
 * нечитаемой полосой. Документ подшивают к договору, поэтому каждый лист
 * отдаётся отдельным файлом формата A4 (решение руководителя 15.09.2026);
 * имена файлов проставляет отправитель: один лист — без номера, несколько —
 * «…_лист1», «…_лист2» по числу реальных листов.
 */
export function generateQuoteJpgPages(data: QuoteData): Buffer[] {
  const pages = buildQuoteLayout(data, pdfMeasure());
  return pages.map((p) => {
    const img = raster(quotePageSvg(p.items));
    return jpeg.encode({ width: img.width, height: img.height, data: img.data }, QUALITY).data;
  });
}

/**
 * Имена файлов листов: `KP_<номер>.jpg` у одностраничного КП и
 * `KP_<номер>_лист1.jpg`, `…_лист2.jpg` — у многостраничного.
 */
export function jpgFileNames(quoteNo: string, pages: number): string[] {
  if (pages <= 1) return [`KP_${quoteNo}.jpg`];
  return Array.from({ length: pages }, (_, i) => `KP_${quoteNo}_лист${i + 1}.jpg`);
}
