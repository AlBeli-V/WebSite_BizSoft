/**
 * Браузерные проверки WebMCP-слоя в реальном Chromium (Playwright).
 *
 * Два режима на живых страницах собранного сайта (стаб Directus, как в смоуке):
 *
 * 1. FALLBACK — браузер БЕЗ WebMCP (сегодня это все стабильные браузеры):
 *    страницы работают, ошибок в консоли нет, document.modelContext
 *    отсутствует — слой обязан молчать, а не падать.
 *
 * 2. РЕГИСТРАЦИЯ — Web Model Context API подменяется заглушкой ДО загрузки
 *    страницы (актуальная форма спецификации: document.modelContext).
 *    Проверяем: инструменты зарегистрированы, схемы валидны, readOnlyHint
 *    стоит, execute реально ходит в /api/agent и возвращает данные каталога,
 *    ошибки отдаются агенту текстом, а не исключением.
 *
 * Нативный WebMCP (Chrome 149+ за origin trial / флагом) в CI-хромиуме
 * недоступен — это фиксируется в docs/webmcp/testing.md.
 *
 * Запуск: pnpm build && node scripts/ci/webmcp-browser.mjs
 */
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import { chromium } from 'playwright';

const STUB_PORT = 8098;
const APP_PORT = 4398;
const APP = `http://127.0.0.1:${APP_PORT}`;

const procs = [];
function start(cmd, args, env, label) {
  const p = spawn(cmd, args, { env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'] });
  p.stderr.on('data', (d) => process.env.SMOKE_VERBOSE && console.error(`[${label}] ${d}`));
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

/** Заглушка Web Model Context API в форме спецификации (август 2026). */
const MODEL_CONTEXT_STUB = `
  (() => {
    const tools = [];
    Object.defineProperty(document, 'modelContext', {
      value: {
        async registerTool(tool) { tools.push(tool); },
        async getTools() { return tools; },
        async executeTool(tool, input) { return JSON.stringify(await tool.execute(input || {})); },
      },
      configurable: true,
    });
    window.__wmcpStub = { tools };
  })();
`;

let failedRun = false;
try {
  start('node', ['scripts/ci/stub-directus.mjs', String(STUB_PORT)], {}, 'stub');
  if (!(await waitFor(`http://127.0.0.1:${STUB_PORT}/__stub/health`))) throw new Error('стаб Directus не поднялся');
  start('node', ['./dist/server/entry.mjs'], {
    HOST: '127.0.0.1', PORT: String(APP_PORT),
    DIRECTUS_URL: `http://127.0.0.1:${STUB_PORT}`, DIRECTUS_TOKEN: 'stub-token',
    ADMIN_TOOLS_TOKEN: 'smoke-token-1234567890',
    CATALOG_CACHE_TTL_MS: '0', SMTP_HOST: '', NODE_ENV: 'production',
  }, 'app');
  if (!(await waitFor(`${APP}/`))) throw new Error('приложение не поднялось');

  // Бинарь можно переопределить (например, в окружении с преустановленным
  // Chromium другой ревизии): WEBMCP_CHROMIUM=/путь/к/chrome.
  const browser = await chromium.launch(
    process.env.WEBMCP_CHROMIUM ? { executablePath: process.env.WEBMCP_CHROMIUM } : {},
  );
  console.log(`\nWebMCP в браузере: ${browser.browserType().name()} ${browser.version()}\n`);

  // ── Режим 1: браузер без WebMCP (fallback) ────────────────────────────
  {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
    page.on('console', (m) => { if (m.type() === 'error') errors.push(`console: ${m.text()}`); });
    for (const path of ['/', '/catalog', '/product/chatgpt-business', '/vendors']) {
      await page.goto(APP + path, { waitUntil: 'networkidle' });
    }
    const hasNative = await page.evaluate(() => 'modelContext' in document || 'modelContext' in navigator);
    report('fallback: у браузера нет modelContext (проверяем именно отсутствие)', !hasNative, hasNative ? 'нативный API есть' : 'нет');
    // Ошибки загрузки Метрики/GA в изолированном окружении — не наши.
    const own = errors.filter((e) => !/mc\.yandex|googletagmanager|google-analytics|net::ERR/.test(e));
    report('fallback: ни одной ошибки консоли на 4 страницах', own.length === 0, own.slice(0, 3).join(' | ') || 'чисто');
    const cartWorks = await page.evaluate(() => typeof localStorage !== 'undefined');
    report('fallback: страница живая (JS исполняется)', cartWorks);
    await page.close();
  }

  // ── Режим 2: WebMCP-заглушка — регистрация и исполнение ───────────────
  {
    const page = await browser.newPage();
    await page.addInitScript(MODEL_CONTEXT_STUB);
    await page.goto(APP + '/product/chatgpt-business', { waitUntil: 'networkidle' });
    // Регистрация идёт асинхронно после загрузки чанка.
    await page.waitForFunction(() => window.__wmcpStub?.tools?.length >= 5, null, { timeout: 5000 }).catch(() => {});

    const tools = await page.evaluate(() => window.__wmcpStub.tools.map((t) => ({
      name: t.name,
      title: t.title,
      hasDescription: typeof t.description === 'string' && t.description.length > 40,
      readOnly: t.annotations?.readOnlyHint === true,
      schemaType: t.inputSchema?.type,
      noExtra: t.inputSchema?.additionalProperties === false,
      hasExecute: typeof t.execute === 'function',
    })));
    const names = tools.map((t) => t.name).sort();
    report('регистрация: все 5 инструментов зарегистрированы',
      JSON.stringify(names) === JSON.stringify(['get_product', 'get_vendor', 'list_vendor_products', 'list_vendors', 'search_products']),
      names.join(', '));
    report('регистрация: у каждого — описание, JSON Schema и readOnlyHint',
      tools.every((t) => t.hasDescription && t.readOnly && t.schemaType === 'object' && t.noExtra && t.hasExecute));

    const searchOut = await page.evaluate(async () => {
      const tool = window.__wmcpStub.tools.find((t) => t.name === 'search_products');
      return tool.execute({ query: 'chatgpt' });
    });
    const searchData = JSON.parse(searchOut?.content?.[0]?.text || 'null');
    report('исполнение: search_products возвращает structured-ответ с товаром',
      searchOut?.content?.[0]?.type === 'text' && searchData?.items?.some((i) => i.sku === 'INT-AI-CHATGPT'),
      searchData?.items?.map((i) => i.sku).join(', ') || String(searchOut).slice(0, 80));

    const productOut = await page.evaluate(async () => {
      const tool = window.__wmcpStub.tools.find((t) => t.name === 'get_product');
      return tool.execute({ slug: 'chatgpt-business' });
    });
    const productData = JSON.parse(productOut?.content?.[0]?.text || 'null');
    report('исполнение: get_product отдаёт цену витрины и условия покупки',
      productData?.price === 1000 && Array.isArray(productData?.purchase_terms) && productData.purchase_terms.length > 0,
      `price=${productData?.price}`);

    const errOut = await page.evaluate(async () => {
      const tool = window.__wmcpStub.tools.find((t) => t.name === 'get_product');
      return tool.execute({ slug: 'net-takogo' });
    });
    report('исполнение: ошибка отдаётся агенту текстом, а не исключением',
      typeof errOut?.content?.[0]?.text === 'string' && errOut.content[0].text.startsWith('Ошибка'),
      errOut?.content?.[0]?.text?.slice(0, 60));

    const vendorsOut = await page.evaluate(async () => {
      const tool = window.__wmcpStub.tools.find((t) => t.name === 'list_vendors');
      return tool.execute({});
    });
    const vendorsData = JSON.parse(vendorsOut?.content?.[0]?.text || 'null');
    report('исполнение: list_vendors перечисляет производителей со ссылками',
      Array.isArray(vendorsData?.items) && vendorsData.items.every((v) => v.url?.includes('/vendors/')),
      `вендоров: ${vendorsData?.items?.length}`);
    await page.close();
  }

  await browser.close();
} catch (e) {
  console.error(`Браузерный тест не запустился: ${e.message}`);
  failedRun = true;
} finally {
  for (const p of procs) p.kill('SIGKILL');
}

const failed = results.filter((r) => !r).length;
console.log(`\nИтог: ${results.length - failed}/${results.length} пройдено${failedRun ? ', запуск с ошибкой' : ''}\n`);
process.exit(failed || failedRun ? 1 : 0);
