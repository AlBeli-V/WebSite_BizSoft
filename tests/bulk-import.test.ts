import { describe, it, expect } from 'vitest';
import { normOrigin, normLicense, normBool, normNum, normList, canonRow, buildPlan } from '../src/lib/bulk-import';
import type { Product } from '../src/lib/types';

describe('normalizers', () => {
  it('origin RU and EN', () => {
    expect(normOrigin('Отечественное')).toBe('domestic');
    expect(normOrigin('foreign')).toBe('foreign');
    expect(normOrigin('xyz')).toBe('');
  });
  it('license RU and EN', () => {
    expect(normLicense('Для организаций')).toBe('org');
    expect(normLicense('student')).toBe('student');
    expect(normLicense('индивидуальное использование')).toBe('individual');
  });
  it('bool', () => {
    expect(normBool('1')).toBe(true);
    expect(normBool('да')).toBe(true);
    expect(normBool('0')).toBe(false);
  });
  it('num with comma and spaces', () => {
    expect(normNum('1 200,50')).toBeCloseTo(1200.5);
    expect(normNum('')).toBeNull();
    expect(normNum('abc')).toBeNull();
  });
  it('list split by | and newline', () => {
    expect(normList('a | b \n c')).toEqual(['a', 'b', 'c']);
  });
  it('canonRow lowercases keys', () => {
    expect(canonRow({ 'SKU': 'X', ' Price ': '10' })).toMatchObject({ sku: 'X', price: '10' });
  });
});

function prod(o: Partial<Product>): Product {
  return { id: 1, name: 'Old', sku: 'A', category: { id: 5, name: 'Office', slug: 'office' } as any, slug: 'a', price: 100, currency: 'RUB', status: 'published', ...o };
}
const resolver = (k: string) => (k.toLowerCase() === 'office' ? 5 : k.toLowerCase() === 'ai' ? 7 : null);

describe('buildPlan', () => {
  it('creates new product', () => {
    const rows = [canonRow({ sku: 'NEW-1', name: 'Новый', origin: 'Отечественное', category: 'office', price: '500' })];
    const plan = buildPlan(rows, [], resolver);
    expect(plan.summary.create).toBe(1);
    const item = plan.items[0];
    expect(item.mode).toBe('create');
    expect(item.payload.slug).toBe('new-1');
    expect(item.payload.origin).toBe('domestic');
    expect(item.payload.category).toBe(5);
    expect(item.payload.price).toBe(500);
  });
  it('updates existing with changed field only', () => {
    const rows = [canonRow({ sku: 'A', price: '150' })];
    const plan = buildPlan(rows, [prod({ sku: 'A', price: 100 })], resolver);
    expect(plan.summary.update).toBe(1);
    expect(plan.items[0].payload.price).toBe(150);
  });
  it('skips when no change', () => {
    const rows = [canonRow({ sku: 'A', price: '100', category: 'office' })];
    const plan = buildPlan(rows, [prod({ sku: 'A', price: 100 })], resolver);
    expect(plan.summary.update).toBe(0);
    expect(plan.items[0].mode).toBe('skip');
    expect(plan.items[0].errors).toHaveLength(0);
  });
  it('errors: missing name on create', () => {
    const plan = buildPlan([canonRow({ sku: 'NEW-2', price: '10' })], [], resolver);
    expect(plan.summary.errors).toBe(1);
    expect(plan.items[0].errors.join()).toMatch(/name/);
  });
  it('errors: unknown category and bad origin', () => {
    const plan = buildPlan([canonRow({ sku: 'A', category: 'unknown', origin: 'qqq' })], [prod({ sku: 'A' })], resolver);
    expect(plan.items[0].errors.length).toBeGreaterThanOrEqual(2);
  });
});
