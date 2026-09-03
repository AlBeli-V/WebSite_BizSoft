/**
 * Подборки Базы знаний по тегам (/blog/tag/<slug>): слаги строятся из русских
 * тегов транслитерацией, и два разных тега не должны склеиваться в один
 * адрес — иначе одна подборка молча подменит другую. Индексируются только
 * подборки не тоньше порога.
 */
import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { collectTags, findTagBySlug, MIN_INDEXED_TAG_POSTS, tagSlug } from '../src/lib/blog-tags';

const BLOG = resolve(__dirname, '../src/content/blog');

/** Теги всех опубликованных статей — из шапки markdown, без сборки Astro. */
function postsFromDisk(): { id: string; tags: string[] }[] {
  return readdirSync(BLOG)
    .filter((f) => f.endsWith('.md'))
    .map((f) => {
      const md = readFileSync(resolve(BLOG, f), 'utf8');
      const head = md.split('\n---\n')[0];
      if (/^draft:\s*true/m.test(head)) return null;
      const m = head.match(/^tags:\s*\[(.*)\]/m);
      const tags = m ? [...m[1].matchAll(/"([^"]+)"/g)].map((x) => x[1]) : [];
      return { id: f.replace(/\.md$/, ''), tags };
    })
    .filter((p): p is { id: string; tags: string[] } => p !== null);
}

describe('слаги тегов Базы знаний', () => {
  it('русский тег транслитерируется в латиницу той же схемой, что слаги статей', () => {
    expect(tagSlug('оформление')).toBe('oformlenie');
    expect(tagSlug('совместная работа')).toBe('sovmestnaya-rabota');
    expect(tagSlug('ИТ-активы')).toBe('it-aktivy');
    expect(tagSlug('ЭДО')).toBe('edo');
    expect(tagSlug('AI')).toBe('ai');
  });

  it('слаг никогда не пустой и состоит только из латиницы, цифр и дефисов', () => {
    for (const p of postsFromDisk()) {
      for (const t of p.tags) {
        const s = tagSlug(t);
        expect(s, `тег «${t}» у ${p.id}`).toMatch(/^[a-z0-9]+(-[a-z0-9]+)*$/);
      }
    }
  });

  it('разные теги статей не склеиваются в один слаг', () => {
    const entries = collectTags(postsFromDisk());
    const bySlug = new Map<string, string[]>();
    for (const e of entries) bySlug.set(e.slug, [...(bySlug.get(e.slug) || []), e.tag]);
    for (const [slug, tags] of bySlug) expect(tags, `слаг ${slug}`).toHaveLength(1);
  });
});

describe('подборки по тегам', () => {
  it('«оформление» — одна из самых больших подборок и она индексируется', () => {
    const entries = collectTags(postsFromDisk());
    const e = entries.find((x) => x.tag === 'оформление');
    expect(e).toBeTruthy();
    expect(e!.indexed).toBe(true);
    expect(e!.count).toBeGreaterThanOrEqual(MIN_INDEXED_TAG_POSTS);
    expect(e!.count).toBe(entries[0].count);
  });

  it('тонкие подборки не индексируются', () => {
    const entries = collectTags([{ tags: ['a', 'b'] }, { tags: ['a'] }, { tags: ['a'] }]);
    expect(findTagBySlug(entries, 'a')?.indexed).toBe(true);
    expect(findTagBySlug(entries, 'b')?.indexed).toBe(false);
    expect(findTagBySlug(entries, 'c')).toBeUndefined();
  });
});
