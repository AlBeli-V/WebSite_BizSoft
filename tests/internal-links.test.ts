import { describe, it, expect } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

/**
 * Защита от страниц-сирот: слой URL попал в sitemap, но на него не ведёт ни
 * одной внутренней ссылки.
 *
 * Инцидент 08.09.2026: слой «Аналоги X» (7 страниц, эксперимент PAGES-EXP-001)
 * существовал только в sitemap.xml.ts и в собственном шаблоне. Разбор покрытия
 * Google показал последствие: Googlebot не обошёл ни одну из 7 страниц, при
 * том что все 7 были в поиске Яндекса. Ссылка из карты — самый слабый сигнал
 * обхода, какой есть; для молодого домена его не хватает.
 *
 * Проверка грубая по замыслу: она следит не за количеством ссылок, а за самим
 * фактом, что слой связан с сайтом. Естественный рост каталога её не ломает —
 * порогов, зависящих от числа товаров, здесь нет.
 */
const SRC = 'src';
const OWN_PAGE = /^src[/\\]pages[/\\]/;

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, out);
    else if (/\.(astro|ts|tsx)$/.test(p)) out.push(p);
  }
  return out;
}

const FILES = walk(SRC).map((p) => ({ path: p, text: readFileSync(p, 'utf8') }));

/** Слои, которые обязаны иметь донора ссылок помимо карты и своего шаблона. */
const LAYERS: { name: string; prefix: string; ownPage: string }[] = [
  { name: 'Аналоги X', prefix: '/alternatives/', ownPage: 'alternatives' },
  { name: 'Сравнения', prefix: '/compare/', ownPage: 'compare' },
  { name: 'Решения', prefix: '/solutions/', ownPage: 'solutions' },
  { name: 'Разделы каталога', prefix: '/catalog/', ownPage: 'catalog' },
  { name: 'Лендинги вендоров', prefix: '/vendors/', ownPage: 'vendors' },
  { name: 'Статьи блога', prefix: '/blog/', ownPage: 'blog' },
];

describe('внутренняя перелинковка: у каждого слоя URL есть донор ссылок', () => {
  for (const layer of LAYERS) {
    it(`${layer.name} (${layer.prefix}) — ссылка есть не только в sitemap`, () => {
      const donors = FILES.filter(({ path, text }) => {
        if (path.includes('sitemap.xml.ts')) return false;
        // Собственный шаблон слоя ссылается сам на себя (canonical, крошки).
        if (OWN_PAGE.test(path) && path.includes(`${layer.ownPage}`)) return false;
        return text.includes(`href="${layer.prefix}`)
          || text.includes(`href={\`${layer.prefix}`)
          || text.includes(`href: \`${layer.prefix}`)
          || text.includes(`href: '${layer.prefix}`)
          || text.includes(`href: "${layer.prefix}`);
      }).map((f) => f.path);
      expect(donors, `слой ${layer.prefix} не получает внутренних ссылок ни с одной страницы`).not.toHaveLength(0);
    });
  }
});
