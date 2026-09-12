/**
 * Снимки живой карточки для сверки с утверждённым макетом.
 *
 * Только чтение публичных страниц: сессия в прод не ходит, а разбирать
 * расхождение композиции по HTML вслепую дороже, чем посмотреть картинку.
 * Кроме снимков сохраняется сам HTML — по нему видно, какие блоки пришли
 * на страницу, а какие нет.
 */
import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const SITE = (process.env.SITE || 'https://biz-soft.pro').replace(/\/$/, '');
const paths = (process.env.PATHS || '').split(',').map((s) => s.trim()).filter(Boolean);
if (paths.length === 0) throw new Error('PATHS пуст');

await mkdir('shots', { recursive: true });
const browser = await chromium.launch();
for (const p of paths) {
  const name = p.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '') || 'root';
  for (const [w, h, tag] of [[1440, 900, 'desk'], [390, 844, 'phone']]) {
    const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
    const res = await page.goto(`${SITE}${p}`, { waitUntil: 'networkidle', timeout: 60000 });
    // Плашка cookie перекрывает первый экран и мешает сверять композицию.
    await page.evaluate(() => document.querySelector('.cookie')?.remove());
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    console.log(`${p} ${tag} status=${res?.status()} overflow=${overflow}px`);
    await page.screenshot({ path: `shots/${name}-${tag}.png`, fullPage: true });
    if (tag === 'desk') await writeFile(`shots/${name}.html`, await page.content(), 'utf8');
    await page.close();
  }
}
await browser.close();
