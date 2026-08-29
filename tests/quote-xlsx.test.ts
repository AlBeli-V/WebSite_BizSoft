/**
 * Excel «Экономика сделки»: внутренний файл с живыми формулами.
 *
 * Проверяется то, что можно сломать молча: формулы вместо значений
 * (руководитель правит закупку в файле и ждёт пересчёта), пометка
 * «внутренний документ», честное «нет данных» по позициям без закупки.
 */
import { describe, expect, it } from 'vitest';
import * as XLSX from 'xlsx';
import { buildQuoteEconomics } from '../src/lib/quote-economics';
import { economicsFileName, generateQuoteEconomicsXlsx } from '../src/lib/xlsx-quote';
import type { Product } from '../src/lib/types';

const fx = { usd: 85, eur: 92, date: '28.08.2026' };
const product = (sku: string, extra: Partial<Product> = {}): Product => ({
  id: 1, name: sku, sku, vendor: 'v', origin: '', slug: sku.toLowerCase(),
  price: 0, currency: 'RUB', status: 'published', ...extra,
} as unknown as Product);

const eco = buildQuoteEconomics(
  [
    { sku: 'A', name: 'Товар А', qty: 10, price: 105000, sum: 1050000 },
    { sku: 'B', name: 'Без закупки', qty: 1, price: 50000, sum: 50000 },
  ],
  [product('A', { base_price_usd: 700 }), product('B')],
  fx,
);

function sheet() {
  const buf = generateQuoteEconomicsXlsx('BZ-20260828-0042', '28.08.2026', eco);
  // sheetStubs: ячейка «только формула» без кэшированного значения — заглушка
  // для парсера, без этой опции он её молча выбрасывает.
  const wb = XLSX.read(buf, { type: 'buffer', cellFormula: true, sheetStubs: true });
  return wb.Sheets[wb.SheetNames[0]];
}

describe('Excel экономики сделки', () => {
  const ws = sheet();
  const cells = Object.entries(ws)
    .filter(([k]) => !k.startsWith('!')) as [string, XLSX.CellObject][];
  const texts = cells.map(([, c]) => String(c.v ?? ''));
  const formulas = cells.filter(([, c]) => c.f).map(([, c]) => c.f as string);

  it('имя файла помечено INTERNAL', () => {
    expect(economicsFileName('BZ-1')).toBe('Economics_KP_BZ-1_INTERNAL.xlsx');
  });

  it('первая строка — предупреждение «внутренний документ»', () => {
    expect(ws.A1?.v).toContain('ВНУТРЕННИЙ ДОКУМЕНТ');
    expect(ws.A1?.v).toContain('не пересылать');
  });

  it('итоги — живые формулы, а не значения', () => {
    expect(formulas.some((f) => f.startsWith('SUM(F'))).toBe(true); // выручка
    expect(formulas.some((f) => f.startsWith('SUM(J'))).toBe(true); // закупка
    expect(formulas.some((f) => f.includes('*7%'))).toBe(true);     // налог от выручки
    expect(formulas.some((f) => f.includes('*10%'))).toBe(true);    // резерв от закупки
  });

  it('строки позиций пересчитываются формулами через ячейку курса', () => {
    expect(formulas.some((f) => /^E\d+\*D\d+$/.test(f))).toBe(true);   // продажа
    expect(formulas.some((f) => /^I\d+\*\$B\$4$/.test(f))).toBe(true); // закупка ₽ по курсу
  });

  it('позиция без закупки — «нет данных», и есть предупреждение об итоге', () => {
    expect(texts.some((t) => t === 'нет данных')).toBe(true);
    expect(texts.some((t) => t.includes('Нет закупочных цен') && t.includes('B'))).toBe(true);
  });

  it('курс ЦБ зафиксирован в листе', () => {
    expect(ws.B4?.v).toBe(85);
    expect(texts.some((t) => t.includes('28.08.2026'))).toBe(true);
  });

  it('подозрение на месячную закупку видно и в строке, и в предупреждении', () => {
    const suspect = buildQuoteEconomics(
      [{ sku: 'M', name: 'Месячная', qty: 1, price: 105000, sum: 105000 }],
      [product('M', { base_price_usd: 100 })], fx);
    const buf = generateQuoteEconomicsXlsx('BZ-1', '28.08.2026', suspect);
    const wb = XLSX.read(buf, { type: 'buffer', cellFormula: true, sheetStubs: true });
    const ws2 = wb.Sheets[wb.SheetNames[0]];
    const t = Object.entries(ws2).filter(([k]) => !k.startsWith('!'))
      .map(([, c]) => String((c as XLSX.CellObject).v ?? '')).join(' | ');
    expect(t).toContain('закупка за МЕСЯЦ');
    expect(t).toContain('Подозрение на МЕСЯЧНУЮ закупку');
  });

  it('блок экономики содержит прибыль и валовую маржу', () => {
    expect(texts.some((t) => t.includes('ПРИБЫЛЬ по сделке'))).toBe(true);
    expect(texts.some((t) => t.includes('Валовая маржа'))).toBe(true);
    expect(texts.some((t) => t.includes('НДС 5%'))).toBe(true);
  });
});
