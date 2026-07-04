// Импорт карточек товаров в biz-soft.pro через /api/admin/import.
// Токен читается из .env (не передаётся в argv). Usage:
//   node scripts/import-cards.mjs <file.xlsx>          — dry-run (ничего не пишет)
//   node scripts/import-cards.mjs <file.xlsx> --apply  — применить
import { readFileSync } from 'node:fs';

function loadEnv() {
  const txt = readFileSync(new URL('../.env', import.meta.url), 'utf8');
  const env = {};
  for (const line of txt.split(/\r?\n/)) {
    const m = line.match(/^([A-Z_]+)=(.*)$/);
    if (m) env[m[1]] = m[2].replace(/^"|"$/g, '');
  }
  return env;
}

const env = loadEnv();
const file = process.argv[2];
const apply = process.argv.includes('--apply');
if (!file) { console.error('нет пути к xlsx'); process.exit(1); }

const xlsxBase64 = readFileSync(file).toString('base64');
const url = `${env.SITE_URL}/api/admin/import`;

const res = await fetch(url, {
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
  console.log('\nРУБЛЁВЫЕ ЦЕНЫ (create):');
  for (const i of data.items.filter((x) => x.mode === 'create')) {
    const price = i.payload.price ?? (i.payload.price_note || '');
    console.log(`  ${i.sku}  →  ${typeof price === 'number' ? price + ' ₽' : price}`);
  }
} else if (data.applied) {
  console.log(`APPLIED: created=${data.created} updated=${data.updated} failed=${data.failed.length}`);
  if (data.failed.length) for (const f of data.failed) console.log(`  FAIL ${f.sku}: ${f.error}`);
} else {
  console.log('HTTP', res.status, JSON.stringify(data).slice(0, 800));
}
