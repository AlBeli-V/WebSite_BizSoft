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
import { amountPhrase } from './rub-words';
import { salutation } from './salutation';
import type { QuoteItem } from './types';

/** Логотип в шапке. Путь от корня проекта — файл читает драйвер формата. */
export const LOGO_FILE = 'public/brand/bizsoft-logo-lockup.png';

/** Подписант коммерческого предложения. */
export const signer = { name: 'Беляев Алексей', role: 'директор по развитию бизнеса' };

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

/** Оговорка о статусе документа — по распоряжению руководителя 21.08.2026. */
export const PRELIMINARY_NOTE =
  'Настоящий документ является предварительной бюджетной оценкой и требует '
  + 'проверки и коррекции сотрудником.';

export type Align = 'left' | 'right' | 'center';

export type Primitive =
  | { kind: 'text'; x: number; y: number; text: string; bold?: boolean;
      size: number; color: string; width?: number; align?: Align }
  | { kind: 'rect'; x: number; y: number; w: number; h: number; fill: string }
  | { kind: 'line'; x1: number; y1: number; x2: number; y2: number;
      color: string; lineWidth: number }
  | { kind: 'image'; x: number; y: number; w: number; h: number; file: string }
  | { kind: 'bullet'; x: number; y: number; size: number; color: string }
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
  /** Подложка оговорки о статусе документа. */
  noteBg: '#FFF4EF',
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
 * Полная раскладка КП по страницам — по образцу руководителя от 25.06.2026.
 *
 * Порядок частей повторяет деловое письмо: логотип и заголовок, реквизиты
 * сторон, обращение по имени, суть предложения, таблица, сумма прописью,
 * условия, оговорка о статусе документа, подпись.
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
  const LINE = 12;

  const pages: Page[] = [];
  let items: Primitive[] = [...watermarks(mark, markSub)];
  const newPage = () => { pages.push({ items }); items = [...watermarks(mark, markSub)]; };

  const put = (p: Primitive) => { items.push(p); };
  const text = (t: string, x: number, y: number, o: Partial<Extract<Primitive, { kind: 'text' }>> = {}) =>
    put({ kind: 'text', x, y, text: t, size: 9, color: COLOR.body, ...o } as Primitive);

  /** Абзац с переносом. Возвращает Y под последней строкой. */
  const para = (t: string, x: number, y: number, w: number,
                o: { size?: number; bold?: boolean; color?: string; align?: Align } = {}) => {
    const size = o.size ?? 9.5;
    let cur = y;
    for (const part of wrap(t, size, w, measure, o.bold)) {
      text(part, x, cur, { size, bold: o.bold, color: o.color || COLOR.body,
                           width: o.align ? w : undefined, align: o.align });
      cur += size * 1.45;
    }
    return cur;
  };

  // ── Шапка: логотип слева, заголовок справа ─────────────────────────────
  put({ kind: 'image', x: left, y: 40, w: 132, h: 44, file: LOGO_FILE });
  text('КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ', left, 52,
       { bold: true, size: 14, color: COLOR.dark, width, align: 'right' });
  text('предварительная бюджетная оценка', left, 70,
       { size: 8, color: COLOR.muted, width, align: 'right' });

  // ── Контакты продавца слева, номера и даты справа ──────────────────────
  let yL = 92;
  for (const l of [seller.address, `Тел.: ${seller.phone}`, `E-mail: ${seller.email}`]) {
    text(l, left, yL, { size: 8.5, color: COLOR.muted });
    yL += 11;
  }

  // Исходящий номер — это и есть номер КП: держать два разных номера на
  // одном документе значит однажды сослаться на не тот. Распоряжение
  // руководителя 21.08.2026.
  let yR = 92;
  for (const l of [
    `Исх. № ${data.outgoingNo || data.quoteNo}`,
    `Дата скачивания: ${data.date}`,
    `Действует до ${data.validUntil}`,
  ]) {
    text(l, left, yR, { size: 8.5, color: COLOR.muted, width, align: 'right' });
    yR += 11;
  }

  let y = Math.max(yL, yR) + 6;
  put({ kind: 'line', x1: left, y1: y, x2: right, y2: y, color: COLOR.rule, lineWidth: 1 });
  y += 16;

  // ── Кому ───────────────────────────────────────────────────────────────
  text('Кому:', left, y, { bold: true, size: 10, color: COLOR.dark });
  y += 14;
  for (const l of [
    data.buyerCompany || '—',
    data.buyerInn ? `ИНН ${data.buyerInn}` : '',
    data.contactName || '',
    data.email || '',
    data.phone ? `Тел.: ${data.phone}` : '',
  ].filter(Boolean)) {
    for (const part of wrap(l, 9, width * 0.6, measure)) {
      text(part, left, y);
      y += 11;
    }
  }

  // ── Обращение и суть предложения ───────────────────────────────────────
  y += 8;
  text(salutation(data.contactName), left, y,
       { bold: true, size: 11, color: COLOR.dark, width, align: 'center' });
  y += 18;

  const company = data.buyerCompany
    ? `в интересах ${data.buyerCompany}`
    : 'в интересах вашей организации';
  y = para(`Направляем вам предварительное коммерческое предложение ${company} `
           + 'на поставку лицензий на программное обеспечение:', left, y, width);
  y += 8;

  // ── Таблица позиций ────────────────────────────────────────────────────
  // Ширины подобраны под реальные строки, а не на глаз: «5 750 000 ₽» при
  // 9 pt занимает около 64 pt. В прежних 46 сумма наезжала на соседнюю
  // колонку, а в 62 обрезалась о правое поле.
  // Артикул стоит перед наименованием: по нему позиция сверяется со счётом
  // и заказом у вендора, а название читается уже вторым.
  const cols = {
    n: left, nW: 20,
    sku: left + 24, skuW: 96,
    name: left + 126,
    qty: right - 176, qtyW: 34,
    price: right - 140, priceW: 66,
    sum: right - 68, sumW: 68,
  };
  const header = () => {
    put({ kind: 'rect', x: left, y, w: width, h: 24, fill: COLOR.head });
    text('№', cols.n + 4, y + 8, { bold: true, color: COLOR.dark });
    text('Артикул', cols.sku, y + 8, { bold: true, color: COLOR.dark, width: cols.skuW });
    text('Наименование', cols.name, y + 8, { bold: true, color: COLOR.dark });
    text('Кол.', cols.qty, y + 8, { bold: true, color: COLOR.dark, width: cols.qtyW, align: 'right' });
    text('Цена, ₽', cols.price, y + 8, { bold: true, color: COLOR.dark, width: cols.priceW, align: 'right' });
    text('Сумма, ₽', cols.sum, y + 8, { bold: true, color: COLOR.dark, width: cols.sumW, align: 'right' });
    y += 24;
  };
  header();

  const nameW = cols.qty - cols.name - 10;
  data.items.forEach((it, i) => {
    const nameLines = wrap(it.name, 9, nameW, measure);
    const rowH = Math.max(20, nameLines.length * LINE + 8);
    if (y + rowH > PAGE.height - 110) {
      newPage();
      y = 56;
      header();
    }
    text(String(i + 1), cols.n + 4, y + 5, { width: cols.nW });
    text(it.sku, cols.sku, y + 5, { size: 8.5, width: cols.skuW });
    nameLines.forEach((part, k) => text(part, cols.name, y + 5 + k * LINE));
    text(String(it.qty), cols.qty, y + 5, { width: cols.qtyW, align: 'right' });
    text(formatRub(it.price), cols.price, y + 5, { width: cols.priceW, align: 'right' });
    text(formatRub(it.sum), cols.sum, y + 5, { width: cols.sumW, align: 'right' });
    put({ kind: 'line', x1: left, y1: y + rowH, x2: right, y2: y + rowH,
          color: COLOR.rule, lineWidth: 0.5 });
    y += rowH;
  });

  // ── Итог и сумма прописью ──────────────────────────────────────────────
  y += 8;
  text(`Итого: ${formatRub(data.total)}`, left, y,
       { bold: true, size: 12, color: COLOR.dark, width, align: 'right' });
  y += 14;
  y = para('Стоимость предложения указана в российских рублях и составляет '
           + `${amountPhrase(data.total)}. `
           + 'НДС не облагается: применяется специальный налоговый режим.',
           left, y, width, { size: 9 });

  // ── Условия ────────────────────────────────────────────────────────────
  y += 10;
  text('Условия поставки', left, y, { bold: true, size: 10, color: COLOR.dark });
  y += 14;
  for (const c of [
    `Срок действия предложения: до ${data.validUntil}.`,
    'Форма поставки: в электронном виде.',
    'Условия оплаты: 100% аванс, безналичный расчёт в рублях по счёту.',
    'Срок поставки: по согласованию сторон в зависимости от типа ПО, от 1 дня.',
  ]) {
    put({ kind: 'bullet', x: left + 3, y: y + 4, size: 3, color: COLOR.accent });
    y = para(c, left + 14, y, width - 14, { size: 9 }) + 2;
  }

  // ── Оговорка о статусе документа ───────────────────────────────────────
  y += 6;
  const noteH = wrap(PRELIMINARY_NOTE, 9, width - 24, measure).length * 13 + 18;
  put({ kind: 'rect', x: left, y, w: width, h: noteH, fill: COLOR.noteBg });
  put({ kind: 'rect', x: left, y, w: 3, h: noteH, fill: COLOR.accent });
  para(PRELIMINARY_NOTE, left + 14, y + 9, width - 24, { size: 9, color: COLOR.dark });
  y += noteH + 14;

  // ── Подпись и реквизиты ────────────────────────────────────────────────
  // Считаем место под весь хвост сразу: разрывать подпись и банковские
  // реквизиты между страницами нельзя, а переносить их целиком при живом
  // запасе на первой — значит отдать читателю полупустой второй лист.
  // Банковские реквизиты из КП убраны распоряжением руководителя: документ
  // предварительный, платёжные данные выставляются счётом, а лишние
  // реквизиты в гуляющем по почте документе — ненужный риск.
  const TAIL_H = 18 + 15 + 33;
  if (y + TAIL_H > PAGE.height - 66) { newPage(); y = 56; }
  text('С уважением,', left, y, { size: 9.5, color: COLOR.body });
  y += 18;
  text(`${signer.name}, ${signer.role}`, left, y, { bold: true, size: 10, color: COLOR.dark });
  y += 15;
  for (const l of [
    seller.address,
    `Тел.: ${seller.phone}`,
    `E-mail: ${seller.email} · ${site.url.replace(/^https?:\/\//, '')}`,
  ]) {
    text(l, left, y, { size: 8.5, color: COLOR.muted });
    y += 11;
  }

  // ── Колонтитул ─────────────────────────────────────────────────────────
  const footY = PAGE.height - 46;
  put({ kind: 'line', x1: left, y1: footY - 8, x2: right, y2: footY - 8,
        color: COLOR.rule, lineWidth: 0.5 });
  text(`${seller.legalName} · ИНН ${seller.inn} · ОГРНИП ${seller.ogrnip}`,
       left, footY, { size: 7, color: COLOR.muted, width, align: 'center' });
  text(`Юридический адрес: ${seller.address} · ${seller.phone} · ${seller.email}`,
       left, footY + 10, { size: 7, color: COLOR.muted, width, align: 'center' });

  pages.push({ items });
  return pages;
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
