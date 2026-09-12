/**
 * Вёрстка, которая не умеет сжиматься, — источник одной и той же поломки.
 *
 * Колонка сетки с пиксельным минимумом (`minmax(260px, 1fr)`) не сжимается
 * ниже своих 260px. Когда на экране остаётся меньше, сетка распирает
 * страницу, документ становится шире экрана, и Safari на телефоне съезжает
 * к левому краю с пустой полосой справа — сайт выглядит сломанным.
 * Так дефект и нашёлся: глазами руководителя на iPhone 12.09.2026.
 *
 * Лечится идиомой `minmax(min(100%, 260px), 1fr)`: там, где места хватает,
 * поведение прежнее, а на узком экране колонка сжимается до ширины родителя.
 *
 * Проверка статическая и грубая по замыслу — она стережёт саму идиому.
 * Измеряет живую ширину браузерная проверка `pnpm check:mobile`
 * (scripts/ci/mobile-layout.mjs) и сторож живого сайта ops-mobile-layout.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';

const ROOT = resolve(__dirname, '..');

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (full.endsWith('.astro')) out.push(full);
  }
  return out;
}

describe('сетки сжимаются на узком экране', () => {
  it('пиксельный минимум колонки всегда обёрнут в min(100%, …)', () => {
    const bad: string[] = [];
    for (const file of walk(resolve(ROOT, 'src'))) {
      const text = readFileSync(file, 'utf8');
      text.split('\n').forEach((line, i) => {
        // minmax(min(100%, 260px), 1fr) — правильная форма, её пропускаем.
        for (const m of line.matchAll(/minmax\(\s*(\d+)px/g)) {
          bad.push(`${file.slice(ROOT.length + 1)}:${i + 1} — minmax(${m[1]}px, …)`);
        }
      });
    }
    expect(bad, `колонка не сожмётся на телефоне:\n${bad.join('\n')}`).toEqual([]);
  });
});

describe('страховка от распирающего содержимого', () => {
  const css = readFileSync(resolve(ROOT, 'src/styles/global.css'), 'utf8');

  it('длинное слово без пробелов переносится, а не раздвигает страницу', () => {
    // Артикулы подарочных карт вида APP-STORE-ITUNES-GIFT-CARD-RU-1000 и
    // названия вроде Enterprise(Distributed) длиннее любой колонки на
    // телефоне. Именно anywhere: break-word разрывает слово, но ширину
    // колонки не уменьшает — сетка всё равно растягивается под слово.
    expect(css).toMatch(/overflow-wrap:\s*anywhere/);
    expect(css).not.toMatch(/overflow-wrap:\s*break-word/);
  });

  it('картинка не шире своей колонки', () => {
    expect(css).toMatch(/img[\s\S]{0,80}max-width:\s*100%/);
  });
});
