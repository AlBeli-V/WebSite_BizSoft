#!/usr/bin/env node
/**
 * Готовит партию текстов, разводящих одинаковые описания линеек.
 *
 *   node scripts/seo/dedupe-descriptions.mjs <файл-со-слагами> [--write]
 *
 * Слаги берутся из отчёта ops-content-audit (раздел «Дубли мета-тегов»,
 * запуск с full=true). Названия и исходные описания — из пакетов
 * scripts/catalog/*.json. Без --write печатается план, с --write результат
 * дописывается в data/seo/product-descriptions.json, откуда его переносит
 * в прод ops-apply-descriptions (сначала apply=false — план).
 *
 * --sync-catalog кладёт новые short_description ещё и в сам пакет каталога:
 * иначе следующий прогон ops-import-vendors вернёт общий текст линейки и
 * дубли появятся снова.
 */
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dedupeGroup } from './dedupe-lib.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const CATALOG = resolve(root, 'scripts/catalog');
const TEXTS = resolve(root, 'data/seo/product-descriptions.json');

const [listFile, ...flags] = process.argv.slice(2);
if (!listFile) {
  console.error('нужен файл со слагами (по одному в строке)');
  process.exit(1);
}
const write = flags.includes('--write');
const syncCatalog = flags.includes('--sync-catalog');

const catalog = new Map();
for (const file of readdirSync(CATALOG).filter((f) => f.endsWith('.json'))) {
  const pkg = JSON.parse(readFileSync(resolve(CATALOG, file), 'utf8'));
  if (pkg.removed) continue;
  for (const p of pkg.products ?? []) {
    if (!p.archive) catalog.set(p.slug, { ...p, vendor: p.vendor ?? pkg.vendor });
  }
}

const slugs = readFileSync(listFile, 'utf8').split('\n').map((s) => s.trim()).filter(Boolean);
const missing = slugs.filter((s) => !catalog.has(s));
if (missing.length) {
  console.error(`нет в пакетах каталога: ${missing.join(', ')}`);
  process.exit(1);
}

// группируем по исходному описанию — ровно так их видит аудит
const groups = new Map();
for (const slug of slugs) {
  const p = catalog.get(slug);
  const key = (p.short_description ?? '').trim();
  groups.set(key, [...(groups.get(key) ?? []), p]);
}

const result = {};
const skipped = [];
for (const [key, group] of groups) {
  if (group.length < 2) {
    skipped.push(`${group[0].slug}: в партии один — разводить не с чем`);
    continue;
  }
  const out = dedupeGroup(group);
  if (!out) {
    skipped.push(`«${key.slice(0, 60)}»: названия карточек не различаются — нужен разбор руками`);
    continue;
  }
  Object.assign(result, out);
}

// описания не должны совпасть ни между собой, ни с чужой карточкой каталога
const taken = new Map();
for (const [slug, p] of catalog) {
  if (slug in result) continue;
  const v = (p.short_description ?? '').trim();
  if (v) taken.set(v, slug);
}
const clashes = [];
const metas = new Map();
for (const [slug, texts] of Object.entries(result)) {
  const v = texts.short_description;
  if (taken.has(v)) clashes.push(`${slug} ↔ ${taken.get(v)}: «${v.slice(0, 60)}»`);
  taken.set(v, slug);
  const m = texts.meta_description;
  if (metas.has(m)) clashes.push(`${slug} ↔ ${metas.get(m)} (meta): «${m.slice(0, 60)}»`);
  metas.set(m, slug);
}
if (clashes.length) {
  console.error('после разведения описания всё ещё совпадают:\n' + clashes.join('\n'));
  process.exit(1);
}

for (const [slug, texts] of Object.entries(result)) {
  console.log(`[${slug}]`);
  console.log(`  short_description (${texts.short_description.length}): ${texts.short_description}`);
  console.log(`  meta_description  (${texts.meta_description.length}): ${texts.meta_description}`);
}
if (skipped.length) console.log('\nпропущено:\n - ' + skipped.join('\n - '));
console.log(`\nкарточек в партии: ${Object.keys(result).length}, групп: ${groups.size}`);

if (write) {
  const payload = JSON.parse(readFileSync(TEXTS, 'utf8'));
  const products = payload.products ?? payload;
  for (const [slug, texts] of Object.entries(result)) {
    products[slug] = { ...(products[slug] ?? {}), ...texts };
  }
  writeFileSync(TEXTS, JSON.stringify(payload, null, 2) + '\n');
  console.log(`записано в ${TEXTS}`);
}

if (syncCatalog) {
  for (const file of readdirSync(CATALOG).filter((f) => f.endsWith('.json'))) {
    const path = resolve(CATALOG, file);
    const pkg = JSON.parse(readFileSync(path, 'utf8'));
    let touched = 0;
    for (const p of pkg.products ?? []) {
      const texts = result[p.slug];
      if (texts && p.short_description !== texts.short_description) {
        p.short_description = texts.short_description;
        touched += 1;
      }
    }
    if (touched) {
      writeFileSync(path, JSON.stringify(pkg, null, 2) + '\n');
      console.log(`пакет ${file}: обновлено описаний ${touched}`);
    }
  }
}
