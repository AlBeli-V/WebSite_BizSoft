/**
 * robots.txt: сборка директивы Clean-param и разбор файла.
 *
 * Зачем слой. Страница с незначащим GET-параметром отдаёт то же содержимое,
 * что и без него, и Яндекс заводит на каждую метку отдельный адрес: к
 * 15.09.2026 в индексе лежали пять копий страниц вендоров с «?etext=», а
 * 22.09.2026 кабинет прислал письмо о дублях уже по блогу и вендорам.
 * Canonical (src/lib/seo.ts) снимает дубль после обхода, Clean-param — до
 * него, поэтому директива обязательна, а её содержимое не должно зависеть
 * от того, вспомнил ли автор правки про robots.txt.
 *
 * Перечень параметров живёт в реестре data/seo/url-params.json, строка
 * Clean-param собирается из него, а блок в public/robots.txt между
 * маркерами пишет robots-sync.mjs. Руками блок не правят: расхождение
 * реестра и файла роняет tests/robots.test.ts.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

/** Предел длины одной строки Clean-param у Яндекса. */
export const CLEAN_PARAM_LIMIT = 500;

export const BEGIN = '# clean-param:begin — собирает scripts/seo/robots-sync.mjs, руками не править';
export const END = '# clean-param:end';

/** Разделы, закрытые от индексации: список сторожится тестом. */
export const REQUIRED_DISALLOW = [
  '/admin', '/api', '/cart', '/checkout', '/search', '/unsubscribe', '/documents/',
];

export function readRegistry(root = process.cwd()) {
  const raw = readFileSync(join(root, 'data/seo/url-params.json'), 'utf8');
  const reg = JSON.parse(raw);
  return {
    insignificant: (reg.insignificant || []).map((p) => p.name),
    meaningful: (reg.meaningful || []).map((p) => p.name),
    entries: reg,
  };
}

/**
 * Строки Clean-param под перечень параметров. Яндекс читает не длиннее 500
 * символов в строке, поэтому длинный перечень разбивается на несколько
 * директив: они складываются, а не заменяют друг друга.
 */
export function cleanParamLines(names) {
  const lines = [];
  let cur = [];
  const len = (arr) => 'Clean-param: '.length + arr.join('&').length;
  for (const n of names) {
    if (cur.length && len([...cur, n]) > CLEAN_PARAM_LIMIT) {
      lines.push(`Clean-param: ${cur.join('&')}`);
      cur = [];
    }
    cur.push(n);
  }
  if (cur.length) lines.push(`Clean-param: ${cur.join('&')}`);
  return lines;
}

/** Содержимое блока между маркерами. */
export function renderBlock(registry) {
  return cleanParamLines(registry.insignificant);
}

/** Переписать блок между маркерами; текст вне блока не трогается. */
export function syncRobots(text, registry) {
  const lines = text.split('\n');
  const from = lines.indexOf(BEGIN);
  const to = lines.indexOf(END);
  if (from === -1 || to === -1 || to < from) {
    throw new Error(`в robots.txt нет маркеров блока Clean-param («${BEGIN}» … «${END}»)`);
  }
  return [...lines.slice(0, from + 1), ...renderBlock(registry), ...lines.slice(to)].join('\n');
}

/** Все параметры, перечисленные в директивах Clean-param файла. */
export function parseCleanParams(text) {
  const out = [];
  for (const line of text.split('\n')) {
    const m = /^\s*Clean-param:\s*(\S+)/i.exec(line);
    if (!m) continue;
    // Второе поле директивы — префикс пути; параметры идут до пробела.
    out.push(...m[1].split('&').filter(Boolean));
  }
  return out;
}

/** Группы User-agent: подряд идущие строки User-agent считаются одной группой. */
export function userAgentGroups(text) {
  const groups = [];
  let cur = null;
  let prevWasAgent = false;
  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const agent = /^User-agent:\s*(\S+)/i.exec(line);
    if (agent) {
      if (!prevWasAgent) {
        cur = { agents: [], directives: [] };
        groups.push(cur);
      }
      cur.agents.push(agent[1]);
      prevWasAgent = true;
      continue;
    }
    prevWasAgent = false;
    if (cur && /^(Allow|Disallow|Crawl-delay):/i.test(line)) cur.directives.push(line);
  }
  return groups;
}

/**
 * Разбор файла: список нарушений по-русски. Пустой список — файл в порядке.
 * Сюда сведены все проверки, которые уже стоили сайту индексации:
 * отдельные группы User-agent (18.09.2026), потерянный Clean-param
 * (15.09.2026), запрет обхода адресов с параметрами (canonical тогда
 * перестаёт работать вовсе).
 */
export function auditRobots(text, registry) {
  const problems = [];
  const params = parseCleanParams(text);

  if (!text.includes(BEGIN) || !text.includes(END)) {
    problems.push('нет маркеров блока Clean-param — блок собирается scripts/seo/robots-sync.mjs');
  } else if (syncRobots(text, registry) !== text) {
    problems.push('блок Clean-param разошёлся с реестром data/seo/url-params.json — соберите заново: pnpm robots:sync');
  }

  const missing = registry.insignificant.filter((p) => !params.includes(p));
  if (missing.length) problems.push(`незначащие параметры не попали в Clean-param: ${missing.join(', ')}`);

  const meaningful = registry.meaningful.filter((p) => params.includes(p));
  if (meaningful.length) {
    problems.push(`в Clean-param попали значащие параметры (робот склеит разные страницы): ${meaningful.join(', ')}`);
  }

  const seen = new Set();
  const dupes = params.filter((p) => (seen.has(p) ? true : (seen.add(p), false)));
  if (dupes.length) problems.push(`параметры повторяются в Clean-param: ${[...new Set(dupes)].join(', ')}`);

  for (const line of text.split('\n')) {
    if (/^\s*Clean-param:/i.test(line) && line.length > CLEAN_PARAM_LIMIT) {
      problems.push(`строка Clean-param длиннее ${CLEAN_PARAM_LIMIT} символов — Яндекс её не прочитает`);
    }
  }

  for (const line of text.split('\n')) {
    const m = /^\s*Disallow:\s*(\S+)/i.exec(line.trim());
    if (m && m[1].includes('?')) {
      problems.push(`запрет «${m[1]}» закрывает обход адресов с параметрами: робот не увидит ни canonical, ни Clean-param`);
    }
  }

  const groups = userAgentGroups(text);
  if (groups.length !== 1) {
    problems.push(`групп User-agent: ${groups.length}. Робот применяет одну подходящую группу целиком, поэтому агенты перечисляются одной группой (разбор 18.09.2026)`);
  }
  const directives = groups.flatMap((g) => g.directives).join('\n');
  for (const path of REQUIRED_DISALLOW) {
    if (!new RegExp(`^\\s*Disallow:\\s*${path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*$`, 'mi').test(directives)) {
      problems.push(`нет запрета на служебный раздел ${path}`);
    }
  }

  if (!/^\s*Sitemap:\s*https:\/\/\S+/mi.test(text)) problems.push('нет строки Sitemap с полным адресом карты сайта');

  return problems;
}

/** Сравнение двух файлов robots.txt без оглядки на переводы строк и хвостовые пробелы. */
export function sameRobots(a, b) {
  const norm = (s) => s.replace(/\r\n/g, '\n').split('\n').map((l) => l.trimEnd()).join('\n').trim();
  return norm(a) === norm(b);
}
