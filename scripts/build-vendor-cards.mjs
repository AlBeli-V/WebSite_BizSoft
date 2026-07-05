// Строит xlsx для пакетной заливки товаров BizSoft из нормализованного JSON вендоров.
// Использование: node scripts/build-vendor-cards.mjs <input.json> <output.xlsx>
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
//           "name": "Canva Teams",
//           "license_type": "org",     // org|individual
//           "base_price": 100,          // число в валюте currency
//           "currency": "EUR",          // EUR|USD
//           "vat_included": true,
//           "billing_note_ru": "за пользователя в год",
//           "price_on_request": false,
//           "short_desc_ru": "…",
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
  'sku', 'name', 'vendor', 'origin', 'category', 'license_type',
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
  const feat = (p.features_ru || []).slice(0, 6);
  const featSentence = feat.length ? `Ключевые возможности: ${feat.join('; ')}.` : '';
  const priceClause = p.price_on_request
    ? `Стоимость ${p.name} рассчитывается индивидуально — оставьте заявку, и мы подготовим коммерческое предложение.`
    : `Оплата в рублях по курсу ЦБ РФ на дату счёта, ${p.billing_note_ru || 'по подписке'}.`;
  return [
    `${p.name} — ${p.short_desc_ru}`.replace(/\.\.$/, '.'),
    featSentence,
    `Решение подходит для ${aud}.`,
    `BizSoft поставляет ${vendorName} российским юридическим лицам и ИП по договору с оплатой по счёту; предоставляем закрывающие документы через ЭДО. ${priceClause}`,
    `Поможем подобрать тариф и количество лицензий, оформим на ООО или ИП.`,
  ].filter(Boolean).join(' ');
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

const input = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const out = process.argv[3];
let sort = input.sortBase ?? 1000;
const rows = [];

for (const v of input.vendors) {
  const vendorCat = v.category || input.block || 'design';
  for (const p of v.products) {
    const category = p.category || vendorCat;
    const sku = `${v.prefix}-${p.key}`.toUpperCase().replace(/[^A-Z0-9-]/g, '');
    const por = !!p.price_on_request;
    let base_usd = '', base_eur = '', peg = '';
    if (!por) {
      if (p.currency === 'USD') { base_usd = round2(p.base_price); peg = 'USD'; }
      else { base_eur = round2(p.vat_included ? p.base_price : p.base_price * VAT_GROSSUP); peg = 'EUR'; }
    }
    rows.push({
      sku,
      name: p.name,
      vendor: v.vendor,
      origin: 'Иностранное',
      category,
      license_type: p.license_type || 'org',
      short_description: p.short_desc_ru,
      description: buildDescription(v.vendor, p, category),
      keywords: buildKeywords(v.vendor, p, category),
      base_price_usd: base_usd,
      base_price_eur: base_eur,
      peg_currency: peg,
      markup_coeff: por ? '' : MARKUP,
      price_locked: 0,
      price: '',
      price_note: por ? 'Цена по запросу' : (p.billing_note_ru || 'по курсу ЦБ'),
      vat_percent: VAT_PERCENT,
      currency: 'RUB',
      promo_price: '', promo_label: '', promo_start: '', promo_end: '',
      features: (p.features_ru || []).join(' | '),
      status: 'published',
      sort: sort += 10,
    });
  }
}

function round2(n) { return Math.round(Number(n) * 100) / 100; }

const aoa = [HEADERS, ...rows.map((r) => HEADERS.map((h) => r[h] ?? ''))];
const ws = XLSX.utils.aoa_to_sheet(aoa);
ws['!cols'] = HEADERS.map((h) => ({ wch: ['description', 'short_description', 'keywords', 'features'].includes(h) ? 46 : h === 'name' ? 32 : 15 }));
const wb = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(wb, ws, 'Товары');
XLSX.writeFile(wb, out);
console.log(`✓ ${rows.length} товаров → ${out}`);
for (const r of rows) console.log(`  ${r.sku}  ${r.name}  [${r.category}/${r.license_type}]  ${r.base_price_eur || r.base_price_usd || r.price_note}${r.peg_currency ? ' ' + r.peg_currency : ''}`);
