#!/usr/bin/env node
/**
 * Пересборка `src/legal/legal-manifest.json` — реестра редакций правовых
 * документов сайта.
 *
 * Манифест — единственное место, откуда сервер берёт версию и контрольный
 * хэш при записи согласия. Из браузера эти значения не принимаются вовсе:
 * иначе доказательством стало бы то, что прислал клиент, а подделать такую
 * запись может кто угодно (ТЗ 16.09.2026, п. 8).
 *
 * Запуск:  node scripts/legal/build-manifest.mjs
 * Проверка (без записи): node scripts/legal/build-manifest.mjs --check
 *
 * Соответствие манифеста файлам держит tests/legal-documents.test.ts, поэтому
 * забыть пересобрать его после новой редакции нельзя — упадёт `pnpm test`.
 */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, writeFileSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const LEGAL_DIR = resolve(ROOT, 'src/legal');
const MANIFEST = resolve(LEGAL_DIR, 'legal-manifest.json');

const DOC_IDS = ['privacy', 'personal-data-consent', 'marketing-consent', 'cookies', 'terms'];

/** Дубль canonicalText из src/lib/legal-doc.ts: скрипт не тянет TypeScript. */
function canonicalText(raw) {
  return (
    raw
      .replace(/\r\n?/g, '\n')
      .split('\n')
      .map((line) => line.replace(/[ \t]+$/, ''))
      .join('\n')
      .replace(/\n+$/, '') + '\n'
  );
}

function sha256(raw) {
  return createHash('sha256').update(canonicalText(raw), 'utf8').digest('hex');
}

/** Название документа — строка `# …` его текста, второй копии заголовка нет. */
function titleOf(text) {
  const line = canonicalText(text).split('\n').find((l) => l.startsWith('# '));
  return line ? line.slice(2).trim() : '';
}

export function buildManifest() {
  const out = {};
  for (const id of DOC_IDS) {
    const dir = resolve(LEGAL_DIR, id);
    if (!existsSync(dir)) throw new Error(`нет каталога редакций: src/legal/${id}`);
    const versions = readdirSync(dir)
      .filter((f) => f.endsWith('.md'))
      .map((f) => f.replace(/\.md$/, ''))
      // Версия = дата редакции ISO, поэтому лексикографический порядок и есть
      // хронологический. Действующая — последняя.
      .sort();
    if (!versions.length) throw new Error(`нет ни одной редакции: src/legal/${id}`);

    const revisions = versions.map((version) => {
      const path = `src/legal/${id}/${version}.md`;
      const text = readFileSync(resolve(ROOT, path), 'utf8');
      return { version, path, sha256: sha256(text) };
    });
    const current = revisions[revisions.length - 1];
    const text = readFileSync(resolve(ROOT, current.path), 'utf8');

    out[id] = {
      title: titleOf(text),
      url: `/legal/${id}`,
      version: current.version,
      path: current.path,
      sha256: current.sha256,
      revisions,
    };
  }
  return out;
}

const manifest = buildManifest();
const json = JSON.stringify(manifest, null, 2) + '\n';

if (process.argv.includes('--check')) {
  const have = existsSync(MANIFEST) ? readFileSync(MANIFEST, 'utf8') : '';
  if (have !== json) {
    console.error('legal-manifest.json устарел — запустите node scripts/legal/build-manifest.mjs');
    process.exit(1);
  }
  console.log('legal-manifest.json актуален');
} else {
  writeFileSync(MANIFEST, json);
  for (const [id, d] of Object.entries(manifest)) {
    console.log(`${id.padEnd(24)} ${d.version}  ${d.sha256.slice(0, 16)}…  редакций: ${d.revisions.length}`);
  }
}
