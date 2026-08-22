#!/usr/bin/env node
/**
 * Правила совместимости позиций ManageEngine — из манифеста, не из головы.
 *
 * Вендор сам говорит о зависимостях названиями таблиц и строк прайса:
 * «Add-on for Professional Edition» продаётся только к Professional,
 * «Additional 100 IT Assets» не продаётся без базового пакета, а облачное и
 * коробочное дополнение Analytics Plus — взаимоисключающие. Скрипт вытаскивает
 * ровно эти три вида связей и ничего сверх них.
 *
 * Запуск: node scripts/sources/me-rules.mjs data/sources/manageengine/2026-08-20
 * Выход:  scripts/content/zoho-rules.json
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const OUT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)), '../content/zoho-rules.json');

function main() {
  const dir = process.argv[2];
  const file = path.join(dir || '', 'manifest.json');
  if (!dir || !fs.existsSync(file)) {
    console.error('укажите каталог снимков, например data/sources/manageengine/2026-08-20');
    process.exit(2);
  }
  const manifest = JSON.parse(fs.readFileSync(file, 'utf8'));
  const rules = [];

  for (const family of manifest.families) {
    const offers = family.deployment_products.flatMap((dp) => dp.offers);
    const base = offers.filter((o) => o.kind === 'base');

    for (const offer of offers) {
      // 1. Дополнение к конкретной редакции: вендор пишет её в названии
      //    таблицы («Add-on for Professional Edition»).
      const edition = offer.offer_name.match(
        /add-?ons?\s+for\s+(Free|Standard|Professional|Premium|Enterprise)\s+Edition/i);
      if (offer.kind === 'addon' && edition) {
        const want = edition[1];
        const target = base.find((b) => b.edition === want);
        rules.push({
          id: `${family.family_slug}-${offer.offer_slug}-requires-${want.toLowerCase()}`,
          appliesTo: { offerSlug: offer.offer_slug, familySlug: family.family_slug },
          requires: { edition: want, familySlug: family.family_slug, offerSlug: target?.offer_slug },
          reason: `Вендор продаёт это дополнение только к редакции ${want} — так названа таблица прайса`,
        });
      } else if (offer.kind === 'addon' && base.length) {
        // 2. Дополнение без указания редакции: нужен любой базовый пакет
        //    того же семейства.
        rules.push({
          id: `${family.family_slug}-${offer.offer_slug}-requires-base`,
          appliesTo: { offerSlug: offer.offer_slug, familySlug: family.family_slug },
          requires: { familySlug: family.family_slug },
          reason: 'Дополнение продаётся только вместе с базовой лицензией того же продукта',
        });
      }

      // 3. Строки «Additional …» расширяют уже купленный объём и сами по себе
      //    поставкой не являются.
      const extra = offer.variants.filter((v) => /^Additional\s/i.test(v.variant_name));
      if (extra.length) {
        rules.push({
          id: `${family.family_slug}-${offer.offer_slug}-additional-extends`,
          appliesTo: {
            offerSlug: offer.offer_slug,
            familySlug: family.family_slug,
            variantPattern: '^Additional\\s',
          },
          extends: { offerSlug: offer.offer_slug, familySlug: family.family_slug },
          reason: 'Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется',
        });
      }
    }

    // 4. Взаимоисключающие пары: одно и то же дополнение в облачной и
    //    коробочной поставке.
    const pairKey = (name) => name
      .replace(/\b(Cloud|On-?Premise[s]?)\b/gi, '')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
    const groups = new Map();
    for (const offer of offers) {
      if (!/\b(Cloud|On-?Premise)/i.test(offer.offer_name)) continue;
      const key = pairKey(offer.offer_name);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(offer);
    }
    for (const [, pair] of groups) {
      if (pair.length < 2) continue;
      for (const offer of pair) {
        for (const other of pair) {
          if (other.offer_slug === offer.offer_slug) continue;
          rules.push({
            id: `${family.family_slug}-${offer.offer_slug}-excludes-${other.offer_slug}`,
            appliesTo: { offerSlug: offer.offer_slug, familySlug: family.family_slug },
            excludes: { offerSlug: other.offer_slug },
            reason: 'Одно и то же дополнение в облачной и коробочной поставке — берут что-то одно',
          });
        }
      }
    }
  }

  fs.writeFileSync(OUT, JSON.stringify({
    generated_from: dir,
    source_collected_at: manifest.source_collected_at,
    rules,
  }, null, 2) + '\n');
  console.log(`правил: ${rules.length} → ${OUT}`);
  const kinds = { requires: 0, extends: 0, excludes: 0 };
  for (const r of rules) for (const k of Object.keys(kinds)) if (r[k]) kinds[k] += 1;
  console.log(`  requires ${kinds.requires}, extends ${kinds.extends}, excludes ${kinds.excludes}`);
}

main();
