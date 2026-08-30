#!/usr/bin/env node
/**
 * Агрегат спроса Вордстата по вендорам → src/data/vendor-demand.json.
 *
 * Источник — reports/seo/wordstat/semantic-universe.jsonl (собирается
 * workflow seo-wordstat). Суммируем wordstat_frequency всех фраз вендора,
 * кроме подкластера «бесплатно и пиратское»: пиратский спрос не должен
 * поднимать товар в коммерческих фидах.
 *
 * Результат коммитится в репозиторий: фид читает готовый JSON и не зависит
 * ни от наличия отчётов Вордстата в рантайме, ни от квоты API.
 *
 * Запуск: node scripts/seo/build-vendor-demand.mjs
 */
import { createReadStream, writeFileSync } from 'node:fs';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const SOURCE = join(root, 'reports/seo/wordstat/semantic-universe.jsonl');
const TARGET = join(root, 'src/data/vendor-demand.json');
const EXCLUDED_SUBCLUSTER = 'бесплатно и пиратское';

const vendors = new Map();
let phrases = 0;

const rl = createInterface({ input: createReadStream(SOURCE, 'utf8'), crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  let row;
  try {
    row = JSON.parse(line);
  } catch {
    continue; // битая строка журнала не должна ронять сборку агрегата
  }
  const vendor = row.vendor;
  if (!vendor || row.subcluster === EXCLUDED_SUBCLUSTER) continue;
  const freq = Number(row.wordstat_frequency) || 0;
  vendors.set(vendor, (vendors.get(vendor) || 0) + freq);
  phrases += 1;
}

// Стабильный порядок ключей: по убыванию спроса — diff при обновлении читается.
const sorted = Object.fromEntries(
  [...vendors.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])),
);

writeFileSync(
  TARGET,
  JSON.stringify(
    {
      note: 'Суммарная месячная частота Вордстата по вендору (без пиратских фраз). Генерируется scripts/seo/build-vendor-demand.mjs, руками не править.',
      source: 'reports/seo/wordstat/semantic-universe.jsonl',
      generated_at: new Date().toISOString(),
      phrases_counted: phrases,
      vendors: sorted,
    },
    null,
    1,
  ) + '\n',
);

console.log(`vendor-demand.json: ${vendors.size} вендоров, ${phrases} фраз учтено`);
