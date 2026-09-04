// Эталонный замер фактической выдачи Яндекса — источник absolute_position.
//
// Зачем (решение руководителя 04.09.2026 по разбору расхождения). Ежедневный
// срез приходит из Yandex Cloud Search API. Тот отдаёт только органические
// документы: рекламы Директа и колдунщиков в ответе нет вовсе. Поэтому по
// срезу можно узнать органическую позицию — и нельзя узнать место, которое
// видит человек. 04.09 отчёт назвал нас первыми там, где в живой выдаче мы
// были вторыми под четырьмя объявлениями.
//
// Сверка с Вебмастером показала, что расхождение системное (медиана +1,9
// позиции, срез оптимистичнее в 76% случаев), но не назвала причину: сдвиг
// неравномерен по глубине, значит вклад дают и реклама, и иное ранжирование
// самого API. Разделить их может только замер настоящей страницы выдачи.
//
// Замер намеренно узкий: два-три десятка запросов раз в неделю. Это эталон
// для калибровки, а не замена срезу — снимать так всё ядро ежедневно нельзя
// ни по нагрузке, ни по риску блокировок.
//
// Пишет reports/seo/serp/<дата>-serp-reference.jsonl, по строке на запрос:
//   organic_position   — место среди органических результатов;
//   absolute_position  — место на странице с учётом рекламы и блоков;
//   ads_before         — сколько рекламных объявлений стоит выше нас;
//   blocks_before      — какие непоисковые блоки стоят выше.
//
// Честность важнее полноты: капча, редирект или пустая страница пишутся в
// строку как ошибка. Выдумывать позицию, которую не удалось увидеть, нельзя —
// такой замер хуже отсутствующего, потому что им будут калибровать.
import { mkdirSync, writeFileSync, readFileSync, existsSync } from 'node:fs';
import { dirname } from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright';
import { chromiumExecutable } from './chromium.mjs';

const OURS = 'biz-soft.pro';
const OUT_DIR = 'reports/seo/serp';
const QUERIES_PATH = 'data/seo/serp-reference-queries.json';
const REGION = 213; // Москва — тот же регион, что у ежедневного среза
const NAV_TIMEOUT_MS = 45_000;
const PAUSE_MS = [7_000, 15_000]; // пауза между запросами, случайная

function pause() {
  const [lo, hi] = PAUSE_MS;
  return new Promise((r) => setTimeout(r, lo + Math.random() * (hi - lo)));
}

function today() {
  return new Date(Date.now() + 3 * 3600 * 1000).toISOString().slice(0, 10);
}

function loadQueries() {
  if (!existsSync(QUERIES_PATH)) {
    throw new Error(`нет списка запросов ${QUERIES_PATH}`);
  }
  const raw = JSON.parse(readFileSync(QUERIES_PATH, 'utf8'));
  const list = Array.isArray(raw) ? raw : raw.queries;
  if (!Array.isArray(list) || list.length === 0) {
    throw new Error(`список запросов в ${QUERIES_PATH} пуст`);
  }
  return list.map(String);
}

// Разбор страницы выдачи. Выполняется в браузере: DOM Яндекса меняется, и
// селекторы держатся на устойчивых признаках — атрибуте рекламы и роли
// органического результата, а не на именах классов.
export function readSerp(ourDomain) {
  const captcha = document.querySelector('.CheckboxCaptcha, form[action*="checkcaptcha"], .AdvancedCaptcha');
  if (captcha) return { error: 'капча: выдача не показана' };

  const items = [];
  const nodes = document.querySelectorAll('#search-result > li, .serp-item, [data-fast-name], .serp-adv-item');
  for (const node of nodes) {
    const isAd = Boolean(
      node.querySelector('[class*="label_type_direct"], .organic__subtitle-link, [data-fast-name="direct"]') ||
      /реклама/i.test(node.querySelector('.Label, .label')?.textContent || '')
    );
    const link = node.querySelector('a[href^="http"]');
    if (!link && !isAd) continue;
    let host = '';
    try { host = new URL(link.href).hostname.replace(/^www\./, ''); } catch { host = ''; }
    items.push({ host, ad: isAd, url: link ? link.href : '' });
  }
  if (items.length === 0) return { error: 'результаты не найдены: разметка выдачи не разобрана' };

  let organic = 0;
  let adsBefore = 0;
  let ourOrganic = null;
  let ourAbsolute = null;
  const blocksBefore = [];
  items.forEach((item, index) => {
    if (!item.ad) organic += 1;
    if (item.host === ourDomain && ourAbsolute === null) {
      ourAbsolute = index + 1;
      ourOrganic = item.ad ? null : organic;
    }
    if (ourAbsolute === null) {
      if (item.ad) adsBefore += 1;
      else if (!item.host) blocksBefore.push('блок без ссылки');
    }
  });
  return {
    organic_position: ourOrganic,
    absolute_position: ourAbsolute,
    ads_before: ourAbsolute === null ? null : adsBefore,
    blocks_before: blocksBefore,
    ads_total: items.filter((i) => i.ad).length,
    results_seen: items.length,
    top: items.slice(0, 10).map((i, n) => ({ position: n + 1, domain: i.host, ad: i.ad })),
  };
}

async function main() {
  const date = process.argv[2] || today();
  const queries = loadQueries();
  const executablePath = chromiumExecutable();
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const context = await browser.newContext({
    locale: 'ru-RU',
    viewport: { width: 1280, height: 900 },
    userAgent:
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  });

  const rows = [];
  for (const query of queries) {
    const url = `https://yandex.ru/search/?text=${encodeURIComponent(query)}&lr=${REGION}`;
    const row = { date, query, region: String(REGION), source: 'yandex-web' };
    const page = await context.newPage();
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT_MS });
      await page.waitForTimeout(2500);
      Object.assign(row, await page.evaluate(readSerp, OURS));
    } catch (e) {
      row.error = `${e.name}: ${e.message}`.slice(0, 200);
    } finally {
      await page.close();
    }
    rows.push(row);
    console.log(
      row.error
        ? `  ✗ «${query}» — ${row.error}`
        : `  «${query}» — органика ${row.organic_position ?? '—'}, ` +
          `абсолют ${row.absolute_position ?? '—'}, реклама выше ${row.ads_before ?? '—'}`
    );
    await pause();
  }
  await browser.close();

  const out = `${OUT_DIR}/${date}-serp-reference.jsonl`;
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, rows.map((r) => JSON.stringify(r)).join('\n') + '\n', 'utf8');

  const measured = rows.filter((r) => !r.error && r.absolute_position !== null);
  const failed = rows.filter((r) => r.error);
  console.log(`\nЗамерено ${measured.length} из ${rows.length}; ошибок ${failed.length}`);
  if (measured.length) {
    const gaps = measured
      .filter((r) => r.organic_position !== null)
      .map((r) => r.absolute_position - r.organic_position)
      .sort((a, b) => a - b);
    const median = gaps.length ? gaps[Math.floor(gaps.length / 2)] : null;
    console.log(`Медиана «абсолют минус органика»: ${median === null ? 'н/д' : `+${median}`}`);
  }
  console.log(out);
  // Полный провал замера — это сбой, а не пустой результат: калибровать
  // нечем, и молча возвращать успех нельзя.
  return measured.length === 0 ? 1 : 0;
}

// Запуск только как программа: проверка парсера импортирует readSerp и
// запускать замер при этом не должна.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().then((code) => process.exit(code)).catch((e) => {
    console.error(e);
    process.exit(1);
  });
}
