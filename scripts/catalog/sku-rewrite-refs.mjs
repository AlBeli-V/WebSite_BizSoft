// Переписывание старых артикулов на новые по карте data/catalog/sku-map.json
// во всех файлах репозитория, где артикул служит ключом: пакеты вендоров,
// реестры импорта, контент вендоров, кросс-листинг, фикстуры, документы.
//
// Запуск: node scripts/catalog/sku-rewrite-refs.mjs [--dry]
//   --dry — только перечислить файлы и число замен, ничего не писать.
//
// Замена — по границе слова: старый артикул не должен быть частью более
// длинного (ADOBE-PS внутри ADOBE-PS-TEAM), поэтому вокруг него не может
// стоять буква, цифра, дефис или подчёркивание. Регистр строгий: слаги в
// нижнем регистре не трогаются. Файлы самой системы артикулов, отчёты и
// выгрузки исключены — там старые артикулы стоят намеренно.
import { readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const dry = process.argv.includes('--dry');

const map = JSON.parse(readFileSync(resolve(ROOT, 'data/catalog/sku-map.json'), 'utf8')).map;
const olds = Object.keys(map).sort((a, b) => b.length - a.length);
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const re = new RegExp(`(?<![A-Za-z0-9_-])(${olds.map(esc).join('|')})(?![A-Za-z0-9_-])`, 'g');

const SKIP = [
  /^data\/catalog\/sku-/,               // выгрузка, правила, расстановка, карта, реестр продуктов
  /^docs\/rules\/sku-system\.md$/,      // примеры старых артикулов в правиле
  /^scripts\/catalog\/sku-/,            // генератор и этот скрипт
  /^scripts\/lib\/zoho-model\.mjs$/,     // прежние артикулы закреплённых карточек — это их адреса
  /^tests\/sku\.test\.ts$/,             // проверка перевода старых артикулов
  /^tests\/(card-display|catalog-index-matrix)\.test\.ts$/, // проверки запасных правил по старым артикулам
  /^src\/lib\/(sku|catalog)\.ts$/,       // примеры старых схем в комментариях к запасным правилам
  /^\.github\/workflows\/ops-sku-migrate\.yml$/,
  /^(reports|exports|node_modules|dist)\//,
];
const EXT = /\.(ts|mjs|cjs|js|json|astro|md|py|yml|yaml|csv|txt)$/;

const files = execFileSync('git', ['ls-files'], { cwd: ROOT, encoding: 'utf8' }).split('\n')
  .filter((f) => f && EXT.test(f) && !SKIP.some((r) => r.test(f)));

let total = 0;
const touched = [];
for (const rel of files) {
  const abs = resolve(ROOT, rel);
  const text = readFileSync(abs, 'utf8');
  let n = 0;
  const out = text.replace(re, (m) => { n++; return map[m]; });
  if (!n) continue;
  total += n;
  touched.push(`${String(n).padStart(5)}  ${rel}`);
  if (!dry) writeFileSync(abs, out);
}
console.log(touched.join('\n'));
console.log(`${dry ? 'нашлось' : 'заменено'}: ${total} вхождений в ${touched.length} файлах`);
