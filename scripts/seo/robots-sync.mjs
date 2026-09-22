#!/usr/bin/env node
/**
 * Сборка и проверка public/robots.txt.
 *
 *   node scripts/seo/robots-sync.mjs --write   — собрать блок Clean-param из
 *                                                реестра data/seo/url-params.json
 *   node scripts/seo/robots-sync.mjs --check   — проверить файл в репозитории
 *   node scripts/seo/robots-sync.mjs --check --base https://biz-soft.pro
 *                                              — дополнительно сверить с продом
 *
 * Прод сверяется с раннера GitHub: из сессии egress к сайту закрыт
 * (docs/rules/prod-access.md), а файл в репозитории и файл на сайте — разные
 * вещи: между ними деплой, который мог не дойти.
 */

import { readFileSync, writeFileSync } from 'node:fs';
import { auditRobots, readRegistry, sameRobots, syncRobots } from './robots-lib.mjs';

const args = process.argv.slice(2);
const has = (f) => args.includes(f);
const value = (f) => { const i = args.indexOf(f); return i === -1 ? '' : (args[i + 1] || ''); };

const FILE = value('--file') || 'public/robots.txt';
const registry = readRegistry();
const text = readFileSync(FILE, 'utf8');

if (has('--write')) {
  const next = syncRobots(text, registry);
  if (next === text) {
    console.log(`${FILE}: блок Clean-param уже собран (${registry.insignificant.length} параметров)`);
  } else {
    writeFileSync(FILE, next);
    console.log(`${FILE}: блок Clean-param собран заново (${registry.insignificant.length} параметров)`);
  }
  process.exit(0);
}

let rc = 0;
const problems = auditRobots(text, registry);
if (problems.length) {
  rc = 1;
  console.log(`✗ ${FILE}`);
  for (const p of problems) console.log(`  — ${p}`);
} else {
  console.log(`✓ ${FILE}: ${registry.insignificant.length} незначащих параметров в Clean-param, служебные разделы закрыты`);
}

const base = value('--base');
if (base) {
  const url = `${base.replace(/\/+$/, '')}/robots.txt`;
  try {
    const res = await fetch(url, { headers: { 'user-agent': 'bizsoft-robots-check' } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const live = await res.text();
    if (sameRobots(live, text)) {
      console.log(`✓ ${url}: совпадает с репозиторием`);
    } else {
      rc = 1;
      console.log(`✗ ${url}: расходится с репозиторием — деплой не дошёл или файл подменён на сервере`);
      const liveParams = live.match(/^\s*Clean-param:.*$/gmi) || [];
      console.log(`  на сайте Clean-param: ${liveParams.length ? liveParams.join(' | ') : 'директивы нет'}`);
    }
  } catch (e) {
    rc = 1;
    console.log(`✗ ${url}: не прочитан (${e.message})`);
  }
}

process.exit(rc);
