/**
 * Word-версия коммерческого предложения — рабочий исходник для руководителя.
 *
 * Решение руководителя 28.08.2026 (заменяет решение от 21.08.2026):
 * Word повторяет клиентский документ один в один по содержанию — те же
 * блоки, тот же порядок, те же тексты и суммы, — но БЕЗ водяных знаков:
 * это внутренний документ для правки перед переговорами. Наружу уходит
 * только PDF/JPG со штампами; Word клиенту не пересылается ни в каком виде.
 *
 * Вёрстка у Word своя (потоковый формат, координаты макета в него не
 * переносятся), поэтому все текстовые блоки берутся из quote-layout.ts —
 * общего содержимого форматов. Совпадение закрепляет tests/quote-docx.test.ts.
 */
import {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, LevelFormat,
  Packer, Paragraph, ShadingType, Table, TableCell, TableRow, TextRun,
  WidthType,
} from 'docx';
import { seller, site } from '../config/site';
import { formatRub } from './pricing';
import { amountPhrase, moneyFmt, singleVatRate, vatOfItems } from './rub-words';
import { salutation } from './salutation';
import {
  buyerLines, footerLines, headMetaLines, HEAD_SUBTITLE, PRELIMINARY_NOTE,
  quoteConditions, quoteIntro, sellerContactLines, signatureContactLines,
  signer, VAT_PERCENT, type QuoteData,
} from './quote-layout';

const GREY = '6B7280';
const DARK = '14161A';
const BODY = '374151';
const ACCENT = 'FF763C';
const NOTE_BG = 'FFF4EF';
const RULE = 'E5E7EB';

type Align = (typeof AlignmentType)[keyof typeof AlignmentType];

const line = (text: string, opts: { size?: number; bold?: boolean; color?: string;
  align?: Align; before?: number; after?: number } = {}) =>
  new Paragraph({
    alignment: opts.align,
    spacing: { before: opts.before ?? 0, after: opts.after ?? 40 },
    children: [new TextRun({ text, bold: opts.bold, color: opts.color || BODY,
                             size: (opts.size || 9) * 2, font: 'Calibri' })],
  });

const cell = (text: string, opts: { bold?: boolean; align?: Align; width: number } = { width: 1000 }) =>
  new TableCell({
    width: { size: opts.width, type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
    children: [new Paragraph({
      alignment: opts.align,
      children: [new TextRun({ text, bold: opts.bold, size: 18, font: 'Calibri' })],
    })],
  });

// Ширины колонок в DXA. Рабочая ширина A4 при полях 2 см ≈ 9640 twips;
// порядок колонок — как в макете: артикул перед наименованием.
const COLS = { n: 480, sku: 1750, name: 3730, qty: 760, price: 1360, sum: 1560 };
const TABLE_W = COLS.n + COLS.sku + COLS.name + COLS.qty + COLS.price + COLS.sum;

export async function generateQuoteDocx(data: QuoteData): Promise<Buffer> {
  const vat = vatOfItems(data.items, VAT_PERCENT);
  const rate = singleVatRate(data.items, VAT_PERCENT);
  const rateLabel = rate === null ? '' : ` ${rate}%`;

  // ── Шапка: марка, заголовок, служебные строки, контакты продавца ───────
  const head = [
    new Paragraph({
      spacing: { after: 40 },
      children: [
        new TextRun({ text: 'BIZ', bold: true, size: 44, color: DARK, font: 'Calibri' }),
        new TextRun({ text: 'Soft', bold: true, size: 44, color: ACCENT, font: 'Calibri' }),
      ],
    }),
    line(site.tagline, { size: 9, color: GREY }),
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      spacing: { before: 200, after: 60 },
      children: [new TextRun({ text: 'КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ', bold: true, size: 30, color: DARK, font: 'Calibri' })],
    }),
    line(HEAD_SUBTITLE, { size: 8.5, color: GREY, after: 120 }),
    ...headMetaLines(data).map((t) => line(t, { size: 9, color: GREY })),
    new Paragraph({ spacing: { after: 60 }, children: [] }),
    ...sellerContactLines().map((t) => line(t, { size: 8.5, color: GREY })),
  ];

  // ── Кому и обращение ───────────────────────────────────────────────────
  const addressee = [
    line('Кому:', { bold: true, size: 10, color: DARK, before: 160 }),
    ...buyerLines(data).map((t) => line(t, { size: 9 })),
    line(salutation(data.contactName), { bold: true, size: 11, color: DARK,
      align: AlignmentType.CENTER, before: 160, after: 120 }),
    line(quoteIntro(data.buyerCompany), { size: 9.5, after: 120 }),
  ];

  // ── Таблица позиций — колонки и порядок как в макете ───────────────────
  const table = new Table({
    width: { size: TABLE_W, type: WidthType.DXA },
    columnWidths: [COLS.n, COLS.sku, COLS.name, COLS.qty, COLS.price, COLS.sum],
    borders: {
      top: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      bottom: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      left: { style: BorderStyle.NONE, size: 0, color: 'auto' },
      right: { style: BorderStyle.NONE, size: 0, color: 'auto' },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: RULE },
      insideVertical: { style: BorderStyle.NONE, size: 0, color: 'auto' },
    },
    rows: [
      new TableRow({
        tableHeader: true,
        children: [
          new TableCell({
            width: { size: COLS.n, type: WidthType.DXA },
            shading: { type: ShadingType.CLEAR, fill: 'F3F4F6' },
            margins: { top: 60, bottom: 60, left: 80, right: 80 },
            children: [new Paragraph({ children: [new TextRun({ text: '№', bold: true, size: 18, font: 'Calibri' })] })],
          }),
          ...([
            ['Артикул', COLS.sku, undefined],
            ['Наименование', COLS.name, undefined],
            ['Кол.', COLS.qty, AlignmentType.RIGHT],
            ['Цена, ₽', COLS.price, AlignmentType.RIGHT],
            ['Сумма, ₽', COLS.sum, AlignmentType.RIGHT],
          ] as const).map(([t, w, a]) => new TableCell({
            width: { size: w, type: WidthType.DXA },
            shading: { type: ShadingType.CLEAR, fill: 'F3F4F6' },
            margins: { top: 60, bottom: 60, left: 80, right: 80 },
            children: [new Paragraph({
              alignment: a,
              children: [new TextRun({ text: t, bold: true, size: 18, font: 'Calibri' })],
            })],
          })),
        ],
      }),
      ...data.items.map((it, i) => new TableRow({
        children: [
          cell(String(i + 1), { width: COLS.n }),
          cell(it.sku, { width: COLS.sku }),
          cell(it.name, { width: COLS.name }),
          cell(String(it.qty), { width: COLS.qty, align: AlignmentType.RIGHT }),
          cell(formatRub(it.price), { width: COLS.price, align: AlignmentType.RIGHT }),
          cell(formatRub(it.sum), { width: COLS.sum, align: AlignmentType.RIGHT }),
        ],
      })),
    ],
  });

  // ── Итог, НДС, сумма прописью — строки как в макете ────────────────────
  const totals = [
    line(`ИТОГО в т.ч. НДС${rateLabel}: ${moneyFmt(data.total)} ₽`,
         { bold: true, size: 12, color: DARK, align: AlignmentType.RIGHT, before: 160 }),
    line(`НДС${rateLabel}: ${moneyFmt(vat)} ₽`,
         { bold: true, size: 10, color: DARK, align: AlignmentType.RIGHT }),
    line(`Стоимость предложения: ${amountPhrase(data.total)}, в т.ч. НДС`
         + `${rateLabel} ${amountPhrase(vat)}.`, { size: 9, after: 120 }),
  ];

  // ── Условия поставки ───────────────────────────────────────────────────
  const conditions = [
    line('Условия поставки', { bold: true, size: 10, color: DARK, before: 120 }),
    ...quoteConditions(data.validUntil).map((t) => new Paragraph({
      numbering: { reference: 'conditions', level: 0 },
      spacing: { after: 40 },
      children: [new TextRun({ text: t, size: 18, color: BODY, font: 'Calibri' })],
    })),
  ];

  // ── Оговорка о статусе на подложке ─────────────────────────────────────
  const note = new Paragraph({
    shading: { type: ShadingType.CLEAR, fill: NOTE_BG },
    spacing: { before: 160, after: 160 },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: ACCENT, space: 4 } },
    children: [new TextRun({ text: PRELIMINARY_NOTE, size: 18, color: DARK, font: 'Calibri' })],
  });

  // ── Подпись ────────────────────────────────────────────────────────────
  const signature = [
    line('С уважением,', { size: 9.5, before: 120 }),
    line(`${signer.name}, ${signer.role}`, { bold: true, size: 10, color: DARK }),
    ...signatureContactLines().map((t) => line(t, { size: 8.5, color: GREY })),
  ];

  const [foot1, foot2] = footerLines();

  const doc = new Document({
    creator: seller.shortName,
    title: `Коммерческое предложение № ${data.quoteNo}`,
    description: `КП для ${data.buyerCompany || 'клиента'} на ${formatRub(data.total)}`,
    numbering: {
      config: [{
        reference: 'conditions',
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 360, hanging: 200 } } },
        }],
      }],
    },
    sections: [{
      footers: {
        default: new Footer({
          children: [
            line(foot1, { size: 7, color: GREY, align: AlignmentType.CENTER, after: 0 }),
            line(foot2, { size: 7, color: GREY, align: AlignmentType.CENTER, after: 0 }),
          ],
        }),
      },
      children: [...head, ...addressee, table, ...totals, ...conditions, note, ...signature],
    }],
  });
  return Packer.toBuffer(doc) as unknown as Promise<Buffer>;
}
