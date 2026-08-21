/**
 * Раскладка коммерческого предложения — один макет для всех форматов.
 *
 * Модуль не рисует, а считает: превращает данные КП в список примитивов с
 * координатами. Рисуют их разные драйверы — pdfkit для PDF, SVG+resvg для JPG.
 *
 * Так сделано намеренно. Раньше макет жил внутри генератора PDF, и появление
 * второго формата означало бы вторую копию раскладки: любая правка в одном
 * месте молча расходилась бы со вторым, а заметил бы это клиент, а не мы.
 * Здесь координаты считаются один раз, и оба формата показывают одно и то же.
 */
import { seller, site } from '../config/site';
import { formatRub } from './pricing';
import type { QuoteItem } from './types';

export interface QuoteData {
  quoteNo: string;
  /** Дата скачивания, dd.mm.yyyy — момент, когда клиент получил документ. */
  date: string;
  validUntil: string;
  buyerCompany: string;
  buyerInn: string;
  contactName: string;
  email: string;
  phone?: string;
  items: QuoteItem[];
  total: number;
  /** Исходящий номер. Поле есть всегда, значение проставляется вручную. */
  outgoingNo?: string;
}

export type Align = 'left' | 'right' | 'center';

export type Primitive =
  | { kind: 'text'; x: number; y: number; text: string; bold?: boolean;
      size: number; color: string; width?: number; align?: Align }
  | { kind: 'rect'; x: number; y: number; w: number; h: number; fill: string }
  | { kind: 'line'; x1: number; y1: number; x2: number; y2: number;
      color: string; lineWidth: number }
  | { kind: 'watermark'; x: number; y: number; text: string; sub?: string;
      size: number; subSize: number; w: number; h: number; radius: number;
      stroke: number; dash: number[]; color: string; opacity: number; angle: number };

export interface Page { items: Primitive[] }

/**
 * Измеритель текста: у обоих форматов шрифт один, поэтому и метрики одни.
 *
 * Ширина нужна не меньше высоты. SVG не переносит текст по ширине сам, и
 * пока перенос жил внутри pdfkit, картинка расходилась с PDF: реквизиты
 * продавца уезжали в колонку покупателя. Поэтому переносим здесь, а
 * драйверы получают готовые однострочные примитивы.
 */
export interface Measure {
  height(text: string, size: number, width: number, bold?: boolean): number;
  width(text: string, size: number, bold?: boolean): number;
}

/** Разбить строку по ширине колонки. Длинное слово не рвём — пусть выступит. */
export function wrap(text: string, size: number, max: number, m: Measure, bold?: boolean): string[] {
  if (!text) return [''];
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let cur = '';
  for (const w of words) {
    const next = cur ? `${cur} ${w}` : w;
    if (cur && m.width(next, size, bold) > max) { lines.push(cur); cur = w; } else { cur = next; }
  }
  if (cur) lines.push(cur);
  return lines;
}

export const PAGE = { width: 595.28, height: 841.89, margin: 48 };
export const COLOR = {
  accent: '#FF763C', dark: '#14161A', muted: '#6B7280',
  body: '#374151', rule: '#E5E7EB', head: '#F3F4F6',
  /** Штамп: фирменный оранжевый, как оттиск на образце. */
  stamp: '#FF763C',
};

/**
 * Водяные знаки: сетка 3×4 = 12 штук на каждой странице.
 *
 * Требование руководителя — не менее девяти равномерно по телу страницы.
 * Три колонки на четыре ряда дают двенадцать и ложатся на A4 ровно: страница
 * выше, чем шире, и сетка 3×3 оставила бы разрежённые поля сверху и снизу.
 * Знак идёт под содержимым и с низкой непрозрачностью — он должен мешать
 * присвоить документ, а не читать его.
 */
export const WATERMARK = {
  cols: 3, rows: 4,
  /** Заметен, но не спорит с текстом: читаемость документа важнее приметности знака. */
  opacity: 0.17,
  size: 17, subSize: 7.5,
  w: 148, h: 52, radius: 8, stroke: 2.4,
  angle: -30,
  /**
   * Рваная обводка вместо сплошной.
   *
   * На образце руководителя штамп потёртый — краска легла неровно. Растровую
   * текстуру пришлось бы тащить картинкой в оба формата; неравномерный пунктир
   * даёт тот же эффект оттиска вектором и одинаково выглядит в PDF и в JPG.
   */
  dash: [9, 2, 4, 2, 14, 3, 6, 2],
};

/**
 * Штамп: рамка со скруглёнными углами и надпись внутри — как на образце.
 *
 * Внутри не «DRAFT», а марка продавца и номер КП. Документ действующий:
 * пометка «черновик» на живом предложении обесценила бы его в глазах
 * получателя, а задача знака — не дать присвоить документ, а не отменить его.
 */
export function watermarks(text: string, sub?: string): Primitive[] {
  const out: Primitive[] = [];
  const stepX = PAGE.width / WATERMARK.cols;
  const stepY = PAGE.height / WATERMARK.rows;
  for (let r = 0; r < WATERMARK.rows; r += 1) {
    for (let c = 0; c < WATERMARK.cols; c += 1) {
      out.push({
        kind: 'watermark',
        x: stepX * (c + 0.5),
        y: stepY * (r + 0.5),
        text,
        sub,
        size: WATERMARK.size,
        subSize: WATERMARK.subSize,
        w: WATERMARK.w,
        h: WATERMARK.h,
        radius: WATERMARK.radius,
        stroke: WATERMARK.stroke,
        dash: WATERMARK.dash,
        color: COLOR.stamp,
        opacity: WATERMARK.opacity,
        angle: WATERMARK.angle,
      });
    }
  }
  return out;
}

/** Строки реквизитов продавца и покупателя. */
function partyLines(data: QuoteData) {
  return {
    seller: [
      seller.legalName,
      seller.address,
      `ИНН ${seller.inn}, ОГРНИП ${seller.ogrnip}`,
      `Тел.: ${seller.phone}`,
      `E-mail: ${seller.email}`,
    ],
    buyer: [
      data.buyerCompany || '—',
      data.buyerInn ? `ИНН ${data.buyerInn}` : '',
      data.contactName ? `Контакт: ${data.contactName}` : '',
      data.email ? `E-mail: ${data.email}` : '',
      data.phone ? `Тел.: ${data.phone}` : '',
    ].filter(Boolean),
  };
}

/**
 * Полная раскладка КП по страницам.
 *
 * Водяные знаки кладутся первыми на каждой странице: драйверы рисуют
 * примитивы по порядку, поэтому знак оказывается под текстом, а не поверх.
 */
export function buildQuoteLayout(data: QuoteData, measure: Measure): Page[] {
  const left = PAGE.margin;
  const right = PAGE.width - PAGE.margin;
  const width = right - left;
  const mark = 'BIZSoft';
  const markSub = data.quoteNo;

  const pages: Page[] = [];
  let items: Primitive[] = [...watermarks(mark, markSub)];
  const newPage = () => { pages.push({ items }); items = [...watermarks(mark, markSub)]; };

  // ── Шапка ──
  items.push({ kind: 'text', x: left, y: 48, text: 'BIZ', bold: true, size: 22, color: COLOR.dark });
  items.push({ kind: 'text', x: left + 44, y: 48, text: 'Soft', bold: true, size: 22, color: COLOR.accent });
  items.push({ kind: 'text', x: left, y: 74, text: site.tagline, size: 9, color: COLOR.muted });

  items.push({ kind: 'text', x: left, y: 48, text: 'Коммерческое предложение',
               bold: true, size: 16, color: COLOR.dark, width, align: 'right' });

  // Исходящий номер — поле есть всегда, значение проставляется вручную.
  // Пустая линия вместо пропуска: документ без места под номер нечем
  // зарегистрировать, а подписанный задним числом номер спорен.
  const headRight = [
    `№ ${data.quoteNo}`,
    `Исх. № ${data.outgoingNo || '__________'}`,
    `Дата скачивания: ${data.date}`,
    `Действует до ${data.validUntil}`,
  ];
  headRight.forEach((t, i) => items.push({
    kind: 'text', x: left, y: 72 + i * 12, text: t,
    size: 9, color: COLOR.muted, width, align: 'right',
  }));

  items.push({ kind: 'line', x1: left, y1: 124, x2: right, y2: 124, color: COLOR.rule, lineWidth: 1 });

  // ── Продавец / Покупатель ──
  let y = 140;
  items.push({ kind: 'text', x: left, y, text: 'Продавец', bold: true, size: 10, color: COLOR.dark });
  items.push({ kind: 'text', x: left + width / 2 + 10, y, text: 'Покупатель', bold: true, size: 10, color: COLOR.dark });
  y += 16;

  const colW = width / 2 - 10;
  const { seller: sLines, buyer: bLines } = partyLines(data);
  const LINE = 12;
  let yL = y; let yR = y;
  for (const l of sLines) {
    for (const part of wrap(l, 9, colW, measure)) {
      items.push({ kind: 'text', x: left, y: yL, text: part, size: 9, color: COLOR.body });
      yL += LINE;
    }
  }
  for (const l of bLines) {
    for (const part of wrap(l, 9, colW, measure)) {
      items.push({ kind: 'text', x: left + width / 2 + 10, y: yR, text: part, size: 9, color: COLOR.body });
      yR += LINE;
    }
  }
  y = Math.max(yL, yR) + 14;

  // ── Таблица позиций ──
  const cols = {
    n: left, name: left + 26, sku: left + width - 230,
    qty: left + width - 150, price: left + width - 110, sum: left + width - 60,
  };
  const header = () => {
    items.push({ kind: 'rect', x: left, y, w: width, h: 22, fill: COLOR.head });
    items.push({ kind: 'text', x: cols.n + 4, y: y + 7, text: '№', bold: true, size: 9, color: COLOR.dark });
    items.push({ kind: 'text', x: cols.name, y: y + 7, text: 'Наименование', bold: true, size: 9, color: COLOR.dark });
    items.push({ kind: 'text', x: cols.sku, y: y + 7, text: 'Артикул', bold: true, size: 9, color: COLOR.dark, width: 76 });
    items.push({ kind: 'text', x: cols.qty, y: y + 7, text: 'Кол-во', bold: true, size: 9, color: COLOR.dark, width: 38, align: 'right' });
    items.push({ kind: 'text', x: cols.price, y: y + 7, text: 'Цена', bold: true, size: 9, color: COLOR.dark, width: 46, align: 'right' });
    items.push({ kind: 'text', x: cols.sum, y: y + 7, text: 'Сумма', bold: true, size: 9, color: COLOR.dark, width: 56, align: 'right' });
    y += 22;
  };
  header();

  const nameW = cols.sku - cols.name - 8;
  data.items.forEach((it, i) => {
    const nameLines = wrap(it.name, 9, nameW, measure);
    const rowH = Math.max(20, nameLines.length * LINE + 8);
    if (y + rowH > PAGE.height - 120) {
      newPage();
      y = 48;
      header();
    }
    items.push({ kind: 'text', x: cols.n + 4, y: y + 4, text: String(i + 1), size: 9, color: COLOR.body, width: 20 });
    nameLines.forEach((part, k) => items.push({
      kind: 'text', x: cols.name, y: y + 4 + k * LINE, text: part, size: 9, color: COLOR.body,
    }));
    items.push({ kind: 'text', x: cols.sku, y: y + 4, text: it.sku, size: 9, color: COLOR.body, width: 76 });
    items.push({ kind: 'text', x: cols.qty, y: y + 4, text: String(it.qty), size: 9, color: COLOR.body, width: 38, align: 'right' });
    items.push({ kind: 'text', x: cols.price, y: y + 4, text: formatRub(it.price), size: 9, color: COLOR.body, width: 46, align: 'right' });
    items.push({ kind: 'text', x: cols.sum, y: y + 4, text: formatRub(it.sum), size: 9, color: COLOR.body, width: 56, align: 'right' });
    items.push({ kind: 'line', x1: left, y1: y + rowH, x2: right, y2: y + rowH, color: COLOR.rule, lineWidth: 0.5 });
    y += rowH;
  });

  // ── Итог ──
  y += 10;
  items.push({ kind: 'text', x: left, y, text: `Итого: ${formatRub(data.total)}`,
               bold: true, size: 12, color: COLOR.dark, width, align: 'right' });
  items.push({ kind: 'text', x: left, y: y + 18, width, align: 'right', size: 8, color: COLOR.muted,
               text: 'НДС не облагается (применяется специальный налоговый режим).' });

  // ── Реквизиты для оплаты ──
  y += 44;
  items.push({ kind: 'text', x: left, y, text: 'Реквизиты для оплаты по счёту', bold: true, size: 10, color: COLOR.dark });
  y += 16;
  bankLines().forEach((l, i) => items.push({
    kind: 'text', x: left, y: y + i * 12, text: l, size: 9, color: COLOR.body,
  }));

  // ── Подвал ──
  items.push({ kind: 'text', x: left, y: PAGE.height - 82, width, align: 'center', size: 8, color: COLOR.muted,
               text: `${seller.shortName} · ${site.url} · ${seller.phone}` });
  items.push({ kind: 'text', x: left, y: PAGE.height - 70, width, align: 'center', size: 8, color: COLOR.muted,
               text: 'Работаем по договору, оплата по счёту, закрывающие документы через ЭДО.' });

  pages.push({ items });
  return pages;
}

export function bankLines(): string[] {
  return [
    `Получатель: ${seller.legalName}`,
    `ИНН ${seller.inn}`,
    `Банк: ${seller.bank.bankName}`,
    `Р/с ${seller.bank.account}`,
    `К/с ${seller.bank.corrAccount}`,
    `БИК ${seller.bank.bik}`,
  ];
}

/** Номер КП вида BZ-YYYYMMDD-XXXX. */
export function buildQuoteNo(now: Date, suffix: string): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `BZ-${y}${m}${d}-${suffix}`;
}

/** dd.mm.yyyy */
export function formatDateRu(d: Date): string {
  return `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}.${d.getFullYear()}`;
}

export function addDays(d: Date, days: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + days);
  return r;
}
