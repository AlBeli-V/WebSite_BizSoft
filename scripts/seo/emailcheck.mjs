// Проверка письма в браузере: горизонтальная прокрутка, ширина, размеры шрифтов.
// Gmail вырезает <style> из тела письма, поэтому вариант без него проверяется отдельно.
// Запуск: node scripts/seo/emailcheck.mjs <html> <json-out>
import { chromium } from 'playwright';
import fs from 'fs';
import { chromiumExecutable } from './chromium.mjs';

const [file, out] = process.argv.slice(2);
const raw = fs.readFileSync(file, 'utf8');
const variants = [
  ['default', raw],
  ['gmail-no-style', raw.replace(/<style>[\s\S]*?<\/style>/g, '')],
];
const widths = [375, 680];

const executablePath = chromiumExecutable();
const browser = await chromium.launch({
  ...(executablePath ? { executablePath } : {}),
  args: ['--no-sandbox'],
});
const results = [];
for (const [variant, html] of variants) {
  for (const width of widths) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    await page.setContent(html, { waitUntil: 'networkidle' });
    const r = await page.evaluate(() => {
      const sizes = [];
      document.querySelectorAll('*').forEach((el) => {
        if (!el.textContent || !el.textContent.trim()) return;
        const cs = getComputedStyle(el);
        const px = parseFloat(cs.fontSize);
        const meta = el.getAttribute('data-meta') === '1';
        if (px) sizes.push({ px, meta });
      });
      return {
        scrollWidth: document.documentElement.scrollWidth,
        docHeight: document.documentElement.scrollHeight,
        minBody: Math.min(...sizes.filter((s) => !s.meta).map((s) => s.px)),
        minMeta: Math.min(...sizes.filter((s) => s.meta).map((s) => s.px)),
      };
    });
    results.push({ variant, width, ...r, noHorizontalScroll: r.scrollWidth <= width + 2 });
    await page.close();
  }
}
await browser.close();
fs.writeFileSync(out, JSON.stringify(results, null, 1));
for (const r of results) {
  console.log(`  ${r.variant} @${r.width}px: прокрутка ${r.noHorizontalScroll ? 'нет' : 'ЕСТЬ'}, `
    + `высота ${r.docHeight}px, минимальный шрифт текста ${r.minBody}px, подписей ${r.minMeta}px`);
}
