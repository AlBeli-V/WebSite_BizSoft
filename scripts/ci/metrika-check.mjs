#!/usr/bin/env node
/**
 * Сторож счётчика: проверяет, что Метрика реально запускается в браузере.
 *
 * Инцидент 04–08.09.2026: файл тега перевели на кэширующий прокси своего
 * домена, и сайт четверо суток не собирал визиты — 45–100 в день до
 * правки, 0–1 после. Ни одна проверка этого не заметила, потому что все
 * они смотрели на код ответа и размер файла: прокси отдавал 200 и файл
 * нужного размера, браузер считал скрипт загруженным, а счётчик не
 * инициализировался. Событие onerror при этом не наступало, поэтому и
 * запасной адрес не подключался.
 *
 * Отсюда предмет проверки: не «отдаётся ли файл», а «дошло ли до вызова
 * ym(id, 'init', …) и ушёл ли хит счётчику».
 *
 * Два режима:
 *   без аргументов — против локальной сборки (стаб Directus + dist).
 *     Тег подменяется заглушкой: проверяется наш код, а не доступность
 *     Яндекса, поэтому шаг годится для CI и не краснеет от чужой сети.
 *   --live <url>   — против живого сайта с настоящим тегом. Именно этот
 *     режим ловит серверные поломки: подмену адреса, битую отдачу
 *     прокси, блокировку запросов счётчика на стороне nginx.
 */
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import { chromium } from 'playwright';

const STUB_PORT = 8097;
const APP_PORT = 4397;
const liveIndex = process.argv.indexOf('--live');
const LIVE = liveIndex !== -1 ? process.argv[liveIndex + 1] : null;
const BASE = LIVE || `http://127.0.0.1:${APP_PORT}`;

// Страницы разных шаблонов: счётчик подключается в общем макете, но
// поломка может быть и в конкретном шаблоне (лишний скрипт, ошибка JS).
const PAGES = ['/', '/vendors/anthropic', '/catalog'];
const TAG_HOST = 'mc.yandex.ru';
const TAG_PATH = '/metrika/tag.js';
// Настоящий tag.js — минифицированный файл в десятки килобайт. Ответ 200
// телом в сотни байт означает не счётчик, а заглушку: так вёл себя прокси
// в инциденте 04–08.09.2026, и ровно поэтому проверка «HTTP 200» одна
// ничего не значит.
const TAG_MIN_BYTES = 20000;

const procs = [];
function start(cmd, args, env, label) {
  const p = spawn(cmd, args, { env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'] });
  p.stderr.on('data', (d) => process.env.METRIKA_CHECK_VERBOSE && console.error(`[${label}] ${d}`));
  procs.push(p);
  return p;
}
async function waitFor(url, tries = 60) {
  for (let i = 0; i < tries; i++) {
    try { const r = await fetch(url); if (r.ok) return true; } catch { /* ждём */ }
    await sleep(250);
  }
  return false;
}

const results = [];
function report(name, ok, got = '') {
  results.push(ok);
  console.log(`  ${ok ? '✅' : '❌'} ${name}${got ? ` — ${got}` : ''}`);
}

/**
 * Заглушка тега для локального режима: ведёт себя как настоящий файл —
 * определяет ym и разбирает очередь, накопленную до загрузки.
 */
const TAG_STUB = `
  window.__tagExecuted = true;
  window.__ymCalls = [];
  var queued = (window.ym && window.ym.a) || [];
  window.ym = function () { window.__ymCalls.push([].slice.call(arguments)); };
  for (var i = 0; i < queued.length; i++) window.__ymCalls.push(queued[i]);
`;

let failed = false;
try {
  if (!LIVE) {
    start('node', ['scripts/ci/stub-directus.mjs', String(STUB_PORT)], {}, 'stub');
    if (!(await waitFor(`http://127.0.0.1:${STUB_PORT}/__stub/health`))) {
      throw new Error('стаб Directus не поднялся');
    }
    start('node', ['./dist/server/entry.mjs'], {
      HOST: '127.0.0.1', PORT: String(APP_PORT),
      DIRECTUS_URL: `http://127.0.0.1:${STUB_PORT}`, DIRECTUS_TOKEN: 'stub-token',
      ADMIN_TOOLS_TOKEN: 'smoke-token-1234567890',
      CATALOG_CACHE_TTL_MS: '0', SMTP_HOST: '', NODE_ENV: 'production',
    }, 'app');
    if (!(await waitFor(`${BASE}/`))) throw new Error('приложение не поднялось');
  }

  const browser = await chromium.launch(
    process.env.METRIKA_CHECK_CHROMIUM ? { executablePath: process.env.METRIKA_CHECK_CHROMIUM } : {},
  );
  console.log(`\nСчётчик в браузере (${LIVE ? 'живой сайт' : 'локальная сборка'}): ${BASE}\n`);

  for (const path of PAGES) {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    const tagRequests = [];
    const tagResponses = [];
    const tagBodies = [];
    const badResources = [];
    const tagHeaders = [];
    const ymRequests = [];
    const hits = [];
    const errors = [];
    page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
    page.on('console', (m) => { if (m.type() === 'error') errors.push(`console: ${m.text()}`); });
    page.on('request', (r) => {
      const u = r.url();
      if (u.includes(TAG_PATH)) tagRequests.push(u);
      if (u.includes(TAG_HOST)) ymRequests.push(u.replace(/^https:\/\/mc\.yandex\.ru/, '').replace(/\?.*/, ''));
      // Хит счётчика: именно он означает, что визит записан.
      if (/mc\.yandex\.ru\/(watch|webvisor)/.test(u)) hits.push(u);
    });
    // Ответ на запрос тега разводит два разных случая: сайт отдал ссылку,
    // но источник недоступен из этой сети (тогда виноват не сайт), и
    // источник ответил, а счётчик всё равно не запустился.
    page.on('response', (r) => {
      if (r.url().includes(TAG_PATH)) {
        tagResponses.push(r.status());
        // Размер тела читается отложенно: обработчик синхронный, а тело
        // приходит позже. Промис складывается и разбирается перед выводом.
        tagBodies.push(r.body().then((b) => b.length).catch(() => -1));
        const h = r.headers();
        tagHeaders.push(`${h['content-type'] || 'без типа'}${h['content-encoding'] ? `, ${h['content-encoding']}` : ''}`);
      }
      // Сбойные ответы прочих ресурсов: без адреса «502» в консоли ничего
      // не объясняет, а объяснять придётся именно его.
      if (r.status() >= 400) badResources.push(`${r.status()} ${r.url().replace(/\?.*/, '')}`);
    });
    page.on('requestfailed', (r) => {
      if (r.url().includes(TAG_PATH)) tagResponses.push(`сбой: ${r.failure()?.errorText || 'неизвестно'}`);
    });

    if (!LIVE) {
      await page.route(`**${TAG_HOST}${TAG_PATH}**`, (route) => route.fulfill({
        status: 200, contentType: 'application/javascript', body: TAG_STUB,
      }));
    }

    await page.goto(BASE + path, { waitUntil: 'networkidle' }).catch((e) => {
      errors.push(`goto: ${e.message}`);
    });
    await page.waitForTimeout(LIVE ? 6000 : 1200);

    const state = await page.evaluate(() => ({
      executed: !!window.__tagExecuted,
      calls: (window.__ymCalls || []).map((a) => String(a[1])),
      ymType: typeof window.ym,
      // У настоящего тега очередь ym.a разобрана и функция заменена своей.
      pending: window.ym && window.ym.a ? window.ym.a.length : 0,
    }));

    const askedTag = tagRequests.filter((u) => u.includes(TAG_HOST));
    report(`${path}: тег запрашивается с домена Метрики`,
      askedTag.length > 0 && tagRequests.every((u) => u.includes(TAG_HOST)),
      tagRequests.map((u) => u.replace(/\?.*/, '')).join(', ') || 'запросов нет');

    if (LIVE) {
      const sizes = (await Promise.all(tagBodies)).filter((n) => n > 0);
      const biggest = sizes.length ? Math.max(...sizes) : 0;
      const delivered = tagResponses.some((r) => r === 200) && biggest >= TAG_MIN_BYTES;
      if (!delivered) {
        // Источник не ответил: из этой сети файл счётчика не приходит.
        // Обвинять сайт нельзя — с той же вероятностью это ограничение
        // сети, откуда идёт проверка. Пункт помечается как невыполненный,
        // но с прямой причиной.
        const why = tagResponses.some((r) => r === 200)
          ? `HTTP 200, но тело ${biggest} Б вместо ≥ ${TAG_MIN_BYTES} Б — это не рабочий тег`
          : `ответы: ${tagResponses.join(', ') || 'ни одного'}`;
        report(`${path}: тег отдан источником`, false, `${why} — проверка счётчика невозможна`);
      } else {
        report(`${path}: тег отдан источником`, true, `HTTP ${tagResponses.join(', ')}, ${biggest} Б`);
        // На живом сайте настоящий тег сам отправляет хит: его наличие и
        // означает «визит записан». Именно этого не было при инциденте.
        report(`${path}: счётчик отправил хит`, hits.length > 0,
          hits.length ? `${hits.length} запрос(ов)` : 'ни одного обращения к watch');
        report(`${path}: ym заменён загруженным тегом`, state.ymType === 'function' && state.pending === 0,
          `typeof ym=${state.ymType}, в очереди ${state.pending}`);
        // Когда тег пришёл целым, а счётчик не запустился, объяснение почти
        // всегда в сообщении браузера про сам домен Метрики — а обычный
        // фильтр ошибок такие сообщения отбрасывает как «чужие». Поэтому
        // здесь они печатаются отдельно: это не вердикт, а диагностика.
        if (hits.length === 0) {
          const ym = errors.filter((e) => /yandex/i.test(e));
          console.log(`     тип ответа тега: ${tagHeaders.join(' | ') || 'нет данных'}`);
          console.log(`     обращения к домену Метрики: ${[...new Set(ymRequests)].join(', ') || 'нет'}`);
          console.log(`     сообщения про Яндекс: ${ym.slice(0, 3).join(' | ') || 'нет'}`);
        }
      }
    } else {
      report(`${path}: файл тега исполнился`, state.executed);
      report(`${path}: вызван init счётчика`, state.calls.includes('init'),
        state.calls.join(', ') || 'вызовов нет');
    }

    const own = errors.filter((e) => !/mc\.yandex|googletagmanager|google-analytics|net::ERR_/.test(e));
    report(`${path}: без ошибок JS`, own.length === 0,
      own.length ? `${own.slice(0, 2).join(' | ')}${badResources.length ? ` [${badResources.slice(0, 3).join(', ')}]` : ''}` : 'чисто');

    await ctx.close();
  }

  await browser.close();
} catch (e) {
  console.error(`\nПроверка не выполнена: ${e.message}`);
  failed = true;
} finally {
  for (const p of procs) p.kill('SIGTERM');
}

const bad = results.filter((r) => !r).length;
console.log(`\nИтог: ${results.length - bad}/${results.length} пройдено, ${bad} не пройдено\n`);
process.exit(failed || bad ? 1 : 0);
