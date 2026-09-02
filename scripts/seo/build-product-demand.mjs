#!/usr/bin/env node
/**
 * Агрегат фактического спроса по карточкам товаров → src/data/product-demand.json.
 *
 * Зачем: фид ранжировался только по спросу вендора из Вордстата, и внутри
 * вендора порядок был алфавитный. Площадка при этом показывает первыми те
 * позиции, что идут первыми в выгрузке. Спрос вендора — оценка рынка, а не
 * нашей витрины: у карточки товара есть собственный измеренный спрос, и он
 * должен решать. Поручение руководителя 02.09.2026 по аудиту Яндекс Бизнеса:
 * «первыми показывать карточки популярных товаров».
 *
 * Источники — свежие суточные выгрузки конвейера (ветка seo-data,
 * накатывается scripts/seo/data_sync.sh):
 *   reports/seo/data/gsc-*.json      → показы и клики страницы /product/<slug>
 *   reports/seo/data/metrika-*.json  → визиты органики на ту же страницу
 * Берётся по одному самому свежему файлу каждого источника: в каждом лежит
 * готовое окно (у Метрики — двухнедельное), и складывать пересекающиеся окна
 * из разных файлов значило бы считать одни и те же визиты дважды.
 *
 * Порог: в файл попадают только карточки со счётом не ниже MIN_SCORE. На
 * единичном визите порядок был бы шумом, а не популярностью; всё, что ниже
 * порога, остаётся на прежнем ранжировании по вендору.
 *
 * Результат коммитится в репозиторий: фид читает готовый JSON и не зависит
 * от наличия выгрузок в рантайме.
 *
 * Запуск: node scripts/seo/build-product-demand.mjs
 */
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const DATA = join(root, 'reports/seo/data');
const TARGET = join(root, 'src/data/product-demand.json');

/** Вклад одного визита, клика и показа в счёт популярности. */
const W_VISIT = 10;
const W_CLICK = 5;
const W_IMPRESSION = 1;
const MIN_SCORE = 3;

function latest(prefix) {
  const files = readdirSync(DATA).filter((f) => f.startsWith(prefix) && f.endsWith('.json')).sort();
  return files.length ? join(DATA, files[files.length - 1]) : null;
}

function slugOf(url) {
  const m = String(url).match(/\/product\/([^/?#]+)/);
  return m ? m[1] : null;
}

const rows = new Map();
const row = (slug) => {
  if (!rows.has(slug)) rows.set(slug, { impressions: 0, clicks: 0, visits: 0 });
  return rows.get(slug);
};

const sources = {};

const gscFile = latest('gsc-');
if (gscFile) {
  const d = JSON.parse(readFileSync(gscFile, 'utf8'));
  const page = d.analytics?.page?.rows || [];
  for (const r of page) {
    const slug = slugOf(r.keys?.[0] || '');
    if (!slug) continue;
    const t = row(slug);
    t.impressions += Number(r.impressions) || 0;
    t.clicks += Number(r.clicks) || 0;
  }
  sources.gsc = { file: gscFile.split('/').pop(), rows: page.length };
}

const metrikaFile = latest('metrika-');
if (metrikaFile) {
  const d = JSON.parse(readFileSync(metrikaFile, 'utf8'));
  const lp = d.organic_landing_pages?.data || [];
  const window = d.organic_landing_pages?.query;
  for (const r of lp) {
    const slug = slugOf(r.dimensions?.[0]?.name || '');
    if (!slug) continue;
    row(slug).visits += Number(r.metrics?.[0]) || 0;
  }
  sources.metrika = {
    file: metrikaFile.split('/').pop(),
    rows: lp.length,
    window: window ? { from: window.date1, to: window.date2 } : null,
  };
}

const scored = [...rows.entries()]
  .map(([slug, t]) => [slug, {
    ...t,
    score: t.visits * W_VISIT + t.clicks * W_CLICK + t.impressions * W_IMPRESSION,
  }])
  .filter(([, t]) => t.score >= MIN_SCORE)
  .sort((a, b) => b[1].score - a[1].score || a[0].localeCompare(b[0]));

writeFileSync(
  TARGET,
  `${JSON.stringify({
    note: ('Измеренный спрос на карточку товара: визиты органики (Метрика) + клики и '
      + 'показы страницы (GSC). Счёт = визиты×10 + клики×5 + показы. Ниже порога '
      + `${MIN_SCORE} карточка в файл не попадает — на единичном визите порядок был бы `
      + 'шумом. Генерируется scripts/seo/build-product-demand.mjs, руками не править.'),
    generated_at: new Date().toISOString(),
    sources,
    weights: { visit: W_VISIT, click: W_CLICK, impression: W_IMPRESSION, min_score: MIN_SCORE },
    products: Object.fromEntries(scored),
  }, null, 1)}\n`,
  'utf8',
);

console.log(`product-demand.json: ${scored.length} карточек со счётом ≥ ${MIN_SCORE}`
  + ` (просмотрено ${rows.size})`);
