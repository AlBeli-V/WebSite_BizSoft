/**
 * PDF коммерческого предложения — драйвер поверх общей раскладки.
 *
 * Сам макет живёт в quote-layout.ts, здесь только рисование примитивов
 * средствами pdfkit. Кириллица — встроенный DejaVu Sans из node_modules,
 * headless-браузер не нужен.
 *
 * PDF — рабочий документ: его отправляет руководитель лично. Клиент со
 * страницы получает JPG (см. jpg-quote.ts), чтобы документ нельзя было
 * отредактировать и выдать за наш.
 */
import PDFDocument from 'pdfkit';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { buildQuoteLayout, PAGE, type QuoteData, type Measure, type Primitive } from './quote-layout';

export type { QuoteData };
export { buildQuoteNo, formatDateRu, addDays } from './quote-layout';

const require = createRequire(import.meta.url);
export function fontPath(file: string): string {
  return require.resolve(`dejavu-fonts-ttf/ttf/${file}`);
}
const FONT_REGULAR = readFileSync(fontPath('DejaVuSans.ttf'));
const FONT_BOLD = readFileSync(fontPath('DejaVuSans-Bold.ttf'));

/** Измеритель на pdfkit: оба формата считают раскладку им, поэтому не расходятся. */
export function pdfMeasure(): Measure {
  const probe = new PDFDocument({ size: 'A4', margin: PAGE.margin });
  probe.registerFont('r', FONT_REGULAR);
  probe.registerFont('b', FONT_BOLD);
  const pick = (size: number, bold?: boolean) => probe.font(bold ? 'b' : 'r').fontSize(size);
  return {
    height: (text, size, width, bold) => { pick(size, bold); return probe.heightOfString(text, { width }); },
    width: (text, size, bold) => { pick(size, bold); return probe.widthOfString(text); },
  };
}

function draw(doc: PDFKit.PDFDocument, p: Primitive): void {
  if (p.kind === 'rect') {
    doc.rect(p.x, p.y, p.w, p.h).fill(p.fill);
    return;
  }
  if (p.kind === 'line') {
    doc.moveTo(p.x1, p.y1).lineTo(p.x2, p.y2)
      .strokeColor(p.color).lineWidth(p.lineWidth).stroke();
    return;
  }
  if (p.kind === 'watermark') {
    doc.save();
    doc.rotate(p.angle, { origin: [p.x, p.y] });
    doc.fillOpacity(p.opacity).strokeOpacity(p.opacity);

    // Рамка оттиска. Пунктир имитирует потёртость краски — сплошная линия
    // выглядит печатью на бланке, а не штампом.
    doc.roundedRect(p.x - p.w / 2, p.y - p.h / 2, p.w, p.h, p.radius)
      .lineWidth(p.stroke).strokeColor(p.color).dash(p.dash[0], { space: p.dash[1] }).stroke();
    doc.undash();

    const hasSub = Boolean(p.sub);
    doc.font('b').fontSize(p.size).fillColor(p.color);
    const tw = doc.widthOfString(p.text);
    const ty = hasSub ? p.y - p.size * 0.75 : p.y - p.size / 2;
    doc.text(p.text, p.x - tw / 2, ty, { lineBreak: false });
    if (hasSub) {
      doc.font('r').fontSize(p.subSize);
      const sw = doc.widthOfString(p.sub!);
      doc.text(p.sub!, p.x - sw / 2, p.y + p.size * 0.35, { lineBreak: false });
    }

    doc.restore();
    doc.fillOpacity(1).strokeOpacity(1);
    return;
  }
  doc.font(p.bold ? 'b' : 'r').fontSize(p.size).fillColor(p.color);
  doc.text(p.text, p.x, p.y,
    p.width ? { width: p.width, align: p.align || 'left' } : { lineBreak: false });
}

export function generateQuotePdf(data: QuoteData): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    try {
      const pages = buildQuoteLayout(data, pdfMeasure());
      const doc = new PDFDocument({ size: 'A4', margin: PAGE.margin, autoFirstPage: false });
      doc.registerFont('r', FONT_REGULAR);
      doc.registerFont('b', FONT_BOLD);

      const chunks: Buffer[] = [];
      doc.on('data', (c: Buffer) => chunks.push(c));
      doc.on('end', () => resolve(Buffer.concat(chunks)));
      doc.on('error', reject);

      for (const page of pages) {
        doc.addPage({ size: 'A4', margin: PAGE.margin });
        for (const p of page.items) draw(doc, p);
      }
      doc.end();
    } catch (e) {
      reject(e);
    }
  });
}
