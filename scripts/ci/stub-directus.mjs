/**
 * Стаб Directus REST API для смоук-проверок.
 *
 * Поднимает минимальный сервер на фикстурах и умеет по команде «ломаться» —
 * это нужно, чтобы проверять поведение сайта при недоступной БД (REL-001,
 * REL-002, REL-004), не трогая ни прод, ни реальный Directus.
 *
 * Управление: GET /__stub/mode?mode=ok|fail|hang
 *   ok   — обычные ответы;
 *   fail — 500 на всех /items/* (Directus жив, но отдаёт ошибку);
 *   hang — ответ не приходит вовсе (проверка таймаутов, REL-003).
 *
 * Запуск: node scripts/ci/stub-directus.mjs [порт]
 */
import { createServer } from 'node:http';

const PORT = Number(process.argv[2] || process.env.STUB_PORT || 8099);
let mode = 'ok';

const CATEGORIES = [
  { id: 1, name: 'AI-сервисы', slug: 'ai', status: 'published', sort: 1 },
  { id: 2, name: 'Дизайн', slug: 'design', status: 'published', sort: 2 },
  { id: 9, name: 'Черновик', slug: 'draft-cat', status: 'draft', sort: 9 },
];

/** Товар со всеми полями, которые читает PRODUCT_FIELDS. */
function product(over) {
  return {
    id: over.id, name: over.name, sku: over.sku, vendor: over.vendor,
    origin: 'foreign', license_type: 'corporate', slug: over.slug,
    short_description: 'Короткое описание', description: '<p>Описание</p>',
    seo_text: '', keywords: '', meta_title: '', meta_description: '',
    price: over.price ?? 1000, price_note: '', vat_percent: 0, currency: 'RUB',
    base_price_usd: null, base_price_eur: null, peg_currency: null,
    peg_to_usd: false, markup_coeff: 1.85, markup_percent: null,
    price_locked: false, promo_price: null, promo_label: '',
    promo_start: null, promo_end: null, features: [], faq: [],
    sort: over.sort ?? 1, status: over.status ?? 'published',
    noindex: over.noindex ?? false, date_updated: '2026-08-01T00:00:00Z',
    for_whom: '', use_cases: '', former_names: '',
    old_slugs: over.old_slugs ?? [], related_products: '', related_solutions: '',
    price_from: false, category: over.category ?? CATEGORIES[0],
    image: null, images: [],
    // Переопределения сверх базовых полей (promo_* для проверок разметки и т.п.)
    ...over,
  };
}

const PRODUCTS = [
  product({ id: 101, name: 'ChatGPT Business', sku: 'INT-AI-CHATGPT', vendor: 'OpenAI', slug: 'chatgpt-business', old_slugs: [{ value: 'chatgpt-team' }] }),
  product({ id: 102, name: 'Figma Organization', sku: 'INT-DESIGN-FIGMA', vendor: 'Figma', slug: 'figma-organization', category: CATEGORIES[1] }),
  // Второй товар из кураторского списка бестселлеров главной: блок hero-карточек
  // рендерится только от двух позиций с ценой, и без него смоук не видел ни
  // структуру заголовков героя, ни сами карточки.
  product({ id: 109, name: 'Claude Team', sku: 'INT-AI-CLAUDE', vendor: 'Anthropic', slug: 'anthropic-team' }),
  product({ id: 103, name: 'Плагин скрытый', sku: 'JB-PLG-HIDDEN', vendor: 'JetBrains', slug: 'plagin-skrytyj' }),
  product({ id: 104, name: 'Товар noindex', sku: 'NOIDX-1', vendor: 'OpenAI', slug: 'tovar-noindex', noindex: true }),
  product({ id: 105, name: 'Черновик', sku: 'DRAFT-1', vendor: 'OpenAI', slug: 'chernovik', status: 'draft' }),
  // Сценарии структурированных данных: «цена по запросу» и активная акция.
  product({ id: 106, name: 'Товар по запросу', sku: 'REQ-1', vendor: 'OpenAI', slug: 'tovar-po-zaprosu', price: 0 }),
  // Карточка со своей метой: проверяем, что meta_* из Directus доезжают до
  // разметки и что бренд в title не задваивается.
  product({ id: 108, name: 'Товар со своей метой', sku: 'META-1', vendor: 'OpenAI', slug: 'tovar-s-metoj', meta_title: 'Свой заголовок карточки | BIZSoft', meta_description: 'Своё описание карточки: проверяем, что мета из Directus попадает в разметку.' }),
  product({ id: 107, name: 'Товар с акцией', sku: 'PROMO-1', vendor: 'OpenAI', slug: 'tovar-s-akciej', price: 2000, promo_price: 1500, promo_label: 'Акция', promo_start: null, promo_end: '2099-12-31' }),
];

const CURRENCY = [{ id: 1, usd_rate: 90, eur_rate: 100, mode: 'auto', source: 'cbr.ru', auto_recalc: false, rate_date: '2026-08-01', updated_at: '2026-08-01T00:00:00Z' }];

/** Значение поля по пути «category.slug». */
function pick(row, path) {
  return path.split('.').reduce((acc, k) => (acc == null ? acc : acc[k]), row);
}

/** Мини-интерпретатор подмножества фильтров Directus, которое использует сайт. */
function match(row, filter) {
  if (!filter || typeof filter !== 'object') return true;
  return Object.entries(filter).every(([key, cond]) => {
    if (key === '_and') return cond.every((c) => match(row, c));
    if (key === '_or') return cond.some((c) => match(row, c));
    // вложенный объект-условие вида { category: { slug: { _eq } } }
    const ops = cond && typeof cond === 'object' ? cond : { _eq: cond };
    return Object.entries(ops).every(([op, want]) => {
      if (!op.startsWith('_')) return match(row, { [`${key}.${op}`]: want });
      const have = pick(row, key);
      switch (op) {
        case '_eq': return have === want;
        case '_neq': return have !== want;
        case '_in': return (Array.isArray(want) ? want : [want]).includes(have);
        case '_icontains': return String(have ?? '').toLowerCase().includes(String(want).toLowerCase());
        default: throw new Error(`stub: неподдержанный оператор ${op}`);
      }
    });
  });
}

const server = createServer((req, res) => {
  const url = new URL(req.url, `http://127.0.0.1:${PORT}`);

  if (url.pathname === '/__stub/mode') {
    mode = url.searchParams.get('mode') || 'ok';
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ mode }));
  }
  if (url.pathname === '/__stub/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ ok: true, mode }));
  }

  if (mode === 'hang') return; // намеренно не отвечаем — проверка таймаутов
  if (mode === 'fail') {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ errors: [{ message: 'stub: Directus недоступен' }] }));
  }

  // запись (leads/quotes/patch) — просто подтверждаем
  if (req.method !== 'GET') {
    let buf = '';
    req.on('data', (c) => { buf += c; });
    return req.on('end', () => {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ data: { id: 1 } }));
    });
  }

  const m = url.pathname.match(/^\/items\/([a-z_]+)/);
  if (!m) {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ errors: [{ message: 'not found' }] }));
  }
  const collection = m[1];
  const source = collection === 'categories' ? CATEGORIES
    : collection === 'products' ? PRODUCTS
    : collection === 'currency_rate' ? CURRENCY
    : [];

  let filter = null;
  const raw = url.searchParams.get('filter');
  if (raw) { try { filter = JSON.parse(raw); } catch { /* игнорируем */ } }

  let rows = source.filter((r) => match(r, filter));
  const limit = Number(url.searchParams.get('limit') ?? -1);
  if (limit > 0) rows = rows.slice(0, limit);

  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ data: rows }));
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[stub-directus] http://127.0.0.1:${PORT} (режим: ${mode})`);
});
