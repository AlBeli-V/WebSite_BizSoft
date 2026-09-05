/**
 * Цена и курс валюты не живут в тексте страницы.
 *
 * Рублёвая цена на витрине считается штатно (`computePegRub`: себестоимость в
 * валюте × курс ЦБ × коэффициент) и переоценивается ежедневно воркфлоу
 * ops-currency-refresh. Любая цифра цены или курса, вписанная в текст руками,
 * назавтра расходится с витриной и вводит покупателя в заблуждение: так на
 * карточках Claude Team жили приписки «($20/мес при годовой оплате)», а в
 * таблице /vendors/docker — «$9 за пользователя в месяц» (находка руководителя
 * 04.09.2026).
 *
 * Проверяются только ВИДИМЫЕ поля. Служебные `notes` и `rejected` в пакетах
 * каталога — журнал происхождения цены для аудита, там ссылка на прайс вендора
 * с суммой обязательна (docs/vendors-expansion-prompt.md, раздел 2), и они на
 * сайт не попадают: импорт берёт только колонки из scripts/import-vendors.mjs.
 *
 * Пороги лицензирования вендора («бесплатно при доходе до $100K», «Enterprise
 * от $1M выручки») — условие лицензии, а не цена: они не привязаны к периоду и
 * правилом не ловятся.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

/** Курс валюты в тексте и цена с периодом («$20/мес», «€15 в месяц», «80 ₽ за доллар»). */
const STALE_MONEY = new RegExp(
  'курс[а-яё]{0,3}\\s+\\d'
  + '|\\d+[\\d\\s.,]*\\s*(?:₽|руб[а-яё.]*)\\s*за\\s*(?:1\\s*)?(?:доллар|евро|\\$|USD|EUR)'
  + '|(?:\\$|€|USD|EUR)\\s?1\\s*[=≈]'
  + '|(?:\\$|€)\\s?\\d+[\\d.,]*\\s*(?:/|за\\s|в\\s)\\s*(?:мес|месяц|год|year|month|место|пользоват)'
  + '|(?:\\$|€)\\s?\\d+[\\d.,]*\\s*/\\s*(?:мес|мес\\.|month|year)',
  'i',
);

/** Собирает все строковые значения структуры, кроме служебных ключей. */
function texts(value: unknown, skip: Set<string>, out: string[] = []): string[] {
  if (typeof value === 'string') out.push(value);
  else if (Array.isArray(value)) for (const v of value) texts(v, skip, out);
  else if (value && typeof value === 'object') {
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      if (!skip.has(k)) texts(v, skip, out);
    }
  }
  return out;
}

function findings(label: string, values: string[]): string[] {
  return values.filter((t) => STALE_MONEY.test(t)).map((t) => {
    const m = STALE_MONEY.exec(t);
    return `${label}: «${m?.[0]}» в «${t.slice(0, 90)}…»`;
  });
}

const CONTENT = resolve(__dirname, '../scripts/content');
const CATALOG = resolve(__dirname, '../scripts/catalog');
const BATCH = resolve(__dirname, '../data/seo/product-descriptions.json');
// Входные данные пайплайна build-zoho-catalog, а не контент лендинга.
const PIPELINE = new Set(['zoho-cards.json', 'zoho-groups.json', 'zoho-rules.json']);

describe('цена и курс не вписаны в текст страницы', () => {
  // Без этой проверки тест мог бы «зеленеть» на сломанном правиле.
  it('правило ловит цену с периодом и курс, но не порог лицензирования', () => {
    for (const bad of ['за место в год ($20/мес при годовой оплате)', 'по курсу 80 ₽ за доллар',
      '$1 = 80 ₽', '$15 за пользователя в месяц', 'Pro — $96/мес']) {
      expect(STALE_MONEY.test(bad), `не поймано: ${bad}`).toBe(true);
    }
    for (const ok of ['Оплата в рублях по курсу ЦБ РФ на дату счёта',
      'Indie ($2000 за проект, бесплатно при доходе до $100K)',
      'Enterprise обязателен при доходе свыше $25 млн',
      'За пользователя, годовая оплата; цена — в карточке товара']) {
      expect(STALE_MONEY.test(ok), `ложная находка: ${ok}`).toBe(false);
    }
  });

  it('контент лендингов производителей', () => {
    const hits: string[] = [];
    for (const f of readdirSync(CONTENT).filter((n) => n.endsWith('.json') && !PIPELINE.has(n))) {
      const pkg = JSON.parse(readFileSync(resolve(CONTENT, f), 'utf8'));
      hits.push(...findings(f, texts(pkg, new Set())));
    }
    expect(hits, ['Цена в тексте лендинга устаревает молча — уберите сумму,',
      'оставьте схему тарификации; цена берётся из карточки товара.', '', ...hits].join('\n')).toEqual([]);
  });

  it('видимые поля карточек в пакетах каталога', () => {
    const hits: string[] = [];
    const skip = new Set(['notes', 'rejected', 'source_url', 'checkout_url', 'price_confidence']);
    if (existsSync(CATALOG)) {
      for (const f of readdirSync(CATALOG).filter((n) => n.endsWith('.json'))) {
        const pkg = JSON.parse(readFileSync(resolve(CATALOG, f), 'utf8'));
        for (const p of pkg.products ?? []) {
          hits.push(...findings(`${f}:${p.slug}`, texts(p, skip)));
        }
      }
    }
    expect(hits, ['Сумма попала в видимое поле карточки. Для журнала происхождения',
      'цены есть notes — он на сайт не идёт.', '', ...hits].join('\n')).toEqual([]);
  });

  it('партия текстов для Directus', () => {
    const batch = JSON.parse(readFileSync(BATCH, 'utf8'));
    const hits: string[] = [];
    for (const [slug, rec] of Object.entries(batch.products ?? {})) {
      hits.push(...findings(slug, texts(rec, new Set())));
    }
    expect(hits, ['Партия публикуется в Directus и попадает на страницу —',
      'цена и курс в тексте недопустимы.', '', ...hits].join('\n')).toEqual([]);
  });
});
