/**
 * Перечень позиций, у которых срок в строке под заголовком принят по
 * умолчанию («12 месяцев» без явного срока в данных) — на проверку
 * руководителю (правило docs/rules/card-title.md).
 *
 * Вход — выгрузка ops-export-products (JSON: name, sku, vendor, price) и,
 * если есть, карта слаг/описание. Вывод — markdown в stdout.
 *
 *   npx tsx scripts/catalog/card-terms-report.ts <export.json> [map.json] [дата]
 */
import { readFileSync } from 'node:fs';
import { termIsAssumed, termLabel, displayName } from '../../src/lib/card-display';
import { cardComposition } from '../../src/lib/product-composition';

const [exportPath, mapPath, stamp] = process.argv.slice(2);
if (!exportPath) {
  console.error('нужен путь к выгрузке каталога');
  process.exit(2);
}
interface Row { name: string; sku: string; vendor: string; price: string | number }
const rows: Row[] = JSON.parse(readFileSync(exportPath, 'utf8'));
const desc = new Map<string, string>();
if (mapPath) for (const m of JSON.parse(readFileSync(mapPath, 'utf8'))) desc.set(m.sku, m.desc || '');

const assumed: { vendor: string; name: string; sku: string; kind: string }[] = [];
const explicit: Record<string, number> = {};
// В выгрузке нет product_type и parent_sku: подарочные карты и номиналы
// опознаются по артикулу теми же масками, что в src/lib/catalog.ts.
const GIFT_PARENT = /-GIFT-CARD$/i;
const GIFT_VARIANT = /-GIFT-CARD-[A-Z]{2,6}-[A-Z0-9-]+$/i;
for (const r of rows) {
  const gift = GIFT_PARENT.test(r.sku) || GIFT_VARIANT.test(r.sku);
  const p = {
    sku: r.sku, name: r.name, price: Number(r.price) || 0,
    product_type: gift ? ('gift_card' as const) : null,
    parent_sku: GIFT_VARIANT.test(r.sku) ? r.sku.replace(/-[A-Z]{2,6}-[A-Z0-9-]+$/i, '') : null,
    short_description: desc.get(r.sku),
  };
  const kind = cardComposition(p);
  const src = { sku: r.sku, name: r.name, short_description: p.short_description };
  if (termIsAssumed(src, kind)) assumed.push({ vendor: r.vendor, name: displayName(r.name), sku: r.sku, kind });
  else { const t = termLabel(src, kind) ?? 'без срока'; explicit[t] = (explicit[t] || 0) + 1; }
}
const plugins = assumed.filter((a) => a.sku.startsWith('JB-PLG-'));
const rest = assumed.filter((a) => !a.sku.startsWith('JB-PLG-'));
const byVendor = new Map<string, typeof rest>();
for (const a of rest) byVendor.set(a.vendor, [...(byVendor.get(a.vendor) || []), a]);

const out: string[] = [];
out.push(`# Срок «12 месяцев» по умолчанию — перечень на проверку`);
out.push('');
out.push(`Дата: ${stamp || new Date().toISOString().slice(0, 10)}. Источник — выгрузка ops-export-products, ${rows.length} позиций.`);
out.push('');
out.push('Правило docs/rules/card-title.md: подписка и дополнение без явного срока в');
out.push('названии, артикуле и описании выходят с «12 месяцев». Ниже — все такие');
out.push('позиции; поправка вносится в src/data/card-terms.json (артикул → срок).');
out.push('');
out.push('## Итог');
out.push('');
out.push('| Срок | Позиций |');
out.push('|---|---:|');
for (const [t, n] of Object.entries(explicit).sort((a, b) => b[1] - a[1])) out.push(`| ${t} — по данным | ${n} |`);
out.push(`| 12 месяцев — по умолчанию, плагины JetBrains Marketplace | ${plugins.length} |`);
out.push(`| 12 месяцев — по умолчанию, остальные | ${rest.length} |`);
out.push('');
out.push(`## Плагины JetBrains Marketplace — ${plugins.length}`);
out.push('');
out.push('Подписка Marketplace годовая у всех плагинов; отдельно не перечисляются.');
out.push('');
out.push(`## Остальные позиции — ${rest.length}`);
for (const [vendor, list] of [...byVendor.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0], 'ru'))) {
  out.push('');
  out.push(`### ${vendor} — ${list.length}`);
  out.push('');
  for (const a of list.sort((x, y) => x.name.localeCompare(y.name, 'ru'))) out.push(`- ${a.name} \`${a.sku}\``);
}
console.log(out.join('\n'));
