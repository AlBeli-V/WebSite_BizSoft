import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Разделы каталога («Назначение ПО»): плитки на /catalog.
 *
 * Плитка несёт три вещи — иконку, название и подпись. Ломается это молча:
 * товар уезжает в раздел, которого нет; у раздела пустой intro и плитка
 * показывает общую для всех фразу про договор и юрлицо; иконки нет и раздел
 * получает безликий квадратик. Ни одно из трёх не роняет сборку, поэтому
 * стережём тестом.
 */

const ROOT = resolve(__dirname, '..');
const plan = JSON.parse(
  readFileSync(resolve(ROOT, 'data/catalog/categories.json'), 'utf8'),
) as {
  create: { slug: string; name: string; sort: number }[];
  intro: Record<string, string>;
};
const icons = readFileSync(resolve(ROOT, 'src/components/CategoryIcon.astro'), 'utf8');
const iconSlugs = new Set(
  (icons.match(/const BY_SLUG[^}]+}/)![0].match(/^\s{2}([a-z-]+):/gm) || [])
    .map((line) => line.trim().replace(':', '')),
);

const packages = readdirSync(resolve(ROOT, 'scripts/catalog'))
  .filter((f) => f.endsWith('.json'))
  .map((f) => ({
    file: f,
    pkg: JSON.parse(readFileSync(resolve(ROOT, 'scripts/catalog', f), 'utf8')) as {
      products: { sku: string; category?: string }[];
    },
  }));

describe('план разделов каталога', () => {
  it('у нового раздела есть слаг, название и место в списке', () => {
    const sorts = plan.create.map((c) => c.sort);
    expect(new Set(sorts).size, 'два раздела с одним sort').toBe(sorts.length);
    for (const c of plan.create) {
      expect(c.slug).toMatch(/^[a-z][a-z0-9-]*$/);
      expect(c.name.length, `${c.slug}: пустое название`).toBeGreaterThan(5);
      expect(Number.isInteger(c.sort), `${c.slug}: sort не число`).toBe(true);
    }
  });

  it('у каждого раздела есть текст, объясняющий назначение', () => {
    for (const [slug, text] of Object.entries(plan.intro)) {
      // Короткая подпись назначения не объясняет, а длинная не влезает в плитку.
      expect(text.length, `${slug}: слишком короткий текст`).toBeGreaterThan(60);
      expect(text.length, `${slug}: слишком длинный текст`).toBeLessThan(210);
      // Ровно та фраза, которую подставляет витрина, когда intro пуст.
      expect(text, `${slug}: типовая заглушка вместо назначения`)
        .not.toContain('Лицензии и подписки для бизнеса');
    }
  });

  it('тексты разделов не повторяются', () => {
    const texts = Object.values(plan.intro);
    expect(new Set(texts).size, 'два раздела с одинаковым текстом').toBe(texts.length);
  });

  it('у каждого раздела своя иконка — иначе плитки неразличимы', () => {
    for (const slug of Object.keys(plan.intro)) {
      expect(iconSlugs, `нет иконки для раздела ${slug}`).toContain(slug);
    }
  });
});

describe('товары и разделы', () => {
  it('каждый товар лежит в разделе, у которого есть название и текст', () => {
    for (const { file, pkg } of packages) {
      for (const p of pkg.products) {
        if (!p.category) continue; // стабы отката несут только артикул
        expect(Object.keys(plan.intro), `${file}/${p.sku}: раздел ${p.category}`)
          .toContain(p.category);
      }
    }
  });

  it('партия ManageEngine разложена по назначению, а не свалена в один раздел', () => {
    const zoho = packages.find((p) => p.file === 'zoho.json')!.pkg.products;
    const used = new Set(zoho.map((p) => p.category));
    expect(used.size, 'вся партия в одном разделе').toBeGreaterThanOrEqual(5);
    // Системными утилитами эти продукты не являются: раздел «system» для них
    // и был исходной ошибкой.
    expect(used).not.toContain('system');
  });

  it('сопровождение лежит в том же разделе, что и его вечная лицензия', () => {
    const zoho = packages.find((p) => p.file === 'zoho.json')!.pkg.products;
    const bySku = new Map(zoho.map((p) => [p.sku, p]));
    for (const a of zoho.filter((p) => p.sku.endsWith('-AMS'))) {
      const licence = bySku.get(a.sku.replace(/-AMS$/, ''));
      expect(a.category, `${a.sku}: раздел разошёлся с лицензией`)
        .toBe(licence?.category);
    }
  });
});
