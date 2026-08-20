// Импорт карточек товаров из вендорских JSON-пакетов (scripts/catalog/<slug>.json)
// через штатный /api/admin/import. Транспорт — xlsx-контейнер (создаётся
// программно; ручной Excel в цепочке не нужен): CSV-парсер импорта не
// поддерживает многострочные описания в кавычках, а xlsx переносы строк
// сохраняет. Токен читается из .env (SITE_URL, ADMIN_TOOLS_TOKEN). Usage:
//   node scripts/import-vendors.mjs                        — dry-run по всем пакетам
//   node scripts/import-vendors.mjs docker gitlab          — dry-run по выбранным slug
//   node scripts/import-vendors.mjs --apply [slugs...]     — применить
//   node scripts/import-vendors.mjs --emit <file.xlsx>     — только собрать файл
//     (без сети и .env; используется воркфлоу ops-import-vendors: файл собирается
//     на раннере, а POST к админ-API выполняется на сервере, где лежит токен)
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import * as XLSX from 'xlsx';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, basename } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const CATALOG_DIR = resolve(__dir, 'catalog');

function loadEnv() {
  const txt = readFileSync(new URL('../.env', import.meta.url), 'utf8');
  const env = {};
  for (const line of txt.split(/\r?\n/)) {
    const m = line.match(/^([A-Z_]+)=(.*)$/);
    if (m) env[m[1]] = m[2].replace(/^"|"$/g, '');
  }
  return env;
}

const args = process.argv.slice(2);
const apply = args.includes('--apply');
const emitIdx = args.indexOf('--emit');
const emitPath = emitIdx >= 0 ? args[emitIdx + 1] : null;
const slugs = args.filter((a, i) => a !== '--apply' && a !== '--emit' && i !== emitIdx + 1);

const files = readdirSync(CATALOG_DIR)
  .filter((f) => f.endsWith('.json'))
  .filter((f) => slugs.length === 0 || slugs.includes(basename(f, '.json')));
if (files.length === 0) { console.error('нет пакетов в scripts/catalog/'); process.exit(1); }

// Колонки листа «Товары» (схема штатного импорта, см. src/lib/bulk-import.ts).
const COLS = ['sku', 'name', 'vendor', 'origin', 'category', 'license_type',
  'short_description', 'description', 'keywords',
  'base_price_usd', 'peg_currency', 'markup_coeff', 'price_locked',
  'price', 'price_note', 'vat_percent', 'currency', 'features', 'status', 'sort'];

const rows = [];
for (const f of files) {
  const pkg = JSON.parse(readFileSync(resolve(CATALOG_DIR, f), 'utf8'));
  const vendor = pkg.vendor_entry?.vendor || '';
  for (const p of pkg.products || []) {
    // Архивный стаб: {sku, archive: true} — upsert только статуса (снятие с витрины).
    if (p.archive) {
      rows.push({ sku: p.sku, status: 'archived' });
      continue;
    }
    const hasBase = typeof p.base_price_usd === 'number' && p.base_price_usd > 0;
    rows.push({
      sku: p.sku,
      name: p.name,
      vendor,
      origin: 'Иностранное',
      category: p.category,
      license_type: p.license_type === 'individual' ? 'Индивидуальное использование' : 'Для организаций',
      short_description: p.short_description || '',
      description: p.description || '',
      keywords: p.keywords || '',
      // Себестоимость в USD + пустая price → импорт сам включит peg_to_usd и
      // посчитает ₽ по курсу ЦБ × коэффициент; ежедневная переоценка её обновляет.
      base_price_usd: hasBase ? p.base_price_usd : '',
      peg_currency: hasBase ? 'USD' : '',
      markup_coeff: p.markup_coeff ?? '',
      price_locked: 0,
      price: hasBase ? '' : 0, // без себестоимости — «Цена по запросу» (0)
      price_note: p.billing || '',
      vat_percent: p.vat_percent ?? 5,
      currency: 'RUB',
      features: Array.isArray(p.features) ? p.features.join(' | ') : '',
      status: p.status || (hasBase ? 'published' : 'published'),
      sort: p.sort ?? '',
    });
  }
}

const sheet = XLSX.utils.aoa_to_sheet([COLS, ...rows.map((r) => COLS.map((c) => r[c] ?? ''))]);
const wb = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(wb, sheet, 'Товары');
const xlsxBase64 = XLSX.write(wb, { type: 'base64', bookType: 'xlsx' });
console.log(`пакетов: ${files.length}, строк: ${rows.length}${emitPath ? ' — только файл' : apply ? ' — ПРИМЕНЯЕМ' : ' — dry-run'}`);

if (emitPath) {
  writeFileSync(emitPath, Buffer.from(xlsxBase64, 'base64'));
  console.log('записан:', emitPath);
  process.exit(0);
}

const env = loadEnv();
const res = await fetch(`${env.SITE_URL}/api/admin/import`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'x-admin-token': env.ADMIN_TOOLS_TOKEN },
  body: JSON.stringify({ format: 'xlsx', xlsxBase64, apply }),
});
const text = await res.text();
let data; try { data = JSON.parse(text); } catch { console.log('HTTP', res.status, text.slice(0, 500)); process.exit(1); }

if (data.dryRun) {
  console.log(`DRY-RUN: rows=${data.summary.rows} create=${data.summary.create} update=${data.summary.update} errors=${data.summary.errors}`);
  const errs = data.items.filter((i) => i.errors && i.errors.length);
  if (errs.length) { console.log('\nОШИБКИ:'); for (const i of errs) console.log(`  ${i.sku}: ${i.errors.join('; ')}`); }
  console.log('\nЦЕНЫ (create):');
  for (const i of data.items.filter((x) => x.mode === 'create')) {
    const price = i.payload.price ?? '(по запросу)';
    console.log(`  ${i.sku}  →  ${typeof price === 'number' ? (price || '(по запросу)') + (price ? ' ₽' : '') : price}  [${i.payload.status}]`);
  }
} else if (data.applied) {
  console.log(`APPLIED: created=${data.created} updated=${data.updated} failed=${data.failed.length}`);
  if (data.failed.length) for (const f of data.failed) console.log(`  FAIL ${f.sku}: ${f.error}`);
} else {
  console.log('HTTP', res.status, JSON.stringify(data).slice(0, 800));
}
