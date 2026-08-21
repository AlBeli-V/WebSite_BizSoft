/**
 * Проверки собранного артефакта (dist) и публичных файлов.
 *
 * Ловит то, что не видно ни в тестах, ни в типах: вырезанный минификатором
 * код целей (ANL-001), утечку служебных файлов в public (SEC-001), ссылки
 * с завершающим слешем вопреки trailingSlash: 'never' (SEO-001).
 *
 * Запуск: pnpm check:artifacts [--baseline]
 */
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs';
import { join, extname } from 'node:path';
import XLSX from 'xlsx';

const BASELINE = process.argv.includes('--baseline');
const results = [];
const add = (ok, name, got) => results.push({ ok, name, got });

function walk(dir, out = []) {
  if (!existsSync(dir)) return out;
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) walk(p, out);
    else out.push(p);
  }
  return out;
}

// ── SEC-001: в public/ не должно быть закупочных цен и коэффициентов наценки ──
// Проверяем содержимое, а не расширение: шаблон загрузки лежать там имеет
// право, выгрузка каталога с себестоимостью — нет.
const SENSITIVE = ['base_price_usd', 'base_price_eur', 'markup_coeff', 'markup_percent'];
const tables = walk('public').filter((f) => ['.xlsx', '.xls', '.ods'].includes(extname(f).toLowerCase()));
const leaked = [];
for (const f of tables) {
  const wb = XLSX.readFile(f);
  for (const name of wb.SheetNames) {
    const rows = XLSX.utils.sheet_to_json(wb.Sheets[name], { defval: '' });
    // Строки-примеры шаблона (sku EXAMPLE-*) содержат условные значения —
    // они и должны показывать формат. Реальные выгрузки таких sku не имеют.
    const hits = rows
      .filter((r) => !/^EXAMPLE-/i.test(String(r.sku ?? '')))
      .filter((r) => SENSITIVE.some((k) => String(r[k] ?? '').trim() !== ''));
    if (hits.length) { leaked.push(`${f} (${hits.length} строк)`); break; }
  }
}
add(leaked.length === 0, 'в public/ нет закупочных цен и наценок', leaked.length ? leaked.join(', ') : `проверено файлов: ${tables.length}`);

const csvLeaked = walk('public').filter((f) => extname(f).toLowerCase() === '.csv');
add(csvLeaked.length === 0, 'в public/ нет CSV-выгрузок', csvLeaked.length ? csvLeaked.join(', ') : 'нет');

// ── ANL-001: вызовы целей не должны вырезаться минификатором ──
if (existsSync('dist/client/_astro')) {
  const chunks = walk('dist/client/_astro').filter((f) => f.endsWith('.js'));
  const withGoal = chunks.filter((f) => readFileSync(f, 'utf8').includes('reachGoal'));
  add(withGoal.length > 0, 'цели Метрики присутствуют в клиентских чанках', `${withGoal.length} чанк(ов) из ${chunks.length}`);

  // Признак вырезанного идентификатора счётчика: `=void 0` рядом с `.ym`
  const dead = chunks.filter((f) => /void 0;[a-zA-Z$_]+\.ym/.test(readFileSync(f, 'utf8')));
  add(dead.length === 0, 'идентификатор счётчика не схлопнут в void 0', dead.length ? dead.map((f) => f.split('/').pop()).join(', ') : 'нет');
} else {
  add(false, 'dist/client собран', 'каталога нет — нужен pnpm build');
}

// ── SEO-001: внутренние ссылки без завершающего слеша (trailingSlash: 'never') ──
const html = walk('dist/client').filter((f) => f.endsWith('.html'));
const slashy = new Set();
for (const f of html) {
  for (const m of readFileSync(f, 'utf8').matchAll(/href="(\/[a-z0-9\-\/]*\/)"/gi)) {
    if (m[1] !== '/') slashy.add(m[1]);
  }
}
add(slashy.size === 0, 'нет внутренних ссылок с завершающим слешем', slashy.size ? [...slashy].slice(0, 8).join(', ') : 'нет');

// ── вывод ──
console.log(`\nПроверки артефакта (${BASELINE ? 'базовый замер' : 'блокирующий режим'})\n`);
let failed = 0;
for (const r of results) {
  if (!r.ok) failed++;
  console.log(`  ${r.ok ? '✅' : '❌'} ${r.name}${r.got ? ` — ${r.got}` : ''}`);
}
console.log(`\nИтог: ${results.length - failed}/${results.length} пройдено, ${failed} не пройдено\n`);
process.exit(BASELINE ? 0 : failed ? 1 : 0);
