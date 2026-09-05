// Рендер PNG-графиков и адаптивных скриншотов письма (Playwright + предустановленный Chromium).
// Использование: node scripts/seo/render.mjs <manifest.json>
// Манифест: [{ "html": "...", "file": "...", "out": "...", "width": 620, "dsf": 2, "fullPage": true }]
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { chromiumExecutable } from './chromium.mjs';

const jobs = JSON.parse(readFileSync(process.argv[2], 'utf-8'));

const executablePath = chromiumExecutable();
const browser = await chromium.launch({
  ...(executablePath ? { executablePath } : {}),
  args: ['--no-sandbox'],
});
for (const job of jobs) {
  const page = await browser.newPage({
    viewport: { width: job.width, height: job.height ?? 800 },
    deviceScaleFactor: job.dsf ?? 2,
  });
  if (job.file) {
    await page.goto('file://' + path.resolve(job.file), { waitUntil: 'load' });
  } else {
    await page.setContent(job.html, { waitUntil: 'load' });
  }
  const target = job.selector ? page.locator(job.selector) : page;
  await target.screenshot({ path: job.out, ...(job.selector ? {} : { fullPage: job.fullPage ?? true }) });
  console.log(`rendered ${job.out} (${job.width}px, dsf ${job.dsf ?? 2})`);
  await page.close();
}
await browser.close();
