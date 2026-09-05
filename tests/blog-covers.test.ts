// Вес обложек статей. Замер PageSpeed 05.09.2026: LCP статей 2,6–2,9 с против
// секунды у остальных шаблонов, виновник по аудиту Lighthouse — обложка-PNG на
// четверть мегабайта. Лечение — WebP двух ширин рядом с PNG; PNG остаётся для
// og:image. Тест держит это состояние: новая статья без WebP или страница,
// вернувшаяся к голому <img>, роняют проверку до выката, а не после.
import { describe, expect, it } from 'vitest';
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(__dirname, '..');
const coversDir = resolve(root, 'public/blog/covers');
const postsDir = resolve(root, 'src/content/blog');

/** Путь обложки из фронтматтера статьи, если он задан. */
function coverOf(file: string): string | null {
  const text = readFileSync(resolve(postsDir, file), 'utf8');
  const m = text.match(/^cover:\s*"?([^"\n]+)"?\s*$/m);
  return m ? m[1].trim() : null;
}

const posts = readdirSync(postsDir).filter((f) => f.endsWith('.md'));

describe('обложки статей: WebP рядом с PNG', () => {
  it('у каждой статьи с обложкой есть обе ширины WebP', () => {
    const missing: string[] = [];
    for (const post of posts) {
      const cover = coverOf(post);
      if (!cover) continue;
      const slug = cover.replace('/blog/covers/', '').replace('.png', '');
      for (const name of [`${slug}.png`, `${slug}.webp`, `${slug}-832.webp`]) {
        if (!existsSync(resolve(coversDir, name))) missing.push(`${post} → ${name}`);
      }
    }
    expect(missing).toEqual([]);
  });

  it('WebP заметно легче PNG — иначе смысла в нём нет', () => {
    const heavy: string[] = [];
    for (const f of readdirSync(coversDir).filter((n) => n.endsWith('.png'))) {
      const slug = f.replace('.png', '');
      const webp = resolve(coversDir, `${slug}.webp`);
      if (!existsSync(webp)) continue;
      const ratio = statSync(webp).size / statSync(resolve(coversDir, f)).size;
      // Порог с запасом: на замере 05.09 доля была около 7 %.
      if (ratio > 0.25) heavy.push(`${slug}: ${(ratio * 100).toFixed(0)} % от PNG`);
    }
    expect(heavy).toEqual([]);
  });

  it('страницы блога показывают обложку через BlogCover, а не голым img', () => {
    const pages = [
      'src/pages/blog/[slug].astro',
      'src/pages/blog/index.astro',
      'src/pages/blog/tag/[tag].astro',
    ];
    for (const page of pages) {
      const text = readFileSync(resolve(root, page), 'utf8');
      expect(text, page).toContain('BlogCover');
      expect(text, page).not.toMatch(/<img[^>]*src=\{(p\.data\.cover|d\.cover)\}/);
    }
  });
});
