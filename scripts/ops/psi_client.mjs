/**
 * Общий клиент PageSpeed Insights v5.
 *
 * Запрос к PSI жил внутри scripts/ops/pagespeed.mjs. Наблюдение за скоростью
 * в ежедневном отчёте берёт тот же вызов, поэтому он вынесен сюда: два места
 * с собственными ретраями и таймаутами разошлись бы через месяц.
 *
 * Ретраи только там, где они осмысленны: 429 (квота) и 5xx (сбой на стороне
 * Google) повторяются с растущей паузой, 4xx повторять бессмысленно — ответ
 * не изменится. Таймаут обязателен: PSI на тяжёлой странице отвечает минуту
 * с лишним, а зависший запрос в прогоне дороже неудачного.
 */
const API = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed';
const DEFAULT_CATEGORIES = ['performance'];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Один замер PSI.
 *
 * @param {string} url          полный адрес страницы
 * @param {string} strategy     mobile | desktop
 * @param {object} [opts]
 * @param {string[]} [opts.categories] категории Lighthouse
 * @param {string} [opts.key]          ключ API (без него — общая квота)
 * @param {number} [opts.attempts]     сколько раз пробовать при 429/5xx
 * @param {number} [opts.timeoutMs]    таймаут одного запроса
 * @param {number} [opts.backoffMs]    база паузы между попытками
 * @returns {Promise<object>} тело ответа PSI
 */
export async function runPagespeed(url, strategy, opts = {}) {
  const {
    categories = DEFAULT_CATEGORIES,
    key = process.env.PSI_API_KEY || '',
    attempts = 3,
    timeoutMs = 120_000,
    backoffMs = 15_000,
  } = opts;

  const q = new URLSearchParams({ url, strategy, locale: 'ru' });
  for (const c of categories) q.append('category', c);
  if (key) q.set('key', key);

  let last;
  for (let attempt = 1; attempt <= attempts; attempt++) {
    let res;
    try {
      res = await fetch(`${API}?${q}`, { signal: AbortSignal.timeout(timeoutMs) });
    } catch (e) {
      // Обрыв и таймаут — того же класса, что 5xx: повторяем.
      last = `сеть: ${e.name === 'TimeoutError' ? `таймаут ${timeoutMs} мс` : e.message}`;
      if (attempt < attempts) await sleep(attempt * backoffMs);
      continue;
    }
    const body = await res.json().catch(() => ({}));
    if (res.ok) return body;
    last = `HTTP ${res.status}: ${body?.error?.message || res.statusText}`;
    if (res.status !== 429 && res.status < 500) break;
    if (attempt < attempts) await sleep(attempt * backoffMs);
  }
  throw new Error(last);
}

/** Балл категории в целых очках (PSI отдаёт долю 0..1). */
export function score(lh, category) {
  const v = lh?.categories?.[category]?.score;
  return v == null ? null : Math.round(v * 100);
}

/** Числовое значение аудита лаборатории (миллисекунды или безразмерное CLS). */
export function metric(lh, audit) {
  const v = lh?.audits?.[audit]?.numericValue;
  return v == null ? null : v;
}

/**
 * Полевые данные CrUX. Их отсутствие — не ошибка: у страниц с малым трафиком
 * Google просто не набирает выборку, и замер лаборатории остаётся валидным.
 */
export function fieldData(data) {
  const m = data?.loadingExperience?.metrics;
  if (!m) return null;
  const pick = (k) => (m[k]?.percentile == null ? null : m[k].percentile);
  const cls = pick('CUMULATIVE_LAYOUT_SHIFT_SCORE');
  return {
    lcp_ms: pick('LARGEST_CONTENTFUL_PAINT_MS'),
    inp_ms: pick('INTERACTION_TO_NEXT_PAINT'),
    cls: cls == null ? null : cls / 100,
  };
}
