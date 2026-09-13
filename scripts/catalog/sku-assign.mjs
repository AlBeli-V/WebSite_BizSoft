// Расстановка артикулов новой системы по опубликованному каталогу
// (правило docs/rules/sku-system.md).
//
// Вход:  data/catalog/sku-legacy-export.json  — срез каталога (ops-export-products)
//        data/catalog/sku-legacy-rules.json   — правила перевода старых артикулов
//        data/catalog/sku-vendors.json        — коды вендоров
// Выход: data/catalog/sku-assignment.json     — старый артикул → новый, с сегментами
//        data/catalog/sku-map.json            — компактная карта старый → новый
//        data/catalog/sku-assignment.csv      — то же для просмотра в Excel
//        data/catalog/sku-products.json       — реестр кодов продуктов (обновляется)
//
// Запуск: node scripts/catalog/sku-assign.mjs [--check]
//   --check — ничего не писать, только сверить, что файлы на диске совпадают
//             с результатом (гейт для теста tests/sku.test.ts).
//
// Детерминированно: один и тот же вход даёт один и тот же выход. Код продукта,
// однажды записанный в sku-products.json, не меняется — реестр читается до
// генерации, новые коды только добавляются.
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { readdirSync } from 'node:fs';
import { buildSku, findDuplicateSkus, parseSku, proposeProductCode, validateSkuParts } from '../../src/lib/sku.ts';
import { buildPositions, skuCodes } from '../lib/zoho-model.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const P = (rel) => resolve(ROOT, rel);
const readJson = (rel) => JSON.parse(readFileSync(P(rel), 'utf8'));

const check = process.argv.includes('--check');

const exportData = readJson('data/catalog/sku-legacy-export.json');
// Позиции, заведённые после среза под старыми артикулами (PR после 12.09.2026).
try { exportData.products.push(...readJson('data/catalog/sku-legacy-extra.json').products); } catch { /* файла нет */ }
const rules = readJson('data/catalog/sku-legacy-rules.json');
const vendorCodes = readJson('data/catalog/sku-vendors.json').vendors;
let registry;
try { registry = readJson('data/catalog/sku-products.json'); } catch { registry = { _note: '', products: {}, plugins: {}, zoho: {} }; }
registry.products ||= {};
registry.plugins ||= {};
registry.zoho ||= {};

// ── Раздел ManageEngine: все позиции модели (карточки, скрытые, сопровождение) ──
// Артикулы считает сама модель (scripts/lib/zoho-model.mjs → sku-legacy-zoho.mjs)
// из последнего снимка магазина вендора; здесь — соответствие старый → новый.
const ME_SRC = P('data/sources/manageengine');
const meDay = readdirSync(ME_SRC).filter((d) => /^\d{4}-\d{2}-\d{2}$/.test(d)).sort().pop();
const mePositions = buildPositions(readJson(`data/sources/manageengine/${meDay}/manifest.json`));
const zohoByLegacy = new Map(mePositions.map((pos) => [pos.legacySku, pos]));

// ── Эвристики для короткой записи правил (только код продукта) ─────────────
const TEAM_RE = /\b(teams?|business|enterprise|corporate|company|organizations?|workspace|studio|msp)\b|для команд|для организаций|организаци|команд|корпоратив/i;
const IND_RE = /\b(individuals?|personal|solo|indie|creator)\b|личная|индивидуальн|персональн/i;
const PERP_RE = /бессрочн|вечная лицензия|perpetual|-PERP\b/i;

function planByName(name) {
  if (TEAM_RE.test(name)) return 'TEAM';
  if (IND_RE.test(name)) return 'IND';
  return 'UNI';
}
function termByName(name, sku) {
  if (PERP_RE.test(name) || PERP_RE.test(sku)) return 'PERP';
  const months = name.match(/(?:^|[\s,(])(\d+)\s*(?:месяц(?:а|ев)?|мес\.)(?=[\s,)]|$)/i);
  if (months) return `${months[1]}M`;
  const skuMonths = sku.match(/-(\d+)M\b/);
  if (skuMonths) return `${skuMonths[1]}M`;
  const years = name.match(/\b(\d)Y\b/) || sku.match(/-(\d)Y\b/);
  if (years) return `${years[1]}Y`;
  if (/квартальн/i.test(name)) return '3M';
  if (/полугодов/i.test(name)) return '6M';
  return '1Y';
}

// ── Реестр кодов продуктов: вендор → код → название линейки; плагины: slug → код ──
function noteProduct(vendorCode, code, label) {
  const bucket = (registry.products[vendorCode] ||= {});
  if (!bucket[code]) bucket[code] = label;
}
function registerPlugin(slug, wanted, label) {
  registry.plugins ||= {};
  if (registry.plugins[slug]) return registry.plugins[slug];
  const taken = new Set(Object.keys(registry.products.JB || {}));
  let code = wanted;
  // Столкновение внутри вендора: цифра к позднее заведённому коду.
  for (let n = 2; taken.has(code); n++) code = `${wanted.slice(0, 12 - String(n).length)}${n}`;
  registry.plugins[slug] = code;
  noteProduct('JB', code, label);
  return code;
}

function parseRule(text) {
  const t = text.trim().split(/\s+/);
  if (t.length === 1) return { kind: 'LIC', product: t[0] };
  const [kind, product, plan, term, unit, variant] = t;
  return { kind, product, plan, term, unit, variant: variant || null };
}

// ── Перевод одной позиции ──────────────────────────────────────────────────
function translate(row) {
  const { vendor, name, sku } = row;
  const vcode = vendorCodes[vendor];
  if (!vcode) throw new Error(`нет кода вендора «${vendor}» (data/catalog/sku-vendors.json) — ${sku}`);
  const review = [];
  let parts, source;

  const rule = rules.legacy[sku];
  const credits = sku.match(/^([A-Z0-9]+)-CREDITS-(\d+)$/);
  const gift = sku.match(/^(.+-GIFT-CARD)-([A-Z]{2,6})-(\d+)$/);
  const jb = sku.match(/^JB-PLG-(.+)-(ORG|IND)$/);
  const me = sku.match(/^(?:ME|MANAGEENGINE)-(.+?)(-PERP)?$/);

  if (rule) {
    const r = parseRule(rule);
    if (!r.plan) { r.plan = planByName(name); review.push('план по названию'); }
    if (!r.term) { r.term = termByName(name, sku); if (r.term === '1Y' && !/год|1Y|365/i.test(name)) review.push('срок по умолчанию 1Y'); }
    if (!r.unit) r.unit = r.kind === 'CRD' || r.kind === 'GFT' ? 'NOM' : 'USER';
    parts = { vendor: vcode, ...r };
    source = 'rules';
  } else if (credits && rules.credits[credits[1]]) {
    parts = { vendor: vcode, kind: 'CRD', product: rules.credits[credits[1]], plan: 'UNI', term: 'BAL', unit: 'NOM', variant: credits[2] };
    source = 'credits';
  } else if (gift && rules.legacy[gift[1]]) {
    const parent = parseRule(rules.legacy[gift[1]]);
    const region = rules.gift_regions[gift[2]];
    if (!region) throw new Error(`неизвестный регион «${gift[2]}» — ${sku}`);
    parts = { vendor: vcode, kind: 'GFT', product: parent.product, plan: 'UNI', term: 'BAL', unit: 'NOM', variant: `${region}${gift[3]}` };
    source = 'gift';
  } else if (jb) {
    const slug = jb[1];
    const product = registerPlugin(slug, proposeProductCode(slug), name.replace(/\s*\(личная\)\s*$/, ''));
    parts = { vendor: vcode, kind: rules.jetbrains.kind, product, plan: jb[2] === 'ORG' ? 'TEAM' : 'IND', term: rules.jetbrains.term, unit: rules.jetbrains.unit, variant: null };
    source = 'jetbrains';
  } else if (me) {
    const pos = zohoByLegacy.get(sku);
    if (!pos) throw new Error(`ManageEngine: позиции «${sku}» нет в модели (снимок ${meDay})`);
    parts = parseSku(pos.sku);
    if (!parts) throw new Error(`ManageEngine: модель дала не системный артикул «${pos.sku}» для ${sku}`);
    source = 'zoho';
  } else {
    throw new Error(`нет правила для артикула ${sku} (${vendor} — ${name})`);
  }

  if (source !== 'jetbrains') noteProduct(vcode, parts.product, name);
  const errs = validateSkuParts(parts);
  if (errs.length) throw new Error(`${sku}: ${errs.join('; ')}`);
  const { vendor: vendor_code, ...segments } = parts;
  return { old: sku, new: buildSku(parts), vendor, vendor_code, name, ...segments, source, review };
}

// ── Прогон ─────────────────────────────────────────────────────────────────
// Сначала позиции с явными правилами: их коды продуктов резервируются в
// реестре раньше, чем автокоды плагинов, — плагин не займёт код линейки.
const ordered = exportData.products
  .map((row, idx) => ({ row, idx }))
  .sort((a, b) => Number(!rules.legacy[a.row.sku]) - Number(!rules.legacy[b.row.sku]) || a.idx - b.idx);
const items = ordered.map(({ row, idx }) => ({ ...translate(row), idx })).sort((a, b) => a.idx - b.idx).map(({ idx, ...i }) => i);
// Позиции ManageEngine вне выгрузки: скрытые строки конфигуратора и контракты
// сопровождения. Они тоже живут в Directus (черновики) и переводятся той же картой.
const exported = new Set(items.map((i) => i.old));
for (const pos of mePositions) {
  if (exported.has(pos.legacySku)) continue;
  const parts = parseSku(pos.sku);
  if (!parts) throw new Error(`ManageEngine: не системный артикул «${pos.sku}» у скрытой позиции ${pos.legacySku}`);
  const { vendor: vendor_code, ...segments } = parts;
  const name = `ManageEngine ${pos.familyName}${pos.edition ? ` ${pos.edition}` : ''}, ${pos.variantName}${pos.isAms ? ' — сопровождение' : pos.licenseModel === 'perpetual' ? ', вечная лицензия' : ''}`;
  items.push({ old: pos.legacySku, new: pos.sku, vendor: 'Zoho', vendor_code, name, ...segments, source: 'zoho-hidden', review: [] });
}
// Автокоды продуктов ManageEngine закрепляются в реестре: выданный код не меняется.
for (const [head, code] of skuCodes) if (!registry.zoho[head]) registry.zoho[head] = code;

const dups = findDuplicateSkus(items.map((i) => i.new));
if (dups.length) {
  for (const d of dups) console.error(`ДУБЛЬ ${d}: ${items.filter((i) => i.new === d).map((i) => `${i.old} (${i.name})`).join(' | ')}`);
  process.exit(1);
}

const bySource = {};
for (const i of items) bySource[i.source] = (bySource[i.source] || 0) + 1;
const output = {
  _note: 'Расстановка артикулов новой системы по опубликованному каталогу: старый артикул → новый. Сгенерировано scripts/catalog/sku-assign.mjs из sku-legacy-export.json и sku-legacy-rules.json; руками не править — править правила и перегенерировать. Поле review — что взято по умолчанию и требует взгляда оператора.',
  exported_at: exportData.exported_at,
  total: items.length,
  by_source: bySource,
  items: items.map(({ review, ...rest }) => (review.length ? { ...rest, review } : rest)),
};
const csv = ['old_sku;new_sku;vendor;name;kind;product;plan;term;unit;variant']
  .concat(items.map((i) => [i.old, i.new, i.vendor, i.name.replace(/;/g, ','), i.kind, i.product, i.plan, i.term, i.unit, i.variant || ''].join(';')))
  .join('\n') + '\n';
registry._note = 'Реестр кодов продуктов для артикулов (docs/rules/sku-system.md). products: код вендора → код продукта (2–12 знаков A–Z/0–9, уникален у вендора) → название линейки, под которым код выдан. plugins: slug плагина JetBrains Marketplace → его код (закреплён, при перегенерации не меняется). zoho: голова старого артикула ManageEngine (семейство и предложение) → автокод продукта позиций конфигуратора. Ведёт scripts/catalog/sku-assign.mjs; код новой позиции оператор берёт отсюда или заводит новый — тем же словом, что у вендора.';
const sortedRegistry = { _note: registry._note, products: {}, plugins: {}, zoho: {} };
for (const v of Object.keys(registry.products).sort()) {
  sortedRegistry.products[v] = Object.fromEntries(Object.entries(registry.products[v]).sort(([a], [b]) => a.localeCompare(b)));
}
sortedRegistry.plugins = Object.fromEntries(Object.entries(registry.plugins).sort(([a], [b]) => a.localeCompare(b)));
sortedRegistry.zoho = Object.fromEntries(Object.entries(registry.zoho).sort(([a], [b]) => a.localeCompare(b)));

const skuMap = {
  _note: 'Карта старый артикул → новый для перехода каталога (docs/rules/sku-system.md): её читают скрипт переписывания ссылок и workflow ops-sku-migrate. Генерируется sku-assign.mjs из sku-assignment.json.',
  map: Object.fromEntries(items.map((i) => [i.old, i.new])),
};
const outputs = [
  ['data/catalog/sku-assignment.json', JSON.stringify(output, null, 1) + '\n'],
  ['data/catalog/sku-map.json', JSON.stringify(skuMap, null, 1) + '\n'],
  ['data/catalog/sku-assignment.csv', csv],
  ['data/catalog/sku-products.json', JSON.stringify(sortedRegistry, null, 1) + '\n'],
];
if (check) {
  let stale = 0;
  for (const [rel, text] of outputs) {
    let cur = '';
    try { cur = readFileSync(P(rel), 'utf8'); } catch { /* нет файла */ }
    if (cur !== text) { stale++; console.error(`устарел: ${rel}`); }
  }
  if (stale) process.exit(1);
  console.log(`сверено: ${items.length} позиций, файлы актуальны`);
} else {
  for (const [rel, text] of outputs) writeFileSync(P(rel), text);
  console.log(`расставлено: ${items.length} позиций`, bySource);
  const flagged = items.filter((i) => i.review.length);
  if (flagged.length) console.log(`на проверку (умолчания): ${flagged.length}`);
}
