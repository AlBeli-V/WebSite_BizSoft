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
  { id: 3, name: 'Подарочные карты и пополнение баланса', slug: 'gift-cards', status: 'published', sort: 19 },
  // Раздел для проверки второй привязки: своих товаров у него в стенде нет,
  // и он наполняется только гостем из реестра data/catalog/cross-listing.json.
  { id: 4, name: 'Сайты и хостинг', slug: 'web', status: 'published', sort: 18 },
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
    noindex: over.noindex ?? false, date_updated: '2026-08-01T00:00:00Z', content_updated_at: '2026-08-01T00:00:00Z',
    for_whom: '', use_cases: '', former_names: '',
    old_slugs: over.old_slugs ?? [], related_products: '', related_solutions: '',
    price_from: false, category: over.category ?? CATEGORIES[0],
    image: null, images: [],
    // Тип товара и варианты (подарочные карты): у обычных товаров пусто.
    product_type: null, parent_sku: null, region_code: null, region_name: null,
    denomination: null, denomination_currency: null, availability: null, variant_label: null,
    // Переопределения сверх базовых полей (promo_* для проверок разметки и т.п.)
    ...over,
  };
}

const PRODUCTS = [
  product({ id: 101, name: 'ChatGPT Business', sku: 'OPAI-LIC-CHATGPTBUS-TEAM-1Y-USER-STD', vendor: 'OpenAI', slug: 'chatgpt-business', old_slugs: [{ value: 'chatgpt-team' }] }),
  // Пополнение баланса API: родитель «по запросу» и два номинала. Без них смоук
  // не видел ни блока номиналов на лендинге вендора, ни того, что карточки
  // -CREDITS-<сумма> не попадают в сетку тарифов и в «Цены от».
  product({ id: 901, name: 'Пополнение баланса OpenAI API', sku: 'OPAI-CRD-API-UNI-BAL-NOM', vendor: 'OpenAI', slug: 'openai-api-balance', price: 0 }),
  product({ id: 902, name: 'OpenAI API — пополнение баланса на 50 $', sku: 'OPAI-CRD-API-UNI-BAL-NOM-50', vendor: 'OpenAI', slug: 'openai-credits-50', price: 11504 }),
  product({ id: 903, name: 'OpenAI API — пополнение баланса на 100 $', sku: 'OPAI-CRD-API-UNI-BAL-NOM-100', vendor: 'OpenAI', slug: 'openai-credits-100', price: 23008 }),
  product({ id: 102, name: 'Figma Organization', sku: 'FIGM-LIC-ORGANIZATION-TEAM-1Y-USER', vendor: 'Figma', slug: 'figma-organization', category: CATEGORIES[1] }),
  // Второй товар из кураторского списка бестселлеров главной: блок hero-карточек
  // рендерится только от двух позиций с ценой, и без него смоук не видел ни
  // структуру заголовков героя, ни сами карточки.
  product({ id: 109, name: 'Claude Team', sku: 'INT-AI-CLAUDE', vendor: 'Anthropic', slug: 'anthropic-team' }),
  // Вторая привязка: товар лежит в «Дизайне», а показывается ещё и в «Сайтах
  // и хостинге» (реестр cross-listing.json). Без него раздел web пуст — так
  // смоук видит и сам механизм, и то, что он не задваивает товар в своём
  // разделе.
  product({ id: 110, name: 'Cloudflare Pro', sku: 'CFLR-LIC-PRO-UNI-1Y-ORG', vendor: 'Cloudflare', slug: 'cloudflare-pro', category: CATEGORIES[1] }),
  product({ id: 103, name: 'Плагин скрытый', sku: 'JB-ADD-HIDDEN-TEAM-1Y-USER', vendor: 'JetBrains', slug: 'plagin-skrytyj' }),
  product({ id: 104, name: 'Товар noindex', sku: 'NOIDX-1', vendor: 'OpenAI', slug: 'tovar-noindex', noindex: true }),
  product({ id: 105, name: 'Черновик', sku: 'DRAFT-1', vendor: 'OpenAI', slug: 'chernovik', status: 'draft' }),
  // Сценарии структурированных данных: «цена по запросу» и активная акция.
  product({ id: 106, name: 'Товар по запросу', sku: 'REQ-1', vendor: 'OpenAI', slug: 'tovar-po-zaprosu', price: 0 }),
  // Карточка со своей метой: проверяем, что meta_* из Directus доезжают до
  // разметки и что бренд в title не задваивается.
  product({ id: 108, name: 'Товар со своей метой', sku: 'META-1', vendor: 'OpenAI', slug: 'tovar-s-metoj', meta_title: 'Свой заголовок карточки | BIZSoft', meta_description: 'Своё описание карточки: проверяем, что мета из Directus попадает в разметку.' }),
  product({ id: 107, name: 'Товар с акцией', sku: 'PROMO-1', vendor: 'OpenAI', slug: 'tovar-s-akciej', price: 2000, promo_price: 1500, promo_label: 'Акция', promo_start: null, promo_end: '2099-12-31' }),
  // Подарочная карта: родитель со страницей и три варианта (два региона).
  // Порядок вариантов в базе нарочно «неправильный» — витрина обязана
  // выстроить номиналы по убыванию сама (lib/gift-cards.ts).
  product({ id: 110, name: 'Apple App Store & iTunes Gift Card', sku: 'APPL-GFT-APPSTORE-UNI-BAL-NOM', vendor: 'Apple', slug: 'app-store-itunes-gift-card',
    price: 1895, price_from: true, product_type: 'gift_card', category: CATEGORIES[2], short_description: 'Цифровая карта пополнения баланса Apple Account.' }),
  product({ id: 111, name: 'Apple Gift Card 500 RUB, Россия', sku: 'APPL-GFT-APPSTORE-UNI-BAL-NOM-RU500', vendor: 'Apple', slug: 'app-store-itunes-gift-card-ru-500',
    price: 1895, product_type: 'gift_card', parent_sku: 'APPL-GFT-APPSTORE-UNI-BAL-NOM', region_code: 'RU', region_name: 'Россия', denomination: 500, denomination_currency: 'RUB', availability: 'in_stock', category: CATEGORIES[2] }),
  product({ id: 112, name: 'Apple Gift Card 1000 RUB, Россия', sku: 'APPL-GFT-APPSTORE-UNI-BAL-NOM-RU1000', vendor: 'Apple', slug: 'app-store-itunes-gift-card-ru-1000',
    price: 3734, product_type: 'gift_card', parent_sku: 'APPL-GFT-APPSTORE-UNI-BAL-NOM', region_code: 'RU', region_name: 'Россия', denomination: 1000, denomination_currency: 'RUB', availability: 'in_stock', category: CATEGORIES[2] }),
  product({ id: 113, name: 'Apple Gift Card 2000 TRY, Турция', sku: 'APPL-GFT-APPSTORE-UNI-BAL-NOM-TR2000', vendor: 'Apple', slug: 'app-store-itunes-gift-card-tr-2000',
    price: 11275, product_type: 'gift_card', parent_sku: 'APPL-GFT-APPSTORE-UNI-BAL-NOM', region_code: 'TR', region_name: 'Турция', denomination: 2000, denomination_currency: 'TRY', availability: 'in_stock', category: CATEGORIES[2] }),
  // Подписка по подарочной ссылке: один регион Global, варианты с подписью
  // вместо денежного номинала (variant_label), срок в месяцах — для порядка.
  product({ id: 114, name: 'Discord Nitro (подарочная подписка)', sku: 'DISC-GFT-NITRO-UNI-BAL-NOM', vendor: 'Discord', slug: 'discord-nitro-gift-card',
    price: 1122, price_from: true, product_type: 'gift_card', category: CATEGORIES[2], short_description: 'Подписка Discord Nitro подарочной ссылкой.' }),
  product({ id: 115, name: 'Discord Nitro Basic, 1 месяц (Global)', sku: 'DISC-GFT-NITROBASIC-UNI-1M-NOM-GL', vendor: 'Discord', slug: 'discord-nitro-gift-card-global-basic-1m',
    price: 1122, product_type: 'gift_card', parent_sku: 'DISC-GFT-NITRO-UNI-BAL-NOM', region_code: 'GLOBAL', region_name: 'Все страны (Global)', denomination: 1, denomination_currency: 'MONTH', variant_label: 'Discord Nitro Basic, 1 месяц', availability: 'in_stock', category: CATEGORIES[2] }),
  product({ id: 116, name: 'Discord Nitro, 12 месяцев (Global)', sku: 'DISC-GFT-NITRO-UNI-12M-NOM-GL', vendor: 'Discord', slug: 'discord-nitro-gift-card-global-nitro-12m',
    price: 22726, product_type: 'gift_card', parent_sku: 'DISC-GFT-NITRO-UNI-BAL-NOM', region_code: 'GLOBAL', region_name: 'Все страны (Global)', denomination: 12, denomination_currency: 'MONTH', variant_label: 'Discord Nitro, 12 месяцев', availability: 'limited', category: CATEGORIES[2] }),
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
  // Проекция полей, как у настоящего Directus: чего сайт не запросил в
  // fields, того он не получит. Без этого стаб маскировал выборки мимо
  // productsQuery — на проде карточка подарочной карты рендерилась как
  // обычный товар, а смоук этого не видел (05.09.2026). Вложенные пути
  // (category.slug, images.directus_files_id.id) отдают верхний объект целиком.
  const fields = (url.searchParams.get('fields') || '').split(',').map((f) => f.trim()).filter(Boolean);
  if (fields.length && !fields.includes('*')) {
    const tops = new Set(fields.map((f) => f.split('.')[0]));
    rows = rows.map((r) => Object.fromEntries(Object.entries(r).filter(([k]) => tops.has(k))));
  }

  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ data: rows }));
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[stub-directus] http://127.0.0.1:${PORT} (режим: ${mode})`);
});
