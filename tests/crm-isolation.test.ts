/**
 * Граница между CRM и сайтом.
 *
 * Требование владельца: CRM — независимая опция, а не часть витрины. Проверка
 * механическая, потому что словами такую границу не удержать: через месяц
 * кто-нибудь импортирует «удобную функцию» из src/crm в карточку товара, и
 * поломка CRM начнёт ронять продажи.
 */
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { resolve, join } from 'node:path';

const ROOT = resolve(__dirname, '..');

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (/\.(ts|astro|mjs|js)$/.test(name)) out.push(full);
  }
  return out;
}

/** Страницы и компоненты витрины — всё, кроме админки и её API. */
const siteFiles = [
  ...walk(resolve(ROOT, 'src/pages')),
  ...walk(resolve(ROOT, 'src/components')),
  ...walk(resolve(ROOT, 'src/lib')),
].filter((f) => !f.includes('/pages/admin/') && !f.includes('/pages/api/admin/'));

describe('изоляция CRM', () => {
  it('витрина не импортирует ничего из src/crm', () => {
    const guilty = siteFiles.filter((f) => /from\s+['"][^'"]*\/crm\//.test(readFileSync(f, 'utf8')));
    expect(guilty.map((f) => f.replace(ROOT, ''))).toEqual([]);
  });

  it('модуль CRM не тянет разметку и запросы сайта', () => {
    // Чистые данные и функции: их можно проверить тестом, перенести и выбросить.
    for (const f of walk(resolve(ROOT, 'src/crm'))) {
      const src = readFileSync(f, 'utf8');
      expect(src, `${f}: обращение к DOM`).not.toMatch(/\bdocument\.|window\./);
      expect(src, `${f}: сетевой вызов`).not.toMatch(/\bfetch\(/);
      expect(src, `${f}: импорт из lib сайта`).not.toMatch(/from\s+['"][^'"]*\/lib\//);
    }
  });

  it('форма заявки на сайте работает без CRM', () => {
    const src = readFileSync(resolve(ROOT, 'src/pages/api/lead.ts'), 'utf8');
    expect(src).not.toMatch(/\/crm\//);
    // Единственный след CRM в коде сайта — начальная стадия заявки.
    expect(src).toContain("status: 'new'");
  });
});
