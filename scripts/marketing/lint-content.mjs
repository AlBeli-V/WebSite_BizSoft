#!/usr/bin/env node
/**
 * Линтер материалов BIZSoft: машинная часть правил из
 * `.claude/skills/bizsoft-content/SKILL.md` и журнала ревью
 * `docs/marketing/content-library/lessons.md`.
 *
 * Запуск: node scripts/marketing/lint-content.mjs <файл.md> [ещё файлы]
 * Код возврата 1, если есть ошибки (warning не валит проверку).
 *
 * Проверяется текст материала — часть файла после строки-разделителя `---`.
 * Служебная шапка (карточка материала) не проверяется: в ней правила
 * обсуждаются, а не нарушаются.
 */
import { readFileSync } from 'node:fs';

/** Обобщения без источника — правило 1 журнала ревью. */
const GENERALIZATIONS = [
  'в большинстве компаний', 'большинство компаний', 'в большинстве случаев',
  'чаще всего', 'почти всегда', 'как правило,', 'регулярно оказывается',
  'обычно это', 'всем известно', 'ни для кого не секрет',
];

/** Абсолюты — правило 2 журнала ревью. */
const ABSOLUTES = [
  'невозможно', 'не может заплатить', 'платёж не пройдёт', 'не примет',
  'нельзя оплатить', 'единственный способ', 'не выставит', 'никогда не',
  'гарантирова',
];

/** Самореклама — раздел «не пишем» навыка. */
const PROMO = [
  'лучший', 'лучшая', 'лучшие', 'надёжный партнёр', 'выгодные условия',
  'широкий спектр', 'индивидуальный подход', 'команда профессионалов',
  'уникальное предложение',
];

const CLICKBAIT = ['шок', 'вся правда', 'никто не знает', 'сенсаци'];

const LIMITS = { minChars: 5000, maxChars: 9000, maxLinks: 2 };

function textOf(md) {
  const i = md.indexOf('\n---\n');
  const body = i === -1 ? md : md.slice(i + 5);
  return body.trim();
}

/** Знаки без markdown-разметки — то, что увидит читатель. */
function plain(body) {
  return body
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/[*_`#>]/g, '')
    .trim();
}

function findAll(hay, needles) {
  const low = hay.toLowerCase();
  return needles.filter((n) => low.includes(n));
}

function lint(file) {
  const md = readFileSync(file, 'utf8');
  const body = textOf(md);
  const text = plain(body);
  const errors = [];
  const warnings = [];
  const notes = [];

  // Объём
  const chars = text.length;
  if (chars < LIMITS.minChars) warnings.push(`объём ${chars} знаков — ниже ориентира ${LIMITS.minChars}`);
  else if (chars > LIMITS.maxChars) warnings.push(`объём ${chars} знаков — выше ориентира ${LIMITS.maxChars}; оправдано, только если этого требует полнота ответа`);
  else notes.push(`объём ${chars} знаков — в ориентире`);

  // Ссылки
  const links = [...body.matchAll(/\]\((https?:\/\/[^)]+)\)/g)].map((m) => m[1]);
  const own = links.filter((u) => u.includes('biz-soft.pro'));
  const foreign = links.filter((u) => !u.includes('biz-soft.pro'));
  if (own.length > LIMITS.maxLinks) errors.push(`ссылок на biz-soft.pro: ${own.length}, потолок ${LIMITS.maxLinks}`);
  else notes.push(`ссылок на сайт: ${own.length}`);
  if (foreign.length) warnings.push(`внешние ссылки (${foreign.length}): ${foreign.join(', ')}`);

  // Ссылка не в первом экране: первые ~1500 знаков
  const firstLink = body.search(/\]\(https?:\/\/[^)]*biz-soft\.pro/);
  if (own.length && firstLink !== -1 && plain(body.slice(0, firstLink)).length < 1500) {
    errors.push('первая ссылка на сайт стоит в первом экране материала');
  }

  // Запрещённые обороты
  const g = findAll(text, GENERALIZATIONS);
  if (g.length) errors.push(`обобщения без источника: ${g.join(', ')}`);
  const a = findAll(text, ABSOLUTES);
  if (a.length) errors.push(`абсолюты (смягчить): ${a.join(', ')}`);
  const p = findAll(text, PROMO);
  if (p.length) errors.push(`рекламные обороты: ${p.join(', ')}`);
  // Кликбейт важен в карточке: заголовок и начало текста, а не весь материал.
  const c = findAll(text.slice(0, 600), CLICKBAIT);
  if (c.length) errors.push(`кликбейт в заголовке или начале: ${c.join(', ')}`);

  // Цены цифрами
  const prices = text.match(/\d[\d\s]{2,}\s?(₽|руб|рублей)/gi);
  if (prices) errors.push(`цены в тексте: ${[...new Set(prices)].join(', ')} — называем принцип расчёта, не цифры`);

  // Структурные признаки
  if (!/BIZSoft/.test(text)) warnings.push('нет упоминания BIZSoft — аффилиация должна быть раскрыта');
  const brandMentions = (text.match(/BIZSoft/g) || []).length;
  if (brandMentions > 3) warnings.push(`BIZSoft упомянут ${brandMentions} раза — достаточно двух-трёх`);
  // Вопрос читателю ищем в хвосте: после него обычно идёт подпись канала.
  const tail = body.split('\n').filter(Boolean).slice(-8).join(' ');
  if (!tail.includes('?')) warnings.push('в конце нет вопроса читателю');
  const h = (body.match(/^#{2,3} /gm) || []).length;
  if (h < 4) warnings.push(`подзаголовков ${h} — материал плохо сканируется`);

  return { file, chars, errors, warnings, notes };
}

const files = process.argv.slice(2);
if (!files.length) {
  console.error('Использование: node scripts/marketing/lint-content.mjs <файл.md> [...]');
  process.exit(2);
}

let failed = false;
for (const f of files) {
  const r = lint(f);
  console.log(`\n${r.file}`);
  r.errors.forEach((e) => console.log(`  ✗ ${e}`));
  r.warnings.forEach((w) => console.log(`  ! ${w}`));
  r.notes.forEach((n) => console.log(`  · ${n}`));
  if (!r.errors.length && !r.warnings.length) console.log('  ✓ замечаний нет');
  if (r.errors.length) failed = true;
}
process.exit(failed ? 1 : 0);
