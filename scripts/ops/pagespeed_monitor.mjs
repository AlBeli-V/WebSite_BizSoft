/**
 * Наблюдение за скоростью сайта для ежедневного отчёта.
 *
 * Отдельного отчёта о PageSpeed нет и не нужно: замер живёт внутри
 * ежедневного письма как показатель технического здоровья. Этот скрипт —
 * только сбор: он снимает метрики и кладёт их в историю, а трактовку
 * (пороги, регрессии, приоритеты) делает scripts/seo/technical.py.
 *
 * Два уровня контроля. Ежедневно меряются три представителя основных
 * шаблонов — весь сайт гонять нельзя, на нём 711 адресов. Раз в неделю
 * снимается расширенная выборка из двенадцати страниц: она показывает, какой
 * шаблон просел, чего дневная тройка увидеть не может.
 *
 * Экономия вызовов заложена в трёх местах: дневной замер — один прогон
 * mobile; недельный — медиана трёх прогонов (Lighthouse шумит, одиночный
 * замер даёт ложные тревоги); повторный запрос той же страницы за тот же
 * период не делается, если результат уже в истории.
 *
 * Запуск:
 *   node scripts/ops/pagespeed_monitor.mjs [--mode daily|weekly|auto] [--force]
 *
 * Окружение: PSI_API_KEY (ключ), PSI_RAW_DIR (куда класть сырые ответы).
 * Скрипт не падает при недоступности PSI: он записывает состояние
 * "unavailable" с причиной, чтобы отчёт вышел и честно сказал об этом.
 */
import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { runPagespeed, score, metric, fieldData } from './psi_client.mjs';

const CONFIG = 'config/pagespeed-monitor.json';
const HISTORY_DIR = 'reports/seo/pagespeed/history';
const LATEST = 'reports/seo/pagespeed/latest.json';

const arg = (name, fallback = '') => {
  const i = process.argv.indexOf(name);
  return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
};
const has = (name) => process.argv.includes(name);

const cfg = JSON.parse(readFileSync(CONFIG, 'utf8'));
const BASE = cfg.base.replace(/\/$/, '');
const RAW_DIR = process.env.PSI_RAW_DIR || '';

/** Дата по Москве: отчёт живёт в московских сутках, история — тоже. */
function today() {
  return new Date().toLocaleDateString('sv-SE', { timeZone: 'Europe/Moscow' });
}

/** День недели по Москве, 1 = понедельник. */
function weekday() {
  const d = new Date().toLocaleDateString('en-US', {
    timeZone: 'Europe/Moscow', weekday: 'short',
  });
  return ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].indexOf(d) + 1;
}

/** Медиана — устойчива к одиночному выбросу Lighthouse, в отличие от среднего. */
function median(values) {
  const v = values.filter((x) => x != null).sort((a, b) => a - b);
  if (!v.length) return null;
  const mid = Math.floor(v.length / 2);
  return v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2;
}

/** Метрики одного ответа PSI в плоском виде. */
function extract(data) {
  const lh = data.lighthouseResult || {};
  return {
    performance: score(lh, 'performance'),
    seo: score(lh, 'seo'),
    accessibility: score(lh, 'accessibility'),
    best_practices: score(lh, 'best-practices'),
    lcp_ms: metric(lh, 'largest-contentful-paint'),
    cls: metric(lh, 'cumulative-layout-shift'),
    tbt_ms: metric(lh, 'total-blocking-time'),
    fcp_ms: metric(lh, 'first-contentful-paint'),
    speed_index_ms: metric(lh, 'speed-index'),
    lighthouse_version: lh.lighthouseVersion || null,
    field: fieldData(data),
  };
}

/** Сведение нескольких прогонов одной страницы: по каждой метрике медиана. */
function combine(runs) {
  const num = (k) => median(runs.map((r) => r[k]));
  const last = runs[runs.length - 1];
  return {
    performance: num('performance') == null ? null : Math.round(num('performance')),
    seo: num('seo') == null ? null : Math.round(num('seo')),
    accessibility: num('accessibility') == null ? null : Math.round(num('accessibility')),
    best_practices: num('best_practices') == null ? null : Math.round(num('best_practices')),
    lcp_ms: num('lcp_ms'),
    cls: num('cls'),
    tbt_ms: num('tbt_ms'),
    fcp_ms: num('fcp_ms'),
    speed_index_ms: num('speed_index_ms'),
    lighthouse_version: last.lighthouse_version,
    field: last.field,
    runs: runs.length,
  };
}

async function measure(entry, strategy, runs) {
  const url = BASE + entry.path;
  const results = [];
  let error = null;
  for (let i = 0; i < runs; i++) {
    try {
      const data = await runPagespeed(url, strategy, {
        categories: ['performance', 'seo', 'accessibility', 'best-practices'],
      });
      if (RAW_DIR) {
        const file = join(RAW_DIR,
          `${entry.path.replace(/\W+/g, '_') || 'root'}-${strategy}-${i + 1}.json`);
        mkdirSync(dirname(file), { recursive: true });
        writeFileSync(file, JSON.stringify(data));
      }
      results.push(extract(data));
    } catch (e) {
      error = e.message;
      break;
    }
  }
  if (!results.length) {
    return { path: entry.path, pageType: entry.pageType, strategy, error };
  }
  return {
    path: entry.path,
    pageType: entry.pageType,
    strategy,
    fieldDataAvailable: Boolean(results[results.length - 1].field),
    ...combine(results),
    ...(error ? { partial_error: error } : {}),
  };
}

async function main() {
  const date = today();
  const mode = (() => {
    const m = arg('--mode', 'auto');
    if (m !== 'auto') return m;
    return weekday() === (cfg.weekly.weekday || 6) ? 'weekly' : 'daily';
  })();
  const plan = mode === 'weekly' ? cfg.weekly : cfg.daily;
  const strategies = plan.strategy === 'both' ? ['mobile', 'desktop'] : [plan.strategy];

  // Дедупликация: замер за сегодня в том же режиме уже есть — второй раз
  // квоту не тратим. Ключ — дата и режим, а не отдельные страницы: набор
  // страниц режима фиксирован конфигурацией.
  const file = join(HISTORY_DIR, `${date}.json`);
  if (existsSync(file) && !has('--force')) {
    const prev = JSON.parse(readFileSync(file, 'utf8'));
    if (prev.mode === mode && (prev.pages || []).length) {
      console.log(`пропуск: замер за ${date} в режиме ${mode} уже есть ` +
                  `(${prev.pages.length} страниц); повтор — с --force`);
      return;
    }
  }

  const pages = [];
  let requests = 0;
  for (const entry of plan.urls) {
    for (const strategy of strategies) {
      // Три прогона нужны только мобильной стратегии: по ней принимаются
      // решения. Desktop снимается одним прогоном — он справочный.
      const runs = strategy === 'mobile' ? (plan.runs || 1) : 1;
      const r = await measure(entry, strategy, runs);
      requests += r.error ? 1 : (r.runs || 1);
      pages.push(r);
      console.log(`${entry.path} [${strategy}] ` +
        (r.error ? `ошибка: ${r.error}` : `perf ${r.performance}, LCP ${Math.round(r.lcp_ms || 0)} мс`));
    }
  }

  const measured = pages.filter((p) => !p.error);
  const payload = {
    schema_version: '1.0.0',
    date,
    mode,
    measured_at: new Date().toISOString(),
    status: measured.length ? 'ok' : 'unavailable',
    ...(measured.length ? {} : { reason: pages[0]?.error || 'PSI не ответил' }),
    requests,
    pages,
  };

  mkdirSync(HISTORY_DIR, { recursive: true });
  writeFileSync(file, JSON.stringify(payload, null, 1) + '\n');
  // latest.json обновляется только удачным замером: иначе сбой PSI стёр бы
  // последний известный результат, и отчёт лишился бы точки сравнения.
  if (measured.length) {
    mkdirSync(dirname(LATEST), { recursive: true });
    writeFileSync(LATEST, JSON.stringify(payload, null, 1) + '\n');
  }
  console.log(`режим ${mode}: страниц ${pages.length}, замеров ${requests}, ` +
              `состояние ${payload.status} -> ${file}`);
}

await main();
