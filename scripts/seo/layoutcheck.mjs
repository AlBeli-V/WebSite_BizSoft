// Проверка вёрстки веб-отчёта в браузере: страница не едет вбок, и ни один
// блок не вылезает за свою рамку.
//
// Откуда проверка. 09.09.2026 руководитель прислал снимок отчёта с телефона:
// спарклайн плитки KPI выходил за карточку. Разбор показал, что дефект был не
// один и не случайный — фиксированная ширина внутри гибкого контейнера
// (спарклайн 96 px в плитке 140 px, сетка теплокарты 432 px, колонка грида с
// минимумом шире экрана). Ни одна проверка конвейера этого не ловила:
// emailcheck смотрит письмо, а прокрутка страницы возникала только на ширинах,
// которых никто не открывал в CI.
//
// Что считается ошибкой:
//   1) document.scrollWidth больше ширины экрана — страница едет вбок;
//   2) элемент с видимым переполнением шире своей рамки. Блоки, которые
//      прокручиваются намеренно (.kit-scroll, .scroll — таблицы и теплокарта),
//      и всё, что лежит внутри них, не считаются: им переполнение положено.
//
// Запуск: node scripts/seo/layoutcheck.mjs <html> <json-out> [ширины через запятую]
import { chromium } from 'playwright';
import fs from 'fs';
import { chromiumExecutable } from './chromium.mjs';

const [file, out, widthsArg] = process.argv.slice(2);
if (!file || !out) {
  console.error('Использование: node scripts/seo/layoutcheck.mjs <html> <json-out> [ширины]');
  process.exit(2);
}
// 320 — самый узкий телефон в обращении, 430 — ширина, на которой сломалась
// плитка в снимке руководителя, 1080 — предел .wrap веб-отчёта.
const widths = (widthsArg ? widthsArg.split(',') : ['320', '390', '430', '768', '1024', '1440'])
  .map(Number);
const TOLERANCE = 1;

const executablePath = chromiumExecutable();
const browser = await chromium.launch({
  ...(executablePath ? { executablePath } : {}),
  args: ['--no-sandbox'],
});

const results = [];
for (const width of widths) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  await page.goto('file://' + fs.realpathSync(file), { waitUntil: 'load' });
  const r = await page.evaluate((tol) => {
    // Законно переполняются только блоки с настоящей прокруткой (auto/scroll):
    // таблица и теплокарта прокручиваются внутри себя. overflow:hidden законным
    // не считается — это не прокрутка, а потеря содержимого, и она проверке
    // подлежит: страховочная обрезка плитки не должна прятать дефект вёрстки.
    const scrollable = (el) => {
      for (let node = el; node; node = node.parentElement) {
        const ox = getComputedStyle(node).overflowX;
        if (ox === 'auto' || ox === 'scroll') return true;
      }
      return false;
    };
    // Обрезка многоточием — приём, а не дефект: строка сознательно
    // укорачивается до ширины колонки и читателю виден знак «…».
    const ellipsised = (el) => getComputedStyle(el).textOverflow === 'ellipsis';
    const bad = [];
    document.querySelectorAll('*').forEach((el) => {
      if (el.clientWidth === 0) return;
      if (el.scrollWidth - el.clientWidth <= tol) return;
      if (scrollable(el) || ellipsised(el)) return;
      const cls = (el.getAttribute('class') || '').trim();
      bad.push({
        selector: el.tagName.toLowerCase() + (cls ? '.' + cls.split(/\s+/).join('.') : ''),
        overflow: el.scrollWidth - el.clientWidth,
      });
    });
    // Одинаковые селекторы схлопываются: сотня строк таблицы — это один дефект.
    const bySelector = new Map();
    for (const b of bad) {
      const seen = bySelector.get(b.selector);
      if (!seen || seen.overflow < b.overflow) bySelector.set(b.selector, b);
    }
    return {
      scrollWidth: document.documentElement.scrollWidth,
      overflowing: [...bySelector.values()].sort((a, b) => b.overflow - a.overflow).slice(0, 12),
    };
  }, TOLERANCE);
  results.push({
    width,
    scrollWidth: r.scrollWidth,
    noHorizontalScroll: r.scrollWidth <= width + TOLERANCE,
    overflowing: r.overflowing,
    noOverflowingBlocks: r.overflowing.length === 0,
  });
  await page.close();
}
await browser.close();

fs.writeFileSync(out, JSON.stringify({ file, results }, null, 1));

let failed = 0;
for (const r of results) {
  const scroll = r.noHorizontalScroll ? 'нет' : `ЕСТЬ (${r.scrollWidth}px)`;
  const blocks = r.noOverflowingBlocks ? 'нет'
    : r.overflowing.map((o) => `${o.selector} +${o.overflow}px`).join('; ');
  console.log(`  @${r.width}px: прокрутка страницы ${scroll}, блоки за рамкой: ${blocks}`);
  if (!r.noHorizontalScroll || !r.noOverflowingBlocks) failed += 1;
}
if (failed) {
  console.error(`Вёрстка отчёта сломана на ${failed} из ${results.length} ширин: ${file}`);
  process.exit(1);
}
console.log(`Вёрстка отчёта в порядке на всех ${results.length} ширинах: ${file}`);
