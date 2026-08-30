/**
 * Общий поиск каталога (страница /catalog?q= и WebMCP search_products).
 */
import { describe, expect, it } from 'vitest';
import { searchProducts } from '../src/lib/product-search';
import type { Product } from '../src/lib/types';

const P = (over: Partial<Product>): Product => ({
  id: over.sku || 'id',
  name: 'X',
  sku: 'X-1',
  vendor: null,
  category: null,
  slug: 'x',
  price: 1000,
  currency: 'RUB',
  status: 'published',
  ...over,
});

const items = [
  P({ name: 'Claude Team', sku: 'AI-CT', keywords: 'AI ассистент команда', vendor: 'Anthropic', price: 42_000 }),
  P({ name: 'Claude Enterprise', sku: 'AI-CE', vendor: 'Anthropic', price: 0 }),
  P({ name: 'ChatGPT Business', sku: 'AI-GPT', vendor: 'OpenAI', keywords: 'AI ассистент', price: 30_000 }),
];

describe('searchProducts', () => {
  it('слова запроса находятся в любом порядке (И-логика по токенам)', () => {
    const r = searchProducts(items, 'команда claude');
    expect(r[0].name).toBe('Claude Team');
  });

  it('точная фраза ранжируется выше набора токенов', () => {
    const r = searchProducts(items, 'claude');
    expect(r.map((p) => p.name)).toContain('Claude Enterprise');
    expect(r[0].vendor).toBe('Anthropic');
  });

  it('если И-логика не нашла ничего — ИЛИ-фолбэк по любому токену', () => {
    const r = searchProducts(items, 'ассистент несуществующее');
    expect(r.length).toBeGreaterThan(0);
  });

  it('поиск по sku и вендору работает', () => {
    expect(searchProducts(items, 'AI-GPT')[0].name).toBe('ChatGPT Business');
    expect(searchProducts(items, 'openai')[0].name).toBe('ChatGPT Business');
  });

  it('«цена по запросу» — в конце, пустой запрос — пустой список', () => {
    const r = searchProducts(items, 'claude');
    expect(r.at(-1)?.name).toBe('Claude Enterprise');
    expect(searchProducts(items, '  ')).toEqual([]);
  });
});
