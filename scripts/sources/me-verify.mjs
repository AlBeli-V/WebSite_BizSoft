#!/usr/bin/env node
/**
 * Сверка манифеста со снимками: ни одной придуманной цены.
 *
 * Для каждого варианта из манифеста ищем в снимках того же семейства пару
 * соседних строк «название позиции / сумма». Если пары нет — значение в
 * манифесте взялось не из источника, и это ошибка, а не мелочь.
 *
 * Запуск: node scripts/sources/me-verify.mjs data/sources/manageengine/2026-08-20
 * Код возврата 1 — есть неподтверждённые значения.
 */

import fs from 'node:fs';
import path from 'node:path';

const money = (line) => (line || '').trim().replace(/^US\$|^\$/, '').replace(/,/g, '');

function main() {
  const dir = process.argv[2];
  for (const f of ['manifest.json', 'details.json']) {
    if (!dir || !fs.existsSync(path.join(dir, f))) {
      console.error(`нет ${dir}/${f}`);
      process.exit(2);
    }
  }
  const manifest = JSON.parse(fs.readFileSync(path.join(dir, 'manifest.json'), 'utf8'));
  const details = JSON.parse(fs.readFileSync(path.join(dir, 'details.json'), 'utf8'));

  // Все снимки семейства: страница по умолчанию плюс каждая вкладка прайса.
  const snapsByUrl = new Map();
  for (const row of details.rows) {
    const ids = [row.source_snapshot_id, ...(row.tabs || []).map((t) => t.source_snapshot_id)]
      .filter(Boolean);
    snapsByUrl.set(row.source_url, ids);
  }

  let checked = 0;
  const unconfirmed = [];

  for (const family of manifest.families) {
    const ids = snapsByUrl.get(family.source_url) || [];
    // Пары «строка → следующая строка» из всех снимков семейства.
    const pairs = new Set();
    for (const id of ids) {
      const file = path.join(dir, 'details', `${id}.txt`);
      if (!fs.existsSync(file)) continue;
      const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/).map((l) => l.trim());
      for (let i = 0; i + 1 < lines.length; i += 1) {
        if (!lines[i] || !lines[i + 1]) continue;
        pairs.add(`${lines[i]} ${money(lines[i + 1])}`);
      }
    }
    for (const dp of family.deployment_products) {
      for (const offer of dp.offers) {
        for (const v of offer.variants) {
          checked += 1;
          if (v.price_status !== 'listed') continue;
          const key = `${v.variant_name} ${String(v.amount_usd)}`;
          if (!pairs.has(key)) {
            unconfirmed.push(`${family.family_name} / ${offer.offer_name} / ${v.variant_name} = ${v.amount_usd}`);
          }
        }
      }
    }
  }

  console.log(`проверено вариантов: ${checked}`);
  if (unconfirmed.length) {
    console.log(`НЕ подтверждено снимками: ${unconfirmed.length}`);
    for (const line of unconfirmed.slice(0, 25)) console.log(`  ${line}`);
    process.exit(1);
  }
  console.log('все значения подтверждены снимками страниц вендора');
}

main();
