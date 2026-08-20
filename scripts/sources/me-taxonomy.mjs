#!/usr/bin/env node
/**
 * Функциональные группы магазина ManageEngine из снимка его главной страницы.
 *
 * Группы и распределение продуктов по ним НЕ придумываются: витрина магазина
 * сама выводит десять разделов, внутри каждого — подразделы, внутри них —
 * продукты с подписью. Снимок текста этой страницы разбирается здесь.
 *
 * Запуск: node scripts/sources/me-taxonomy.mjs data/sources/manageengine/2026-08-20
 * Выход:  <каталог>/taxonomy.json
 */

import fs from 'node:fs';
import path from 'node:path';

// Десять разделов витрины. Список сверяется со снимком: если магазин
// перестроят, скрипт скажет об этом, а не тихо разложит продукты не туда.
const GROUPS = [
  'Identity and access management',
  'Unified service management',
  'Unified endpoint management and security',
  'IT operations management and observability',
  'Security information and event management',
  'Advanced IT analytics',
  'Low-code app development',
  'Cloud solutions for enterprise IT',
  'IT management for MSPs',
  'Services',
];

function main() {
  const dir = process.argv[2];
  const discoveryFile = path.join(dir || '', 'discovery.json');
  if (!dir || !fs.existsSync(discoveryFile)) {
    console.error('укажите каталог снимков, например data/sources/manageengine/2026-08-20');
    process.exit(2);
  }
  const discovery = JSON.parse(fs.readFileSync(discoveryFile, 'utf8'));
  const homeId = discovery.meta?.source_snapshot_id;
  const homeText = path.join(dir, 'discovery', `${homeId}.txt`);
  if (!fs.existsSync(homeText)) {
    console.error(`нет снимка главной страницы: ${homeText}`);
    process.exit(2);
  }
  const lines = fs.readFileSync(homeText, 'utf8').split('\n').map((l) => l.trim());

  // Продукт витрины: у ссылки магазина подпись собрана как «Название Слоган».
  // Название — то, что совпадает с отдельной строкой на главной.
  const links = discovery.links || [];

  // Раздел витрины начинается там, где строка в точности равна названию
  // группы. В верхней навигации те же названия перенесены по строкам, поэтому
  // туда совпадение не попадает.
  // Верхняя навигация магазина перечисляет те же десять названий. Часть из
  // них там перенесена по строкам, часть — нет («Services»), поэтому просто
  // «первое совпадение» подобрало бы пункт меню и сдвинуло границы разделов.
  // Навигация заканчивается там, где начинается первый настоящий раздел.
  const navEnd = lines.indexOf(GROUPS[0]);
  if (navEnd < 0) {
    console.error(`витрина изменилась: раздела «${GROUPS[0]}» на главной нет`);
    process.exit(3);
  }

  const groupAt = new Map();
  lines.forEach((l, i) => {
    if (i >= navEnd && GROUPS.includes(l) && !groupAt.has(l)) groupAt.set(l, i);
  });
  const missing = GROUPS.filter((g) => !groupAt.has(g));
  if (missing.length) {
    console.error(`витрина изменилась, разделы не найдены: ${missing.join('; ')}`);
    process.exit(3);
  }

  const bounds = [...groupAt.entries()]
    .map(([name, at]) => ({ name, at }))
    .sort((a, b) => a.at - b.at);
  const groupOf = (idx) => {
    let cur = null;
    for (const b of bounds) { if (b.at <= idx) cur = b.name; else break; }
    return cur;
  };

  const rows = [];
  const unmatched = [];
  for (const link of links) {
    const label = (link.label || '').replace(/\s+/g, ' ').trim();
    if (!label) continue;
    // Ищем строку главной, с которой начинается подпись ссылки: это название
    // продукта, а остаток подписи — его слоган.
    // Один и тот же продукт может стоять на витрине дважды: в своём разделе и
    // в разделе для сервис-провайдеров, под тем же названием, но с разным
    // слоганом и разной ссылкой. Совпадения по одному названию мало — иначе
    // обе ссылки указали бы на одно место и один из разделов остался бы без
    // продукта. Поэтому требуем, чтобы следующей строкой шёл слоган именно
    // этой ссылки.
    let found = -1;
    let name = '';
    for (let i = 0; i < lines.length; i += 1) {
      const l = lines[i];
      if (!l || l.length < 3) continue;
      if (!(label === l || (label.startsWith(l) && label[l.length] === ' '))) continue;
      const tail = label.slice(l.length).trim();
      const exact = tail === '' || (lines[i + 1] || '') === tail;
      if (!exact) continue;
      if (l.length > name.length) { found = i; name = l; }
    }
    // Запасной путь: слоган на витрине мог быть перенесён по строкам.
    if (found < 0) {
      for (let i = 0; i < lines.length; i += 1) {
        const l = lines[i];
        if (!l || l.length < 3) continue;
        if (label === l || (label.startsWith(l) && label[l.length] === ' ')) {
          if (l.length > name.length) { found = i; name = l; }
        }
      }
    }
    if (found < 0) { unmatched.push(label); continue; }
    const group = groupOf(found);
    if (!group) { unmatched.push(label); continue; }
    const tagline = label.slice(name.length).trim();
    // Подраздел — ближайший заголовок выше продукта, который не является ни
    // группой, ни названием другого продукта. Заголовки на витрине идут
    // парой «название / описание», поэтому берём строку перед описанием.
    // Подраздел — ближайший заголовок выше продукта. На витрине заголовок
    // идёт связкой «заголовок, пусто, описание, пусто», а продукт — связкой
    // «название, слоган» без пустых строк. Отличать по одному лишь тексту
    // нельзя: слоганы продуктов, у которых нет ссылки в магазин, иначе
    // принимаются за заголовки.
    const isHeading = (i) =>
      lines[i] && lines[i].length <= 90
      && !lines[i + 1] && lines[i + 2] && !lines[i + 3];
    let subgroup = null;
    for (let i = found - 1; i > 0; i -= 1) {
      if (GROUPS.includes(lines[i])) break;
      if (isHeading(i)) { subgroup = lines[i]; break; }
    }
    rows.push({ name, tagline, group, subgroup, url: link.url });
  }

  const taxonomy = {
    collected_at: discovery.collected_at,
    source_url: discovery.store,
    source_snapshot_id: homeId,
    groups: GROUPS.map((g) => ({
      group: g,
      products: [...new Map(
        rows.filter((r) => r.group === g)
          .map(({ name, tagline, subgroup, url }) => [name, { name, tagline, subgroup, url }]),
      ).values()],
    })),
    unmatched,
  };

  const out = path.join(dir, 'taxonomy.json');
  fs.writeFileSync(out, JSON.stringify(taxonomy, null, 2) + '\n');
  console.log(`таксономия: ${out}`);
  for (const g of taxonomy.groups) console.log(`  ${g.group}: ${g.products.length}`);
  if (unmatched.length) console.log(`  не разложено: ${unmatched.length}`);
}

main();
