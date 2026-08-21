/**
 * Word-версия коммерческого предложения — рабочий формат для руководителя.
 *
 * Решение руководителя 21.08.2026: на почту приходит два вложения — Word и
 * PDF. Word нужен, чтобы поправить документ перед отправкой (уточнить состав,
 * вписать исходящий номер), PDF — чтобы отправить как есть.
 *
 * Клиенту ни тот, ни другой не уходит: со страницы и в письме клиенту
 * отдаётся картинка (jpg-quote.ts).
 *
 * Водяные знаки здесь тоже есть: если документ сохранят в PDF из Word,
 * защита не должна исчезнуть по дороге.
 */
import {
  AlignmentType, BorderStyle, Document, HeadingLevel, Packer, Paragraph,
  Table, TableCell, TableRow, TextRun, WidthType,
} from 'docx';
import { seller, site } from '../config/site';
import { formatRub } from './pricing';
import { WATERMARK, type QuoteData } from './quote-layout';

const GREY = '6B7280';
const DARK = '14161A';
const ACCENT = 'FF763C';

const line = (text: string, opts: { size?: number; bold?: boolean; color?: string;
  align?: (typeof AlignmentType)[keyof typeof AlignmentType] } = {}) =>
  new Paragraph({
    alignment: opts.align,
    spacing: { after: 40 },
    children: [new TextRun({ text, bold: opts.bold, color: opts.color || DARK,
                             size: (opts.size || 9) * 2, font: 'Calibri' })],
  });

const cell = (text: string, opts: { bold?: boolean; align?: any; width?: number } = {}) =>
  new TableCell({
    width: opts.width ? { size: opts.width, type: WidthType.PERCENTAGE } : undefined,
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
    children: [new Paragraph({
      alignment: opts.align,
      children: [new TextRun({ text, bold: opts.bold, size: 18, font: 'Calibri' })],
    })],
  });

/**
 * Полоса водяных знаков строкой.
 *
 * Полноценный водяной знак Word рисует через VML в колонтитуле, чего пакет
 * docx не даёт напрямую. Вместо подделки под него — честная светло-серая
 * подложка повторяющимся текстом: она так же помечает документ как наш и
 * так же переживает сохранение в PDF, но не притворяется печатью.
 */
function watermarkBand(mark: string): Paragraph {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 120 },
    children: [new TextRun({ text: Array(3).fill(mark).join('   ·   '),
                             color: 'D9DCE1', size: 16, font: 'Calibri' })],
  });
}

export async function generateQuoteDocx(data: QuoteData): Promise<Buffer> {
  const mark = `BIZSoft · ${data.quoteNo}`;
  const bands = WATERMARK.rows;

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
      spacing: { before: 200, after: 120 },
      children: [new TextRun({ text: 'Коммерческое предложение', bold: true, size: 32, color: DARK, font: 'Calibri' })],
    }),
    line(`№ ${data.quoteNo}`, { size: 9, color: GREY }),
    line(`Исх. № ${data.outgoingNo || '__________'}`, { size: 9, color: GREY }),
    line(`Дата скачивания: ${data.date}`, { size: 9, color: GREY }),
    line(`Действует до ${data.validUntil}`, { size: 9, color: GREY }),
  ];

  const parties = [
    line('Продавец', { bold: true, size: 11 }),
    ...[seller.legalName, seller.address, `ИНН ${seller.inn}, ОГРНИП ${seller.ogrnip}`,
        `Тел.: ${seller.phone}`, `E-mail: ${seller.email}`].map((t) => line(t, { size: 9, color: '374151' })),
    watermarkBand(mark),
    line('Покупатель', { bold: true, size: 11 }),
    ...[data.buyerCompany || '—',
        data.buyerInn ? `ИНН ${data.buyerInn}` : '',
        data.contactName ? `Контакт: ${data.contactName}` : '',
        data.email ? `E-mail: ${data.email}` : '',
        data.phone ? `Тел.: ${data.phone}` : '',
       ].filter(Boolean).map((t) => line(t, { size: 9, color: '374151' })),
  ];

  const table = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 2, color: 'E5E7EB' },
      bottom: { style: BorderStyle.SINGLE, size: 2, color: 'E5E7EB' },
      left: { style: BorderStyle.NONE, size: 0, color: 'auto' },
      right: { style: BorderStyle.NONE, size: 0, color: 'auto' },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: 'E5E7EB' },
      insideVertical: { style: BorderStyle.NONE, size: 0, color: 'auto' },
    },
    rows: [
      new TableRow({
        tableHeader: true,
        children: [
          cell('№', { bold: true, width: 5 }),
          cell('Наименование', { bold: true, width: 45 }),
          cell('Артикул', { bold: true, width: 20 }),
          cell('Кол-во', { bold: true, width: 8, align: AlignmentType.RIGHT }),
          cell('Цена', { bold: true, width: 11, align: AlignmentType.RIGHT }),
          cell('Сумма', { bold: true, width: 11, align: AlignmentType.RIGHT }),
        ],
      }),
      ...data.items.map((it, i) => new TableRow({
        children: [
          cell(String(i + 1)),
          cell(it.name),
          cell(it.sku),
          cell(String(it.qty), { align: AlignmentType.RIGHT }),
          cell(formatRub(it.price), { align: AlignmentType.RIGHT }),
          cell(formatRub(it.sum), { align: AlignmentType.RIGHT }),
        ],
      })),
    ],
  });

  const tail = [
    new Paragraph({ spacing: { before: 200 }, alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: `Итого: ${formatRub(data.total)}`, bold: true, size: 24, color: DARK, font: 'Calibri' })] }),
    line('НДС не облагается (применяется специальный налоговый режим).',
         { size: 8, color: GREY, align: AlignmentType.RIGHT }),
    watermarkBand(mark),
    ...Array.from({ length: Math.max(0, bands - 2) }, () => watermarkBand(mark)),
    line(`${seller.shortName} · ${site.url} · ${seller.phone}`,
         { size: 8, color: GREY, align: AlignmentType.CENTER }),
    line('Форма поставки — в электронном виде. Оплата: 100% аванс.',
         { size: 8, color: GREY, align: AlignmentType.CENTER }),
  ];

  const doc = new Document({
    creator: seller.shortName,
    title: `Коммерческое предложение № ${data.quoteNo}`,
    description: `КП для ${data.buyerCompany || 'клиента'} на ${formatRub(data.total)}`,
    sections: [{ children: [...head, ...parties, table, ...tail] }],
  });
  return Packer.toBuffer(doc) as unknown as Promise<Buffer>;
}
