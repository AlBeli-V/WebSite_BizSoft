#!/usr/bin/env node
/**
 * Миграция модели BizSoft v2:
 *  - новые поля товара: vendor, origin (Отеч/Иностр), license_type, price_note,
 *    vat_percent, keywords (SEO), images (M2M медиатека-галерея).
 *  - новая таксономия категорий (типы ПО) + поле origin для фильтрации.
 *  - пере-сидирование демо-данных под фильтры (оба происхождения, разные вендоры/категории).
 *
 * Запуск (контейнер на сети bizsoft_default), как в directus-setup.mjs:
 *   docker run --rm --network bizsoft_default -e DIRECTUS_URL=http://directus:8055 \
 *     -e ENV_FILE=/env -v /opt/bizsoft/.env:/env:ro -v $PWD/directus-migrate-v2.mjs:/m.mjs:ro \
 *     node:22-alpine node /m.mjs
 */
import { readFileSync } from 'node:fs';

function loadEnvFile(path) {
  const out = {};
  try {
    for (const line of readFileSync(path, 'utf8').split(/\r?\n/)) {
      const t = line.trim();
      if (!t || t.startsWith('#')) continue;
      const i = t.indexOf('=');
      if (i < 0) continue;
      let v = t.slice(i + 1).trim();
      if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
      out[t.slice(0, i).trim()] = v;
    }
  } catch {}
  return out;
}
const env = { ...(process.env.ENV_FILE ? loadEnvFile(process.env.ENV_FILE) : {}), ...process.env };
const DIRECTUS_URL = (env.DIRECTUS_URL || 'http://directus:8055').replace(/\/$/, '');
const ADMIN_EMAIL = env.ADMIN_EMAIL || env.DIRECTUS_ADMIN_EMAIL;
const ADMIN_PASSWORD = env.ADMIN_PASSWORD || env.DIRECTUS_ADMIN_PASSWORD;

let token = '';
async function api(method, path, body) {
  const res = await fetch(DIRECTUS_URL + path, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json; try { json = text ? JSON.parse(text) : {}; } catch { json = { raw: text }; }
  if (!res.ok) { const e = new Error(`${method} ${path} → ${res.status}: ${json?.errors?.[0]?.message || text?.slice(0,160)}`); e.status = res.status; throw e; }
  return json.data;
}
async function login() {
  const r = await fetch(DIRECTUS_URL + '/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: ADMIN_EMAIL, password: ADMIN_PASSWORD }) });
  if (!r.ok) throw new Error('login failed ' + r.status);
  token = (await r.json()).data.access_token;
  console.log('✓ login');
}
async function fields(coll) { return new Set((await api('GET', `/fields/${coll}`)).map((f) => f.field)); }
async function ensureField(coll, field, def) {
  const have = await fields(coll);
  if (have.has(field)) { console.log(`= ${coll}.${field}`); return; }
  await api('POST', `/fields/${coll}`, { field, ...def });
  console.log(`✓ ${coll}.${field}`);
}
async function collections() { return new Set((await api('GET', '/collections')).map((c) => c.collection)); }
async function relationExists(coll, field) {
  const rels = await api('GET', '/relations');
  return rels.some((r) => r.collection === coll && r.field === field);
}

const SELECT = (choices) => ({ type: 'string', meta: { interface: 'select-dropdown', display: 'labels', options: { choices } } });

async function addProductFields() {
  await ensureField('products', 'vendor', { type: 'string', meta: { interface: 'input', note: 'Производитель/вендор', width: 'half' } });
  await ensureField('products', 'origin', { ...SELECT([{ text: 'Отечественное ПО', value: 'domestic' }, { text: 'Иностранное ПО', value: 'foreign' }]), meta: { ...SELECT([]).meta, width: 'half', note: 'Происхождение (для каталога)', options: { choices: [{ text: 'Отечественное ПО', value: 'domestic' }, { text: 'Иностранное ПО', value: 'foreign' }] } }, schema: { default_value: 'foreign' } });
  await ensureField('products', 'license_type', { ...SELECT([]), meta: { interface: 'select-dropdown', display: 'labels', width: 'half', note: 'Тип лицензии', options: { choices: [{ text: 'Для организаций', value: 'org' }, { text: 'Индивидуальное использование', value: 'individual' }, { text: 'Студенческая версия', value: 'student' }] } }, schema: { default_value: 'org' } });
  await ensureField('products', 'price_note', { type: 'string', meta: { interface: 'input', note: 'Примечание к цене (напр. «за пользователя в год»)' } });
  await ensureField('products', 'vat_percent', { type: 'float', meta: { interface: 'input', width: 'half', note: 'НДС, %' }, schema: { default_value: 5 } });
  await ensureField('products', 'keywords', { type: 'text', meta: { interface: 'input-multiline', note: 'Ключевые слова/синонимы через запятую — для SEO/ИИ-индексации' } });
}

async function addImagesM2M() {
  const cols = await collections();
  // 1) junction collection
  if (!cols.has('products_files')) {
    await api('POST', '/collections', {
      collection: 'products_files',
      meta: { hidden: true, icon: 'collections' },
      schema: {},
      fields: [{ field: 'id', type: 'integer', schema: { is_primary_key: true, has_auto_increment: true }, meta: { hidden: true } }],
    });
    console.log('✓ collection products_files');
  } else console.log('= collection products_files');
  // 2) junction fields
  const jf = await fields('products_files');
  if (!jf.has('products_id')) { await api('POST', '/fields/products_files', { field: 'products_id', type: 'integer', schema: {}, meta: { hidden: true } }); console.log('✓ products_files.products_id'); }
  if (!jf.has('directus_files_id')) { await api('POST', '/fields/products_files', { field: 'directus_files_id', type: 'uuid', schema: {}, meta: { hidden: true } }); console.log('✓ products_files.directus_files_id'); }
  if (!jf.has('sort')) { await api('POST', '/fields/products_files', { field: 'sort', type: 'integer', schema: {}, meta: { hidden: true } }); console.log('✓ products_files.sort'); }
  // 3) alias field on products
  const pf = await fields('products');
  if (!pf.has('images')) {
    await api('POST', '/fields/products', { field: 'images', type: 'alias', meta: { interface: 'files', special: ['m2m'], options: {}, note: 'Галерея изображений (логотип/скриншоты)' } });
    console.log('✓ products.images (alias)');
  } else console.log('= products.images');
  // 4) relations
  if (!(await relationExists('products_files', 'products_id'))) {
    await api('POST', '/relations', { collection: 'products_files', field: 'products_id', related_collection: 'products', meta: { one_field: 'images', sort_field: 'sort', junction_field: 'directus_files_id' }, schema: { on_delete: 'CASCADE' } });
    console.log('✓ relation products_files.products_id → products');
  }
  if (!(await relationExists('products_files', 'directus_files_id'))) {
    await api('POST', '/relations', { collection: 'products_files', field: 'directus_files_id', related_collection: 'directus_files', meta: { one_field: null, junction_field: 'products_id' }, schema: { on_delete: 'CASCADE' } });
    console.log('✓ relation products_files.directus_files_id → directus_files');
  }
}

const CATEGORIES = [
  ['office', 'Офисное ПО', 'Текстовые редакторы, таблицы, презентации и офисные пакеты для совместной работы.'],
  ['development', 'Средства разработки', 'IDE, среды, репозитории и инструменты для команд разработки.'],
  ['vcs', 'ВКС и коммуникации', 'Видеоконференцсвязь, мессенджеры и корпоративные коммуникации.'],
  ['collaboration', 'Доски и совместная работа', 'Онлайн-доски, прототипирование и совместное проектирование.'],
  ['pm', 'Трекеры и управление проектами', 'Таск-трекеры, управление задачами и проектами.'],
  ['media', 'Звук, видео и медиа', 'Аудио- и видеоредакторы, обработка медиа.'],
  ['system', 'Системное ПО и ОС', 'Операционные системы, виртуализация и системные утилиты.'],
  ['engineering', 'Инженерное ПО (CAD/CAE)', 'САПР, инженерное проектирование и расчёты.'],
  ['architecture', 'Архитектура и BIM', 'Архитектурное проектирование и информационное моделирование зданий.'],
  ['design', 'Дизайн и графика', 'Растровая и векторная графика, дизайн интерфейсов.'],
  ['security', 'Антивирусы и безопасность', 'Антивирусы, защита и информационная безопасность.'],
  ['monitoring', 'Мониторинг и аналитика', 'Мониторинг инфраструктуры, логи и аналитика.'],
  ['ai', 'AI-сервисы', 'Сервисы искусственного интеллекта для текста, кода и графики.'],
  ['database', 'СУБД и данные', 'Базы данных, хранение и обработка данных.'],
];

async function reseedCategories() {
  // удаляем все старые категории (демо)
  const old = await api('GET', '/items/categories?limit=-1&fields=id');
  if (old.length) await api('DELETE', '/items/categories', old.map((c) => c.id));
  console.log(`= removed ${old.length} old categories`);
  const map = {};
  let sort = 1;
  for (const [slug, name, seo] of CATEGORIES) {
    const c = await api('POST', '/items/categories', { slug, name, seo_text: seo, sort: sort++, status: 'published', meta_title: `${name} для бизнеса по договору`, meta_description: `${name}: подписки и лицензии для юрлиц РФ по договору, счёту и с закрывающими через ЭДО.` });
    map[slug] = c.id;
    console.log(`✓ category ${slug}`);
  }
  return map;
}

function demo(catIds) {
  const base = (p) => ({
    currency: 'RUB', status: 'published', vat_percent: 5,
    slug: p.sku.toLowerCase(),
    seo_text: `${p.name} (${p.vendor}) — поставка для юрлиц РФ по договору с оплатой по счёту и закрывающими документами через ЭДО. Своевременная поставка и ответственность за качество.`,
    meta_title: `${p.name} — купить лицензию для юрлица`,
    meta_description: p.short_description,
    ...p,
    category: catIds[p.cat], cat: undefined,
  });
  return [
    // ── Отечественное ПО ──
    { sku: 'MYOF-LIC-STANDARD-TEAM-1Y-USER', name: 'МойОфис Стандартный', vendor: 'МойОфис', origin: 'domestic', cat: 'office', license_type: 'org', price: 3900, price_note: 'за пользователя в год', short_description: 'Российский офисный пакет: документы, таблицы, презентации, почта.', description: 'Отечественный офисный пакет для организаций: редакторы документов, таблиц и презентаций, совместная работа, совместимость с распространёнными форматами. Включён в реестр российского ПО.', keywords: 'мойофис, офисный пакет, российский офис, замена microsoft office, реестр отечественного по', features: ['Документы, таблицы, презентации', 'Совместная работа', 'Реестр российского ПО'], sort: 1 },
    { sku: 'R7-LIC-PROFESSIONAL-TEAM-1Y-USER', name: 'Р7-Офис Профессиональный', vendor: 'Р7', origin: 'domestic', cat: 'office', license_type: 'org', price: 4500, price_note: 'за пользователя в год', short_description: 'Российский офисный пакет с серверной частью и редакторами онлайн.', description: 'Офисный пакет Р7-Офис: онлайн-редакторы документов, таблиц и презентаций, серверная совместная работа. Включён в реестр российского ПО.', keywords: 'р7 офис, r7 office, российский офис, онлайн редактор документов', features: ['Онлайн-редакторы', 'Серверная версия', 'Реестр российского ПО'], sort: 2 },
    { sku: 'KNTR-LIC-TOLK-TEAM-1Y-USER', name: 'Контур.Толк', vendor: 'Контур', origin: 'domestic', cat: 'vcs', license_type: 'org', price: 5200, price_note: 'за организатора в год', short_description: 'Российский сервис видеоконференцсвязи и вебинаров.', description: 'Контур.Толк — отечественная платформа видеоконференцсвязи: встречи, вебинары, запись, демонстрация экрана. Размещение в РФ.', keywords: 'контур толк, российская вкс, видеоконференцсвязь, замена zoom, вебинары', features: ['Встречи и вебинары', 'Запись', 'Данные в РФ'], sort: 3, promo_price: 4500, promo_label: 'до конца квартала', promo_start: '2026-06-01', promo_end: '2026-08-31' },
    { sku: 'ASTR-LIC-LINUXSE-TEAM-PERP-DEV', name: 'Astra Linux Special Edition', vendor: 'ГК «Астра»', origin: 'domestic', cat: 'system', license_type: 'org', price: 12900, price_note: 'бессрочная лицензия на устройство', short_description: 'Российская операционная система на базе Linux.', description: 'Astra Linux — отечественная защищённая операционная система для рабочих станций и серверов. Сертифицирована, включена в реестр российского ПО.', keywords: 'astra linux, астра линукс, российская ос, операционная система, импортозамещение', features: ['Защищённая ОС', 'Сертификаты ФСТЭК', 'Реестр российского ПО'], sort: 4 },
    { sku: 'KASP-LIC-ENDPOINTSEC-TEAM-1Y-DEV', name: 'Kaspersky Endpoint Security', vendor: 'Лаборатория Касперского', origin: 'domestic', cat: 'security', license_type: 'org', price: 2400, price_note: 'за узел в год', short_description: 'Защита рабочих станций и серверов от угроз.', description: 'Kaspersky Endpoint Security — корпоративная защита рабочих мест и серверов: антивирус, контроль программ и устройств, шифрование. Российский вендор.', keywords: 'касперский, kaspersky, антивирус, защита рабочих станций, информационная безопасность', features: ['Антивирус и EDR', 'Контроль устройств', 'Централизованное управление'], sort: 5 },
    { sku: 'YNDX-LIC-TRACKER-TEAM-1Y-USER', name: 'Яндекс Трекер', vendor: 'Яндекс', origin: 'domestic', cat: 'pm', license_type: 'org', price: 1100, price_note: 'за пользователя в месяц', short_description: 'Российский таск-трекер для управления задачами и проектами.', description: 'Яндекс Трекер — система управления задачами и процессами: доски, очереди, спринты, автоматизация. Размещение в РФ.', keywords: 'яндекс трекер, таск трекер, управление задачами, замена jira, российский трекер', features: ['Доски и спринты', 'Автоматизация', 'Данные в РФ'], sort: 6 },
    { sku: 'ASCN-LIC-KOMPAS3D-TEAM-PERP-USER', name: 'КОМПАС-3D', vendor: 'АСКОН', origin: 'domestic', cat: 'engineering', license_type: 'org', price: 0, base_price_usd: 0, price_note: 'цена по запросу — рассчитаем под конфигурацию', short_description: 'Российская система трёхмерного проектирования (САПР).', description: 'КОМПАС-3D — отечественная САПР для машиностроения и приборостроения: 3D-моделирование, чертежи, спецификации. Реестр российского ПО.', keywords: 'компас 3d, аскон, сапр, российская cad, проектирование, машиностроение', features: ['3D-моделирование', 'Чертежи и спецификации', 'Реестр российского ПО'], sort: 7 },
    // ── Иностранное ПО ──
    { sku: 'MSFT-LIC-M365BUSSTD-TEAM-1Y-USER', name: 'Microsoft 365 Business Standard', vendor: 'Microsoft', origin: 'foreign', cat: 'office', license_type: 'org', price: 0, price_note: 'цена по запросу — зависит от количества и срока', short_description: 'Облачный офис: Word, Excel, PowerPoint, Teams, почта.', description: 'Microsoft 365 Business Standard — облачный офисный пакет с приложениями Office, корпоративной почтой и совместной работой. Оформление на юрлицо.', keywords: 'microsoft 365, office 365, ms office, word excel powerpoint, корпоративная почта', features: ['Office-приложения', 'Почта и Teams', 'Облачное хранилище'], sort: 11 },
    { sku: 'JB-LIC-ALLPACK-UNI-1Y-USER', name: 'JetBrains All Products Pack', vendor: 'JetBrains', origin: 'foreign', cat: 'development', license_type: 'org', price: 0, base_price_usd: 779, peg_to_usd: true, markup_percent: 15, price_note: 'за разработчика в год, по курсу ЦБ', short_description: 'Набор всех IDE JetBrains для команды разработки.', description: 'JetBrains All Products Pack — доступ ко всем средам разработки JetBrains (IntelliJ IDEA, PyCharm, WebStorm и др.) для одного разработчика.', keywords: 'jetbrains, intellij idea, pycharm, webstorm, ide, среда разработки', features: ['Все IDE JetBrains', 'Командные лицензии', 'Обновления включены'], sort: 12 },
    { sku: 'INT-VCS-ZOOM', name: 'Zoom Business', vendor: 'Zoom', origin: 'foreign', cat: 'vcs', license_type: 'org', price: 0, base_price_usd: 199, peg_to_usd: true, markup_percent: 15, price_note: 'за организатора в год, по курсу ЦБ', short_description: 'Видеоконференции и вебинары для бизнеса.', description: 'Zoom Business — видеоконференцсвязь для компаний: встречи до 300 участников, запись, брендирование, админ-панель.', keywords: 'zoom, зум, видеоконференцсвязь, вебинары, онлайн встречи', features: ['До 300 участников', 'Запись в облако', 'Админ-панель'], sort: 13 },
    { sku: 'INT-COLLAB-MIRO', name: 'Miro Business', vendor: 'Miro', origin: 'foreign', cat: 'collaboration', license_type: 'org', price: 0, base_price_usd: 192, peg_to_usd: true, markup_percent: 15, price_note: 'за пользователя в год, по курсу ЦБ', short_description: 'Онлайн-доска для совместной работы и прототипов.', description: 'Miro — бесконечная онлайн-доска для командной работы: майнд-карты, схемы, прототипы, воркшопы в реальном времени.', keywords: 'miro, миро, онлайн доска, совместная работа, прототипирование, майнд карта', features: ['Бесконечная доска', 'Реальное время', 'Шаблоны'], sort: 14 },
    { sku: 'FIGM-LIC-ORGANIZATION-TEAM-1Y-USER', name: 'Figma Organization', vendor: 'Figma', origin: 'foreign', cat: 'design', license_type: 'org', price: 0, base_price_usd: 540, peg_to_usd: true, markup_percent: 15, price_note: 'за редактора в год, по курсу ЦБ', short_description: 'Совместный дизайн интерфейсов и прототипирование.', description: 'Figma — платформа для дизайна интерфейсов и прототипов в реальном времени, дизайн-системы, совместная работа команды.', keywords: 'figma, фигма, дизайн интерфейсов, ui ux, прототип, дизайн система', features: ['Дизайн в реальном времени', 'Дизайн-системы', 'Прототипы'], sort: 15 },
    { sku: 'ADSK-LIC-AUTOCAD-UNI-1Y-USER', name: 'Autodesk AutoCAD', vendor: 'Autodesk', origin: 'foreign', cat: 'engineering', license_type: 'org', price: 0, base_price_usd: 2030, peg_to_usd: true, markup_percent: 15, price_note: 'за рабочее место в год, по курсу ЦБ', short_description: 'Профессиональная САПР для проектирования и черчения.', description: 'Autodesk AutoCAD — мировой стандарт автоматизированного проектирования: 2D/3D-черчение, аннотирование, обмен DWG.', keywords: 'autocad, автокад, autodesk, сапр, cad, черчение, проектирование', features: ['2D/3D-черчение', 'Формат DWG', 'Отраслевые наборы'], sort: 16 },
    { sku: 'OPAI-LIC-CHATGPTBUS-TEAM-1Y-USER-STD', name: 'ChatGPT Team', vendor: 'OpenAI', origin: 'foreign', cat: 'ai', license_type: 'org', price: 0, base_price_usd: 360, peg_to_usd: true, markup_percent: 15, price_note: 'за пользователя в год, по курсу ЦБ', short_description: 'AI-ассистент для команды: текст, код, анализ.', description: 'ChatGPT Team — командный доступ к продвинутым моделям OpenAI для генерации текста и кода, анализа данных, общего рабочего пространства.', keywords: 'chatgpt, openai, ai ассистент, нейросеть, генерация текста, искусственный интеллект', features: ['Командное пространство', 'Продвинутые модели', 'Конфиденциальность данных'], sort: 17, license_type: 'org' },
  ].map(base);
}

async function reseedProducts(catIds) {
  const old = await api('GET', '/items/products?limit=-1&fields=id');
  if (old.length) await api('DELETE', '/items/products', old.map((p) => p.id));
  console.log(`= removed ${old.length} old products`);
  for (const p of demo(catIds)) {
    await api('POST', '/items/products', p);
    console.log(`✓ product ${p.sku}`);
  }
}

async function main() {
  if (!ADMIN_EMAIL || !ADMIN_PASSWORD) throw new Error('no ADMIN creds');
  console.log('Directus:', DIRECTUS_URL);
  await login();
  await addProductFields();
  await addImagesM2M();
  const catIds = await reseedCategories();
  await reseedProducts(catIds);
  console.log('\n✅ MIGRATION v2 COMPLETE');
}
main().catch((e) => { console.error('\n❌ ERROR:', e.message); process.exit(1); });
