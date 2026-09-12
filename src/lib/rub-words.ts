/**
 * Сумма прописью для КП-таблицы спецификации (клиент и сервер).
 * Формат строки: «799 000,00 (Семьсот девяносто девять тысяч) рублей 00 копеек,
 * в т.ч. НДС 5% 38 047,62 (Тридцать восемь тысяч сорок семь) рублей 62 копейки.»
 */

const UNITS_M = ['', 'один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять'];
const UNITS_F = ['', 'одна', 'две', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять'];
const TEENS = ['десять', 'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать', 'пятнадцать', 'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать'];
const TENS = ['', '', 'двадцать', 'тридцать', 'сорок', 'пятьдесят', 'шестьдесят', 'семьдесят', 'восемьдесят', 'девяносто'];
const HUNDREDS = ['', 'сто', 'двести', 'триста', 'четыреста', 'пятьсот', 'шестьсот', 'семьсот', 'восемьсот', 'девятьсот'];

/** Форма слова по числу: pluralForm(n, ['рубль','рубля','рублей']). */
export function pluralForm(n: number, forms: [string, string, string]): string {
  const a = Math.abs(Math.trunc(n)) % 100;
  const b = a % 10;
  if (a > 10 && a < 20) return forms[2];
  if (b > 1 && b < 5) return forms[1];
  if (b === 1) return forms[0];
  return forms[2];
}

function triadWords(n: number, feminine: boolean): string {
  const units = feminine ? UNITS_F : UNITS_M;
  const parts: string[] = [];
  const h = Math.trunc(n / 100);
  const t = Math.trunc((n % 100) / 10);
  const u = n % 10;
  if (h) parts.push(HUNDREDS[h]);
  if (t === 1) parts.push(TEENS[u]);
  else {
    if (t) parts.push(TENS[t]);
    if (u) parts.push(units[u]);
  }
  return parts.join(' ');
}

const SCALES: [string, string, string, boolean][] = [
  ['', '', '', false],
  ['тысяча', 'тысячи', 'тысяч', true],
  ['миллион', 'миллиона', 'миллионов', false],
  ['миллиард', 'миллиарда', 'миллиардов', false],
];

/** Целое число прописью (до миллиардов). */
export function numberWords(n: number): string {
  n = Math.trunc(Math.abs(n));
  if (n === 0) return 'ноль';
  const triads: number[] = [];
  while (n > 0) { triads.push(n % 1000); n = Math.trunc(n / 1000); }
  const parts: string[] = [];
  for (let i = triads.length - 1; i >= 0; i--) {
    const tri = triads[i];
    if (!tri) continue;
    const [one, few, many, fem] = SCALES[i];
    parts.push(triadWords(tri, fem));
    if (i > 0) parts.push(pluralForm(tri, [one, few, many]));
  }
  return parts.join(' ');
}

/** «799 000,00» — денежный формат с двумя знаками. */
export function moneyFmt(n: number): string {
  return new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** «18 000 000,00 (Восемнадцать миллионов) рублей 00 копеек» — как в образце КП. */
export function amountPhrase(n: number): string {
  const rub = Math.trunc(n);
  const kop = Math.round((n - rub) * 100);
  const kopStr = String(kop).padStart(2, '0');
  return `${moneyFmt(n)} (${capitalize(numberWords(rub))}) ${pluralForm(rub, ['рубль', 'рубля', 'рублей'])} ${kopStr} ${pluralForm(kop, ['копейка', 'копейки', 'копеек'])}`;
}

/** Полная строка под таблицей: сумма и выделенный НДС (в т.ч., ставка vatPercent). */
export function totalWithVatWords(total: number, vatPercent = 5): string {
  const vat = Math.round((total * vatPercent / (100 + vatPercent)) * 100) / 100;
  return `${amountPhrase(total)}, в т.ч. НДС ${vatPercent}% ${amountPhrase(vat)}.`;
}

/**
 * Сумма НДС «в т.ч.» по позициям с их собственными ставками.
 *
 * Считаем по каждой позиции и складываем, а не берём одну ставку на весь
 * документ: у товаров ставка своя, и позиция без НДС в общем расчёте
 * добавила бы к налогу пять процентов от своей стоимости — то есть налог
 * с того, что им не облагается.
 */
export function vatOfItems(
  items: { sum: number; vat_percent?: number | null }[],
  fallback = 5,
): number {
  const total = items.reduce((acc, i) => {
    const rate = i.vat_percent ?? fallback;
    if (!rate) return acc;
    return acc + (i.sum * rate) / (100 + rate);
  }, 0);
  return Math.round(total * 100) / 100;
}

/** Единая ставка документа, если она у всех позиций одна. Иначе null. */
export function singleVatRate(
  items: { vat_percent?: number | null }[],
  fallback = 5,
): number | null {
  const rates = new Set(items.map((i) => i.vat_percent ?? fallback));
  return rates.size === 1 ? [...rates][0] : null;
}

/** Сумма НДС «в т.ч.» по ставке (по умолчанию 5%). */
export function vatIncluded(total: number, vatPercent = 5): number {
  return Math.round((total * vatPercent / (100 + vatPercent)) * 100) / 100;
}
