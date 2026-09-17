#!/usr/bin/env node
/**
 * Идемпотентная настройка Directus для BizSoft:
 *   - коллекции categories, products, leads, quotes, currency_rate
 *   - поля, связи (M2O category, M2O image→directus_files)
 *   - сервисная роль + статический токен (scoped) для Astro-приложения
 *   - публичные права на чтение published (best-effort)
 *   - демо-наполнение (4 раздела, 7 товаров, запись курса)
 *
 * Запуск (на сервере, в контейнере на сети bizsoft_default):
 *   docker run --rm --network bizsoft_default \
 *     -e DIRECTUS_URL=http://directus:8055 \
 *     -e ENV_FILE=/env -e TOKEN_OUT=/out/token \
 *     -v /opt/bizsoft/.env:/env:ro -v /tmp/bz:/out \
 *     -v /tmp/directus-setup.mjs:/setup.mjs node:22-alpine node /setup.mjs
 *
 * Учётка админа берётся из ENV_FILE (ADMIN_EMAIL/ADMIN_PASSWORD) или process.env.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { randomBytes } from 'node:crypto';

// ── чтение env-файла без shell-評価 (split на первом '=') ──
function loadEnvFile(path) {
  const out = {};
  try {
    const txt = readFileSync(path, 'utf8');
    for (const line of txt.split(/\r?\n/)) {
      const t = line.trim();
      if (!t || t.startsWith('#')) continue;
      const i = t.indexOf('=');
      if (i < 0) continue;
      let v = t.slice(i + 1).trim();
      if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
      out[t.slice(0, i).trim()] = v;
    }
  } catch {
    /* нет файла — используем process.env */
  }
  return out;
}

const fileEnv = process.env.ENV_FILE ? loadEnvFile(process.env.ENV_FILE) : {};
const env = { ...fileEnv, ...process.env };
const DIRECTUS_URL = (env.DIRECTUS_URL || 'http://directus:8055').replace(/\/$/, '');
const ADMIN_EMAIL = env.ADMIN_EMAIL || env.DIRECTUS_ADMIN_EMAIL;
const ADMIN_PASSWORD = env.ADMIN_PASSWORD || env.DIRECTUS_ADMIN_PASSWORD;
const TOKEN_OUT = process.env.TOKEN_OUT || '';
// Позволяем задать фикс. токен (для повторных прогонов), иначе генерируем.
const SERVICE_TOKEN = env.SITE_SERVICE_TOKEN || 'bz_' + randomBytes(24).toString('hex');

let token = '';
async function api(method, path, body) {
  const res = await fetch(DIRECTUS_URL + path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json;
  try { json = text ? JSON.parse(text) : {}; } catch { json = { raw: text }; }
  if (!res.ok) {
    const err = new Error(`${method} ${path} → ${res.status}: ${json?.errors?.[0]?.message || text?.slice(0, 200)}`);
    err.status = res.status;
    err.body = json;
    throw err;
  }
  return json.data;
}

async function login() {
  const r = await fetch(DIRECTUS_URL + '/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: ADMIN_EMAIL, password: ADMIN_PASSWORD }),
  });
  if (!r.ok) throw new Error('Login failed: ' + r.status + ' ' + (await r.text()).slice(0, 160));
  token = (await r.json()).data.access_token;
  console.log('✓ login OK');
}

// ── helpers схемы (идемпотентные) ──
const existingCollections = new Set();
async function loadCollections() {
  const cols = await api('GET', '/collections');
  cols.forEach((c) => existingCollections.add(c.collection));
}

async function ensureCollection(name, meta = {}) {
  if (existingCollections.has(name)) { console.log(`= collection ${name} exists`); return; }
  await api('POST', '/collections', {
    collection: name,
    schema: { name },
    meta: { icon: 'box', ...meta },
    fields: [
      { field: 'id', type: 'integer', meta: { hidden: true, interface: 'input', readonly: true }, schema: { is_primary_key: true, has_auto_increment: true } },
    ],
  });
  existingCollections.add(name);
  console.log(`✓ collection ${name} created`);
}

async function getFields(collection) {
  const f = await api('GET', `/fields/${collection}`);
  return new Set(f.map((x) => x.field));
}

async function ensureField(collection, field, def) {
  const have = await getFields(collection);
  if (have.has(field)) return;
  await api('POST', `/fields/${collection}`, { field, ...def });
  console.log(`  ✓ ${collection}.${field}`);
}

async function ensureRelation(collection, field, relatedCollection, onDelete = 'SET NULL') {
  const rels = await api('GET', '/relations');
  if (rels.some((r) => r.collection === collection && r.field === field)) return;
  await api('POST', '/relations', {
    collection,
    field,
    related_collection: relatedCollection,
    schema: { on_delete: onDelete },
    meta: {},
  });
  console.log(`  ✓ relation ${collection}.${field} → ${relatedCollection}`);
}

const STATUS_DEF = {
  type: 'string',
  meta: {
    interface: 'select-dropdown',
    display: 'labels',
    width: 'half',
    options: {
      choices: [
        { text: 'Опубликовано', value: 'published' },
        { text: 'Черновик', value: 'draft' },
        { text: 'В архиве', value: 'archived' },
      ],
    },
  },
  schema: { default_value: 'draft' },
};

async function buildSchema() {
  await loadCollections();

  // ── categories ──
  await ensureCollection('categories', { icon: 'category', sort_field: 'sort' });
  await ensureField('categories', 'status', STATUS_DEF);
  await ensureField('categories', 'name', { type: 'string', meta: { interface: 'input', required: true } , schema: { is_nullable: false } });
  await ensureField('categories', 'slug', { type: 'string', meta: { interface: 'input', required: true, note: 'kebab-case, латиница' }, schema: { is_unique: true, is_nullable: false } });
  await ensureField('categories', 'seo_text', { type: 'text', meta: { interface: 'input-rich-text-md' } });
  await ensureField('categories', 'meta_title', { type: 'string', meta: { interface: 'input' } });
  await ensureField('categories', 'meta_description', { type: 'text', meta: { interface: 'input-multiline' } });
  await ensureField('categories', 'sort', { type: 'integer', meta: { interface: 'input', hidden: true } });

  // ── products ──
  await ensureCollection('products', { icon: 'shopping_bag', sort_field: 'sort' });
  await ensureField('products', 'status', STATUS_DEF);
  await ensureField('products', 'name', { type: 'string', meta: { interface: 'input', required: true }, schema: { is_nullable: false } });
  await ensureField('products', 'sku', { type: 'string', meta: { interface: 'input', required: true, note: 'Артикул (уникальный)' }, schema: { is_unique: true, is_nullable: false } });
  await ensureField('products', 'slug', { type: 'string', meta: { interface: 'input', required: true }, schema: { is_unique: true, is_nullable: false } });
  // M2O category
  await ensureField('products', 'category', { type: 'integer', meta: { interface: 'select-dropdown-m2o', special: ['m2o'], options: { template: '{{name}}' } } });
  await ensureRelation('products', 'category', 'categories');
  await ensureField('products', 'short_description', { type: 'text', meta: { interface: 'input-multiline' } });
  await ensureField('products', 'description', { type: 'text', meta: { interface: 'input-rich-text-md' } });
  await ensureField('products', 'seo_text', { type: 'text', meta: { interface: 'input-rich-text-md' } });
  // Динамическая нижняя часть карточки (решение руководителя 13.09.2026,
  // docs/tasks/product-card-content-system/README.md п. 4): классификация
  // по осям и модули контента. Пустое content_modules — legacy-рендер.
  await ensureField('products', 'product_nature', { type: 'string', meta: { interface: 'select-dropdown', width: 'half', options: { choices: ['mono', 'suite', 'addon', 'credit', 'service'].map((v) => ({ text: v, value: v })) }, note: 'Природа товара (ось NATURE)' } });
  await ensureField('products', 'packaging', { type: 'string', meta: { interface: 'select-dropdown', width: 'half', options: { choices: ['single', 'edition_tier', 'volume_tier', 'configuration', 'composite'].map((v) => ({ text: v, value: v })) }, note: 'Как позиция соотносится с соседями (ось PACKAGING)' } });
  await ensureField('products', 'family_key', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Семейство соседних SKU: <ВЕНДОР>-<ПРОДУКТ>' } });
  await ensureField('products', 'unit_label', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Единица расчёта словами: рабочее место, сервер, пакет: 10 устройств' } });
  await ensureField('products', 'edition_label', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Редакция внутри семейства' } });
  await ensureField('products', 'volume_label', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Объём или тип нагрузки внутри семейства' } });
  await ensureField('products', 'base_product_sku', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Для дополнений: артикул базового продукта' } });
  await ensureField('products', 'addon_source', { type: 'string', meta: { interface: 'select-dropdown', width: 'half', options: { choices: [{ text: 'vendor', value: 'vendor' }, { text: 'marketplace', value: 'marketplace' }] }, note: 'Дополнение самого производителя или стороннего разработчика' } });
  await ensureField('products', 'license_model', { type: 'string', meta: { interface: 'select-dropdown', width: 'half', options: { choices: ['free', 'monthly', 'annual', 'annual_fallback', 'perpetual', 'external'].map((v) => ({ text: v, value: v })) }, note: 'Модель лицензирования дополнения' } });
  await ensureField('products', 'content_modules', { type: 'json', meta: { interface: 'input-code', options: { language: 'json' }, note: 'Модули нижней части карточки: [{code,title,kind,body,items,rows,links}]. Пусто — legacy-рендер.' } });
  await ensureField('products', 'content_version', { type: 'string', meta: { interface: 'input', width: 'half', readonly: true, note: 'Версия конвейера контента (cm-1.0)' } });
  await ensureField('products', 'meta_title', { type: 'string', meta: { interface: 'input' } });
  await ensureField('products', 'meta_description', { type: 'text', meta: { interface: 'input-multiline' } });
  await ensureField('products', 'price', { type: 'float', meta: { interface: 'input', note: 'Цена, ₽' }, schema: { default_value: 0 } });
  await ensureField('products', 'currency', { type: 'string', meta: { interface: 'input' }, schema: { default_value: 'RUB' } });
  await ensureField('products', 'base_price_usd', { type: 'float', meta: { interface: 'input', note: 'Базовая цена в USD (для привязки к курсу)' } });
  await ensureField('products', 'peg_to_usd', { type: 'boolean', meta: { interface: 'boolean' }, schema: { default_value: false } });
  // Закупка: поля появились на проде разными путями — здесь они закреплены,
  // чтобы новая база собиралась целиком (ensureField пропускает существующие).
  await ensureField('products', 'base_price_eur', { type: 'float', meta: { interface: 'input', note: 'Закупочная себестоимость в EUR (с сайта производителя)' } });
  await ensureField('products', 'peg_currency', { type: 'string', meta: { interface: 'select-dropdown', options: { choices: [{ text: 'USD', value: 'USD' }, { text: 'EUR', value: 'EUR' }] }, note: 'Валюта закупки' } });
  await ensureField('products', 'markup_coeff', { type: 'float', meta: { interface: 'input', note: 'Коэффициент наценки: цена = себестоимость × курс × коэф. База 1.85' } });
  // Свежесть закупочной цены — решение руководителя 28.08.2026: менеджер
  // должен видеть, сегодняшняя это цена или трёхмесячной давности, и откуда
  // она взята. Экономика КП помечает устаревшие цены по этой дате.
  await ensureField('products', 'purchase_updated_at', { type: 'timestamp', meta: { interface: 'datetime', width: 'half', note: 'Когда закупочная цена сверялась с сайтом производителя.' } });
  await ensureField('products', 'purchase_source', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Откуда взята закупочная цена: страница прайса вендора.' } });
  // Дата содержательного изменения карточки — источник lastmod в sitemap
  // (03.09.2026). Ставится импортом каталога, правками текстов и меты
  // (админка, ops-apply-descriptions, ops-fix-meta); переоценка цен её не
  // трогает — в отличие от date_updated, который Directus сдвигает при любом
  // PATCH. Без значения sitemap не отдаёт lastmod у товара.
  await ensureField('products', 'content_updated_at', { type: 'timestamp', meta: { interface: 'datetime', width: 'half', note: 'Дата содержательного изменения карточки — lastmod в sitemap. Переоценка цен не трогает.' } });
  // Тип товара и варианты (05.09.2026, подарочные карты Apple — docs/gift-cards.md).
  // Вариант = отдельная строка с parent_sku, регионом и номиналом; закупка в
  // base_price_usd, коэффициент 3,0 — переоценивает тот же ops-currency-refresh.
  await ensureField('products', 'product_type', { type: 'string', meta: { interface: 'select-dropdown', width: 'half', options: { allowNone: true, choices: [{ text: 'Подарочная карта', value: 'gift_card' }] }, note: 'Пусто — обычная лицензия/подписка. gift_card — цифровая подарочная карта: цена = закупка USD × курс × 3,0.' } });
  await ensureField('products', 'parent_sku', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Артикул родительской карточки — только у варианта (номинала). Вариант страницы не имеет: 301 на родителя.' } });
  await ensureField('products', 'region_code', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Регион карты: RU, KZ, TR (ISO 3166-1 alpha-2).' } });
  await ensureField('products', 'region_name', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Название региона для витрины: Россия, Казахстан, Турция.' } });
  await ensureField('products', 'denomination', { type: 'float', meta: { interface: 'input', width: 'half', note: 'Номинал — сумма, зачисляемая на баланс аккаунта. В расчёте цены не участвует.' } });
  await ensureField('products', 'denomination_currency', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Валюта номинала: RUB, KZT, TRY.' } });
  await ensureField('products', 'variant_label', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Подпись варианта на витрине, если номинал — не сумма в валюте (например, «Nitro, 12 месяцев»). Пусто — подпись из номинала.' } });
  await ensureField('products', 'availability', { type: 'string', meta: { interface: 'select-dropdown', width: 'half', options: { choices: [{ text: 'В наличии', value: 'in_stock' }, { text: 'Ограниченное количество', value: 'limited' }, { text: 'Нет в наличии', value: 'out_of_stock' }] }, note: 'Наличие кодов варианта. out_of_stock — вариант показан, но не выбирается.' }, schema: { default_value: 'in_stock' } });
  await ensureField('products', 'markup_percent', { type: 'float', meta: { interface: 'input', note: 'Наценка, %' }, schema: { default_value: 0 } });
  await ensureField('products', 'promo_price', { type: 'float', meta: { interface: 'input', note: 'Акционная цена, ₽' } });
  await ensureField('products', 'promo_label', { type: 'string', meta: { interface: 'input' } });
  await ensureField('products', 'promo_start', { type: 'date', meta: { interface: 'datetime', width: 'half' } });
  await ensureField('products', 'promo_end', { type: 'date', meta: { interface: 'datetime', width: 'half' } });
  // image M2O → directus_files
  await ensureField('products', 'image', { type: 'uuid', meta: { interface: 'file-image', special: ['file'] } });
  await ensureRelation('products', 'image', 'directus_files');
  await ensureField('products', 'features', { type: 'json', meta: { interface: 'list', options: { fields: [{ field: 'value', type: 'string', meta: { interface: 'input' } }] }, note: 'Список характеристик' } });
  await ensureField('products', 'faq', { type: 'json', meta: { interface: 'list', options: { fields: [{ field: 'q', type: 'string', meta: { interface: 'input' } }, { field: 'a', type: 'string', meta: { interface: 'input-multiline' } }] } } });
  await ensureField('products', 'sort', { type: 'integer', meta: { interface: 'input', hidden: true } });

  // ── leads ──
  await ensureCollection('leads', { icon: 'contact_mail' });
  await ensureField('leads', 'created_at', { type: 'timestamp', meta: { interface: 'datetime', special: ['date-created'], readonly: true, width: 'half' } });
  await ensureField('leads', 'name', { type: 'string', meta: { interface: 'input' } });
  await ensureField('leads', 'company', { type: 'string', meta: { interface: 'input' } });
  await ensureField('leads', 'email', { type: 'string', meta: { interface: 'input', required: true }, schema: { is_nullable: false } });
  await ensureField('leads', 'phone', { type: 'string', meta: { interface: 'input' } });
  await ensureField('leads', 'message', { type: 'text', meta: { interface: 'input-multiline' } });
  await ensureField('leads', 'product_ref', { type: 'string', meta: { interface: 'input' } });
  await ensureField('leads', 'consent', { type: 'boolean', meta: { interface: 'boolean' }, schema: { default_value: false } });
  await ensureField('leads', 'source', { type: 'string', meta: { interface: 'input' } });
  // Реквизиты и номер КП: заявка из скачивания предложения приходит уже с ними.
  await ensureField('leads', 'inn', { type: 'string', meta: { interface: 'input', width: 'half', note: 'ИНН организации, если клиент его указал.' } });
  await ensureField('leads', 'quote_no', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Номер скачанного коммерческого предложения.' } });

  // ── воронка продаж (добавлено 20.08.2026) ──
  // До этого заявка хранила только контакт: по ней нельзя было сказать, чем
  // дело кончилось. Уровни «обращение → сделка → выручка» в отчётах оставались
  // пустыми не потому, что продаж не было, а потому, что их негде было отметить.
  await ensureField('leads', 'status', {
    type: 'string',
    meta: {
      interface: 'select-dropdown', width: 'half',
      note: 'Стадия воронки. Меняется менеджером по мере работы с заявкой.',
      options: { choices: [
        { text: 'Новая', value: 'new' },
        { text: 'В работе', value: 'in_progress' },
        { text: 'Квалифицирована', value: 'qualified' },
        { text: 'Отправлено КП', value: 'proposal' },
        { text: 'Выставлен счёт', value: 'invoiced' },
        { text: 'Оплачено', value: 'won' },
        { text: 'Отказ', value: 'lost' },
        { text: 'Мусор', value: 'spam' },
      ] },
    },
    schema: { default_value: 'new' },
  });
  // ── Источник обращения ──
  //
  // До появления этих полей связать заявку с каналом было невозможно ни в одну
  // сторону: в аналитике нет события заявки, в CRM нет источника визита. Поле
  // source при этом хранит идентификатор формы, а не канал, и в письме
  // менеджеру строка «Источник: pricing» читалась как источник перехода —
  // поэтому форма и канал теперь лежат в разных полях.
  await ensureField('leads', 'form_source', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Какая форма сайта приняла заявку: pricing, question, quote.' } });
  await ensureField('leads', 'last_touch_source', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Канал последнего касания: что привело к заявке сейчас.' } });
  await ensureField('leads', 'first_touch_source', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Канал первого касания: откуда клиент узнал о нас. Не перезаписывается 90 дней.' } });
  await ensureField('leads', 'first_touch_ts', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Когда состоялось первое касание.' } });
  await ensureField('leads', 'landing_path', { type: 'string', meta: { interface: 'input', note: 'Страница входа на сайт.' } });
  await ensureField('leads', 'utm_source', { type: 'string', meta: { interface: 'input', width: 'half' } });
  await ensureField('leads', 'utm_medium', { type: 'string', meta: { interface: 'input', width: 'half' } });
  await ensureField('leads', 'utm_campaign', { type: 'string', meta: { interface: 'input', width: 'half' } });
  await ensureField('leads', 'utm_content', { type: 'string', meta: { interface: 'input', width: 'half' } });
  await ensureField('leads', 'utm_term', { type: 'string', meta: { interface: 'input', width: 'half' } });
  await ensureField('leads', 'yclid', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Автометка Яндекс.Директа.' } });
  await ensureField('leads', 'gclid', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Автометка Google Ads.' } });
  // Идентификаторы посетителя в счётчиках — ключ к обратной сверке
  // «заявка в CRM ↔ визит в аналитике». Без них сквозная аналитика невозможна
  // в принципе: связать две системы больше нечем.
  await ensureField('leads', 'first_touch_referrer', { type: 'string', meta: { interface: 'input', note: 'Полный адрес первого перехода. Хоста мало: yandex.ru — это и выдача, и карточка организации, и Дзен.' } });
  await ensureField('leads', 'last_touch_referrer', { type: 'string', meta: { interface: 'input', note: 'Полный адрес последнего перехода — по нему письмо отличает органику от карточки в Яндекс Бизнесе.' } });
  await ensureField('leads', 'visit_path', { type: 'text', meta: { interface: 'input-multiline', note: 'Шаги посетителя по сайту из браузера: «дд.мм чч:мм~/страница» через «|». Метрика тот же путь отдаёт с задержкой.' } });
  await ensureField('leads', 'ym_client_id', { type: 'string', meta: { interface: 'input', width: 'half', note: 'ClientID Яндекс.Метрики.' } });
  await ensureField('leads', 'ga_client_id', { type: 'string', meta: { interface: 'input', width: 'half', note: 'client_id GA4.' } });

  // Связь с зеркалом Bitrix24 (docs/rules/crm-mirror.md): без номера лида
  // портала обратный канал не знает, к какой заявке относится его событие,
  // и стадия из портала не возвращается.
  await ensureField('leads', 'b24_lead_id', { type: 'integer', meta: { interface: 'input', width: 'half', readonly: true, note: 'Номер лида в Bitrix24. Проставляется автоматически при зеркалировании заявки.' } });
  // Ссылки на доказательства согласий (152-ФЗ). В заявке лежат только
  // ссылки: сам журнал consent_audit_log остаётся источником истины, а
  // Bitrix24 получает те же значения в свои поля (docs/rules/consent-audit.md).
  await ensureField('leads', 'consent_event_id', { type: 'uuid', meta: { interface: 'input', width: 'half', readonly: true, note: 'Событие согласия на обработку ПДн, по которому принята заявка.' } });
  await ensureField('leads', 'marketing_consent', { type: 'boolean', meta: { interface: 'boolean', width: 'half', readonly: true, note: 'Было ли отмечено необязательное согласие на рассылку.' }, schema: { default_value: false } });
  await ensureField('leads', 'marketing_consent_event_id', { type: 'uuid', meta: { interface: 'input', width: 'half', readonly: true, note: 'Событие MARKETING granted, если согласие дано.' } });
  await ensureField('leads', 'owner', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Ответственный менеджер.' } });
  await ensureField('leads', 'amount', { type: 'float', meta: { interface: 'input', width: 'half', note: 'Сумма сделки в рублях. Заполняется при выставлении счёта.' } });
  // Экономика сделки из КП (P1, решение руководителя 28.08.2026): воронка
  // отвечает не только «сколько выручки в работе», но и «сколько прибыли».
  await ensureField('leads', 'quote_cost_rub', { type: 'float', meta: { interface: 'input', width: 'half', note: 'Закупка по КП, ₽ (по курсу ЦБ на дату КП).' } });
  await ensureField('leads', 'quote_margin_rub', { type: 'float', meta: { interface: 'input', width: 'half', note: 'Расчётная прибыль по КП, ₽ (после НДС, налога и валютных расходов).' } });
  await ensureField('leads', 'quote_margin_pct', { type: 'float', meta: { interface: 'input', width: 'half', note: 'Прибыль по КП, % от выручки.' } });
  await ensureField('leads', 'quote_fx_rate', { type: 'float', meta: { interface: 'input', width: 'half', note: 'Курс ЦБ USD, зафиксированный при расчёте КП.' } });
  await ensureField('leads', 'qualified_at', { type: 'timestamp', meta: { interface: 'datetime', width: 'half', note: 'Когда стало ясно, что это реальный покупатель.' } });
  await ensureField('leads', 'closed_at', { type: 'timestamp', meta: { interface: 'datetime', width: 'half', note: 'Дата оплаты или отказа.' } });
  await ensureField('leads', 'lost_reason', {
    type: 'string',
    meta: {
      interface: 'select-dropdown', width: 'half',
      note: 'Заполняется только при отказе — по нему видно, где теряем сделки.',
      options: { choices: [
        { text: 'Цена', value: 'price' },
        { text: 'Сроки', value: 'timing' },
        { text: 'Не смогли поставить', value: 'no_supply' },
        { text: 'Выбрали другого поставщика', value: 'competitor' },
        { text: 'Не вышли на связь', value: 'no_contact' },
        { text: 'Не наш профиль', value: 'not_our_case' },
      ] },
    },
  });
  await ensureField('leads', 'next_action_at', { type: 'timestamp', meta: { interface: 'datetime', width: 'half', note: 'Когда вернуться к заявке.' } });
  await ensureField('leads', 'note', { type: 'text', meta: { interface: 'input-multiline', note: 'Внутренний комментарий менеджера. Клиенту не показывается.' } });
  await ensureField('leads', 'updated_at', { type: 'timestamp', meta: { interface: 'datetime', special: ['date-updated'], readonly: true, width: 'half' } });

  // ── lead_events: история работы с заявкой ──
  // Отдельная коллекция, а не поле в заявке: событий много, они не переписывают
  // друг друга, и по ним считается срок ответа. Хранить их списком в JSON —
  // значит потерять возможность отобрать «все письма за неделю» одним запросом.
  await ensureCollection('lead_events', { icon: 'history' });
  await ensureField('lead_events', 'created_at', { type: 'timestamp', meta: { interface: 'datetime', special: ['date-created'], readonly: true, width: 'half' } });
  await ensureField('lead_events', 'lead', { type: 'integer', meta: { interface: 'input', width: 'half', note: 'Заявка, к которой относится событие.' } });
  await ensureField('lead_events', 'kind', {
    type: 'string',
    meta: {
      interface: 'select-dropdown', width: 'half',
      options: { choices: [
        { text: 'Заметка', value: 'note' },
        { text: 'Письмо', value: 'email' },
        { text: 'Звонок', value: 'call' },
        { text: 'Смена стадии', value: 'stage' },
      ] },
    },
    schema: { default_value: 'note' },
  });
  await ensureField('lead_events', 'author', { type: 'string', meta: { interface: 'input', width: 'half' } });
  await ensureField('lead_events', 'subject', { type: 'string', meta: { interface: 'input' } });
  await ensureField('lead_events', 'text', { type: 'text', meta: { interface: 'input-multiline' } });
  await ensureRelation('lead_events', 'lead', 'leads', 'CASCADE');

  // ── quotes ──
  await ensureCollection('quotes', { icon: 'request_quote' });
  await ensureField('quotes', 'created_at', { type: 'timestamp', meta: { interface: 'datetime', special: ['date-created'], readonly: true, width: 'half' } });
  await ensureField('quotes', 'quote_no', { type: 'string', meta: { interface: 'input' } });
  await ensureField('quotes', 'buyer_company', { type: 'string', meta: { interface: 'input' } });
  await ensureField('quotes', 'buyer_inn', { type: 'string', meta: { interface: 'input' } });
  await ensureField('quotes', 'contact_name', { type: 'string', meta: { interface: 'input' } });
  await ensureField('quotes', 'email', { type: 'string', meta: { interface: 'input' } });
  await ensureField('quotes', 'phone', { type: 'string', meta: { interface: 'input' } });
  await ensureField('quotes', 'items', { type: 'json', meta: { interface: 'input-code', options: { language: 'json' } } });
  await ensureField('quotes', 'total', { type: 'float', meta: { interface: 'input' } });
  await ensureField('quotes', 'consent', { type: 'boolean', meta: { interface: 'boolean' }, schema: { default_value: false } });

  // ── currency_rate ──
  await ensureCollection('currency_rate', { icon: 'currency_exchange' });
  await ensureField('currency_rate', 'mode', { type: 'string', meta: { interface: 'select-dropdown', options: { choices: [{ text: 'Вручную', value: 'manual' }, { text: 'Авто (ЦБ РФ)', value: 'auto' }] } }, schema: { default_value: 'manual' } });
  await ensureField('currency_rate', 'usd_rate', { type: 'float', meta: { interface: 'input', note: 'Рублей за 1 USD' } });
  await ensureField('currency_rate', 'rate_date', { type: 'date', meta: { interface: 'datetime' } });
  await ensureField('currency_rate', 'source', { type: 'string', meta: { interface: 'input' } });
  await ensureField('currency_rate', 'auto_recalc', { type: 'boolean', meta: { interface: 'boolean' }, schema: { default_value: false } });
  await ensureField('currency_rate', 'updated_at', { type: 'timestamp', meta: { interface: 'datetime', special: ['date-updated'], readonly: true } });

  // ── app_kv: общее хранилище счётчиков и кэша ──
  // Пороги на публичных формах (SEC-RL-001) и кэш справочника организаций.
  // Счётчик в памяти процесса при двух инстансах считает вдвое больше, чем
  // должен, и обнуляется рестартом — поэтому состояние живёт в базе.
  // Ключ — строковый первичный: upsert идёт прямо по нему, без поиска.
  if (!existingCollections.has('app_kv')) {
    await api('POST', '/collections', {
      collection: 'app_kv',
      schema: { name: 'app_kv' },
      meta: { icon: 'key', note: 'Счётчики лимитов и кэш. Служебная таблица, руками не правится.', hidden: true },
      fields: [
        {
          field: 'key',
          type: 'string',
          meta: { interface: 'input', readonly: true },
          schema: { is_primary_key: true, has_auto_increment: false, is_nullable: false, max_length: 190 },
        },
      ],
    });
    existingCollections.add('app_kv');
    console.log('✓ collection app_kv created');
  } else {
    console.log('= collection app_kv exists');
  }
  await ensureField('app_kv', 'value', { type: 'json', meta: { interface: 'input-code', options: { language: 'json' }, readonly: true } });
  await ensureField('app_kv', 'expires_at', { type: 'timestamp', meta: { interface: 'datetime', readonly: true, note: 'После этого момента запись считается отсутствующей' } });

  // ── consent_audit_log: неизменяемые доказательства согласий ──
  //
  // Только INSERT: событие, однажды записанное, не правится и не удаляется
  // (ТЗ 16.09.2026, п. 3). Ошибка исправляется новым корректирующим
  // событием со ссылкой на исходное (`corrects_event`), а не правкой
  // старого — иначе журнал перестаёт быть доказательством и становится
  // просто таблицей. Права сервисной роли ниже это закрепляют: create и
  // read есть, update и delete нет.
  //
  // Bitrix24 источником доказательств не является: портал хранит копию для
  // работы менеджера, а подтверждать волеизъявление перед Роскомнадзором
  // или ФАС можно только отсюда.
  await ensureCollection('consent_audit_log', {
    icon: 'gavel',
    note: 'Журнал согласий. Записи не редактируются и не удаляются — только новое корректирующее событие.',
  });
  await ensureField('consent_audit_log', 'event_id', { type: 'uuid', meta: { interface: 'input', readonly: true, width: 'half', note: 'Идентификатор события. Уходит в CRM и в карточку доказательства.' }, schema: { is_unique: true, is_indexed: true } });
  await ensureField('consent_audit_log', 'subject_id', { type: 'uuid', meta: { interface: 'input', readonly: true, width: 'half', note: 'Субъект: один и тот же адрес получает один и тот же идентификатор.' }, schema: { is_indexed: true } });
  await ensureField('consent_audit_log', 'source', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Откуда пришло событие: идентификатор формы, cookie-баннер, ссылка отписки, админ.' }, schema: { is_indexed: true } });
  await ensureField('consent_audit_log', 'source_action', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Как выражена воля: checkbox, bulk_control_all, cookie_banner и т. д.' } });
  await ensureField('consent_audit_log', 'page_url', { type: 'text', meta: { interface: 'input', note: 'Страница, на которой человек дал согласие.' } });
  await ensureField('consent_audit_log', 'form_id', { type: 'string', meta: { interface: 'input', width: 'half' } });
  await ensureField('consent_audit_log', 'submitted_at', { type: 'timestamp', meta: { interface: 'datetime', width: 'half', note: 'Момент волеизъявления.' }, schema: { is_indexed: true } });
  await ensureField('consent_audit_log', 'last_name', { type: 'string', meta: { interface: 'input', width: 'half' } });
  await ensureField('consent_audit_log', 'first_name', { type: 'string', meta: { interface: 'input', width: 'half' } });
  await ensureField('consent_audit_log', 'company', { type: 'string', meta: { interface: 'input', width: 'half' }, schema: { is_indexed: true } });
  await ensureField('consent_audit_log', 'phone', { type: 'string', meta: { interface: 'input', width: 'half' }, schema: { is_indexed: true } });
  await ensureField('consent_audit_log', 'email', { type: 'string', meta: { interface: 'input', width: 'half' }, schema: { is_indexed: true } });
  await ensureField('consent_audit_log', 'consent_type', {
    type: 'string',
    meta: {
      interface: 'select-dropdown', width: 'half', display: 'labels',
      options: { choices: [
        { text: 'Персональные данные', value: 'personal_data' },
        { text: 'Реклама и рассылка', value: 'marketing' },
        { text: 'Яндекс.Метрика', value: 'yandex_analytics' },
        { text: 'Google Analytics', value: 'google_analytics' },
      ] },
    },
    schema: { is_indexed: true },
  });
  await ensureField('consent_audit_log', 'consent_action', {
    type: 'string',
    meta: {
      interface: 'select-dropdown', width: 'half', display: 'labels',
      options: { choices: [
        { text: 'Дано', value: 'granted' },
        { text: 'Отозвано', value: 'withdrawn' },
        { text: 'Отказано', value: 'denied' },
        { text: 'Подтверждено заново', value: 'renewed' },
      ] },
    },
    schema: { is_indexed: true },
  });
  await ensureField('consent_audit_log', 'consent_scope', { type: 'json', meta: { interface: 'input-code', options: { language: 'json' }, note: 'Объём согласия: цели, каналы, состав данных.' } });
  await ensureField('consent_audit_log', 'document_version', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Версия документа из legal-manifest.json. С клиента не принимается.' } });
  await ensureField('consent_audit_log', 'document_sha256', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Контрольный хэш редакции — по нему восстанавливается текст.' }, schema: { max_length: 64 } });
  await ensureField('consent_audit_log', 'consent_text_snapshot', { type: 'text', meta: { interface: 'input-multiline', note: 'Формулировка, которую человек видел в форме. Снимок, а не ссылка: текст интерфейса меняется.' } });
  await ensureField('consent_audit_log', 'ip_address', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Доступен только привилегированной роли.' }, schema: { max_length: 45 } });
  await ensureField('consent_audit_log', 'user_agent', { type: 'text', meta: { interface: 'input', note: 'Доступен только привилегированной роли.' } });
  await ensureField('consent_audit_log', 'request_id', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Связывает события одной отправки формы.' }, schema: { is_indexed: true } });
  await ensureField('consent_audit_log', 'lead_id', { type: 'integer', meta: { interface: 'input', width: 'half', note: 'Заявка в воронке Directus.' } });
  await ensureField('consent_audit_log', 'bitrix_lead_id', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Номер лида в Bitrix24. Портал — зеркало, а не источник доказательства.' }, schema: { is_indexed: true } });
  await ensureField('consent_audit_log', 'corrects_event', { type: 'uuid', meta: { interface: 'input', width: 'half', note: 'Исходное событие, которое исправляет это. Заполняется только у корректирующих записей.' } });
  await ensureField('consent_audit_log', 'created_at', { type: 'timestamp', meta: { interface: 'datetime', special: ['date-created'], readonly: true, width: 'half' } });

  // ── marketing_registry: текущее разрешение на рассылку ──
  //
  // Журнал отвечает на вопрос «что было», реестр — «можно ли слать письмо
  // сейчас». Разделение не косметическое: аудиторию рассылки собирают по
  // реестру, а доказывают журналом. Адрес из реестра не удаляется даже
  // после отзыва — иначе следующая выгрузка подпишет человека заново,
  // потому что «его нет в списке отписавшихся» (ТЗ, п. 4).
  await ensureCollection('marketing_registry', {
    icon: 'mark_email_read',
    note: 'Разрешение на рекламную рассылку. Адрес не удаляется после отзыва — он остаётся в suppression.',
  });
  await ensureField('marketing_registry', 'subject_id', { type: 'uuid', meta: { interface: 'input', readonly: true, width: 'half' }, schema: { is_indexed: true } });
  await ensureField('marketing_registry', 'email_normalized', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Адрес в нижнем регистре без пробелов — ключ реестра.' }, schema: { is_unique: true, is_indexed: true, max_length: 320 } });
  await ensureField('marketing_registry', 'status', {
    type: 'string',
    meta: {
      interface: 'select-dropdown', width: 'half', display: 'labels',
      note: 'Рассылать можно только subscribed.',
      options: { choices: [
        { text: 'Подписан', value: 'subscribed' },
        { text: 'Отписался', value: 'unsubscribed' },
        { text: 'Заблокирован', value: 'suppressed' },
        { text: 'Недоставляемый', value: 'bounced' },
      ] },
    },
    schema: { default_value: 'unsubscribed', is_indexed: true },
  });
  await ensureField('marketing_registry', 'consent_event_id', { type: 'uuid', meta: { interface: 'input', width: 'half', note: 'Событие MARKETING granted, на котором держится подписка. Без него адрес в аудиторию не попадает.' } });
  await ensureField('marketing_registry', 'subscribed_at', { type: 'timestamp', meta: { interface: 'datetime', width: 'half' } });
  await ensureField('marketing_registry', 'unsubscribed_at', { type: 'timestamp', meta: { interface: 'datetime', width: 'half' } });
  await ensureField('marketing_registry', 'unsubscribe_reason', { type: 'string', meta: { interface: 'input', width: 'half', note: 'link, email_request, complaint, bounce, admin.' } });
  await ensureField('marketing_registry', 'source', { type: 'string', meta: { interface: 'input', width: 'half' } });
  await ensureField('marketing_registry', 'provider_contact_id', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Идентификатор контакта у провайдера рассылки. Провайдер заменяем.' } });
  await ensureField('marketing_registry', 'updated_at', { type: 'timestamp', meta: { interface: 'datetime', special: ['date-updated'], readonly: true, width: 'half' } });

  // ── admin_audit_log: кто и что смотрел в разделе комплаенса ──
  //
  // Доступ к доказательствам сам является действием, которое нужно уметь
  // объяснить: кто открыл карточку субъекта, кто выгрузил журнал, кто
  // поменял маркетинговый статус (HELP администратора, п. 7).
  await ensureCollection('admin_audit_log', { icon: 'admin_panel_settings', note: 'Действия в разделе «Комплаенс». Только запись и чтение.' });
  await ensureField('admin_audit_log', 'actor', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Роль и имя администратора.' }, schema: { is_indexed: true } });
  await ensureField('admin_audit_log', 'role', { type: 'string', meta: { interface: 'input', width: 'half', note: 'compliance_admin или owner.' } });
  await ensureField('admin_audit_log', 'action', { type: 'string', meta: { interface: 'input', width: 'half', note: 'view_log, view_evidence, export, set_marketing_status, record_withdrawal, build_audience.' }, schema: { is_indexed: true } });
  await ensureField('admin_audit_log', 'target', { type: 'string', meta: { interface: 'input', width: 'half', note: 'Что именно: адрес субъекта, event_id, имя выгрузки.' } });
  await ensureField('admin_audit_log', 'details', { type: 'json', meta: { interface: 'input-code', options: { language: 'json' }, note: 'Фильтры запроса и объём выгрузки.' } });
  await ensureField('admin_audit_log', 'ip_address', { type: 'string', meta: { interface: 'input', width: 'half' }, schema: { max_length: 45 } });
  await ensureField('admin_audit_log', 'created_at', { type: 'timestamp', meta: { interface: 'datetime', special: ['date-created'], readonly: true, width: 'half' }, schema: { is_indexed: true } });

  console.log('✓ schema ready');
}

// ── права/токен (Directus v11: policies + access) ──
const APP_PERMS = [
  ['categories', 'read'],
  ['products', 'read'], ['products', 'update'],
  // Чтение и правка лидов нужны админ-странице /admin/leads: воронка ведётся
  // с телефона через сайт, а не через админку Directus (она наружу не смотрит).
  // delete нужен для удаления мусорных заявок из корзины админ-кабинета.
  ['leads', 'create'], ['leads', 'read'], ['leads', 'update'], ['leads', 'delete'],
  ['lead_events', 'create'], ['lead_events', 'read'], ['lead_events', 'delete'],
  ['quotes', 'create'], ['quotes', 'read'],
  ['currency_rate', 'read'], ['currency_rate', 'create'], ['currency_rate', 'update'],
  // Счётчики лимитов и кэш справочника: сайт читает, создаёт и обновляет
  // записи сам; delete — для уборки просроченных ключей.
  ['app_kv', 'create'], ['app_kv', 'read'], ['app_kv', 'update'], ['app_kv', 'delete'],
  // Журнал согласий: create и read — и ничего больше. Права на update и
  // delete здесь не появляются даже «временно, чтобы поправить опечатку»:
  // возможность переписать событие обесценивает весь журнал как
  // доказательство (ТЗ 16.09.2026, п. 3). Исправление — новая запись с
  // corrects_event. Проверку держит tests/consent-schema.test.ts.
  ['consent_audit_log', 'create'], ['consent_audit_log', 'read'],
  // Реестр рассылок, наоборот, хранит текущее состояние: статус меняется
  // при подписке и отписке. Delete нет — адрес остаётся в suppression.
  ['marketing_registry', 'create'], ['marketing_registry', 'read'], ['marketing_registry', 'update'],
  ['admin_audit_log', 'create'], ['admin_audit_log', 'read'],
  ['directus_files', 'read'],
];

/**
 * Роль, политика и права сервисного доступа сайта.
 *
 * Отделено от выдачи токена намеренно. Права — единственное, что нужно
 * приложению для работы с новой коллекцией, и они ничего не ломают:
 * существующие не трогаются, недостающие досыпаются. Сброс токена и
 * демо-каталог, наоборот, ломают прод, если после них не синхронизировать
 * окружение, — поэтому они остались в ensureServiceAccess и в режим
 * «только схема» не попадают.
 *
 * Без этого шага новая коллекция появлялась, а сайт получал на неё 403:
 * политика сервисной роли создана с app_access и admin_access = false,
 * то есть без явного разрешения доступа нет. Ровно так и вышло бы с
 * app_kv — пороги форм молча остались бы невключёнными.
 */
async function ensureServicePermissions() {
  // роль
  let role = (await api('GET', '/roles?filter[name][_eq]=Site Service&limit=1')) || [];
  let roleId = role[0]?.id;
  if (!roleId) {
    const created = await api('POST', '/roles', { name: 'Site Service', icon: 'dns', description: 'Сервисный доступ Astro-сайта BizSoft' });
    roleId = created.id;
    console.log('✓ role Site Service created');
  }
  // политика
  let pol = await api('GET', '/policies?filter[name][_eq]=Site Service Policy&limit=1');
  let policyId = pol[0]?.id;
  if (!policyId) {
    const created = await api('POST', '/policies', { name: 'Site Service Policy', icon: 'dns', description: 'Права сервисного доступа сайта', app_access: false, admin_access: false });
    policyId = created.id;
    console.log('✓ policy created');
  }
  // привязка роль↔политика
  const access = await api('GET', `/access?filter[role][_eq]=${roleId}&filter[policy][_eq]=${policyId}&limit=1`);
  if (!access.length) {
    await api('POST', '/access', { role: roleId, policy: policyId });
    console.log('✓ access role↔policy linked');
  }
  // права
  const perms = await api('GET', `/permissions?filter[policy][_eq]=${policyId}&limit=-1`);
  const have = new Set(perms.map((p) => `${p.collection}:${p.action}`));
  for (const [collection, action] of APP_PERMS) {
    if (have.has(`${collection}:${action}`)) continue;
    // Без custom-правил (filter-based permissions ограничены в этой редакции).
    // Фильтрацию status=published выполняет само приложение в каждом запросе.
    try {
      await api('POST', '/permissions', { policy: policyId, collection, action, fields: ['*'], permissions: {}, validation: {} });
    } catch (e) {
      console.log(`  ! perm ${collection}:${action} skipped — ${e.message}`);
    }
  }
  console.log('✓ service permissions ensured');
  return { roleId, policyId };
}

/**
 * Полный сервисный доступ: права плюс статический токен служебной учётки.
 * Токен пересоздаётся при каждом вызове, поэтому следом обязателен
 * ops-directus-token-sync — иначе сайт остаётся со старым токеном.
 */
async function ensureServiceAccess() {
  const { roleId } = await ensureServicePermissions();

  // сервисный пользователь со статическим токеном
  let users = await api('GET', '/users?filter[email][_eq]=service@biz-soft.pro&limit=1');
  let userId = users[0]?.id;
  if (!userId) {
    const u = await api('POST', '/users', {
      first_name: 'Site', last_name: 'Service', email: 'service@biz-soft.pro',
      password: randomBytes(18).toString('hex'), role: roleId, token: SERVICE_TOKEN, status: 'active',
    });
    userId = u.id;
    console.log('✓ service user created');
  } else {
    await api('PATCH', `/users/${userId}`, { token: SERVICE_TOKEN, role: roleId, status: 'active' });
    console.log('= service user updated (token reset)');
  }
  if (TOKEN_OUT) { writeFileSync(TOKEN_OUT, SERVICE_TOKEN); console.log('✓ token written to', TOKEN_OUT); }
}

async function ensurePublicRead() {
  try {
    // публичная политика в v11 привязана к access с role=null
    const acc = await api('GET', '/access?filter[role][_null]=true&limit=1');
    const publicPolicyId = acc[0]?.policy;
    if (!publicPolicyId) { console.log('! public policy не найдена — пропускаю публичные права'); return; }
    const perms = await api('GET', `/permissions?filter[policy][_eq]=${publicPolicyId}&limit=-1`);
    const have = new Set(perms.map((p) => `${p.collection}:${p.action}`));
    // Только публичные ассеты (изображения товаров) — чтобы <img> грузились без токена,
    // если админ-домен когда-нибудь будет открыт. Контент сайт читает сервисным токеном.
    if (!have.has('directus_files:read')) {
      await api('POST', '/permissions', { policy: publicPolicyId, collection: 'directus_files', action: 'read', fields: ['*'], permissions: {}, validation: {} });
    }
    console.log('✓ public read permissions ensured');
  } catch (e) {
    console.log('! public read setup skipped:', e.message);
  }
}

// ── демо-данные ──
const CATEGORIES = [
  { name: 'AI-сервисы', slug: 'ai-services', sort: 1, meta_title: 'AI-сервисы для бизнеса по договору', meta_description: 'Подписки на AI-сервисы для генерации текста, кода и графики для юрлиц РФ: договор, счёт, ЭДО.', seo_text: 'Подключаем юридическим лицам доступ к ведущим AI-сервисам для генерации контента, кода и изображений. Работаем по договору с оплатой по счёту и закрывающими документами.' },
  { name: 'Графика и дизайн', slug: 'graphics-design', sort: 2, meta_title: 'Графические редакторы для компаний', meta_description: 'Лицензии на графические и дизайн-редакторы для российских юрлиц: договор, счёт, закрывающие документы.', seo_text: 'Профессиональные графические и дизайн-инструменты для команд: от растровой и векторной графики до совместной работы над макетами. Поставка по договору.' },
  { name: 'Видеосвязь и коммуникации', slug: 'communications', sort: 3, meta_title: 'Сервисы видеоконференцсвязи для бизнеса', meta_description: 'Подписки на видеоконференцсвязь и корпоративные коммуникации для юрлиц РФ по договору и счёту.', seo_text: 'Сервисы видеоконференцсвязи, вебинаров и корпоративных коммуникаций для распределённых команд. Прозрачная поставка по договору.' },
  { name: 'Разработка и инструменты', slug: 'developer-tools', sort: 4, meta_title: 'Инструменты для разработчиков по договору', meta_description: 'Подписки на инструменты разработки, репозитории и AI-ассистенты для юрлиц РФ: счёт, договор, ЭДО.', seo_text: 'Инструменты для команд разработки: среды, репозитории, AI-ассистенты для кода. Оформление по договору с закрывающими документами.' },
];

function demoProducts(catIds) {
  const today = '2026-06-27';
  return [
    { name: 'AI-ассистент для текста — Команда', sku: 'AI-TXT-TEAM', slug: 'ai-text-team', category: catIds['ai-services'], price: 4900, short_description: 'Доступ к продвинутой языковой модели для генерации и редактуры текста.', description: 'Корпоративный доступ к AI-ассистенту для написания и редактуры текстов, перевода и анализа документов. Командные рабочие пространства, контроль доступа, единый счёт.', features: ['Командные рабочие пространства', 'Единый счёт и договор', 'Закрывающие документы через ЭДО'], faq: [{ q: 'Как оформляется доступ?', a: 'По договору с оплатой по счёту. После оплаты выдаём доступы и закрывающие документы через ЭДО.' }], sort: 1, promo_price: 3900, promo_label: 'Старт сезона', promo_start: '2026-06-01', promo_end: '2026-07-31' },
    { name: 'AI-генерация изображений — Бизнес', sku: 'AI-IMG-BIZ', slug: 'ai-image-business', category: catIds['ai-services'], price: 6500, short_description: 'Генерация изображений и иллюстраций по текстовому описанию для маркетинга.', description: 'Сервис генерации изображений для маркетинга и дизайна: иллюстрации, концепты, баннеры. Коммерческая лицензия, командный доступ.', features: ['Коммерческая лицензия', 'Командный доступ', 'Высокое разрешение'], faq: [{ q: 'Можно ли использовать результаты коммерчески?', a: 'Да, тариф включает коммерческую лицензию на сгенерированные изображения.' }], sort: 2 },
    { name: 'Графический редактор Pro — годовая', sku: 'GFX-PRO-1Y', slug: 'graphics-pro-yearly', category: catIds['graphics-design'], price: 28900, short_description: 'Профессиональный редактор растровой и векторной графики, годовая подписка.', description: 'Полный набор инструментов для дизайна: растровая и векторная графика, макеты, библиотеки. Годовая подписка на пользователя.', features: ['Растровая и векторная графика', 'Облачные библиотеки', 'Совместная работа'], faq: [{ q: 'Подписка на пользователя или на компанию?', a: 'Цена указана за одного пользователя в год. Для команды рассчитаем объёмную скидку.' }], sort: 1, base_price_usd: 320, peg_to_usd: true, markup_percent: 15 },
    { name: 'Сервис совместного дизайна — Команда', sku: 'GFX-COLLAB', slug: 'design-collab-team', category: catIds['graphics-design'], price: 9900, short_description: 'Облачный сервис совместного проектирования интерфейсов и макетов.', description: 'Командная платформа для проектирования интерфейсов, прототипов и дизайн-систем в реальном времени.', features: ['Реальное время', 'Дизайн-системы', 'Комментарии и ревью'], faq: [{ q: 'Сколько участников можно подключить?', a: 'Базовый тариф — до 5 редакторов. Расширение — по запросу.' }], sort: 2, promo_price: 7900, promo_label: '−20%', promo_start: '2026-06-15', promo_end: '2026-08-15' },
    { name: 'Видеоконференцсвязь — Бизнес', sku: 'VCS-BIZ', slug: 'video-conferencing-business', category: catIds['communications'], price: 5400, short_description: 'Видеоконференции, вебинары и запись встреч для распределённых команд.', description: 'Корпоративная видеоконференцсвязь: встречи, вебинары, запись, демонстрация экрана, интеграции с календарём.', features: ['До 300 участников', 'Запись встреч', 'Вебинары'], faq: [{ q: 'Есть ли запись встреч?', a: 'Да, запись в облако и локально доступна на бизнес-тарифе.' }], sort: 1 },
    { name: 'Корпоративный мессенджер — Команда', sku: 'COMM-CHAT', slug: 'corporate-chat-team', category: catIds['communications'], price: 3200, short_description: 'Защищённый командный мессенджер с каналами и интеграциями.', description: 'Командные коммуникации: каналы, треды, файлы, интеграции с рабочими инструментами. Единый счёт для компании.', features: ['Каналы и треды', 'Интеграции', 'Хранение файлов'], faq: [{ q: 'Как считается цена?', a: 'За активного пользователя в месяц. Договор и счёт на компанию.' }], sort: 2 },
    { name: 'AI-ассистент для кода — Команда', sku: 'DEV-AI-TEAM', slug: 'ai-code-assistant-team', category: catIds['developer-tools'], price: 7800, short_description: 'AI-ассистент для написания и ревью кода в IDE команды.', description: 'Помощник разработчика: автодополнение, генерация и ревью кода, объяснение и рефакторинг. Командные политики и единый счёт.', features: ['Автодополнение и генерация', 'Ревью и рефакторинг', 'Командные политики'], faq: [{ q: 'В каких средах работает?', a: 'Поддерживаются популярные IDE и редакторы. Список уточним под ваш стек.' }], sort: 1, base_price_usd: 95, peg_to_usd: true, markup_percent: 12 },
  ].map((p) => ({ currency: 'RUB', status: 'published', seo_text: `${p.name}: поставка для юрлиц РФ по договору с оплатой по счёту и закрывающими документами через ЭДО. Своевременная поставка и ответственность за качество.`, meta_title: `${p.name} — купить по договору`, meta_description: p.short_description, ...p, updated: today }));
}

async function seed() {
  const existing = await api('GET', '/items/categories?limit=-1');
  const bySlug = {};
  existing.forEach((c) => (bySlug[c.slug] = c.id));
  for (const c of CATEGORIES) {
    if (bySlug[c.slug]) { console.log(`= category ${c.slug} exists`); continue; }
    const created = await api('POST', '/items/categories', { ...c, status: 'published' });
    bySlug[c.slug] = created.id;
    console.log(`✓ category ${c.slug}`);
  }

  const existingProducts = await api('GET', '/items/products?limit=-1&fields=sku');
  const haveSku = new Set(existingProducts.map((p) => p.sku));
  for (const p of demoProducts(bySlug)) {
    if (haveSku.has(p.sku)) { console.log(`= product ${p.sku} exists`); continue; }
    const { updated, ...payload } = p; // updated не поле БД
    await api('POST', '/items/products', payload);
    console.log(`✓ product ${p.sku}`);
  }

  // запись курса (singleton)
  const rate = await api('GET', '/items/currency_rate?limit=1');
  if (!rate.length) {
    await api('POST', '/items/currency_rate', { mode: 'manual', usd_rate: 90, rate_date: '2026-06-27', source: 'manual-seed', auto_recalc: false });
    console.log('✓ currency_rate seed');
  } else {
    console.log('= currency_rate exists');
  }
  console.log('✓ seed done');
}

/**
 * Режим «только схема»: коллекции, поля и права на них — и ничего больше.
 *
 * Полный прогон делает две вещи сверх этого — пересоздаёт токен служебной
 * учётки и досыпает демо-каталог. 20.08.2026 на проде это уже стоило простоя:
 * сайт остался со старым токеном, каталог опустел, карточки начали отдавать
 * 404. Для добавления новых полей ни то, ни другое не нужно, а риск
 * несоразмерен: --schema-only исключает оба шага и потому не требует
 * последующего ops-directus-token-sync.
 *
 * Права при этом выдаются всегда. Коллекция без прав для приложения всё
 * равно что её нет — оно получает 403, — а выдача прав, в отличие от сброса
 * токена, ничего не ломает и повторного запуска не требует.
 */
const SCHEMA_ONLY = process.argv.includes('--schema-only');

async function main() {
  if (!ADMIN_EMAIL || !ADMIN_PASSWORD) throw new Error('Нет ADMIN_EMAIL/ADMIN_PASSWORD');
  console.log('Directus:', DIRECTUS_URL);
  if (SCHEMA_ONLY) console.log('Режим: только схема — токен не трогаем, демо-данные не досыпаем');
  await login();
  await buildSchema();
  if (SCHEMA_ONLY) {
    await ensureServicePermissions();
    console.log('\n✅ СХЕМА И ПРАВА ПРИМЕНЕНЫ (без пересоздания токена и без демо-данных)');
    return;
  }
  await ensureServiceAccess();
  await ensurePublicRead();
  await seed();
  console.log('\n✅ DIRECTUS SETUP COMPLETE');
}

main().catch((e) => { console.error('\n❌ ERROR:', e.message); if (e.body) console.error(JSON.stringify(e.body).slice(0, 400)); process.exit(1); });
