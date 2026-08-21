import { describe, it, expect } from 'vitest';
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
