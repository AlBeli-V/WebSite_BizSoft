/**
 * Замер PageSpeed Insights (Lighthouse Google) по страницам прода.
 *
 * Зачем скрипт: сессия ассистента не достаёт до biz-soft.pro, а анонимная
 * квота PSI API общая на всех и часто исчерпана (429). Раннер GitHub с
 * ключом PSI_API_KEY (Google Cloud → PageSpeed Insights API, бесплатно)
 * снимает тот же отчёт, что pagespeed.web.dev, и кладёт в журнал (issue #22).
 *
 * Окружение:
 *   URLS         пути через запятую (по умолчанию главная, раздел, карточка)
 *   STRATEGY     mobile | desktop | both (по умолчанию mobile)
 *   PSI_API_KEY  ключ API (необязателен; без ключа — общая квота)
 *   BASE         https://biz-soft.pro
 *
 * Вывод: балл, метрики лаборатории, полевые данные CrUX (если есть) и
 * аудиты с потерями. Код выхода 1, если хотя бы один замер не удался.
 */
const BASE = (process.env.BASE || 'https://biz-soft.pro').replace(/\/$/, '');
const paths = (process.env.URLS || '/,/catalog/ai,/product/chatgpt-business').split(',').map((s) => s.trim()).filter(Boolean);
const strategies = (process.env.STRATEGY || 'mobile') === 'both' ? ['mobile', 'desktop'] : [process.env.STRATEGY || 'mobile'];
const KEY = process.env.PSI_API_KEY || '';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function psi(url, strategy) {
  const q = new URLSearchParams({ url, strategy, category: 'performance', locale: 'ru' });
  if (KEY) q.set('key', KEY);
  const api = `https://www.googleapis.com/pagespeedonline/v5/runPagespeed?${q}`;
  let last;
  for (let attempt = 1; attempt <= 3; attempt++) {
    const res = await fetch(api, { signal: AbortSignal.timeout(120_000) });
    const body = await res.json().catch(() => ({}));
    if (res.ok) return body;
    last = `HTTP ${res.status}: ${body?.error?.message || res.statusText}`;
    if (res.status !== 429 && res.status < 500) break;
    await sleep(attempt * 15_000);
  }
  throw new Error(last);
}

const zone = (s) => (s >= 90 ? 'зелёная' : s >= 50 ? 'жёлтая' : 'красная');
const ms = (v) => (v == null ? '—' : v >= 1000 ? `${(v / 1000).toFixed(1)} с` : `${Math.round(v)} мс`);

function report(url, strategy, data) {
  const lh = data.lighthouseResult;
  const a = lh.audits;
  const score = Math.round((lh.categories.performance.score ?? 0) * 100);
  const out = [];
  out.push(`── ${url} [${strategy}] — балл ${score} (${zone(score)} зона), Lighthouse ${lh.lighthouseVersion}`);
  const metrics = [
    ['FCP', 'first-contentful-paint'], ['LCP', 'largest-contentful-paint'], ['TBT', 'total-blocking-time'],
    ['CLS', 'cumulative-layout-shift'], ['SI', 'speed-index'], ['TTFB', 'server-response-time'],
  ];
  out.push('  лаборатория: ' + metrics.map(([n, k]) => `${n} ${a[k]?.displayValue ?? '—'}`).join(' · '));
  const lcpEl = a['largest-contentful-paint-element']?.details?.items?.[0]?.items?.[0]?.node;
  if (lcpEl) out.push(`  LCP-элемент: ${lcpEl.selector} — «${(lcpEl.nodeLabel || '').slice(0, 80)}»`);
  const field = data.loadingExperience?.metrics;
  if (field && data.loadingExperience?.overall_category) {
    const f = (k) => field[k] ? `${field[k].percentile}${k === 'CUMULATIVE_LAYOUT_SHIFT_SCORE' ? '' : ' мс'} (${field[k].category})` : '—';
    out.push(`  поле (CrUX, ${data.loadingExperience.overall_category}): LCP ${f('LARGEST_CONTENTFUL_PAINT_MS')} · INP ${f('INTERACTION_TO_NEXT_PAINT')} · CLS ${f('CUMULATIVE_LAYOUT_SHIFT_SCORE')}`);
  } else {
    out.push('  поле (CrUX): нет данных — трафика недостаточно для выборки');
  }
  const losses = Object.values(a)
    .filter((x) => x.score != null && x.score < 1 && !/^(first-contentful|largest-contentful|total-blocking|cumulative-layout|speed-index|interactive|max-potential)/.test(x.id))
    .map((x) => ({ id: x.id, score: x.score, note: x.displayValue || '', save: x.details?.overallSavingsMs || 0, bytes: x.details?.overallSavingsBytes || 0 }))
    .sort((p, q) => q.save - p.save || q.bytes - p.bytes || p.score - q.score);
  if (losses.length) {
    out.push('  аудиты с потерями:');
    for (const l of losses.slice(0, 12)) out.push(`    ${l.id} (${l.score}) ${l.note}${l.save ? ` — до ${ms(l.save)}` : ''}`);
  }
  const third = a['third-party-summary']?.details?.items || [];
  if (third.length) out.push('  сторонние: ' + third.slice(0, 5).map((t) => `${t.entity?.text || t.entity} ${Math.round(t.blockingTime)} мс блокировки, ${Math.round(t.transferSize / 1024)} КБ`).join(' · '));
  return { score, text: out.join('\n') };
}

let failed = 0;
const scores = [];
for (const p of paths) {
  const url = BASE + p;
  for (const s of strategies) {
    try {
      const data = await psi(url, s);
      const r = report(url, s, data);
      scores.push(`${p} [${s}] ${r.score}`);
      console.log(r.text);
    } catch (e) {
      failed++;
      console.log(`── ${url} [${s}] — замер не удался: ${e.message}`);
    }
    console.log('');
  }
}
console.log('Итог: ' + (scores.join(' · ') || 'нет замеров') + (failed ? ` · не удалось: ${failed}` : ''));
process.exit(failed ? 1 : 0);
