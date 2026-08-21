/**
 * Чистая логика CSV для импорта/экспорта цен.
 * Формат: UTF-8 с BOM, разделитель «;» (удобно для Excel в RU-локали).
 */
import type { Product } from './types';

export const CSV_COLUMNS = [
  'sku',
  'name',
  'category',
  'price',
  'currency',
  'base_price_usd',
  'peg_to_usd',
  'markup_percent',
  'promo_price',
  'promo_label',
  'promo_start',
  'promo_end',
] as const;

export type CsvColumn = (typeof CSV_COLUMNS)[number];
const BOM = '﻿';
const SEP = ';';

function escapeCell(v: unknown): string {
  const s = v == null ? '' : String(v);
  if (s.includes(SEP) || s.includes('"') || s.includes('\n') || s.includes('\r')) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

function categorySlug(p: Product): string {
  if (p.category && typeof p.category === 'object') return p.category.slug;
  return p.category != null ? String(p.category) : '';
}

/** Экспорт выбранных товаров в CSV (UTF-8 BOM, ';'). */
export function productsToCsv(products: Product[]): string {
  const lines = [CSV_COLUMNS.join(SEP)];
  for (const p of products) {
    const row: Record<CsvColumn, unknown> = {
      sku: p.sku,
      name: p.name,
      category: categorySlug(p),
      price: p.price ?? '',
      currency: p.currency ?? 'RUB',
      base_price_usd: p.base_price_usd ?? '',
      peg_to_usd: p.peg_to_usd ? '1' : '0',
      markup_percent: p.markup_percent ?? '',
      promo_price: p.promo_price ?? '',
      promo_label: p.promo_label ?? '',
      promo_start: p.promo_start ?? '',
      promo_end: p.promo_end ?? '',
    };
    lines.push(CSV_COLUMNS.map((c) => escapeCell(row[c])).join(SEP));
  }
  return BOM + lines.join('\r\n');
}

/** Разбор одной CSV-строки с учётом кавычек. */
function parseLine(line: string): string[] {
  const out: string[] = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (line[i + 1] === '"') { cur += '"'; i++; }
        else inQuotes = false;
      } else cur += ch;
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === SEP) {
      out.push(cur); cur = '';
    } else cur += ch;
  }
  out.push(cur);
  return out;
}

export interface CsvRow {
  sku: string;
  [key: string]: string;
}

/** Парсинг CSV в массив объектов по заголовку. BOM срезается. */
export function parseCsv(text: string): CsvRow[] {
  const clean = text.replace(/^﻿/, '');
  const rawLines = clean.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (rawLines.length < 2) return [];
  const header = parseLine(rawLines[0]).map((h) => h.trim());
  const rows: CsvRow[] = [];
  for (let i = 1; i < rawLines.length; i++) {
    const cells = parseLine(rawLines[i]);
    const obj: Record<string, string> = {};
    header.forEach((h, idx) => (obj[h] = (cells[idx] ?? '').trim()));
    if (obj.sku) rows.push(obj as CsvRow);
  }
  return rows;
}

const NUM_FIELDS = ['price', 'base_price_usd', 'markup_percent', 'promo_price'];

export interface CsvImportChange {
  sku: string;
  found: boolean;
  field: string;
  before: string;
  after: string;
}

export interface CsvImportResult {
  changes: CsvImportChange[];
  errors: { sku: string; message: string }[];
  /** карта sku → объект изменений для применения */
  updates: Record<string, Record<string, unknown>>;
}

function num(v: string): number | null {
  if (v === '') return null;
  const n = parseFloat(v.replace(',', '.'));
  return isFinite(n) ? n : NaN as number;
}

/**
 * Сравнить строки CSV с текущими товарами (по sku) и построить предпросмотр
 * «было → станет» + карту обновлений. Меняем только присутствующие в CSV поля.
 */
export function diffCsvImport(rows: CsvRow[], products: Product[]): CsvImportResult {
  const bySku = new Map(products.map((p) => [p.sku, p]));
  const changes: CsvImportChange[] = [];
  const errors: { sku: string; message: string }[] = [];
  const updates: Record<string, Record<string, unknown>> = {};

  const editable = ['price', 'currency', 'base_price_usd', 'peg_to_usd', 'markup_percent', 'promo_price', 'promo_label', 'promo_start', 'promo_end'];

  for (const row of rows) {
    const p = bySku.get(row.sku);
    if (!p) {
      errors.push({ sku: row.sku, message: 'товар с таким sku не найден' });
      changes.push({ sku: row.sku, found: false, field: '—', before: '—', after: '—' });
      continue;
    }
    const upd: Record<string, unknown> = {};
    for (const field of editable) {
      if (!(field in row)) continue;
      const raw = row[field];
      // пустую ячейку игнорируем (не затираем), кроме явных промо-полей — оставим как есть
      let after: unknown = raw;
      if (NUM_FIELDS.includes(field)) {
        if (raw === '') continue;
        const n = num(raw);
        if (n == null || Number.isNaN(n)) { errors.push({ sku: row.sku, message: `поле ${field}: не число «${raw}»` }); continue; }
        after = n;
      } else if (field === 'peg_to_usd') {
        if (raw === '') continue;
        after = raw === '1' || raw.toLowerCase() === 'true';
      } else {
        if (raw === '') continue;
      }
      const beforeVal = (p as unknown as Record<string, unknown>)[field];
      const beforeStr = beforeVal == null ? '' : String(beforeVal);
      const afterStr = String(after);
      if (beforeStr !== afterStr) {
        changes.push({ sku: row.sku, found: true, field, before: beforeStr || '—', after: afterStr });
        upd[field] = after;
      }
    }
    if (Object.keys(upd).length > 0) updates[row.sku] = upd;
  }
  return { changes, errors, updates };
}
