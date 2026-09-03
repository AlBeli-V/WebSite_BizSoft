/**
 * Храповик против потери статуса прогона в воркфлоу.
 *
 * Аудит 03.09.2026: статус прогона терялся на трёх уровнях подряд —
 * `|| true` вокруг основного скрипта, `exit 0` после «токен не найден»,
 * шаг «Post to issue» с `if: always()`, который печатает вывод под штатным
 * заголовком без `steps.*.outcome`, и шаги журнала без `always()`, которые
 * при падении молчат, хотя «тишина = порядок» в проекте принято. Так
 * ops-yandex-recrawl отдавал зелёный прогон и запись «переобход запрошен»
 * при HTTP 429 по каждому URL.
 *
 * Правила простые и текстовые — их можно прочитать за минуту. Существующие
 * нарушения записаны в data/reports/workflow-lint-baseline.json; тест
 * падает, когда в файле нарушений по правилу становится больше, чем в
 * базе. База обновляется только вниз: WORKFLOW_LINT_WRITE_BASELINE=1 pnpm
 * test перезаписывает её текущим состоянием, и в PR это видно как диф.
 */
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(__dirname, '..');
const dir = resolve(root, '.github/workflows');
const baselinePath = resolve(root, 'data/reports/workflow-lint-baseline.json');

export const RULES: Record<string, string> = {
  R1: '`|| true` после вызова скрипта или push — сбой не влияет на статус прогона',
  R2: '`exit 0` после «не найден/не задан» — отсутствие секрета выглядит успехом',
  R3: 'шаг журнала с `if: always()` не смотрит на `steps.*.outcome` — упавший шаг публикуется как штатный',
  R4: 'шаг журнала без `if: always()` — при падении в журнал не попадает ничего',
  R5: '`curl` за телом ответа без проверки кода (`-f`/`--fail`/`http_code`); запросы заголовков (-I/-D -) не считаются',
  R6: 'локальный action `journal-post` без `actions/checkout` — раннер его не находит, и шаг журнала падает',
  R7: '`actions/checkout` при явном `permissions:` без `contents: read` — токен не читает репозиторий, checkout падает с «Repository not found»',
};

type Counts = Record<string, number>;

function isComment(line: string): boolean {
  return /^\s*#/.test(line);
}

/** Разбить файл на шаги по строкам `- name:`; каждый шаг — набор строк. */
function steps(lines: string[]): string[][] {
  const out: string[][] = [];
  let current: string[] | null = null;
  for (const line of lines) {
    if (/^\s*-\s+name:/.test(line)) {
      if (current) out.push(current);
      current = [line];
    } else if (current) {
      current.push(line);
    }
  }
  if (current) out.push(current);
  return out;
}

export function lint(text: string): Counts {
  const lines = text.split('\n');
  const counts: Counts = { R1: 0, R2: 0, R3: 0, R4: 0, R5: 0, R6: 0, R7: 0 };

  lines.forEach((line, index) => {
    if (isComment(line)) return;
    // Маскировка — это `|| true` после вызова скрипта, инструмента или push.
    // Диагностика вида `grep -c … || true`, `docker system df || true`,
    // `cp … || true` статус не подменяет: там нечего маскировать.
    if (/(python3|node|bash|pnpm|npx|gh|git push|git pull|data_sync\.sh|docker compose (exec|up|run))\b[^|\n]*\|\|\s*true\b/.test(line)) counts.R1 += 1;
    if (/curl\s/.test(line) && !/(\s-f\b|--fail|-sf\b|-fsS|-fS|-sSf|http_code|-w\s|\s-s?S?I\b|-D\s-)/.test(line)) {
      counts.R5 += 1;
    }
    if (/не найден|не задан|NOT FOUND|отсутству/i.test(line)) {
      const window = lines.slice(index, index + 5).filter((l) => !isComment(l));
      if (window.some((l) => /(^|;|&&)\s*exit 0\b/.test(l))) counts.R2 += 1;
    }
  });

  // Локальный action едет с репозиторием: без checkout раннер не находит
  // action.yml, и журнал молчит — так 03.09.2026 упали 32 ops-воркфлоу
  // сразу после перевода на journal-post.
  const code = lines.filter((l) => !isComment(l)).join('\n');
  if (/uses:\s*\.\/\.github\/actions\/journal-post/.test(code) && !/uses:\s*actions\/checkout@/.test(code)) counts.R6 += 1;
  // Явный блок permissions обнуляет всё неперечисленное: без contents токен
  // не читает репозиторий, и checkout падает — так упал прогон #204 ops-probe
  // сразу после добавления checkout.
  if (/uses:\s*actions\/checkout@/.test(code) && /^\s*permissions:/m.test(code) && !/^\s+contents:\s*(read|write)\b/m.test(code)) counts.R7 += 1;

  for (const step of steps(lines)) {
    const body = step.join('\n');
    const postsToJournal = /createComment|issues\.create|issue_number:\s*22/.test(body);
    if (!postsToJournal) continue;
    const always = /if:\s*always\(\)/.test(body);
    const hasIf = /^\s*if:/m.test(body);
    if (always && !/\.outcome\b/.test(body)) counts.R3 += 1;
    if (!hasIf) counts.R4 += 1;
  }
  return counts;
}

function scan(): Record<string, Counts> {
  const result: Record<string, Counts> = {};
  for (const name of readdirSync(dir).filter((n) => n.endsWith('.yml')).sort()) {
    const counts = lint(readFileSync(resolve(dir, name), 'utf8'));
    if (Object.values(counts).some((n) => n > 0)) result[name] = counts;
  }
  return result;
}

describe('срок годности одноразовых воркфлоу', () => {
  it('файл с истёкшим `# expires:` перенесён в .github/workflows-archive/ или продлён', () => {
    const today = new Date().toISOString().slice(0, 10);
    const expired: string[] = [];
    for (const name of readdirSync(dir).filter((n) => n.endsWith('.yml'))) {
      const m = readFileSync(resolve(dir, name), 'utf8').match(/^#\s*expires:\s*(\d{4}-\d{2}-\d{2})/m);
      if (m && m[1] < today) expired.push(`${name}: срок ${m[1]} вышел`);
    }
    expect(expired).toEqual([]);
  });
});

describe('линт воркфлоу: статус прогона не теряется', () => {
  const current = scan();

  it('база нарушений существует и разбирается', () => {
    if (process.env.WORKFLOW_LINT_WRITE_BASELINE === '1') {
      writeFileSync(baselinePath, JSON.stringify({ rules: RULES, files: current }, null, 2) + '\n');
    }
    const baseline = JSON.parse(readFileSync(baselinePath, 'utf8'));
    expect(baseline.files).toBeTypeOf('object');
  });

  it('новых нарушений нет — по каждому файлу и правилу не больше, чем в базе', () => {
    const baseline = JSON.parse(readFileSync(baselinePath, 'utf8')).files as Record<string, Counts>;
    const grown: string[] = [];
    const shrunk: string[] = [];
    for (const [file, counts] of Object.entries(current)) {
      for (const [rule, n] of Object.entries(counts)) {
        const was = baseline[file]?.[rule] ?? 0;
        if (n > was) grown.push(`${file} ${rule}: было ${was}, стало ${n} — ${RULES[rule]}`);
        if (n < was) shrunk.push(`${file} ${rule}: было ${was}, стало ${n}`);
      }
    }
    for (const [file, counts] of Object.entries(baseline)) {
      for (const [rule, was] of Object.entries(counts)) {
        if (was > 0 && (current[file]?.[rule] ?? 0) === 0) shrunk.push(`${file} ${rule}: было ${was}, стало 0`);
      }
    }
    if (shrunk.length) {
      console.log('Нарушений стало меньше — обновите базу: WORKFLOW_LINT_WRITE_BASELINE=1 pnpm test\n  ' + shrunk.join('\n  '));
    }
    expect(grown, 'Новые нарушения:\n  ' + grown.join('\n  ')).toEqual([]);
  });
});
