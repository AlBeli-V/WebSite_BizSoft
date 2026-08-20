/**
 * Смоук-проверки собранного сайта против стаба Directus.
 *
 * Поднимает scripts/ci/stub-directus.mjs и dist/server/entry.mjs, затем
 * проверяет HTTP-контракт: коды ответов при живой и при упавшей БД, состав
 * sitemap, noindex служебных страниц, 301 со старых слагов.
 *
 * Запуск: pnpm smoke            — блокирующий режим (падает при расхождении)
 *         pnpm smoke --baseline — только отчёт, всегда код 0
 *
 * Требует предварительной сборки (pnpm build).
 */
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const BASELINE = process.argv.includes('--baseline');
const STUB_PORT = 8099;
const APP_PORT = 4399;
const APP = `http://127.0.0.1:${APP_PORT}`;
const STUB = `http://127.0.0.1:${STUB_PORT}`;

const checks = [];
/** @param {string} name @param {() => Promise<{ok: boolean, got: string}>} fn */
function check(name, fn) { checks.push({ name, fn }); }

async function req(path, opts = {}) {
  const res = await fetch(APP + path, { redirect: 'manual', ...opts });
  const body = res.status === 204 ? '' : await res.text();
  return { status: res.status, body, headers: res.headers };
}
async function setMode(mode) {
  await fetch(`${STUB}/__stub/mode?mode=${mode}`);
  // кэш каталога живёт 60 с — смоук запускается с CATALOG_CACHE_TTL_MS=0
}

// ── БД жива ──────────────────────────────────────────────────────────────
check('главная отдаёт 200', async () => {
  const r = await req('/');
  return { ok: r.status === 200, got: String(r.status) };
});
check('каталог отдаёт 200', async () => {
  const r = await req('/catalog');
  return { ok: r.status === 200, got: String(r.status) };
});
check('раздел каталога отдаёт 200 и содержит товар', async () => {
  const r = await req('/catalog/ai');
  return { ok: r.status === 200 && r.body.includes('ChatGPT Business'), got: `${r.status}, товар ${r.body.includes('ChatGPT Business') ? 'есть' : 'НЕТ'}` };
});
check('карточка товара отдаёт 200', async () => {
  const r = await req('/product/chatgpt-business');
  return { ok: r.status === 200, got: String(r.status) };
});
check('несуществующий товар отдаёт 404', async () => {
  const r = await req('/product/net-takogo-tovara');
  return { ok: r.status === 404, got: String(r.status) };
});
check('устаревший слаг отдаёт 301 на актуальный', async () => {
  const r = await req('/product/chatgpt-team');
  const loc = r.headers.get('location') || '';
  return { ok: r.status === 301 && loc.endsWith('/product/chatgpt-business'), got: `${r.status} → ${loc || '—'}` };
});
check('sitemap отдаёт 200 и содержит товар', async () => {
  const r = await req('/sitemap.xml');
  return { ok: r.status === 200 && r.body.includes('/product/chatgpt-business'), got: `${r.status}, товар ${r.body.includes('/product/chatgpt-business') ? 'есть' : 'НЕТ'}` };
});
check('sitemap не содержит noindex-товар', async () => {
  const r = await req('/sitemap.xml');
  return { ok: !r.body.includes('/product/tovar-noindex'), got: r.body.includes('/product/tovar-noindex') ? 'ЕСТЬ (не должно)' : 'нет' };
});
check('sitemap не содержит плагин JB-PLG', async () => {
  const r = await req('/sitemap.xml');
  return { ok: !r.body.includes('/product/plagin-skrytyj'), got: r.body.includes('/product/plagin-skrytyj') ? 'ЕСТЬ (не должно)' : 'нет' };
});
check('sitemap не содержит черновик', async () => {
  const r = await req('/sitemap.xml');
  return { ok: !r.body.includes('/product/chernovik'), got: r.body.includes('/product/chernovik') ? 'ЕСТЬ (не должно)' : 'нет' };
});
check('sitemap: нет повторяющихся <loc>', async () => {
  const r = await req('/sitemap.xml');
  const locs = [...r.body.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
  const dup = locs.filter((l, i) => locs.indexOf(l) !== i);
  return { ok: dup.length === 0, got: dup.length ? `дубли: ${[...new Set(dup)].join(', ')}` : 'нет' };
});
check('sitemap: /vendors присутствует', async () => {
  const r = await req('/sitemap.xml');
  return { ok: /<loc>[^<]*\/vendors<\/loc>/.test(r.body), got: /<loc>[^<]*\/vendors<\/loc>/.test(r.body) ? 'есть' : 'НЕТ' };
});
check('админ-страница помечена noindex', async () => {
  const r = await req('/admin/prices');
  return { ok: r.body.includes('noindex'), got: r.body.includes('noindex') ? 'есть' : 'НЕТ' };
});
check('админ-API без токена отдаёт 401', async () => {
  const r = await req('/api/admin/products');
  return { ok: r.status === 401, got: String(r.status) };
});
check('цели Метрики доезжают до браузера на карточке товара', async () => {
  // Код целей лежит в общем чанке и подключается как модуль, поэтому
  // ищем его не в самой разметке, а в подключаемых ею скриптах.
  const r = await req('/product/chatgpt-business');
  if (r.body.includes('reachGoal')) return { ok: true, got: 'инлайн' };
  // Модуль целей общий, поэтому подключается вложенным импортом: обходим
  // граф импортов от страницы вглубь.
  // Внутри чанков импорты относительные («./analytics.abc.js»), в разметке —
  // абсолютные. Приводим к одному виду и обходим граф вглубь.
  const RE = /["'(](?:\/_astro\/|\.\/)([\w.\-]+\.js)["')]/g;
  const seen = new Set();
  const queue = [...r.body.matchAll(RE)].map((m) => m[1]);
  while (queue.length) {
    const file = queue.shift();
    if (seen.has(file)) continue;
    seen.add(file);
    const chunk = await req(`/_astro/${file}`);
    if (chunk.status !== 200) continue;
    if (chunk.body.includes('reachGoal')) return { ok: true, got: `чанк ${file}` };
    for (const m of chunk.body.matchAll(RE)) queue.push(m[1]);
  }
  return { ok: false, got: `НЕТ (обойдено чанков: ${seen.size})` };
});
check('форма заявки: пустой POST отклоняется с 422', async () => {
  const r = await req('/api/lead', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  return { ok: r.status === 422, got: String(r.status) };
});

// ── БД недоступна ────────────────────────────────────────────────────────
check('[БД упала] карточка товара отдаёт 503, а не 404', async () => {
  await setMode('fail');
  const r = await req('/product/chatgpt-business');
  await setMode('ok');
  return { ok: r.status === 503, got: String(r.status) };
});
check('[БД упала] sitemap отдаёт 503, а не усечённый 200', async () => {
  await setMode('fail');
  const r = await req('/sitemap.xml');
  await setMode('ok');
  return { ok: r.status === 503, got: String(r.status) };
});
check('[БД упала] каталог отдаёт 503, а не пустой 200', async () => {
  await setMode('fail');
  const r = await req('/catalog');
  await setMode('ok');
  return { ok: r.status === 503, got: String(r.status) };
});
check('[БД зависла] карточка товара отвечает за 15 с (таймаут)', async () => {
  await setMode('hang');
  const t0 = Date.now();
  let status = 'таймаут теста';
  try {
    const r = await Promise.race([
      req('/product/chatgpt-business').then((x) => String(x.status)),
      sleep(15_000).then(() => 'нет ответа за 15 с'),
    ]);
    status = r;
  } catch (e) { status = `ошибка: ${e.message}`; }
  const ms = Date.now() - t0;
  await setMode('ok');
  return { ok: status === '503' || status === '504', got: `${status} за ${(ms / 1000).toFixed(1)} с` };
});

// ── запуск ───────────────────────────────────────────────────────────────
const procs = [];
function start(cmd, args, env, label) {
  const p = spawn(cmd, args, { env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'] });
  p.stdout.on('data', (d) => process.env.SMOKE_VERBOSE && console.log(`[${label}] ${d}`));
  p.stderr.on('data', (d) => process.env.SMOKE_VERBOSE && console.error(`[${label}] ${d}`));
  procs.push(p);
  return p;
}
async function waitFor(url, tries = 60) {
  for (let i = 0; i < tries; i++) {
    try { const r = await fetch(url); if (r.ok) return true; } catch { /* ещё не поднялся */ }
    await sleep(250);
  }
  return false;
}

let failed = 0;
try {
  start('node', ['scripts/ci/stub-directus.mjs', String(STUB_PORT)], {}, 'stub');
  if (!(await waitFor(`${STUB}/__stub/health`))) throw new Error('стаб Directus не поднялся');

  start('node', ['./dist/server/entry.mjs'], {
    HOST: '127.0.0.1', PORT: String(APP_PORT),
    DIRECTUS_URL: STUB, DIRECTUS_TOKEN: 'stub-token',
    ADMIN_TOOLS_TOKEN: 'smoke-token-1234567890',
    CATALOG_CACHE_TTL_MS: '0', // без кэша, иначе режим fail не виден сразу
    SMTP_HOST: '', NODE_ENV: 'production',
  }, 'app');
  if (!(await waitFor(`${APP}/`))) throw new Error('приложение не поднялось');

  console.log(`\nСмоук-проверки (${BASELINE ? 'базовый замер' : 'блокирующий режим'})\n`);
  for (const c of checks) {
    let ok = false, got = '';
    try { ({ ok, got } = await c.fn()); } catch (e) { got = `ошибка: ${e.message}`; }
    if (!ok) failed++;
    console.log(`  ${ok ? '✅' : '❌'} ${c.name}${got ? ` — ${got}` : ''}`);
  }
  console.log(`\nИтог: ${checks.length - failed}/${checks.length} пройдено, ${failed} не пройдено\n`);
} catch (e) {
  console.error(`Смоук не запустился: ${e.message}`);
  failed = failed || 1;
} finally {
  for (const p of procs) p.kill('SIGKILL');
}
process.exit(BASELINE ? 0 : failed ? 1 : 0);
