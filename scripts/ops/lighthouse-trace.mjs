/**
 * Прогон Lighthouse по страницам прода прямо на раннере, с разбором трассы.
 *
 * Зачем отдельно от pagespeed.mjs: PageSpeed Insights отдаёт только сводку.
 * Когда метрика не вычисляется (NO_LCP — «у страницы нет кандидата Largest
 * Contentful Paint»), из сводки не видно, кандидатов не было вовсе или
 * последний был отозван и чем. Ответ лежит в событиях трассы
 * largestContentfulPaint::Candidate и ::Invalidate — их и печатает этот
 * скрипт. Заодно замер повторяемый: PSI на общей инфраструктуре Google
 * сильно шумит (один и тот же раздел каталога давал 95 и 76 подряд).
 *
 * Окружение:
 *   URLS       пути через запятую (по умолчанию главная)
 *   BASE       https://biz-soft.pro
 *   RUNS       сколько прогонов на страницу (по умолчанию 1), печатается медиана
 *   FORM       mobile (по умолчанию) | desktop
 *
 * Требует установленного пакета lighthouse и Chrome на машине:
 *   npm install --no-save lighthouse@13
 *
 * Код выхода 1, если хотя бы один прогон не дал балла.
 */
import { mkdtempSync, readdirSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';

const BASE = (process.env.BASE || 'https://biz-soft.pro').replace(/\/$/, '');
const paths = (process.env.URLS || '/').split(',').map((s) => s.trim()).filter(Boolean);
const RUNS = Math.max(1, Number(process.env.RUNS || 1));
const FORM = process.env.FORM === 'desktop' ? 'desktop' : 'mobile';

const short = (u) => String(u || '').replace(BASE, '') || '/';
const median = (xs) => {
  const s = [...xs].sort((a, b) => a - b);
  return s.length % 2 ? s[(s.length - 1) / 2] : Math.round((s[s.length / 2 - 1] + s[s.length / 2]) / 2);
};

/** Один прогон Lighthouse; возвращает отчёт и события LCP из трассы. */
function run(url, dir, i) {
  const out = join(dir, `run-${i}`);
  const args = [
    'lighthouse', url,
    '--only-categories=performance',
    `--form-factor=${FORM}`,
    FORM === 'mobile' ? '--screenEmulation.mobile' : '--screenEmulation.disabled',
    '--output=json', `--output-path=${out}.report.json`,
    '--save-assets', '--quiet',
    '--chrome-flags=--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage',
  ];
  const r = spawnSync('npx', args, { cwd: dir, encoding: 'utf8', maxBuffer: 512 * 1024 * 1024 });
  if (r.status !== 0) throw new Error(`lighthouse завершился с кодом ${r.status}: ${(r.stderr || '').slice(-400)}`);
  const report = JSON.parse(readFileSync(`${out}.report.json`, 'utf8'));
  // --save-assets кладёт трассу рядом с отчётом, добавляя к имени номер
  // прогона: run-1.report.json → run-1.report-0.trace.json.
  let lcpEvents = [];
  try {
    const traceFile = readdirSync(dir).find((f) => f.startsWith(`run-${i}.report`) && f.endsWith('.trace.json'));
    if (!traceFile) throw new Error('файл трассы не найден в каталоге прогона');
    const trace = JSON.parse(readFileSync(join(dir, traceFile), 'utf8'));
    const events = trace.traceEvents || trace;
    lcpEvents = events
      .filter((e) => e.name === 'largestContentfulPaint::Candidate' || e.name === 'largestContentfulPaint::Invalidate')
      .map((e) => ({ name: e.name.replace('largestContentfulPaint::', ''), ts: e.ts, size: e.args?.data?.size, type: e.args?.data?.type, frame: e.args?.frame }))
      .sort((a, b) => a.ts - b.ts);
  } catch (e) {
    lcpEvents = [{ name: 'трасса не прочитана', note: e.message }];
  }
  return { report, lcpEvents };
}

let failed = 0;
const summary = [];
for (const p of paths) {
  const url = BASE + p;
  const dir = mkdtempSync(join(tmpdir(), 'lh-'));
  const scores = [];
  try {
    for (let i = 1; i <= RUNS; i++) {
      const { report, lcpEvents } = run(url, dir, i);
      const a = report.audits;
      const raw = report.categories.performance.score;
      const score = raw == null ? null : Math.round(raw * 100);
      if (score == null) failed++; else scores.push(score);
      console.log(`── ${short(url)} [${FORM}] прогон ${i}/${RUNS} — ${score == null ? 'балл не вычислен' : `балл ${score}`}`);
      console.log('  ' + [['FCP', 'first-contentful-paint'], ['LCP', 'largest-contentful-paint'], ['TBT', 'total-blocking-time'], ['CLS', 'cumulative-layout-shift'], ['SI', 'speed-index']]
        .map(([n, k]) => `${n} ${a[k]?.displayValue ?? '—'}`).join(' · '));
      if (a['largest-contentful-paint']?.scoreDisplayMode === 'error') console.log(`  LCP не вычислен: ${a['largest-contentful-paint'].errorMessage}`);
      const el = a['largest-contentful-paint-element']?.details?.items?.[0]?.items?.[0]?.node;
      if (el) console.log(`  LCP-элемент: ${el.selector} — «${(el.nodeLabel || '').slice(0, 70)}»`);
      // Главное: события LCP из трассы — кандидат или отзыв, в порядке времени.
      const t0 = lcpEvents.length ? lcpEvents[0].ts : 0;
      console.log(`  события LCP в трассе: ${lcpEvents.length}`);
      for (const e of lcpEvents.slice(0, 12)) {
        console.log(`    ${e.name}${e.ts ? ` +${Math.round((e.ts - t0) / 1000)} мс` : ''}${e.size ? ` размер ${e.size}` : ''}${e.type ? ` (${e.type})` : ''}${e.note ? ` ${e.note}` : ''}`);
      }
      if (lcpEvents.length && lcpEvents[lcpEvents.length - 1].name === 'Invalidate') {
        console.log('    → последнее событие — отзыв кандидата: страница показала контент и затем его убрала или изменила');
      }
      console.log('');
    }
  } catch (e) {
    failed++;
    console.log(`── ${short(url)} [${FORM}] — прогон не удался: ${e.message}\n`);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
  summary.push(`${short(url)} ${scores.length ? median(scores) : 'нет балла'}${RUNS > 1 && scores.length ? ` (из ${scores.join('/')})` : ''}`);
}
console.log('Итог (медиана): ' + summary.join(' · ') + (failed ? ` · проблемных прогонов: ${failed}` : ''));
process.exit(failed ? 1 : 0);
