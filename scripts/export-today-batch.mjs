// Выгрузка вендоров и товаров партии в xlsx — для изготовления иконок.
// Использование: node scripts/export-today-batch.mjs <out.xlsx> <slug> [slug...]
// Лист «Производители»: slug, название, юрлицо, категория, сайт, есть ли иконка
// в пакете (src/assets/vendor-icons) и файл логотипа.
// Лист «Продукты»: вендор, sku, slug, имя, URL карточки, приписка к цене.
import * as XLSX from 'xlsx';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const [outPath, ...slugs] = process.argv.slice(2);
if (!outPath || slugs.length === 0) {
  console.error('usage: node scripts/export-today-batch.mjs <out.xlsx> <slug> [slug...]');
  process.exit(1);
}

const hasIcon = (slug) =>
  existsSync(resolve(__dir, `../src/assets/vendor-icons/color/${slug}.svg`)) &&
  existsSync(resolve(__dir, `../src/assets/vendor-icons/mono/${slug}.svg`));

const vendors = [];
const products = [];
for (const slug of slugs) {
  const file = resolve(__dir, `catalog/${slug}.json`);
  if (!existsSync(file)) { console.error(`нет пакета: ${slug}`); continue; }
  const pkg = JSON.parse(readFileSync(file, 'utf8'));
  const v = pkg.vendor_entry || {};
  const live = pkg.products.filter((p) => !p.archive);
  vendors.push({
    'Слаг вендора': slug,
    'Производитель': v.vendor || '',
    'Юридическое лицо': v.legalName || '',
    'Категория': v.catLabel || '',
    'Сайт вендора': v.site || '',
    'Страница на biz-soft.pro': `https://biz-soft.pro/vendors/${slug}`,
    'Иконка в пакете': hasIcon(slug) ? 'есть' : 'НУЖНА',
    'Файл логотипа': `public/brand-logos/${slug}-logo.svg`,
    'Товаров в партии': live.length,
    'Имя файла иконки': `${slug}.svg`,
  });
  for (const p of live) {
    products.push({
      'Производитель': v.vendor || '',
      'Слаг вендора': slug,
      'SKU': p.sku,
      'Слаг товара': p.slug,
      'Название карточки': p.name,
      'Официальное название': p.official_name || '',
      'Категория': p.category || '',
      'Страница товара': `https://biz-soft.pro/product/${p.slug}`,
      'Приписка к цене': p.billing || '',
      'Минимум': p.min_quantity ?? 1,
      'Имя файла иконки': `${slug}.svg`,
    });
  }
}

const wb = XLSX.utils.book_new();
const fit = (rows) => {
  const ws = XLSX.utils.json_to_sheet(rows);
  ws['!cols'] = Object.keys(rows[0] || {}).map((k) => ({
    wch: Math.min(52, Math.max(k.length + 2, ...rows.map((r) => String(r[k] ?? '').length + 2))),
  }));
  return ws;
};
XLSX.utils.book_append_sheet(wb, fit(vendors), 'Производители');
XLSX.utils.book_append_sheet(wb, fit(products), 'Продукты');
XLSX.writeFile(wb, outPath);
console.log(`${outPath}: вендоров ${vendors.length}, товаров ${products.length}`);
console.log('иконки нужны для:', vendors.filter((v) => v['Иконка в пакете'] === 'НУЖНА').map((v) => v['Слаг вендора']).join(', ') || '—');
