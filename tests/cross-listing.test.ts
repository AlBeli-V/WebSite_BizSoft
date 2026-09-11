/**
 * Реестр второй привязки товара к разделу.
 *
 * Реестр живёт в репозитории, а товары — в базе, и разъехаться они могут молча:
 * артикул с опечаткой просто никогда не совпадёт, раздел с опечаткой не
 * покажется нигде, а домашний раздел в списке задвоит товар в его же выдаче.
 * Ни одно из этих расхождений не падает в рантайме — поэтому сторож здесь.
 *
 * Проверить существование артикула в боевой базе тест не может (сети нет), но
 * может проверить всё остальное: форму записи, известность раздела и то, что
 * механизм действительно добавляет товар в раздел и не задваивает его.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  CROSS_LISTING,
  categoryMembers,
  crossListedCount,
  extraCategories,
  inCategory,
  productCategories,
} from '../src/lib/cross-listing';
import { countByCategory } from '../src/lib/catalog';
import type { Product } from '../src/lib/types';

const ROOT = resolve(__dirname, '..');
const registry = JSON.parse(
  readFileSync(resolve(ROOT, 'data/catalog/cross-listing.json'), 'utf8'),
) as { also: Record<string, string[]>; _reasons: Record<string, string> };
const categoriesPlan = JSON.parse(
  readFileSync(resolve(ROOT, 'data/catalog/categories.json'), 'utf8'),
) as { intro: Record<string, string>; merge: Record<string, string> };

/** Разделы, которые заведены в плане каталога, — целевые для второй привязки. */
const KNOWN = new Set(Object.keys(categoriesPlan.intro));

function product(sku: string, categorySlug: string, slug = sku.toLowerCase()): Product {
  return {
    id: sku, name: sku, sku, slug, price: 1, currency: 'RUB',
    category: { id: categorySlug, name: categorySlug, slug: categorySlug, status: 'published' },
  } as unknown as Product;
}

describe('реестр второй привязки', () => {
  it('ключи — артикулы в верхнем регистре, значения непустые', () => {
    for (const [sku, cats] of Object.entries(registry.also)) {
      expect(sku, `артикул ${sku}`).toBe(sku.toUpperCase());
      expect(sku).toMatch(/^[A-Z0-9][A-Z0-9-]*$/);
      expect(Array.isArray(cats), `у ${sku} значение не список`).toBe(true);
      expect(cats.length, `у ${sku} пустой список разделов`).toBeGreaterThan(0);
    }
  });

  it('каждый раздел назначения заведён в плане каталога', () => {
    for (const [sku, cats] of Object.entries(registry.also)) {
      for (const c of cats) {
        expect(KNOWN.has(c), `${sku}: раздел «${c}» не заведён в categories.json`).toBe(true);
      }
    }
  });

  it('вторая привязка не ведёт в слитый дубль раздела', () => {
    // Дубли отдают 301 на основной раздел: товар, привязанный к дублю,
    // не показался бы нигде.
    for (const [sku, cats] of Object.entries(registry.also)) {
      for (const c of cats) {
        expect(categoriesPlan.merge[c], `${sku}: «${c}» — слитый дубль`).toBeUndefined();
      }
    }
  });

  it('разделы в записи не повторяются', () => {
    for (const [sku, cats] of Object.entries(registry.also)) {
      expect(new Set(cats).size, `у ${sku} повторяющиеся разделы`).toBe(cats.length);
    }
  });

  it('у каждого раздела назначения записана причина', () => {
    const used = new Set(Object.values(registry.also).flat());
    for (const c of used) {
      expect(registry._reasons[c], `нет причины для раздела «${c}»`).toBeTruthy();
    }
  });

  it('реестр доезжает до кода в верхнем регистре', () => {
    expect(Object.keys(CROSS_LISTING).length).toBe(Object.keys(registry.also).length);
    for (const sku of Object.keys(CROSS_LISTING)) expect(sku).toBe(sku.toUpperCase());
  });
});

describe('механизм второй привязки', () => {
  it('домашний раздел из списка отбрасывается — товар не задваивается', () => {
    // Даже если в реестр попадёт домашний раздел товара, выдача не должна
    // показать его дважды.
    const p = product('SLACK-PRO', 'collaboration');
    expect(extraCategories(p)).toEqual([]);
    expect(productCategories(p)).toEqual(['collaboration']);
    expect(categoryMembers([p], 'collaboration')).toHaveLength(1);
  });

  it('товар виден и в своём разделе, и во втором', () => {
    const p = product('SLACK-PRO', 'vcs');
    expect(inCategory(p, 'vcs')).toBe(true);
    expect(inCategory(p, 'collaboration')).toBe(true);
    expect(inCategory(p, 'design')).toBe(false);
  });

  it('свои товары раздела идут раньше пришедших второй привязкой', () => {
    // Иначе «Сайты и хостинг» открывались бы карточкой Cloudflare, а не WordPress.
    const own = product('WORDPRESS-BUSINESS', 'web');
    const guest = product('CLOUDFLARE-PRO', 'security');
    expect(categoryMembers([guest, own], 'web').map((p) => p.sku)).toEqual([
      'WORDPRESS-BUSINESS', 'CLOUDFLARE-PRO',
    ]);
  });

  it('счётчик раздела включает вторую привязку', () => {
    const counts = countByCategory([
      product('WORDPRESS-BUSINESS', 'web'),
      product('CLOUDFLARE-PRO', 'security'),
    ]);
    expect(counts.web).toBe(2);
    // Домашний раздел гостя при этом не теряет свою позицию.
    expect(counts.security).toBe(1);
  });

  it('видно, сколько позиций в разделе — гости', () => {
    const items = [product('WORDPRESS-BUSINESS', 'web'), product('CLOUDFLARE-PRO', 'security')];
    expect(crossListedCount(items, 'web')).toBe(1);
    expect(crossListedCount(items, 'security')).toBe(0);
  });

  it('товар вне реестра ведёт себя как прежде', () => {
    const p = product('NOTHING-SPECIAL', 'design');
    expect(extraCategories(p)).toEqual([]);
    expect(countByCategory([p])).toEqual({ design: 1 });
  });
});
