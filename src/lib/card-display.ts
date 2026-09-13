/**
 * Заголовок карточки и строка под ним: имя продукта без маркеров плана и
 * срока, ниже — тип плана и срок. Правило docs/rules/card-title.md
 * (решение руководителя 13.09.2026), действует на все позиции каталога.
 *
 * Срока в схеме каталога нет. Он читается из данных позиции в таком порядке:
 * поправка оператора (card-terms.json) → явный срок в названии или артикуле
 * → бессрочность в описании → вид позиции. Подписка без явного срока выходит
 * годовой: программы для юрлиц у производителей каталога годовые, а список
 * таких позиций уходит руководителю на проверку письмом; поправка
 * закрепляется в реестре, а не правкой названия.
 *
 * «Кредитов в месяц» в описании — квота, а не срок: тариф с месячной квотой
 * продаётся на год, и месяцем его называть нельзя.
 */
import CARD_TERMS from '../data/card-terms.json';
import type { CardComposition } from './product-composition';

export const TERM = {
  year: '12 месяцев',
  perpetual: 'бессрочно',
  balance: 'до истечения баланса',
} as const;

/** Поправки оператора: артикул → строка срока (значения из TERM или «N месяцев»). */
const TERM_OVERRIDE = CARD_TERMS as Record<string, string>;

/** «1 месяц», «3 месяца», «12 месяцев», «24 месяца». */
export function monthsLabel(n: number): string {
  const m10 = n % 10;
  const m100 = n % 100;
  const word = m100 >= 11 && m100 <= 19 ? 'месяцев'
    : m10 === 1 ? 'месяц'
    : m10 >= 2 && m10 <= 4 ? 'месяца'
    : 'месяцев';
  return `${n} ${word}`;
}

/**
 * Маркеры, которые из названия уходят: тип плана и срок. Редакция (Pro,
 * Enterprise, Organization), тип места (Premium seat, Dev seat) и
 * «продление» остаются — это разные товары, а не разные условия одного.
 */
const NAME_STRIP: RegExp[] = [
  // (Teams), (Individuals), (Individual), (личная), (индивидуальный), (бессрочная), (1 год), (12 месяцев)
  /\s*\((teams?|individuals?|личная|индивидуальн(ый|ая)|командн(ый|ая)|бессрочн(ый|ая)|perpetual|\d+\s*(год|года|лет|месяц(а|ев)?)|1\s*\(один\)\s*год)\)/gi,
  // «, вечная лицензия», «, 1 год», «, 12 месяцев», «, бессрочная»
  /,\s*(вечная лицензия|бессрочн(ый|ая)|\d+\s*(год|года|лет|месяц(а|ев)?))(?=,|\s*\(|$)/gi,
  // «Cinema 4D 1Y (Teams)», «Maxon One 1Y»
  /\s+\d[YМ]\b/g,
  // «Adobe Firefly for teams», «Acrobat Pro для команд», «for individuals»
  /\s+(for teams|for individuals|для команд|для организаций)(?=,|\s*\(|$)/gi,
  // «Claude Team, Premium seat» → «Claude, Premium seat»: план уходит, тип места остаётся
  /\s+Teams?(?=,)/g,
  // «BrowserStack Live Team» — план в конце названия; «Business / Team» — через косую
  /\s*\/\s*Teams?$/g,
  /\s+Teams?$/g,
];

export function displayName(name: string): string {
  let s = name;
  for (const re of NAME_STRIP) s = s.replace(re, '');
  return s.replace(/\s{2,}/g, ' ').replace(/\s+([,)])/g, '$1').trim();
}

interface TermSource { sku: string; name: string; short_description?: string | null }

/** Явный срок, названный в артикуле или названии; null — не назван. */
function explicitTerm(p: TermSource): string | null {
  const sku = p.sku.toUpperCase();
  const name = p.name;
  const desc = (p.short_description || '').toLowerCase();
  if (/-PERP\b/.test(sku) || /бессрочн|вечная лицензия|perpetual/i.test(name)) return TERM.perpetual;
  const months = name.match(/(?:^|[\s,(])(\d+)\s*(?:месяц(?:а|ев)?|мес\.)(?=[\s,)]|$)/i);
  if (months) return monthsLabel(Number(months[1]));
  const skuMonths = sku.match(/-(\d+)M\b/);
  if (skuMonths) return monthsLabel(Number(skuMonths[1]));
  const years = name.match(/\b(\d)Y\b/) || sku.match(/-(\d)Y\b/);
  if (years) return monthsLabel(12 * Number(years[1]));
  if (/\(1\s*\(один\)\s*год\)|\(1 год\)|на 1 \(один\) год|на год\b|,\s*1 год\b/i.test(name)) return TERM.year;
  // Описание годится только для бессрочности: «в месяц» там означает квоту.
  if (/бессрочн|вечная лицензия/.test(desc)) return TERM.perpetual;
  return null;
}

/**
 * Строка срока для подзаголовка и параметров. Договорная позиция срока не
 * несёт — условия в договоре; остальные без явного срока выходят годовыми.
 */
export function termLabel(p: TermSource, composition: CardComposition): string | null {
  const override = TERM_OVERRIDE[p.sku];
  if (override) return override;
  const explicit = explicitTerm(p);
  if (explicit) return explicit;
  if (composition === 'balance_topup' || isCreditsPack(p)) return TERM.balance;
  if (composition === 'quote_only') return null;
  return TERM.year;
}

/**
 * Пакет кредитов и пополнение баланса API по композиции — дополнение к
 * продукту (счётчика мест у них нет, вопрос «к чему» главный), но срок у
 * них тот же, что у номинала: баланс живёт, пока не израсходован.
 */
function isCreditsPack(p: TermSource): boolean {
  return /-CREDITS-\d+$/i.test(p.sku) || /пополнение баланса|пакет [\d\s]+кредитов|\bcredits\b/i.test(p.name);
}

/** Считается ли срок по умолчанию (для перечня на проверку руководителю). */
export function termIsAssumed(p: TermSource, composition: CardComposition): boolean {
  return !TERM_OVERRIDE[p.sku] && !explicitTerm(p) && composition !== 'balance_topup' && composition !== 'quote_only' && !isCreditsPack(p);
}
