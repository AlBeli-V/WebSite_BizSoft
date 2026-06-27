import { describe, it, expect } from 'vitest';
import { productsToCsv, parseCsv, diffCsvImport, CSV_COLUMNS } from '../src/lib/csv';
import type { Product } from '../src/lib/types';

function product(o: Partial<Product> = {}): Product {
  return { id: 1, name: 'Сервис', sku: 'SKU-1', category: null, slug: 's', price: 1000, currency: 'RUB', status: 'published', ...o };
}

describe('productsToCsv', () => {
  it('starts with BOM and header', () => {
    const csv = productsToCsv([product()]);
    expect(csv.charCodeAt(0)).toBe(0xfeff);
    expect(csv).toContain(CSV_COLUMNS.join(';'));
  });
  it('quotes cells with separators', () => {
    const csv = productsToCsv([product({ name: 'A; B "C"' })]);
    expect(csv).toContain('"A; B ""C"""');
  });
});

describe('parseCsv', () => {
  it('parses header + rows, strips BOM', () => {
    const text = '﻿sku;name;price\r\nSKU-1;Сервис;1500\r\nSKU-2;Другой;2000';
    const rows = parseCsv(text);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ sku: 'SKU-1', name: 'Сервис', price: '1500' });
  });
  it('handles quoted fields', () => {
    const text = 'sku;name\r\nSKU-1;"A; B"';
    const rows = parseCsv(text);
    expect(rows[0].name).toBe('A; B');
  });
  it('ignores rows without sku', () => {
    const text = 'sku;price\r\n;100\r\nSKU-1;200';
    expect(parseCsv(text)).toHaveLength(1);
  });
});

describe('diffCsvImport', () => {
  const products = [product({ sku: 'SKU-1', price: 1000, promo_price: null })];
  it('detects price change', () => {
    const rows = parseCsv('sku;price\r\nSKU-1;1500');
    const res = diffCsvImport(rows, products);
    expect(res.changes).toHaveLength(1);
    expect(res.updates['SKU-1'].price).toBe(1500);
  });
  it('reports unknown sku as error', () => {
    const rows = parseCsv('sku;price\r\nSKU-X;1500');
    const res = diffCsvImport(rows, products);
    expect(res.errors[0].sku).toBe('SKU-X');
    expect(Object.keys(res.updates)).toHaveLength(0);
  });
  it('flags non-numeric price', () => {
    const rows = parseCsv('sku;price\r\nSKU-1;abc');
    const res = diffCsvImport(rows, products);
    expect(res.errors.some((e) => e.message.includes('price'))).toBe(true);
  });
  it('ignores empty cells (no overwrite)', () => {
    const rows = parseCsv('sku;price;promo_label\r\nSKU-1;;');
    const res = diffCsvImport(rows, products);
    expect(Object.keys(res.updates)).toHaveLength(0);
  });
});
