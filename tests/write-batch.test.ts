import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { chunk, WRITE_BATCH } from '../src/lib/directus';

/**
 * Разбиение на пачки для импорта и ежедневной переоценки.
 * Ошибка здесь тихо теряет часть позиций, поэтому границы проверяем явно.
 */
describe('разбиение на пачки', () => {
  it('пустой список не даёт ни одной пачки', () => {
    expect(chunk([], 10)).toEqual([]);
  });

  it('список короче пачки уходит одной пачкой целиком', () => {
    expect(chunk([1, 2, 3], 10)).toEqual([[1, 2, 3]]);
  });

  it('ровное деление не даёт пустого хвоста', () => {
    const parts = chunk([1, 2, 3, 4], 2);
    expect(parts).toEqual([[1, 2], [3, 4]]);
  });

  it('неровное деление сохраняет остаток', () => {
    expect(chunk([1, 2, 3, 4, 5], 2)).toEqual([[1, 2], [3, 4], [5]]);
  });

  it('ни одна позиция не теряется и порядок сохраняется', () => {
    const items = Array.from({ length: 4700 }, (_, i) => i);
    const flat = chunk(items, WRITE_BATCH).flat();
    expect(flat).toHaveLength(items.length);
    expect(flat).toEqual(items);
  });

  it('размер пачки разумный: не по одному и не всё разом', () => {
    expect(WRITE_BATCH).toBeGreaterThan(10);
    expect(WRITE_BATCH).toBeLessThanOrEqual(500);
  });
});

describe('поля для переоценки', () => {
  it('в выборке есть всё, на что смотрит выбор области и расчёт', async () => {
    const src = readFileSync(resolve(__dirname, '../src/lib/directus.ts'), 'utf8');
    const block = src.slice(src.indexOf('const REPRICE_FIELDS'), src.indexOf('/** Товары в объёме'));
    // Поля выбора области: без них переоценка «по вендору» или «по категории»
    // тихо не найдёт ни одного товара.
    for (const field of ['vendor', 'category.slug', 'origin']) {
      expect(block, `нет поля ${field}`).toContain(`'${field}'`);
    }
    // Поля расчёта: себестоимость, привязка, коэффициент, текущая цена, замок.
    for (const field of ['id', 'sku', 'price', 'base_price_usd', 'base_price_eur',
      'peg_currency', 'peg_to_usd', 'markup_coeff', 'price_locked']) {
      expect(block, `нет поля ${field}`).toContain(`'${field}'`);
    }
  });
});
