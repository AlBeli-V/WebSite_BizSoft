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
  AlignmentType, BorderStyle, Document, Footer, Header, HeadingLevel, ImageRun,
  LevelFormat, PageNumber, Packer, Paragraph, ShadingType, Table, TableCell,
  TableRow, TextRun, VerticalAlign, WidthType,
} from 'docx';
import { seller, site } from '../config/site';
import { formatRub } from './pricing';
import { amountPhrase, moneyFmt, singleVatRate, vatOfItems } from './rub-words';
import { salutation } from './salutation';
import {
  buyerBlock, continuationLine, footerLines, headMetaLines, HEAD_SUBTITLE, itemSpec,
  MARK_FILE, PRELIMINARY_NOTE, quoteConditions, quoteIntro, sellerContactLines,
  signatureContactLines, signer, VAT_PERCENT, type QuoteData,
} from './quote-layout';
import { logoBuffer } from './pdf-quote';

/**
 * Шрифт документа — тот же Raleway, что на сайте (решение руководителя
 * 15.09.2026). Word подставляет свой шрифт, если Raleway не установлен у
 * получателя; файлы начертаний лежат в public/brand/fonts — их ставят
 * один раз на машину, где документ правят перед отправкой.
 */
const FONT = 'Raleway';
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
                             size: (opts.size || 9) * 2, font: FONT })],
  });

const cell = (text: string, opts: { bold?: boolean; align?: Align; width: number } = { width: 1000 }) =>
  new TableCell({
    width: { size: opts.width, type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
    children: [new Paragraph({
      alignment: opts.align,
      children: [new TextRun({ text, bold: opts.bold, size: 18, font: FONT })],
    })],
  });

/**
 * Поля страницы в твипах (1 см = 567): слева 3 см, справа, сверху и снизу
 * по 1 см — те же, что в макете картинки и PDF (docs/rules/quote-document.md).
 */
const TWIP_CM = 567;
const MARGIN = { left: 3 * TWIP_CM, right: TWIP_CM, top: TWIP_CM, bottom: TWIP_CM };

// Рабочая ширина A4 (11906 твипов) минус поля. Таблица занимает её целиком:
// документ подшивают к договору, и колонка не должна обрываться раньше поля.
const TABLE_W = 11906 - MARGIN.left - MARGIN.right;
// Доли повторяют макет: №, описание, кол-во, цена, сумма.
const COLS = { n: 400, desc: TABLE_W - 400 - 760 - 1560 - 1680, qty: 760, price: 1560, sum: 1680 };

/** Ячейка описания: производитель и название, артикул, договорная фраза. */
const descCell = (spec: { title: string; sku: string; text: string }) =>
  new TableCell({
    width: { size: COLS.desc, type: WidthType.DXA },
    margins: { top: 80, bottom: 80, left: 80, right: 80 },
    children: [
      new Paragraph({ spacing: { after: 20 },
        children: [new TextRun({ text: spec.title, bold: true, size: 18, color: DARK, font: FONT })] }),
      new Paragraph({ spacing: { after: 40 },
        children: [new TextRun({ text: spec.sku, size: 15, color: GREY, font: FONT })] }),
      new Paragraph({
        children: [new TextRun({ text: spec.text, size: 16, color: BODY, font: FONT })] }),
    ],
  });

/**
 * Знак марки в колонтитуле. Высота — две строки реквизитов (≈24 пт),
 * ширина по пропорции файла 290×350. Файла нет — колонтитул обходится без
 * знака: документ важнее картинки.
 */
function markParagraph(): Paragraph[] {
  try {
    const data = logoBuffer(MARK_FILE);
    return [new Paragraph({
      spacing: { after: 0 },
      children: [new ImageRun({
        data, type: 'png',
        transformation: { height: 24, width: Math.round(24 * (290 / 350)) },
      })],
    })];
  } catch (e) {
    console.error('знак для колонтитула Word не прочитан', e);
    return [];
  }
}

export async function generateQuoteDocx(data: QuoteData): Promise<Buffer> {
  const vat = vatOfItems(data.items, VAT_PERCENT);
  const rate = singleVatRate(data.items, VAT_PERCENT);
  const rateLabel = rate === null ? '' : ` ${rate}%`;

  // ── Шапка: марка, заголовок, служебные строки, контакты продавца ───────
  const head = [
    new Paragraph({
      spacing: { after: 40 },
      children: [
        new TextRun({ text: 'BIZ', bold: true, size: 44, color: DARK, font: FONT }),
        new TextRun({ text: 'Soft', bold: true, size: 44, color: ACCENT, font: FONT }),
      ],
    }),
    line(site.tagline, { size: 9, color: GREY }),
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      spacing: { before: 200, after: 60 },
      children: [new TextRun({ text: 'КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ', bold: true, size: 30, color: DARK, font: FONT })],
    }),
    line(HEAD_SUBTITLE, { size: 8.5, color: GREY, after: 120 }),
    ...headMetaLines(data).map((t) => line(t, { size: 9, color: GREY })),
    new Paragraph({ spacing: { after: 60 }, children: [] }),
    ...sellerContactLines().map((t) => line(t, { size: 8.5, color: GREY })),
  ];

  // ── Кому и обращение ───────────────────────────────────────────────────
  // Подпись и заказчик — одна строка, остальное под ней с тем же отступом
  // (композиция руководителя 16.09.2026). Висячий отступ держит «Кому:» у
  // поля, а текст — на общей вертикали.
  const buyer = buyerBlock(data);
  const BUYER_INDENT = 700;
  const addressee = [
    new Paragraph({
      spacing: { before: 160, after: 40 },
      indent: { left: BUYER_INDENT, hanging: BUYER_INDENT },
      children: [
        new TextRun({ text: 'Кому:\t', bold: true, color: DARK, size: 20, font: FONT }),
        new TextRun({ text: buyer.head, color: BODY, size: 18, font: FONT }),
      ],
    }),
    ...buyer.lines.map((t: string) => new Paragraph({
      spacing: { after: 40 },
      indent: { left: BUYER_INDENT },
      children: [new TextRun({ text: t, color: BODY, size: 18, font: FONT })],
    })),
    line(salutation(data.contactName), { bold: true, size: 11, color: DARK,
      align: AlignmentType.CENTER, before: 160, after: 120 }),
    line(quoteIntro(data.buyerCompany), { size: 9.5, after: 120, align: AlignmentType.JUSTIFIED }),
  ];

  // ── Таблица позиций — колонки и порядок как в макете ───────────────────
  const table = new Table({
    width: { size: TABLE_W, type: WidthType.DXA },
    columnWidths: [COLS.n, COLS.desc, COLS.qty, COLS.price, COLS.sum],
    borders: {
      top: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      bottom: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      left: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      right: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: RULE },
      // Разлинованная таблица: документ печатают и подшивают к договору,
      // а без вертикальных границ колонки на бумаге сливаются.
      insideVertical: { style: BorderStyle.SINGLE, size: 1, color: RULE },
    },
    rows: [
      // Шапка: подписи по центру ячейки и по её середине, денежные колонки —
      // в две строки со ставкой налога (решение руководителя 15.09.2026).
      new TableRow({
        tableHeader: true,
        children: ([
          [['№'], COLS.n],
          [['Описание'], COLS.desc],
          [['Кол-во'], COLS.qty],
          [['Цена Руб.', `в т.ч. НДС${rateLabel}`], COLS.price],
          [['Сумма Руб.', `в т.ч. НДС${rateLabel}`], COLS.sum],
        ] as [string[], number][]).map(([lines, w]) => new TableCell({
          width: { size: w, type: WidthType.DXA },
          shading: { type: ShadingType.CLEAR, fill: 'F3F4F6' },
          margins: { top: 60, bottom: 60, left: 80, right: 80 },
          verticalAlign: VerticalAlign.CENTER,
          children: lines.map((t) => new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { after: 0 },
            children: [new TextRun({ text: t, bold: true, size: 16, font: FONT })],
          })),
        })),
      }),
      ...data.items.map((it, i) => new TableRow({
        children: [
          cell(String(i + 1), { width: COLS.n }),
          descCell(itemSpec(it)),
          cell(String(it.qty), { width: COLS.qty, align: AlignmentType.RIGHT }),
          // Копейки: цены в документе сверяют со счётом до копейки, а
          // formatRub округляет до рубля.
          cell(moneyFmt(it.price), { width: COLS.price, align: AlignmentType.RIGHT }),
          cell(moneyFmt(it.sum), { width: COLS.sum, align: AlignmentType.RIGHT }),
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
    ...quoteConditions(data.validUntil, data.date).map((t) => new Paragraph({
      numbering: { reference: 'conditions', level: 0 },
      spacing: { after: 40 },
      children: [new TextRun({ text: t, size: 18, color: BODY, font: FONT })],
    })),
  ];

  // ── Оговорка о статусе на подложке ─────────────────────────────────────
  const note = new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    shading: { type: ShadingType.CLEAR, fill: NOTE_BG },
    spacing: { before: 160, after: 160 },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: ACCENT, space: 4 } },
    children: [new TextRun({ text: PRELIMINARY_NOTE, size: 18, color: DARK, font: FONT })],
  });

  // ── Подпись ────────────────────────────────────────────────────────────
  const signature = [
    line('С уважением,', { size: 9.5, before: 120 }),
    line(`${signer.name}, ${signer.role}`, { bold: true, size: 10, color: DARK }),
    ...signatureContactLines().map((t) => line(t, { size: 8.5, color: GREY })),
  ];

  const [foot1, foot2] = footerLines();

  // Колонтитулы: первый лист без шапки продолжения, остальные — с ней.
  // Word печатает документ сам, но лист без имени документа теряется так же,
  // как лист картинки (docs/rules/quote-document.md).
  // Колонтитул собран таблицей без границ: знак слева, реквизиты от него
  // влево-выключкой, номер листа — к правому полю. Абзацами так не выйдет:
  // в одной строке Word умеет только одно выравнивание.
  const footCell = (children: Paragraph[], width: number, align?: Align) => new TableCell({
    width: { size: width, type: WidthType.DXA },
    margins: { top: 0, bottom: 0, left: 0, right: 0 },
    verticalAlign: VerticalAlign.CENTER,
    borders: {
      top: { style: BorderStyle.NONE, size: 0, color: 'auto' },
      bottom: { style: BorderStyle.NONE, size: 0, color: 'auto' },
      left: { style: BorderStyle.NONE, size: 0, color: 'auto' },
      right: { style: BorderStyle.NONE, size: 0, color: 'auto' },
    },
    children: children.length ? children : [new Paragraph({ alignment: align, children: [] })],
  });

  const markW = 500; // ≈0,9 см — высота двух строк реквизитов
  const pageNoW = 1100;
  const footerChildren = () => [
    new Table({
      width: { size: TABLE_W, type: WidthType.DXA },
      columnWidths: [markW, TABLE_W - markW - pageNoW, pageNoW],
      borders: {
        top: { style: BorderStyle.NONE, size: 0, color: 'auto' },
        bottom: { style: BorderStyle.NONE, size: 0, color: 'auto' },
        left: { style: BorderStyle.NONE, size: 0, color: 'auto' },
        right: { style: BorderStyle.NONE, size: 0, color: 'auto' },
        insideHorizontal: { style: BorderStyle.NONE, size: 0, color: 'auto' },
        insideVertical: { style: BorderStyle.NONE, size: 0, color: 'auto' },
      },
      rows: [new TableRow({
        children: [
          footCell(markParagraph(), markW),
          footCell([
            line(foot1, { size: 7, color: GREY, after: 0 }),
            line(foot2, { size: 7, color: GREY, after: 0 }),
          ], TABLE_W - markW - pageNoW),
          footCell([new Paragraph({
            alignment: AlignmentType.RIGHT,
            spacing: { after: 0 },
            children: [
              new TextRun({ text: 'Лист ', size: 14, color: GREY, font: FONT }),
              new TextRun({ children: [PageNumber.CURRENT], size: 14, color: GREY, font: FONT }),
              new TextRun({ text: ' из ', size: 14, color: GREY, font: FONT }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 14, color: GREY, font: FONT }),
            ],
          })], pageNoW, AlignmentType.RIGHT),
        ],
      })],
    }),
  ];

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
      properties: {
        titlePage: true,
        page: { margin: MARGIN },
      },
      headers: {
        // first — первый лист: шапка документа уже в теле, повторять нечего.
        first: new Header({ children: [] }),
        default: new Header({
          children: [line(continuationLine(data), { size: 8, color: GREY, after: 0 })],
        }),
      },
      footers: {
        first: new Footer({ children: footerChildren() }),
        default: new Footer({ children: footerChildren() }),
      },
      children: [...head, ...addressee, table, ...totals, ...conditions, note, ...signature],
    }],
  });
  return Packer.toBuffer(doc) as unknown as Promise<Buffer>;
}
