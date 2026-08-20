/**
 * Обход официального магазина ManageEngine.
 *
 * Запускается только на раннере GitHub (см. .github/workflows/ops-me-crawl.yml):
 * у сессии ассистента нет egress к сайтам вендоров, а страницы магазина
 * рисует JavaScript, поэтому нужен полноценный браузер, а не HTTP-парсер.
 *
 *   STAGE=discovery node scripts/sources/me-crawl.mjs   — карта магазина
 *   STAGE=details   node scripts/sources/me-crawl.mjs   — страницы продуктов
 *
 * Окно волны задаётся OFFSET и LIMIT; details.json дополняется, а не
 * перезаписывается, поэтому волны можно гнать по очереди.
 *
 * Ничего не отправляем и не покупаем: только чтение. Частота ограничена,
 * каждый снимок сохраняется с URL и датой, чтобы у любого значения в каталоге
 * был воспроизводимый источник.
 */
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync, readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';

const STAGE = process.env.STAGE || 'discovery';
const LIMIT = Number(process.env.LIMIT || 25);
const OFFSET = Number(process.env.OFFSET || 0); // окно волны в списке ссылок
// Каталог снимков привязан к дате. Волны идут не один день, поэтому дату
// можно задать явно — иначе details не найдёт вчерашний discovery.json.
const DAY = (process.env.DAY || '').trim() || new Date().toISOString().slice(0, 10);
const OUT = resolve(`data/sources/manageengine/${DAY}`);
const STORE = 'https://store.manageengine.com/';
const PAUSE_MS = 1500; // вежливая пауза между страницами

const log = [];
function say(line) { console.log(line); log.push(line); }

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const snapId = (url) => createHash('sha1').update(url).digest('hex').slice(0, 12);

/** Снимок страницы: HTML + текст + метаданные источника. */
async function snapshot(page, url, dir, tab = null) {
  const html = await page.content();
  const text = await page.evaluate(() => document.body?.innerText || '');
  const id = snapId(tab ? `${url}#tab=${tab}` : url);
  mkdirSync(dir, { recursive: true });
  writeFileSync(`${dir}/${id}.html`, html);
  writeFileSync(`${dir}/${id}.txt`, text);
  return {
    source_snapshot_id: id,
    source_url: url,
    source_checked_at: new Date().toISOString(),
    ...(tab ? { tab } : {}),
  };
}

/**
 * Переключатели прайса на странице магазина: «Annual Subscription /
 * Perpetual» и «Cloud / On-Premise». Обходчик по умолчанию снимает только
 * активную вкладку, и вечные лицензии в снимок не попадают. Здесь мы
 * находим сами переключатели по тексту — вслепую кликать по странице
 * магазина нельзя.
 */
const TAB_LABELS = [
  'Annual Subscription', 'Perpetual', 'Subscription',
  'On-Premise', 'On-Premises', 'Cloud',
];

async function findTabs(page) {
  return page.evaluate((labels) => {
    const out = [];
    const nodes = document.querySelectorAll('a,button,li,span,label,div[role="tab"]');
    for (const el of nodes) {
      const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
      if (!labels.includes(text)) continue;
      // Переключатель — короткий кликабельный элемент, а не абзац с тем же словом.
      if (el.children.length > 1) continue;
      const box = el.getBoundingClientRect();
      if (box.width < 20 || box.height < 10) continue;
      if (out.some((o) => o.text === text)) continue;
      out.push({ text, tag: el.tagName.toLowerCase() });
    }
    return out;
  }, TAB_LABELS);
}

/** Кликнуть по вкладке с заданным текстом. Возвращает true, если получилось. */
async function clickTab(page, text) {
  const target = page.locator(
    `a:text-is("${text}"), button:text-is("${text}"), li:text-is("${text}"), span:text-is("${text}"), label:text-is("${text}")`
  ).first();
  try {
    await target.click({ timeout: 5000 });
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await sleep(1200);
    return true;
  } catch {
    return false;
  }
}

async function open(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  // Магазин дорисовывает цены и списки после загрузки — ждём сетевого затишья.
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
  await sleep(800);
}

/** Этап 1: собрать с главной страницы разделы и ссылки на продукты. */
async function discovery(page) {
  say(`магазин: ${STORE}`);
  await open(page, STORE);
  const meta = await snapshot(page, STORE, `${OUT}/discovery`);

  const links = await page.evaluate(() => {
    const seen = new Map();
    for (const a of document.querySelectorAll('a[href]')) {
      const href = a.getAttribute('href') || '';
      if (!href || href.startsWith('#') || href.startsWith('mailto:')) continue;
      let abs;
      try { abs = new URL(href, location.href).toString(); } catch { continue; }
      if (!abs.includes('manageengine.com')) continue;
      const label = (a.textContent || '').replace(/\s+/g, ' ').trim();
      if (!seen.has(abs)) seen.set(abs, { url: abs, label, store: abs.includes('store.manageengine.com') });
    }
    return [...seen.values()];
  });

  const store = links.filter((l) => l.store && l.url !== STORE);
  say(`ссылок всего: ${links.length}, из них внутрь магазина: ${store.length}`);

  // Заголовки разделов магазина — для функциональных групп.
  const sections = await page.evaluate(() =>
    [...document.querySelectorAll('h1,h2,h3')]
      .map((h) => (h.textContent || '').replace(/\s+/g, ' ').trim())
      .filter((t) => t && t.length < 120));
  say(`заголовков разделов: ${sections.length}`);

  mkdirSync(OUT, { recursive: true });
  writeFileSync(`${OUT}/discovery.json`, JSON.stringify(
    { collected_at: new Date().toISOString(), store: STORE, meta, sections, links: store }, null, 1));

  say('');
  say('--- первые 40 ссылок магазина ---');
  for (const l of store.slice(0, 40)) say(`  ${l.label || '(без текста)'} → ${l.url}`);
}

/** Этап 2: пройти по продуктовым ссылкам и снять коммерческие данные. */
async function details(page) {
  const file = `${OUT}/discovery.json`;
  if (!existsSync(file)) {
    say(`нет ${file} — сначала запустите этап discovery за сегодняшнюю дату`);
    return;
  }
  const { links } = JSON.parse(readFileSync(file, 'utf8'));
  const targets = links.slice(OFFSET, OFFSET + LIMIT);
  say(`страниц к обходу: ${targets.length} из ${links.length} (окно ${OFFSET}–${OFFSET + targets.length})`);

  // Волны докладываются в один и тот же details.json: перезапись потеряла бы
  // предыдущие окна.
  const prev = existsSync(`${OUT}/details.json`)
    ? JSON.parse(readFileSync(`${OUT}/details.json`, 'utf8')).rows || []
    : [];
  const rows = prev.filter((r) => !targets.some((t) => t.url === r.url));
  if (prev.length) say(`уже снято ранее: ${prev.length}, оставляем ${rows.length}`);

  // Снятие коммерческих данных с текущего состояния страницы. Вызывается и
  // для активной вкладки, и после клика по каждой из остальных.
  const scrape = () => {
    const txt = (el) => (el?.textContent || '').replace(/\s+/g, ' ').trim();
    const body = document.body?.innerText || '';
    return {
      title: document.title,
      h1: txt(document.querySelector('h1')),
      // Денежные суммы с окружением — цену без контекста использовать нельзя.
      money: (body.match(/.{0,70}(?:US\$|\$|₹|€)\s?[0-9][0-9,. ]*.{0,70}/g) || []).slice(0, 60),
      editions: [...new Set((body.match(/\b(Standard|Professional|Enterprise|Free|Premium)\s+Edition\b/g) || []))],
      metrics: [...new Set((body.match(/\b\d[\d,]*\s+(Technicians?|Users?|Devices?|Endpoints?|Servers?|Agents?|Nodes?|Domain Controllers?|Mailboxes?)\b/gi) || []))].slice(0, 60),
      terms: [...new Set((body.match(/\b(Annual Subscription|Perpetual|Subscription|Maintenance|AMS|Renewal)\b/gi) || []))],
      deployment: /\b(On-?Prem|Cloud|SaaS)\b/i.test(body)
        ? [...new Set((body.match(/\b(On-?Premises?|On-?Prem|Cloud|SaaS)\b/gi) || []))] : [],
    };
  };

  for (const [i, l] of targets.entries()) {
    try {
      await open(page, l.url);
      const meta = await snapshot(page, l.url, `${OUT}/details`);
      const data = await page.evaluate(scrape);

      // Вкладки прайса. Активную мы уже сняли выше; кликаем по остальным и
      // снимаем каждую отдельно — иначе вечные лицензии и вторая схема
      // поставки в снимок не попадают вовсе.
      const tabs = [];
      const found = await findTabs(page);
      for (const t of found) {
        if (!(await clickTab(page, t.text))) continue;
        const tabMeta = await snapshot(page, l.url, `${OUT}/details`, t.text);
        const tabData = await page.evaluate(scrape);
        if (tabData.money.length) tabs.push({ ...tabMeta, ...tabData });
        await sleep(PAUSE_MS);
      }

      rows.push({ ...l, ...meta, ...data, tabs });
      say(`${i + 1}/${targets.length} ${l.url}`);
      say(`    редакции: ${data.editions.join(', ') || '—'}`);
      say(`    метрики: ${data.metrics.slice(0, 6).join('; ') || '—'}`);
      say(`    сумм найдено: ${data.money.length}`);
      say(`    вкладок снято: ${tabs.length ? tabs.map((t) => t.tab).join(', ') : '—'}`);
    } catch (e) {
      say(`${i + 1}/${targets.length} ${l.url} → ошибка: ${e.message}`);
      rows.push({ ...l, error: e.message });
    }
    await sleep(PAUSE_MS);
  }

  writeFileSync(`${OUT}/details.json`, JSON.stringify(
    { collected_at: new Date().toISOString(), count: rows.length, rows }, null, 1));
  say('');
  say(`снято страниц: ${rows.filter((r) => !r.error).length}, с ошибкой: ${rows.filter((r) => r.error).length}`);
}

const browser = await chromium.launch();
const page = await browser.newPage({
  userAgent: 'Mozilla/5.0 (compatible; BIZSoft-catalog-bot; +https://biz-soft.pro)',
  viewport: { width: 1440, height: 2000 },
});
try {
  if (STAGE === 'discovery') await discovery(page);
  else if (STAGE === 'details') await details(page);
  else say(`неизвестный этап: ${STAGE}`);
} finally {
  await browser.close();
  writeFileSync('/tmp/me-crawl-summary.txt', log.join('\n'));
}
