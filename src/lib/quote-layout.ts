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
import { amountPhrase, moneyFmt, numberWords, pluralForm, singleVatRate, vatOfItems } from './rub-words';
import { salutation } from './salutation';
import { specLine } from './spec-line';
import type { QuoteItem } from './types';

/** Логотип в шапке. Путь от корня проекта — файл читает драйвер формата. */
export const LOGO_FILE = 'public/brand/bizsoft-logo-lockup.png';

/**
 * Знак в колонтитуле — марка без надписи (решение руководителя 15.09.2026).
 * Высота равна двум строкам реквизитов, ширина — по пропорции файла
 * (290×350): знак не растягивается.
 */
export const MARK_FILE = 'public/brand/bizsoft-mark-transparent.png';
export const FOOT = {
  /** Высота знака и всего блока реквизитов, пт. */
  h: 20,
  /** Ширина знака по пропорции 290×350. */
  w: 20 * (290 / 350),
  /** Просвет между знаком и текстом. */
  gap: 8,
  /** Кегль строк реквизитов и интерлиньяж. */
  size: 7,
  line: 10,
};

/** Y линии над колонтитулом: сам колонтитул стоит на нижнем поле. */
export function footRuleY(): number {
  return PAGE.height - PAGE.margin.bottom - FOOT.h - 8;
}

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

/**
 * Ставка НДС в ценах предложения.
 *
 * Цены в таблице указаны с включённым налогом, поэтому итог подписывается
 * «в т.ч.», а не «плюс»: разница между этими двумя словами — пять процентов
 * суммы договора.
 */
export const VAT_PERCENT = 5;

/**
 * Оговорка о статусе документа — распоряжение руководителя 28.08.2026
 * (заменяет формулировку от 21.08.2026 «требует проверки и коррекции
 * сотрудником»: она говорила клиенту, что документ может быть неверным).
 *
 * «Не является публичной офертой» — обязательная часть: документ с ценами
 * и сроком действия без этой фразы рискует быть прочитан как оферта.
 */
export const PRELIMINARY_NOTE =
  'Предложение носит предварительный характер и не является публичной '
  + 'офертой. Окончательная стоимость, скидки за объём и индивидуальные '
  + 'условия оплаты и поставки согласовываются сторонами в ходе переговоров.';

/** Подзаголовок под названием документа в шапке. */
export const HEAD_SUBTITLE = 'предварительное предложение · не является публичной офертой';

export type Align = 'left' | 'right' | 'center';

export type Primitive =
  | { kind: 'text'; x: number; y: number; text: string; bold?: boolean;
      size: number; color: string; width?: number; align?: Align }
  | { kind: 'rect'; x: number; y: number; w: number; h: number; fill: string }
  | { kind: 'line'; x1: number; y1: number; x2: number; y2: number;
      color: string; lineWidth: number }
  | { kind: 'image'; x: number; y: number; w: number; h: number; file: string }
  | { kind: 'bullet'; x: number; y: number; size: number; color: string }
  /**
   * Боковая полоса-знак: подложка во всю высоту листа, вдоль неё снизу
   * вверх — надпись прописными, на концах — замок. Рисуется под текстом.
   */
  | { kind: 'band'; x: number; y: number; w: number; h: number;
      fill: string; fillOpacity: number; edge: string;
      text: string; textColor: string; textOpacity: number;
      size: number; spacing: number; lock: number };

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

/** Пункт на сантиметр: поля документа руководитель задаёт в сантиметрах. */
export const CM = 28.3465;

/**
 * Поля страницы — решение руководителя 15.09.2026: слева 3 см под подшивку,
 * справа, сверху и снизу по 1 см. Всё содержимое, включая таблицу и
 * колонтитул, живёт внутри этого поля.
 */
export const PAGE = {
  width: 595.28,
  height: 841.89,
  margin: { left: 3 * CM, right: CM, top: CM, bottom: CM },
};
export const COLOR = {
  accent: '#FF763C', dark: '#14161A', muted: '#6B7280',
  body: '#374151', rule: '#E5E7EB', head: '#F3F4F6',
  /** Подложка оговорки о статусе документа. */
  noteBg: '#FFF4EF',
  /** Знак статуса: красный — решение руководителя 28.08.2026. */
  stamp: '#C81E1E',
  /** Полоса «КОНФИДЕНЦИАЛЬНО»: деловой синий, не спорит с фирменным оранжевым. */
  confidential: '#1D4ED8',
};

/**
 * Водяные знаки — две боковые полосы (референс руководителя 15.09.2026,
 * заменяет шесть штампов сеткой 2×3 от 28.08.2026).
 *
 * Слева «КОНФИДЕНЦИАЛЬНО», справа «ПРЕДВАРИТЕЛЬНОЕ КОММЕРЧЕСКОЕ
 * ПРЕДЛОЖЕНИЕ». Полосы идут во всю высоту листа и упираются в его края:
 * распечатать документ и выдать за официальную переписку, отрезав знак,
 * нельзя — край без полосы виден сразу. При этом они бледные и стоят в
 * полях: правая заходит на границу полосы набора всего на несколько
 * пунктов, и текст под ней читается.
 *
 * Прежние штампы сняты целиком: шесть оттисков поверх таблицы мешали
 * читать спецификацию, а полоса решает ту же задачу, не заходя в текст.
 */
export const BAND = {
  /** Ширина полосы и отступ от края листа, пт. Правая полоса заходит на
   *  границу полосы набора примерно на полтора пункта: знак пересекает
   *  край документа, но не накрывает цифры итога. */
  w: 26,
  inset: 4,
  /** Подложка едва заметна, надпись читается — знак не спорит с текстом. */
  fillOpacity: 0.12,
  textOpacity: 0.55,
  size: 10.5,
  /** Разрядка: надпись во всю высоту листа держится ритмом, а не кеглем. */
  spacing: 2.2,
  /** Сторона значка замка на концах полосы. */
  lock: 13,
};

export const BAND_LEFT_TEXT = 'КОНФИДЕНЦИАЛЬНО';
export const BAND_RIGHT_TEXT = 'ПРЕДВАРИТЕЛЬНОЕ КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ';

/** Две полосы листа: левая — синяя, правая — красная, обе под содержимым. */
export function watermarks(): Primitive[] {
  const band = (x: number, color: string, text: string): Primitive => ({
    kind: 'band',
    x,
    y: 0,
    w: BAND.w,
    h: PAGE.height,
    fill: color,
    fillOpacity: BAND.fillOpacity,
    edge: color,
    text,
    textColor: color,
    textOpacity: BAND.textOpacity,
    size: BAND.size,
    spacing: BAND.spacing,
    lock: BAND.lock,
  });
  return [
    band(BAND.inset, COLOR.confidential, BAND_LEFT_TEXT),
    band(PAGE.width - BAND.inset - BAND.w, COLOR.stamp, BAND_RIGHT_TEXT),
  ];
}

/**
 * Общее содержимое КП для всех форматов.
 *
 * Word-версия верстается другой библиотекой и не может рисовать по
 * координатам макета, но обязана совпадать с ним по содержанию. Поэтому
 * каждый текстовый блок существует один раз — здесь, — а форматы только
 * раскладывают его; расхождение содержимого становится невозможным по
 * построению, и это закрепляет tests/quote-docx.test.ts.
 */

/** Контактные строки продавца в шапке и подписи. */
export function sellerContactLines(): string[] {
  return [seller.address, `Тел.: ${seller.phone}`, `E-mail: ${seller.email}`];
}

/** Контакты в блоке подписи (те же, плюс адрес сайта). */
export function signatureContactLines(): string[] {
  return [
    seller.address,
    `Тел.: ${seller.phone}`,
    `E-mail: ${seller.email} · ${site.url.replace(/^https?:\/\//, '')}`,
  ];
}

/** Служебные строки: исходящий номер, дата, срок действия. */
export function headMetaLines(data: QuoteData): string[] {
  // Исходящий номер — это и есть номер КП: держать два разных номера на
  // одном документе значит однажды сослаться на не тот. Распоряжение
  // руководителя 21.08.2026.
  return [
    `Исх. № ${data.outgoingNo || data.quoteNo}`,
    `Дата скачивания: ${data.date}`,
    `Действует до ${data.validUntil}`,
  ];
}

/** Блок «Кому»: реквизиты покупателя из формы. */
export function buyerLines(data: QuoteData): string[] {
  return [
    data.buyerCompany || '—',
    data.buyerInn ? `ИНН ${data.buyerInn}` : '',
    data.contactName || '',
    data.email || '',
    data.phone ? `Тел.: ${data.phone}` : '',
  ].filter(Boolean);
}

/**
 * Вводная фраза под обращением (формулировка руководителя 15.09.2026).
 *
 * «Поставка лицензий» ушла: мы не поставляем лицензии, а оказываем услуги по
 * обеспечению доступа — к ПО, к web-сервисам и к балансам API. Предмет
 * предложения обязан совпадать с предметом договора и с описанием позиций
 * в таблице (`docs/rules/spec-line.md`), иначе шапка обещает одно, а
 * спецификация называет другое.
 */
export function quoteIntro(buyerCompany: string): string {
  const company = buyerCompany ? `в интересах ${buyerCompany}` : 'в интересах вашей организации';
  return `Направляем Вам предварительное коммерческое предложение ${company} `
    + 'на оказание комплексных услуг по обеспечению доступа к программному обеспечению (ПО), '
    + 'web-сервисам и/или пополнению балансов API токенов. Детальная спецификация состава '
    + 'услуг отражена в таблице настоящего предложения:';
}

/**
 * Описание позиции для документа — то же, что в спецификации на сайте
 * (`docs/rules/spec-line.md`): юридическое название производителя и
 * название, артикул, договорная фраза.
 *
 * Собирает один и тот же `specLine()`: покупатель видит на странице ровно
 * тот текст, который придёт ему письмом, а менеджер переносит ячейку в
 * спецификацию к договору целиком. Сноска об аренде почты сюда не
 * попадает — она пояснение на странице, а не строка документа
 * (`docs/rules/email-rent.md`).
 */
export interface ItemSpec { title: string; sku: string; text: string }

export function itemSpec(it: QuoteItem): ItemSpec {
  const line = specLine({
    sku: it.sku,
    name: it.name,
    vendor: it.vendor || '',
    emailRent: Boolean(it.email_rent),
  });
  return { title: line.title, sku: `Артикул: ${it.sku}`, text: line.text };
}

/** Условия поставки — список под таблицей. */
export function quoteConditions(validUntil: string, issued: string): string[] {
  return [
    validityLine(issued, validUntil),
    'Форма поставки: в электронном виде.',
    'Условия оплаты: 100% аванс, безналичный расчёт в рублях по счёту.',
    'Срок поставки: по согласованию сторон в зависимости от типа ПО, от 1 дня.',
    // Цены каталога привязаны к курсу ЦБ (docs/rules/catalog.md): между
    // выпуском предложения и оплатой счёта курс двигается, и оговорка о
    // пересчёте должна стоять в самом предложении, а не всплывать при счёте.
    `Стоимость: рублёвый эквивалент стоимости рассчитан по курсу ЦБ РФ на дату ${issued} `
    + '(дата формирования КП). В случае изменения курса валют более чем на 5% на дату '
    + 'заключения Договора и оплаты Счёта стоимость корректируется на дельту курсовой '
    + 'разницы — как в большую, так и в меньшую сторону.',
  ];
}

/** Дата вида dd.mm.yyyy → UTC-полночь; null — строка не распознана. */
function parseRuDate(s: string): Date | null {
  const m = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(s.trim());
  if (!m) return null;
  const d = new Date(Date.UTC(Number(m[3]), Number(m[2]) - 1, Number(m[1])));
  return Number.isNaN(d.getTime()) ? null : d;
}

/**
 * Рабочих дней от выпуска предложения до последнего дня действия.
 *
 * Считаются дни после даты выпуска по дату окончания включительно, суббота
 * и воскресенье не в счёт. Праздники не учитываются: производственный
 * календарь в проекте не ведётся, и подставлять его «примерно» значило бы
 * назвать клиенту срок, которого нет.
 */
export function workdaysBetween(issued: string, validUntil: string): number | null {
  const from = parseRuDate(issued);
  const to = parseRuDate(validUntil);
  if (!from || !to || to <= from) return null;
  let count = 0;
  const cur = new Date(from);
  while (cur < to) {
    cur.setUTCDate(cur.getUTCDate() + 1);
    const day = cur.getUTCDay();
    if (day !== 0 && day !== 6) count += 1;
  }
  return count;
}

/** «Срок действия предложения: 5 (пять) рабочих дней до 22.09.2026.» */
export function validityLine(issued: string, validUntil: string): string {
  const days = workdaysBetween(issued, validUntil);
  // Без распознанных дат срок называется одной датой: соврать о числе
  // рабочих дней хуже, чем не назвать его.
  if (days === null || days === 0) return `Срок действия предложения: до ${validUntil}.`;
  const word = pluralForm(days, ['рабочий день', 'рабочих дня', 'рабочих дней']);
  return `Срок действия предложения: ${days} (${numberWords(days)}) ${word} до ${validUntil}.`;
}

/**
 * Шапка листов продолжения: распечатанный второй лист обязан называть
 * документ, к которому относится. Текст один на все форматы.
 */
export function continuationLine(data: QuoteData): string {
  return `Коммерческое предложение № ${data.outgoingNo || data.quoteNo} от ${data.date} — продолжение`;
}

/** Две строки колонтитула с реквизитами продавца. */
export function footerLines(): [string, string] {
  return [
    `${seller.legalName} · ИНН ${seller.inn} · ОГРНИП ${seller.ogrnip}`,
    `Юридический адрес: ${seller.address} · ${seller.phone} · ${seller.email}`,
  ];
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
  const left = PAGE.margin.left;
  const right = PAGE.width - PAGE.margin.right;
  const top = PAGE.margin.top;
  const width = right - left;
  const LINE = 12;

  const pages: Page[] = [];
  let items: Primitive[] = [...watermarks()];
  const newPage = () => { pages.push({ items }); items = [...watermarks()]; };

  const put = (p: Primitive) => { items.push(p); };
  const text = (t: string, x: number, y: number, o: Partial<Extract<Primitive, { kind: 'text' }>> = {}) =>
    put({ kind: 'text', x, y, text: t, size: 9, color: COLOR.body, ...o } as Primitive);

  /**
   * Абзац с переносом. Возвращает Y под последней строкой.
   *
   * `justify` — выключка по ширине: строка растягивается до правого поля
   * пробелами между словами (последняя строка абзаца остаётся как есть).
   * Делается здесь, а не драйвером: SVG выключки не умеет вовсе, а мы и так
   * переносим текст сами — иначе картинка разошлась бы с PDF.
   */
  const para = (t: string, x: number, y: number, w: number,
                o: { size?: number; bold?: boolean; color?: string; align?: Align;
                     justify?: boolean } = {}) => {
    const size = o.size ?? 9.5;
    const color = o.color || COLOR.body;
    const lines = wrap(t, size, w, measure, o.bold);
    let cur = y;
    lines.forEach((part, i) => {
      const last = i === lines.length - 1;
      const words = part.split(' ').filter(Boolean);
      if (o.justify && !last && words.length > 1) {
        const wordsW = words.reduce((acc, word) => acc + measure.width(word, size, o.bold), 0);
        const gap = (w - wordsW) / (words.length - 1);
        let wx = x;
        for (const word of words) {
          text(word, wx, cur, { size, bold: o.bold, color });
          wx += measure.width(word, size, o.bold) + gap;
        }
      } else {
        text(part, x, cur, { size, bold: o.bold, color,
                             width: o.align ? w : undefined, align: o.align });
      }
      cur += size * 1.45;
    });
    return cur;
  };

  // ── Шапка: логотип слева, заголовок справа ─────────────────────────────
  // Всё считается от верхнего поля: сдвинулось поле — сдвинулась шапка.
  put({ kind: 'image', x: left, y: top, w: 132, h: 44, file: LOGO_FILE });
  text('КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ', left, top + 12,
       { bold: true, size: 14, color: COLOR.dark, width, align: 'right' });
  text(HEAD_SUBTITLE, left, top + 30,
       { size: 8, color: COLOR.muted, width, align: 'right' });

  // ── Контакты продавца слева, номера и даты справа ──────────────────────
  let yL = top + 52;
  for (const l of sellerContactLines()) {
    text(l, left, yL, { size: 8.5, color: COLOR.muted });
    yL += 11;
  }

  let yR = top + 52;
  for (const l of headMetaLines(data)) {
    text(l, left, yR, { size: 8.5, color: COLOR.muted, width, align: 'right' });
    yR += 11;
  }

  let y = Math.max(yL, yR) + 6;
  put({ kind: 'line', x1: left, y1: y, x2: right, y2: y, color: COLOR.rule, lineWidth: 1 });
  y += 16;

  // ── Кому ───────────────────────────────────────────────────────────────
  text('Кому:', left, y, { bold: true, size: 10, color: COLOR.dark });
  y += 14;
  for (const l of buyerLines(data)) {
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

  y = para(quoteIntro(data.buyerCompany), left, y, width, { justify: true });
  y += 8;

  // Ставка налога считается до таблицы: она стоит и в её шапке, и в итогах.
  // Ставки разные — числа в заголовке нет: там стояла бы ставка, по которой
  // посчитана только часть суммы.
  const vat = vatOfItems(data.items, VAT_PERCENT);
  const rate = singleVatRate(data.items, VAT_PERCENT);
  const rateLabel = rate === null ? '' : ` ${rate}%`;
  const headRate = rateLabel;

  // ── Таблица позиций ────────────────────────────────────────────────────
  // Структура повторяет спецификацию на сайте (docs/rules/spec-line.md):
  // описание позиции целиком (производитель и название, артикул, договорная
  // фраза), количество, цена и сумма. Отдельной колонки артикула нет — он
  // стоит внутри описания, как в предмете договора; прежняя колонка в 96 pt
  // не вмещала системный артикул, и он наезжал на название.
  //
  // Документ печатают и подшивают к договору, поэтому таблица разлинована:
  // у каждой ячейки есть границы, шапка повторяется на каждом листе, а
  // строка не разрывается между листами.
  // Границы ячеек считаются от правого поля, а текст ставится внутрь с
  // отступом: раньше колонки задавались точками старта, и строка описания
  // заходила под соседнюю границу, а «Цена, ₽» упиралась в линию.
  const B = {
    n0: left,
    n1: left + 20,
    desc1: right - 200,
    qty1: right - 162,
    price1: right - 84,
    sum1: right,
  };
  const CELL = 5;
  const cols = {
    n: B.n0, nW: B.n1 - B.n0,
    desc: B.n1 + CELL, descW: B.desc1 - B.n1 - CELL * 2,
    qty: B.desc1 + CELL, qtyW: B.qty1 - B.desc1 - CELL * 2,
    price: B.qty1 + CELL, priceW: B.price1 - B.qty1 - CELL * 2,
    sum: B.price1 + CELL, sumW: B.sum1 - B.price1 - CELL * 2,
  };
  const PAD = 5;
  // Нижняя граница содержимого: под ней живёт колонтитул со знаком, а под
  // ним — нижнее поле страницы.
  const BOTTOM = footRuleY() - 10;

  /** Границы строки таблицы: вертикали по колонкам и линия снизу. */
  const gridRow = (rowTop: number, h: number) => {
    for (const x of [B.n0, B.n1, B.desc1, B.qty1, B.price1, B.sum1]) {
      put({ kind: 'line', x1: x, y1: rowTop, x2: x, y2: rowTop + h, color: COLOR.rule, lineWidth: 0.5 });
    }
    put({ kind: 'line', x1: left, y1: rowTop + h, x2: right, y2: rowTop + h, color: COLOR.rule, lineWidth: 0.5 });
  };

  // Шапка таблицы: все подписи по центру ячейки и по её середине, денежные
  // колонки — в две строки (решение руководителя 15.09.2026). Ставка налога
  // названа прямо в заголовке: цена в таблице указана с НДС, и читатель не
  // должен искать это в примечании под итогом.
  const HEAD_SIZE = 8;
  const HEAD_LINE = 9.5;
  const HEAD_H = 26;
  const headCells: [string[], number, number][] = [
    [['№'], cols.n, cols.nW],
    [['Описание'], cols.desc, cols.descW],
    [['Кол-во'], cols.qty, cols.qtyW],
    [[`Цена Руб.`, `в т.ч. НДС${headRate}`], cols.price, cols.priceW],
    [[`Сумма Руб.`, `в т.ч. НДС${headRate}`], cols.sum, cols.sumW],
  ];
  const header = () => {
    put({ kind: 'rect', x: left, y, w: width, h: HEAD_H, fill: COLOR.head });
    for (const [lines, x, w] of headCells) {
      const startY = y + (HEAD_H - lines.length * HEAD_LINE) / 2 + 1;
      lines.forEach((part, i) => {
        text(part, x, startY + i * HEAD_LINE,
             { bold: true, size: HEAD_SIZE, color: COLOR.dark, width: w, align: 'center' });
      });
    }
    gridRow(y, HEAD_H);
    y += HEAD_H;
  };
  header();

  data.items.forEach((it, i) => {
    const spec = itemSpec(it);
    const titleLines = wrap(spec.title, 9, cols.descW, measure, true);
    const textLines = wrap(spec.text, 8, cols.descW, measure);
    const rowH = PAD * 2 + titleLines.length * 11.5 + 10.5 + textLines.length * 10.5;

    // Строка не разрывается между листами: переносим её целиком и повторяем
    // шапку — распечатанный лист обязан читаться сам по себе.
    if (y + rowH > BOTTOM) {
      newPage();
      y = top + 28;
      header();
    }
    let ty = y + PAD;
    titleLines.forEach((part) => { text(part, cols.desc, ty, { size: 9, bold: true, color: COLOR.dark }); ty += 11.5; });
    text(spec.sku, cols.desc, ty, { size: 7.5, color: COLOR.muted });
    ty += 10.5;
    textLines.forEach((part) => { text(part, cols.desc, ty, { size: 8, color: COLOR.body }); ty += 10.5; });

    text(String(i + 1), cols.n, y + PAD, { size: 8.5, width: cols.nW, align: 'center' });
    text(String(it.qty), cols.qty, y + PAD, { size: 9, width: cols.qtyW, align: 'right' });
    text(moneyFmt(it.price), cols.price, y + PAD, { size: 9, width: cols.priceW, align: 'right' });
    text(moneyFmt(it.sum), cols.sum, y + PAD, { size: 9, bold: true, width: cols.sumW, align: 'right' });
    gridRow(y, rowH);
    y += rowH;
  });

  // ── Итог и сумма прописью ──────────────────────────────────────────────
  // Цены в таблице указаны с НДС, поэтому итог называется «в т.ч.», а налог
  // выделяется отдельной строкой: покупателю нужно видеть сумму вычета, а не
  // выводить её самому.
  //
  // Ставка берётся у позиций, а не одна на документ: она задаётся у товара.
  // Если ставки разные, единой в заголовке не пишем — там стояла бы ставка,
  // по которой посчитана только часть суммы.
  // Итог, налог и сумма прописью — один смысловой блок: разорвать его
  // между листами значит отправить лист с суммой без расшифровки.
  const totalsH = 16 + 16 + wrap(`Стоимость предложения: ${amountPhrase(data.total)}, в т.ч. НДС`
    + `${rateLabel} ${amountPhrase(vat)}.`, 9, width, measure).length * 13 + 8;
  if (y + totalsH > BOTTOM) { newPage(); y = top + 28; }
  y += 8;
  // Копейки здесь обязательны: formatRub округляет до рубля, и строка НДС
  // разошлась бы с суммой прописью — а её сверяют до копейки.
  text(`ИТОГО в т.ч. НДС${rateLabel}: ${moneyFmt(data.total)} ₽`, left, y,
       { bold: true, size: 12, color: COLOR.dark, width, align: 'right' });
  y += 16;
  text(`НДС${rateLabel}: ${moneyFmt(vat)} ₽`, left, y,
       { bold: true, size: 10, color: COLOR.dark, width, align: 'right' });
  y += 16;
  y = para(`Стоимость предложения: ${amountPhrase(data.total)}, в т.ч. НДС`
           + `${rateLabel} ${amountPhrase(vat)}.`,
           left, y, width, { size: 9, justify: true });

  // ── Условия ────────────────────────────────────────────────────────────
  y += 10;
  const condH = 14 + quoteConditions(data.validUntil, data.date)
    .reduce((h, c) => h + wrap(c, 9, width - 14, measure).length * 13 + 2, 0);
  if (y + condH > BOTTOM) { newPage(); y = top + 28; }
  text('Условия поставки', left, y, { bold: true, size: 10, color: COLOR.dark });
  y += 14;
  for (const c of quoteConditions(data.validUntil, data.date)) {
    put({ kind: 'bullet', x: left + 3, y: y + 4, size: 3, color: COLOR.accent });
    y = para(c, left + 14, y, width - 14, { size: 9 }) + 2;
  }

  // ── Оговорка о статусе документа ───────────────────────────────────────
  y += 6;
  const noteH = wrap(PRELIMINARY_NOTE, 9, width - 24, measure).length * 13 + 18;
  if (y + noteH > BOTTOM) { newPage(); y = top + 28; }
  put({ kind: 'rect', x: left, y, w: width, h: noteH, fill: COLOR.noteBg });
  put({ kind: 'rect', x: left, y, w: 3, h: noteH, fill: COLOR.accent });
  para(PRELIMINARY_NOTE, left + 14, y + 9, width - 24, { size: 9, color: COLOR.dark, justify: true });
  y += noteH + 10;

  // ── Подпись и реквизиты ────────────────────────────────────────────────
  // Считаем место под весь хвост сразу: разрывать подпись и банковские
  // реквизиты между страницами нельзя, а переносить их целиком при живом
  // запасе на первой — значит отдать читателю полупустой второй лист.
  // Банковские реквизиты из КП убраны распоряжением руководителя: документ
  // предварительный, платёжные данные выставляются счётом, а лишние
  // реквизиты в гуляющем по почте документе — ненужный риск.
  // У хвоста свой предел: он не строка таблицы, ему достаточно поместиться
  // над линией колонтитула. С общим пределом BOTTOM подпись уезжала на
  // отдельный лист из-за девяти пунктов — и получался лист с одной подписью.
  const TAIL_H = 18 + 15 + 33;
  if (y + TAIL_H > footRuleY() - 4) { newPage(); y = top + 28; }
  text('С уважением,', left, y, { size: 9.5, color: COLOR.body });
  y += 18;
  text(`${signer.name}, ${signer.role}`, left, y, { bold: true, size: 10, color: COLOR.dark });
  y += 15;
  for (const l of signatureContactLines()) {
    text(l, left, y, { size: 8.5, color: COLOR.muted });
    y += 11;
  }

  pages.push({ items });

  // ── Колонтитул и нумерация листов ──────────────────────────────────────
  // Раньше реквизиты стояли только на последнем листе: распечатанный первый
  // лист многостраничного КП оставался без продавца и без номера. Теперь
  // каждый лист самодостаточен — шапка продолжения сверху, реквизиты и
  // «Лист N из M» снизу.
  // Колонтитул: знак слева, обе строки реквизитов от него влево-выключкой,
  // номер листа — к правому полю (постановка руководителя 15.09.2026).
  const [foot1, foot2] = footerLines();
  const ruleY = footRuleY();
  const footY = ruleY + 8;
  const textX = left + FOOT.w + FOOT.gap;
  pages.forEach((page, idx) => {
    const add = (p: Primitive) => page.items.push(p);
    if (idx > 0) {
      add({ kind: 'text', x: left, y: top + 6, size: 8, color: COLOR.muted,
            text: continuationLine(data), width, align: 'left' });
      add({ kind: 'line', x1: left, y1: top + 18, x2: right, y2: top + 18,
            color: COLOR.rule, lineWidth: 0.5 });
    }
    add({ kind: 'line', x1: left, y1: ruleY, x2: right, y2: ruleY, color: COLOR.rule, lineWidth: 0.5 });
    add({ kind: 'image', x: left, y: footY, w: FOOT.w, h: FOOT.h, file: MARK_FILE });
    add({ kind: 'text', x: textX, y: footY, text: foot1, size: FOOT.size, color: COLOR.muted });
    add({ kind: 'text', x: textX, y: footY + FOOT.line, text: foot2, size: FOOT.size, color: COLOR.muted });
    add({ kind: 'text', x: left, y: footY + FOOT.line, text: sheetLabel(idx + 1, pages.length),
          size: 7.5, color: COLOR.muted, width, align: 'right' });
  });
  return pages;
}

/** Подпись листа в колонтитуле: «Лист 2 из 3». Один лист тоже подписывается. */
export function sheetLabel(page: number, total: number): string {
  return `Лист ${page} из ${total}`;
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
