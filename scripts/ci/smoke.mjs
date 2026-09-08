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
check('уникальные <title> у страниц из sitemap', async () => {
  // Одинаковые title на разных URL Яндекс считает дублями и снимает
  // страницы с индексации. Title карточки — это meta_title из Directus
  // (src/pages/product/[slug].astro), так что проверяем итоговую разметку.
  const r = await req('/sitemap.xml');
  const paths = [...r.body.matchAll(/<loc>([^<]+)<\/loc>/g)]
    .map((m) => new URL(m[1]).pathname);
  const byTitle = new Map();
  for (const p of paths) {
    const page = await req(p);
    const t = (page.body.match(/<title>([^<]*)<\/title>/) || [, ''])[1].trim();
    if (!t) continue;
    byTitle.set(t, [...(byTitle.get(t) || []), p]);
  }
  const dup = [...byTitle.entries()].filter(([, ps]) => ps.length > 1);
  return {
    ok: dup.length === 0,
    got: dup.length
      ? dup.map(([t, ps]) => `«${t}» — ${ps.join(', ')}`).join('; ')
      : `нет (${byTitle.size} страниц)`,
  };
});
check('иерархия заголовков без пропусков и ровно один h1', async () => {
  // Lighthouse (правило axe heading-order) считает ошибкой скачок уровня
  // больше чем на один: <h1> → <h3> в обход <h2>. Так уехали на прод
  // карточки в героях и сетках товаров — заголовок секции там визуально не
  // нужен, и его просто не ставили. Проверяем всю выдачу sitemap, чтобы
  // новая страница с той же ошибкой не прошла молча; невидимый заголовок
  // секции ставится классом .sr-only.
  const r = await req('/sitemap.xml');
  const paths = [...r.body.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => new URL(m[1]).pathname);
  const bad = [];
  for (const p of paths) {
    const page = await req(p);
    const html = page.body.replace(/<!--[\s\S]*?-->/g, '');
    const levels = [...html.matchAll(/<h([1-6])[\s>]/gi)].map((m) => Number(m[1]));
    const h1 = levels.filter((l) => l === 1).length;
    const jumps = [];
    let prev = 0;
    for (const l of levels) {
      if (prev && l > prev + 1) jumps.push(`h${prev}→h${l}`);
      prev = l;
    }
    if (h1 !== 1 || jumps.length) bad.push(`${p} (h1: ${h1}${jumps.length ? ', ' + jumps.join(', ') : ''})`);
  }
  return { ok: bad.length === 0, got: bad.length ? bad.slice(0, 8).join('; ') : `нет (${paths.length} страниц)` };
});
check('мета карточки из Directus доезжает до разметки', async () => {
  // Заголовок и описание страницы товара берутся из meta_title/meta_description
  // Directus; если связь порвётся, страница начнёт отдавать название товара и
  // общее описание сайта — то есть один и тот же текст на сотнях карточек.
  const r = await req('/product/tovar-s-metoj');
  const title = (r.body.match(/<title>([^<]*)<\/title>/) || [, ''])[1];
  const desc = (r.body.match(/<meta name="description" content="([^"]*)"/) || [, ''])[1];
  const ok = title === 'Свой заголовок карточки | BIZSoft' && desc.startsWith('Своё описание карточки');
  return { ok, got: `title «${title}», description «${desc.slice(0, 40)}…»` };
});
check('бренд в title не задваивается', async () => {
  // meta_title из Directus уже содержит «| BIZSoft» — SeoHead не должен
  // дописывать бренд второй раз.
  const r = await req('/product/tovar-s-metoj');
  const title = (r.body.match(/<title>([^<]*)<\/title>/) || [, ''])[1];
  const hits = (title.match(/BIZSoft/gi) || []).length;
  return { ok: hits === 1, got: `вхождений бренда: ${hits}` };
});
// ── Подарочные карты: одна страница на все номиналы ──
check('подарочная карта: страница родителя отдаёт 200 с выбором региона и номинала', async () => {
  const r = await req('/product/app-store-itunes-gift-card');
  const html = r.body;
  if (r.status !== 200) throw new Error(`HTTP ${r.status}`);
  if (!html.includes('data-gift-card')) throw new Error('нет селектора вариантов');
  if (!html.includes('data-region="RU"') || !html.includes('data-region="TR"')) throw new Error('нет кнопок регионов');
  // Номиналы региона по убыванию: 1000 раньше 500, хотя в базе порядок обратный.
  const i1000 = html.indexOf('data-sku="APP-STORE-ITUNES-GIFT-CARD-RU-1000"');
  const i500 = html.indexOf('data-sku="APP-STORE-ITUNES-GIFT-CARD-RU-500"');
  if (i1000 < 0 || i500 < 0 || i1000 > i500) throw new Error('номиналы не по убыванию');
  if (/base_price_usd|markup_coeff/.test(html)) throw new Error('закупка попала в HTML');
  if (!html.includes('rel="canonical" href="https://biz-soft.pro/product/app-store-itunes-gift-card"')) throw new Error('canonical не на родителя');
  return { ok: true, got: '200, селектор, регионы RU/TR, номиналы по убыванию, закупки в HTML нет' };
});
check('подарочная карта: ?sku= не меняет canonical и не закрывает страницу от индексации', async () => {
  const html = (await req('/product/app-store-itunes-gift-card?sku=APP-STORE-ITUNES-GIFT-CARD-TR-2000')).body;
  if (!html.includes('rel="canonical" href="https://biz-soft.pro/product/app-store-itunes-gift-card"')) throw new Error('canonical с параметром');
  if (html.includes('name="robots" content="noindex')) throw new Error('родитель закрыт noindex');
  return { ok: true, got: 'canonical без параметров, noindex нет' };
});
check('подарочная карта: страница варианта отдаёт 301 на родителя с выбранным номиналом', async () => {
  const r = await req('/product/app-store-itunes-gift-card-ru-1000');
  if (r.status !== 301) throw new Error(`HTTP ${r.status}`);
  const loc = r.headers.get('location') || '';
  if (!loc.startsWith('/product/app-store-itunes-gift-card?sku=APP-STORE-ITUNES-GIFT-CARD-RU-1000')) throw new Error(`location: ${loc}`);
  return { ok: true, got: `301 → ${loc}` };
});
check('подарочная карта: sitemap содержит родителя и не содержит варианты', async () => {
  const xml = (await req('/sitemap.xml')).body;
  if (!xml.includes('/product/app-store-itunes-gift-card</loc>')) throw new Error('родителя нет в sitemap');
  if (xml.includes('app-store-itunes-gift-card-ru-') || xml.includes('app-store-itunes-gift-card-tr-')) throw new Error('вариант попал в sitemap');
  return { ok: true, got: 'родитель есть, вариантов нет' };
});
check('подарочная карта: JSON-LD — один Product с AggregateOffer, диапазон совпадает с витриной', async () => {
  const html = (await req('/product/app-store-itunes-gift-card')).body;
  const nodes = ldNodes(html);
  const products = ofType(nodes, 'Product');
  if (products.length !== 1) throw new Error(`Product: ${products.length}`);
  const offers = products[0].offers;
  if (!offers || offers['@type'] !== 'AggregateOffer') throw new Error('нет AggregateOffer');
  if (offers.lowPrice !== 1895 || offers.highPrice !== 11275 || offers.offerCount !== 3) throw new Error(`диапазон ${offers.lowPrice}–${offers.highPrice} × ${offers.offerCount}`);
  if (!html.includes('itemtype="https://schema.org/AggregateOffer"')) throw new Error('microdata без AggregateOffer');
  if (!html.includes('itemprop="lowPrice" content="1895"')) throw new Error('microdata lowPrice расходится');
  return { ok: true, got: `AggregateOffer ${offers.lowPrice}–${offers.highPrice} × ${offers.offerCount}, microdata согласована` };
});
check('подарочная подписка (Discord): один регион Global, подписи вариантов, 12 месяцев раньше 1 месяца', async () => {
  const r = await req('/product/discord-nitro-gift-card');
  const html = r.body;
  if (r.status !== 200) throw new Error(`HTTP ${r.status}`);
  if (!html.includes('data-gift-card')) throw new Error('нет селектора');
  if ((html.match(/data-region="GLOBAL"/g) || []).length !== 1) throw new Error('регион Global должен быть один и показан строкой');
  if (!html.includes('Discord Nitro, 12 месяцев') || !html.includes('Discord Nitro Basic, 1 месяц')) throw new Error('нет подписей вариантов');
  const i12 = html.indexOf('data-sku="DISCORD-NITRO-GIFT-CARD-GLOBAL-NITRO-12M"');
  const i1 = html.indexOf('data-sku="DISCORD-NITRO-GIFT-CARD-GLOBAL-BASIC-1M"');
  if (i12 < 0 || i1 < 0 || i12 > i1) throw new Error('порядок вариантов не по убыванию срока');
  if (!html.includes('Ограниченное количество')) throw new Error('пометка ограниченного наличия не выведена');
  const nodes = ldNodes(html);
  const offers = ofType(nodes, 'Product')[0]?.offers;
  if (!offers || offers['@type'] !== 'AggregateOffer' || offers.lowPrice !== 1122 || offers.highPrice !== 22726) throw new Error('AggregateOffer расходится с витриной');
  return { ok: true, got: 'Global, 2 варианта, AggregateOffer 1122–22726' };
});
check('подарочная карта: WebMCP отдаёт вариант с ценой и без закупки', async () => {
  const r = await req('/api/agent/get_product?slug=app-store-itunes-gift-card-ru-1000');
  const j = JSON.parse(r.body);
  if (r.status !== 200) throw new Error(`HTTP ${r.status}`);
  if (j?.data?.price !== 3734) throw new Error(`price=${j?.data?.price}`);
  if (JSON.stringify(j).includes('base_price')) throw new Error('закупка в ответе агенту');
  return { ok: true, got: `price=${j.data.price}, закупки нет` };
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
// Документ КП собирается только в собранном приложении: пути к логотипу и
// шрифтам в dist другие, чем в исходниках. Юнит-тесты этого не видят — они
// работают с src, — и дефект уехал на прод, где КП не уходило вовсе.
// Отправка письма в смоуке заведомо не удастся (SMTP не настроен) и даёт
// 502; ошибка сборки документа даёт 500 и именно её мы здесь ловим.
check('КП: документ собирается в собранном приложении', async () => {
  const r = await req('/api/quote', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      buyer_company: 'ООО «Смоук»', buyer_inn: '7707083893',
      contact_name: 'Смоуков Иван', email: 'smoke@example.com',
      phone: '+7 900 000-00-00', consent: true,
      items: [{ sku: 'INT-AI-CHATGPT', qty: 1 }],
    }),
  });
  const broken = r.status === 500 && r.body.includes('сформировать документ');
  return { ok: !broken, got: `${r.status} ${r.body.slice(0, 120)}` };
});

// ── WebMCP: read-only API для AI-агентов (/api/agent/*) ──────────────────
// Слой прогрессивного улучшения: те же данные, что на витрине, тем же
// effectivePrice. Смоук сверяет цену API с ценой в JSON-LD той же карточки —
// четвёртый слой (UI ↔ JSON-LD ↔ microdata ↔ WebMCP) не должен разъезжаться.
check('WebMCP: get_product отдаёт карточку с той же ценой, что витрина', async () => {
  const r = await req('/api/agent/get_product?slug=chatgpt-business');
  if (r.status !== 200) return { ok: false, got: `HTTP ${r.status}` };
  const body = JSON.parse(r.body);
  const priceOk = body?.ok === true && body?.data?.price === 1000;
  const urlOk = body?.data?.url === 'https://biz-soft.pro/product/chatgpt-business';
  return { ok: priceOk && urlOk, got: `price=${body?.data?.price} url=${body?.data?.url}` };
});
check('WebMCP: search_products находит товар и даёт ссылку на карточку', async () => {
  const r = await req('/api/agent/search_products?query=chatgpt');
  const body = r.status === 200 ? JSON.parse(r.body) : null;
  const hit = body?.data?.items?.find((i) => i.url?.endsWith('/product/chatgpt-business'));
  return { ok: Boolean(hit), got: hit ? `найден ${hit.sku}` : `HTTP ${r.status}, не найден` };
});
check('WebMCP: фильтры подбора сужают выдачу (раздел + потолок цены)', async () => {
  const r = await req('/api/agent/search_products?category=design&max_price=5000');
  const body = r.status === 200 ? JSON.parse(r.body) : null;
  const items = body?.data?.items || [];
  // «Цена по запросу» внутрь ценового диапазона попадать не должна.
  const ok = items.length > 0 && items.every((i) => typeof i.price === 'number' && i.price <= 5000);
  return { ok, got: `HTTP ${r.status}, ${items.length} поз.: ${items.map((i) => i.price).join(', ') || '—'}` };
});
check('WebMCP: list_categories отдаёт разделы со ссылками', async () => {
  const r = await req('/api/agent/list_categories');
  const body = r.status === 200 ? JSON.parse(r.body) : null;
  const items = body?.data?.items || [];
  const ok = items.length > 0 && items.every((i) => i.url?.startsWith('https://biz-soft.pro/catalog/') && i.products_count > 0);
  return { ok, got: `HTTP ${r.status}, ${items.map((i) => i.slug).join(', ') || '—'}` };
});
check('WebMCP: search_policies отвечает условиями с сайта, не выдумкой', async () => {
  const r = await req('/api/agent/search_policies?query=' + encodeURIComponent('дадите закрывающие документы'));
  const body = r.status === 200 ? JSON.parse(r.body) : null;
  const top = body?.data?.items?.[0];
  const ok = Boolean(top?.answer) && top?.url?.startsWith('https://biz-soft.pro/');
  return { ok, got: top ? `${top.id} → ${top.url}` : `HTTP ${r.status}` };
});
check('WebMCP: пустого вызова каталога нет — 400 вместо всей базы', async () => {
  const r = await req('/api/agent/search_products');
  return { ok: r.status === 400, got: String(r.status) };
});
check('WebMCP: мусорный вход отклоняется схемой (400), не 500', async () => {
  const r = await req('/api/agent/search_products?query=x&limit=abc&hack=1');
  return { ok: r.status === 400, got: String(r.status) };
});
check('WebMCP: неизвестный инструмент — 404', async () => {
  const r = await req('/api/agent/get_chatgpt');
  return { ok: r.status === 404, got: String(r.status) };
});
check('WebMCP: служебный API не индексируется (X-Robots-Tag)', async () => {
  const r = await req('/api/agent/list_vendors');
  const tag = r.headers.get('x-robots-tag') || '';
  return { ok: tag.includes('noindex'), got: tag || 'заголовка НЕТ' };
});
check('WebMCP: /api/agent не попадает в sitemap', async () => {
  const r = await req('/sitemap.xml');
  return { ok: !r.body.includes('/api/agent'), got: r.body.includes('/api/agent') ? 'ЕСТЬ (не должно)' : 'нет' };
});
check('WebMCP: регистратор инструментов доезжает до браузера', async () => {
  // Как и цели Метрики: код лежит в модульном чанке — обходим граф импортов.
  const r = await req('/');
  const RE = /["'(](?:\/_astro\/|\.\/)([\w.\-]+\.js)["')]/g;
  const seen = new Set();
  const queue = [...r.body.matchAll(RE)].map((m) => m[1]);
  while (queue.length) {
    const file = queue.shift();
    if (seen.has(file)) continue;
    seen.add(file);
    const chunk = await req(`/_astro/${file}`);
    if (chunk.status !== 200) continue;
    if (chunk.body.includes('modelContext')) return { ok: true, got: `чанк ${file}` };
    for (const m of chunk.body.matchAll(RE)) queue.push(m[1]);
  }
  return { ok: false, got: `НЕТ (обойдено чанков: ${seen.size})` };
});

// ── Структурированные данные (Schema.org) ────────────────────────────────
// Единый слой разметки: JSON-LD + microdata карточки строятся из тех же
// данных, что и витрина. Смоук ловит расхождение «разметка ↔ страница»
// и дубли типов (BreadcrumbList/FAQPage должны выводиться ровно один раз).
/** Все JSON-LD-узлы страницы плоским списком (или null при битом JSON). */
function ldNodes(html) {
  const nodes = [];
  for (const m of html.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/gs)) {
    try {
      const parsed = JSON.parse(m[1]);
      nodes.push(...(Array.isArray(parsed) ? parsed : [parsed]));
    } catch { return null; }
  }
  return nodes;
}
const ofType = (nodes, type) => nodes.filter((n) => n['@type'] === type || (Array.isArray(n['@type']) && n['@type'].includes(type)));

check('разметка: карточка товара — валидный JSON-LD, ровно один Product и один BreadcrumbList', async () => {
  const r = await req('/product/chatgpt-business');
  const nodes = ldNodes(r.body);
  if (!nodes) return { ok: false, got: 'битый JSON-LD' };
  const p = ofType(nodes, 'Product').length;
  const b = ofType(nodes, 'BreadcrumbList').length;
  return { ok: p === 1 && b === 1, got: `Product: ${p}, BreadcrumbList: ${b}` };
});
check('разметка: цена и URL в JSON-LD совпадают с витриной и canonical', async () => {
  const r = await req('/product/chatgpt-business');
  const nodes = ldNodes(r.body) || [];
  const offer = ofType(nodes, 'Product')[0]?.offers;
  const domPrice = r.body.match(/data-price="([0-9.]+)"/)?.[1];
  const canonical = r.body.match(/<link rel="canonical" href="([^"]+)"/)?.[1];
  const ok = offer && String(offer.price) === '1000' && domPrice === '1000'
    && offer.priceCurrency === 'RUB' && offer.url === canonical;
  return { ok: Boolean(ok), got: `ld=${offer?.price} dom=${domPrice} url=${offer?.url} canonical=${canonical}` };
});
check('разметка: microdata карточки согласована с JSON-LD', async () => {
  const r = await req('/product/chatgpt-business');
  const nodes = ldNodes(r.body) || [];
  const offer = ofType(nodes, 'Product')[0]?.offers;
  const hasScope = r.body.includes('itemtype="https://schema.org/Product"');
  const mdPrice = r.body.match(/itemprop="price" content="([0-9.]+)"/)?.[1];
  const mdCur = r.body.match(/itemprop="priceCurrency" content="([A-Z]+)"/)?.[1];
  const ok = hasScope && offer && mdPrice === String(offer.price) && mdCur === offer.priceCurrency;
  return { ok: Boolean(ok), got: `scope=${hasScope} md=${mdPrice} ${mdCur} ld=${offer?.price} ${offer?.priceCurrency}` };
});
/**
 * Идентификаторы узлов разметки страницы: @id из JSON-LD + itemid microdata.
 * Повтор идентификатора — не «две записи об одном товаре», а один узел,
 * которому потребитель приписывает каждое поле дважды.
 */
function nodeIds(html) {
  const ids = [];
  for (const n of ldNodes(html) || []) if (n && n['@id']) ids.push(String(n['@id']));
  for (const m of html.matchAll(/itemid="([^"]+)"/g)) ids.push(m[1]);
  return ids;
}
check('разметка: карточка товара — ни один идентификатор узла не повторяется', async () => {
  const r = await req('/product/chatgpt-business');
  const ids = nodeIds(r.body);
  const dup = ids.filter((id, i) => ids.indexOf(id) !== i);
  return { ok: dup.length === 0, got: dup.length ? `дубли: ${[...new Set(dup)].join(', ')}` : `узлов с @id/itemid: ${ids.length}, дублей нет` };
});
check('разметка: главная и контакты — один узел организации, без повтора @id', async () => {
  const got = [];
  for (const path of ['/', '/contacts']) {
    const r = await req(path);
    const ids = nodeIds(r.body);
    const orgs = (ldNodes(r.body) || []).filter((n) => n['@id'] === 'https://biz-soft.pro/#organization');
    const dup = ids.filter((id, i) => ids.indexOf(id) !== i);
    if (orgs.length !== 1 || dup.length) return { ok: false, got: `${path}: узлов организации ${orgs.length}, дубли ${[...new Set(dup)].join(', ') || '—'}` };
    got.push(`${path}: 1 узел`);
  }
  return { ok: true, got: got.join(', ') };
});
check('разметка: локальный профиль организации — полный узел (name, address, график)', async () => {
  const r = await req('/contacts');
  const org = (ldNodes(r.body) || []).find((n) => n['@id'] === 'https://biz-soft.pro/#organization');
  const ok = Boolean(org && org.name && org.address && org.openingHoursSpecification && String(org['@type']).includes('LocalBusiness'));
  return { ok, got: org ? `type=${JSON.stringify(org['@type'])} name=${Boolean(org.name)} address=${Boolean(org.address)} hours=${Boolean(org.openingHoursSpecification)}` : 'узла нет' };
});
check('разметка: «цена по запросу» — без Product и в JSON-LD, и в microdata', async () => {
  const r = await req('/product/tovar-po-zaprosu');
  const nodes = ldNodes(r.body) || [];
  const p = ofType(nodes, 'Product').length;
  const md = r.body.includes('itemtype="https://schema.org/Product"');
  const visible = r.body.includes('Цена по запросу');
  return { ok: r.status === 200 && p === 0 && !md && visible, got: `${r.status}, Product ld=${p} md=${md}, виден «по запросу»=${visible}` };
});
check('разметка: у акции в Offer промо-цена и priceValidUntil', async () => {
  const r = await req('/product/tovar-s-akciej');
  const nodes = ldNodes(r.body) || [];
  const offer = ofType(nodes, 'Product')[0]?.offers;
  return { ok: Boolean(offer && String(offer.price) === '1500' && offer.priceValidUntil === '2099-12-31'), got: `price=${offer?.price} until=${offer?.priceValidUntil}` };
});
check('разметка: вендорный лендинг без дублей BreadcrumbList/FAQPage', async () => {
  const r = await req('/vendors/adobe');
  const nodes = ldNodes(r.body);
  if (!nodes) return { ok: false, got: 'битый JSON-LD' };
  const b = ofType(nodes, 'BreadcrumbList').length;
  const f = ofType(nodes, 'FAQPage').length;
  return { ok: b === 1 && f === 1, got: `BreadcrumbList: ${b}, FAQPage: ${f}` };
});
check('разметка: каталог без дублей FAQPage', async () => {
  const r = await req('/catalog');
  const nodes = ldNodes(r.body);
  if (!nodes) return { ok: false, got: 'битый JSON-LD' };
  const f = ofType(nodes, 'FAQPage').length;
  return { ok: f === 1, got: `FAQPage: ${f}` };
});
check('разметка: организация — один @id на всех узлах Organization', async () => {
  const r = await req('/');
  const nodes = ldNodes(r.body) || [];
  const orgs = ofType(nodes, 'Organization');
  const ids = [...new Set(orgs.map((o) => o['@id']))];
  return { ok: orgs.length > 0 && ids.length === 1 && ids[0] === 'https://biz-soft.pro/#organization', got: `узлов: ${orgs.length}, @id: ${ids.join(' | ')}` };
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
check('[БД упала] WebMCP API отдаёт 503 с понятной агенту ошибкой', async () => {
  await setMode('fail');
  const r = await req('/api/agent/search_products?query=chatgpt');
  await setMode('ok');
  const body = (() => { try { return JSON.parse(r.body); } catch { return null; } })();
  return { ok: r.status === 503 && body?.ok === false && Boolean(body?.error), got: `${r.status} ${r.body.slice(0, 80)}` };
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
