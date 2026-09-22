// Строит xlsx для пакетной заливки товаров BizSoft из нормализованного JSON вендоров.
// Использование: node scripts/build-vendor-cards.mjs <input.json> <output.xlsx>
//                node scripts/build-vendor-cards.mjs <input.json> <output.xlsx> --only SKU1,SKU2
//
// --only отбирает из реестра перечисленные SKU: партия из одной-двух карточек
// заливается, не трогая остальные позиции реестра (импорт — upsert по sku,
// и без отбора в него уехали бы все 20+ строк файла).
//
// Формат input.json:
// {
//   "block": "design",                 // код категории по умолчанию для вендоров без своей
//   "sortBase": 1000,                  // стартовый sort
//   "vendors": [
//     {
//       "vendor": "Canva",
//       "prefix": "CANVA",             // префикс SKU
//       "category": "design",          // код категории (перекрывает block)
//       "products": [
//         {
//           "key": "TEAMS",            // суффикс SKU
//           "sku": "OPAI-LIC-CHATGPTBUS-TEAM-1Y-USER-STD",   // необяз.: готовый SKU вместо prefix-key —
//                                      // для карточки, которая уже живёт в
//                                      // Directus под «интеграционным» sku;
//                                      // upsert идёт по нему, слаг не меняется
//           "slug": "perplexity-pro",  // необяз.: адрес новой карточки; без него
//                                      // новая позиция получает слаг из артикула
//           "markup_coeff": 1.85,      // необяз.: свой коэффициент вместо общего
//           "sort": 1310,              // необяз.: свой sort вместо сквозного
//           "name": "Canva Teams",
//           "license_type": "org",     // org|individual
//           "base_price": 100,          // число в валюте currency
//           "currency": "EUR",          // EUR|USD
//           "vat_included": true,
//           "billing_note_ru": "за пользователя в год",
//           "price_on_request": false,
//           "short_desc_ru": "…",
//           "description_ru": "…",      // необяз.: готовое описание вместо
//                                      // генерируемой рамки

//           "features_ru": ["…"],
//           "category": "design"        // необяз., перекрывает вендорскую
//         }
//       ]
//     }
//   ]
// }
import * as XLSX from 'xlsx';
import { readFileSync, writeFileSync } from 'node:fs';

const HEADERS = [
  'sku', 'sku_kind', 'sku_product', 'sku_plan', 'sku_term', 'sku_unit', 'sku_variant',
  // slug — адрес карточки. Без него новая позиция получает адрес из артикула
  // (pplx-lic-pro-ind-1y-user), и расходится всё, что адресует карточку слагом:
  // семейства content_modules, очередь выкладки, переобход (правило
  // docs/rules/catalog.md, разбор 14.09.2026). У существующей позиции импорт
  // строку со слагом игнорирует — смена адреса идёт через ops-rename-product.
  'slug',
  'name', 'vendor', 'origin', 'category', 'license_type',
  'short_description', 'description', 'keywords',
  'base_price_usd', 'base_price_eur', 'peg_currency', 'markup_coeff', 'price_locked',
  'price', 'price_note', 'vat_percent', 'currency',
  'promo_price', 'promo_label', 'promo_start', 'promo_end',
  'features', 'status', 'sort',
];

const MARKUP = 1.9;
const VAT_PERCENT = 5;
const VAT_GROSSUP = 1.20; // если цена вендора без НДС — приводим EUR к «с НДС» (ориентир EU ~20%)

const CATEGORY_AUDIENCE = {
  design: 'дизайн-студий, брендинговых и рекламных агентств, продуктовых команд',
  media: 'видеопродакшн-студий, моушн-дизайнеров и монтажёров',
  development: 'игровых студий и команд разработки',
  ai: 'креативных команд, использующих генеративный ИИ',
  collaboration: 'распределённых команд и агентств',
  pm: 'команд, управляющих проектами и задачами',
  // AI-подкатегории (см. docs/ai-catalog-redesign.md)
  'ai-text': 'команд, которым нужен корпоративный AI-ассистент для текста и знаний',
  'ai-code': 'команд разработки и IT-компаний',
  'ai-image': 'дизайнеров, арт-директоров и креативных команд',
  'ai-video': 'видеопродакшн-команд, маркетологов и контент-студий',
  'ai-audio': 'команд, работающих с озвучкой, подкастами и аудиоконтентом',
  'ai-office': 'компаний, внедряющих AI в офисную продуктивность',
  'ai-marketing': 'маркетинговых команд и агентств',
  'ai-enterprise': 'крупных организаций с требованиями к безопасности и комплаенсу',
};

// Ключевой запрос по коду категории для buildKeywords.
const CATEGORY_KEYWORD = {
  design: 'графический дизайн',
  media: 'видеопродакшн',
  development: 'разработка игр',
  ai: 'нейросеть',
  'ai-text': 'корпоративный AI-ассистент',
  'ai-code': 'AI для разработки кода',
  'ai-image': 'нейросеть для изображений',
  'ai-video': 'нейросеть для видео',
  'ai-audio': 'AI для озвучки',
  'ai-office': 'AI для офиса',
  'ai-marketing': 'AI для маркетинга',
  'ai-enterprise': 'корпоративный AI',
};

const licLabel = (l) => (l === 'individual' ? 'Индивидуальное использование' : l === 'student' ? 'Студенческая версия' : 'Для организаций');

function slug(s) {
  return String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

function buildDescription(vendorName, p, category) {
  const aud = CATEGORY_AUDIENCE[category] || 'бизнеса';
  // Описание — связный текст абзацами, а не склейка полей карточки.
  // Чего здесь сознательно нет:
  //  - повтора «Название — краткое описание»: лид уже стоит выше на странице;
  //  - списка возможностей строкой через «;» — он отдельным блоком «Что входит»
  //    из поля features, и в тексте это дубль;
  //  - цены и курса: рублёвая цена считается по курсу ЦБ и меняется ежедневно,
  //    а цифра в тексте — нет (карточки Claude Team жили с припиской
  //    «($80/мес при годовой оплате)», разошедшейся с прайсом вендора);
  //  - призыва «поможем подобрать, оставьте заявку»: для этого на странице есть
  //    кнопки, а описание должно отвечать на вопрос покупателя.
  // Дальше карточка дорабатывается вручную через data/seo/product-descriptions.json:
  // генератор даёт корректную рамку, содержательные абзацы пишет человек.
  const purchase = p.price_on_request
    ? `Стоимость ${p.name} зависит от числа мест и состава — рассчитываем по запросу и фиксируем в коммерческом предложении.`
    : `Рублёвая сумма считается от прайса вендора по курсу ЦБ РФ на дату счёта и фиксируется в счёте.`;
  return [
    `${p.short_desc_ru}`,
    `Тариф рассчитан на ${aud}: подписка оформляется на компанию, а не на личный аккаунт сотрудника, `
      + `поэтому доступы остаются у организации при смене команды.`,
    `${vendorName} мы поставляем российским юридическим лицам и ИП по договору с оплатой по счёту; `
      + `закрывающие документы передаём через ЭДО. ${purchase}`,
  ].filter(Boolean).join('\n\n');
}

function buildKeywords(vendorName, p, category) {
  const eng = p.name;
  const parts = [
    `${vendorName} купить`,
    `${vendorName} для юрлица`,
    `${vendorName} оплата по счёту`,
    `${eng} цена`,
    `${eng}`,
    `${vendorName} для России`,
    CATEGORY_KEYWORD[category] || 'ПО для бизнеса',
  ];
  return parts.join(', ');
}

const argv = process.argv.slice(2);
const onlyIdx = argv.indexOf('--only');
const only = onlyIdx >= 0
  ? new Set(String(argv[onlyIdx + 1] || '').split(',').map((s) => s.trim().toUpperCase()).filter(Boolean))
  : null;
const positional = argv.filter((a, i) => (onlyIdx < 0 ? true : a !== '--only' && i !== onlyIdx + 1));
const input = JSON.parse(readFileSync(positional[0], 'utf8'));
const out = positional[1];
let sort = input.sortBase ?? 1000;
const rows = [];

for (const v of input.vendors) {
  const vendorCat = v.category || input.block || 'design';
  for (const p of v.products) {
    const category = p.category || vendorCat;
    // Позиция без sku, но с сегментами sku_* — артикул соберёт импорт
    // (docs/rules/sku-system.md); prefix-key — прежний способ для карточек,
    // заведённых до единой системы.
    const auto = !p.sku && p.sku_product;
    const sku = auto ? '' : (p.sku || `${v.prefix}-${p.key}`).toUpperCase().replace(/[^A-Z0-9-]/g, '');
    // Сквозной sort двигается на каждой позиции реестра, а не только на
    // отобранных: иначе --only переставлял бы карточки в разделе каталога.
    const rowSort = p.sort ?? (sort += 10);
    if (only && !only.has(sku || p.key)) continue;
    const por = !!p.price_on_request;
    let base_usd = '', base_eur = '', peg = '';
    if (!por) {
      if (p.currency === 'USD') { base_usd = round2(p.base_price); peg = 'USD'; }
      else { base_eur = round2(p.vat_included ? p.base_price : p.base_price * VAT_GROSSUP); peg = 'EUR'; }
    }
    rows.push({
      sku,
      sku_kind: p.sku_kind || '', sku_product: p.sku_product || '', sku_plan: p.sku_plan || '',
      sku_term: p.sku_term || '', sku_unit: p.sku_unit || '', sku_variant: p.sku_variant || '',
      slug: p.slug || '',
      name: p.name,
      vendor: v.vendor,
      origin: 'Иностранное',
      category,
      license_type: p.license_type || 'org',
      short_description: p.short_desc_ru,
      // description_ru — готовый текст карточки из реестра. Нужен там, где
      // рамка генератора неверна по сути: пополнение баланса API — не подписка
      // за место, и фраза «подписка оформляется на компанию» в нём была бы
      // ложью. Реестры без этого поля работают как раньше.
      description: p.description_ru || buildDescription(v.vendor, p, category),
      keywords: buildKeywords(v.vendor, p, category),
      base_price_usd: base_usd,
      base_price_eur: base_eur,
      peg_currency: peg,
      markup_coeff: por ? '' : (p.markup_coeff ?? MARKUP),
      price_locked: 0,
      price: '',
      price_note: por ? 'Цена по запросу' : (p.billing_note_ru || 'по курсу ЦБ'),
      vat_percent: VAT_PERCENT,
      currency: 'RUB',
      promo_price: '', promo_label: '', promo_start: '', promo_end: '',
      features: (p.features_ru || []).join(' | '),
      status: p.status || 'published',
      sort: rowSort,
    });
  }
}

function round2(n) { return Math.round(Number(n) * 100) / 100; }

if (only) {
  const missing = [...only].filter((s) => !rows.some((r) => r.sku === s));
  if (missing.length) {
    console.error(`нет в реестре: ${missing.join(', ')}`);
    process.exit(1);
  }
}
if (rows.length === 0) { console.error('нечего собирать: строк 0'); process.exit(1); }

const aoa = [HEADERS, ...rows.map((r) => HEADERS.map((h) => r[h] ?? ''))];
const ws = XLSX.utils.aoa_to_sheet(aoa);
ws['!cols'] = HEADERS.map((h) => ({ wch: ['description', 'short_description', 'keywords', 'features'].includes(h) ? 46 : h === 'name' ? 32 : 15 }));
const wb = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(wb, ws, 'Товары');
XLSX.writeFile(wb, out);
console.log(`✓ ${rows.length} товаров → ${out}`);
for (const r of rows) console.log(`  ${r.sku}  ${r.name}  [${r.category}/${r.license_type}]  ${r.base_price_eur || r.base_price_usd || r.price_note}${r.peg_currency ? ' ' + r.peg_currency : ''}`);
