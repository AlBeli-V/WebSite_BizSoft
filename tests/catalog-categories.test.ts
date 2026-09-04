import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { aiSubcategories } from '../src/data/ai-hub';
import { textBlocks } from '../src/lib/text-blocks';

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
  merge: Record<string, string>;
  intro: Record<string, string>;
  content: Record<string, CategoryContent | string>;
};
interface CategoryContent {
  meta_title: string;
  meta_description: string;
  seo_text: string;
  faqs: { q: string; a: string }[];
}
const content = Object.entries(plan.content).filter(
  (e): e is [string, CategoryContent] => !e[0].startsWith('_'),
);
const segmentPage = readFileSync(resolve(ROOT, 'src/pages/catalog/[segment].astro'), 'utf8');
const icons = readFileSync(resolve(ROOT, 'src/components/CategoryIcon.astro'), 'utf8');
// Ключ с дефисом записан в кавычках ('ai-text': …) — регексп понимает оба вида.
const iconSlugs = new Set(
  (icons.match(/const BY_SLUG[^}]+}/)![0].match(/^\s{2}'?([a-z-]+)'?:/gm) || [])
    .map((line) => line.trim().replace(/[':]/g, '')),
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

describe('слитые дубли разделов', () => {
  it('дубль переезжает в существующий раздел и сам целью слияния не является', () => {
    for (const [dup, canon] of Object.entries(plan.merge)) {
      expect(Object.keys(plan.intro), `цель слияния ${canon} без текста`).toContain(canon);
      expect(plan.merge[canon], `${canon} и цель, и дубль одновременно`).toBeUndefined();
      expect(plan.intro[dup], `у дубля ${dup} остался текст раздела`).toBeUndefined();
    }
  });

  it('со слитого адреса стоит 301 — иначе проиндексированная страница отдаст 404', () => {
    // Раздел уходит в archived, а getCategoryBySlug берёт только published:
    // без редиректа /catalog/<дубль> сразу превратился бы в 404.
    for (const [dup, canon] of Object.entries(plan.merge)) {
      const line = new RegExp(`['"]?${dup}['"]?:\\s*['"]${canon}['"]`);
      expect(segmentPage, `нет редиректа ${dup} → ${canon}`).toMatch(line);
    }
  });
});

describe('товары и разделы', () => {
  it('каждый товар лежит в разделе, у которого есть название и текст', () => {
    // AI-подкатегории — не плитки /catalog, их тексты живут в src/data/ai-hub.ts
    // и в Directus (заведены миграцией ai-catalog-migrate), поэтому товар в
    // ai-* — тоже валидная привязка.
    const known = [...Object.keys(plan.intro), ...aiSubcategories.map((s) => s.categorySlug)];
    for (const { file, pkg } of packages) {
      for (const p of pkg.products) {
        if (!p.category) continue; // стабы отката несут только артикул
        expect(known, `${file}/${p.sku}: раздел ${p.category}`).toContain(p.category);
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

  it('план переразложения ведёт в существующие разделы и не расходится с пакетами', () => {
    // ops-recategorize правит живую базу, а ops-import-vendors при следующем
    // прогоне перезапишет категорию значением из пакета. Разошлись — перенос
    // молча откатится, поэтому пакетная позиция плана обязана нести ту же
    // категорию и в scripts/catalog/*.json.
    const replan = JSON.parse(
      readFileSync(resolve(ROOT, 'data/catalog/recategorize.json'), 'utf8'),
    ) as { moves: Record<string, string> };
    const known = [...Object.keys(plan.intro), ...aiSubcategories.map((s) => s.categorySlug)];
    const packaged = new Map<string, string>();
    for (const { pkg } of packages) {
      for (const p of pkg.products) if (p.category) packaged.set(p.sku, p.category);
    }
    for (const [sku, target] of Object.entries(replan.moves)) {
      expect(known, `${sku}: целевой раздел ${target}`).toContain(target);
      if (packaged.has(sku)) {
        expect(packaged.get(sku), `${sku}: пакет и план разошлись`).toBe(target);
      }
    }
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

describe('тексты страниц разделов (план thin-pages, группа F)', () => {
  it('текст пишется разделу, который есть в плане', () => {
    for (const [slug] of content) {
      expect(Object.keys(plan.intro), `${slug}: текст без раздела`).toContain(slug);
    }
  });

  it('мета в пределах выдачи и не повторяется', () => {
    const titles = content.map(([, c]) => c.meta_title);
    const descs = content.map(([, c]) => c.meta_description);
    expect(new Set(titles).size).toBe(titles.length);
    expect(new Set(descs).size).toBe(descs.length);
    for (const [slug, c] of content) {
      expect(c.meta_title.length, `${slug}.meta_title`).toBeLessThanOrEqual(60);
      expect(c.meta_description.length, `${slug}.meta_description`).toBeLessThanOrEqual(160);
    }
  });

  it('блок «Как выбрать» — структурированный текст, а не абзац-заглушка', () => {
    for (const [slug, c] of content) {
      const blocks = textBlocks(c.seo_text);
      expect(blocks.filter((b) => b.type === 'h2').length, `${slug}: подзаголовки`).toBeGreaterThanOrEqual(2);
      expect(blocks.filter((b) => b.type === 'p').length, `${slug}: абзацы`).toBeGreaterThanOrEqual(3);
      expect(c.seo_text.length, `${slug}: слишком короткий текст`).toBeGreaterThan(1200);
    }
  });

  it('вопросы раздела свои, а не типовые про покупку', () => {
    const seen = new Set<string>();
    for (const [slug, c] of content) {
      expect(c.faqs.length, `${slug}: вопросов`).toBeGreaterThanOrEqual(4);
      for (const f of c.faqs) {
        expect(f.q.trim().length, `${slug}: пустой вопрос`).toBeGreaterThan(10);
        expect(f.a.trim().length, `${slug}: короткий ответ «${f.q}»`).toBeGreaterThan(60);
        expect(seen.has(f.q), `${slug}: вопрос повторяется — «${f.q}»`).toBe(false);
        seen.add(f.q);
      }
    }
  });

  it('витрина выводит seo_text блоком, а не подставляет вместо лида', () => {
    expect(segmentPage).toContain('textBlocks(pageCategory?.seo_text)');
    expect(segmentPage).not.toMatch(/lead = pageCategory\.intro \|\| pageCategory\.seo_text/);
  });
});

describe('разбор текста раздела', () => {
  it('подзаголовок, абзац и список различаются', () => {
    const blocks = textBlocks('## Раздел\n\nАбзац первый\nпродолжение.\n\n- один\n- два\n\n## Второй\n\nЕщё абзац.');
    expect(blocks).toEqual([
      { type: 'h2', text: 'Раздел' },
      { type: 'p', text: 'Абзац первый продолжение.' },
      { type: 'ul', items: ['один', 'два'] },
      { type: 'h2', text: 'Второй' },
      { type: 'p', text: 'Ещё абзац.' },
    ]);
    expect(textBlocks(null)).toEqual([]);
    expect(textBlocks('')).toEqual([]);
  });
});
