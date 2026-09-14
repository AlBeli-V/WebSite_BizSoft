/**
 * Контракт аналитики: защита от регрессий, которые не видны глазом.
 *
 * Каждая проверка здесь родилась из находки аудита 21.08.2026. Все они —
 * статические: они смотрят на исходники, а не на живой счётчик, и потому
 * работают в CI без секретов и без сети.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const SRC = 'src';

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

const files = walk(SRC).filter((f) => f.endsWith('.astro') || f.endsWith('.ts'));
const read = (f: string) => readFileSync(f, 'utf8');

/** Имена целей, которые сайт отправляет. Тот же разбор, что в snapshot.py. */
function declaredGoals(): Set<string> {
  const names = new Set<string>();
  for (const f of files) {
    const text = read(f);
    for (const m of text.matchAll(/trackGoal\(\s*'([a-z0-9_]+)'/g)) names.add(m[1]);
    for (const m of text.matchAll(/data-ev(?:-view)?="([a-z0-9_]+)"/g)) names.add(m[1]);
  }
  return names;
}

describe('счётчики', () => {
  it('Метрика подключается ровно один раз', () => {
    const layout = read('src/layouts/BaseLayout.astro');
    expect(layout.match(/<Analytics\s*\/>/g)?.length ?? 0).toBe(1);
    const analytics = read('src/components/Analytics.astro');
    expect(analytics.match(/metrika\/tag\.js/g)?.length ?? 0).toBe(1);
  });

  it('GA4 конфигурируется ровно один раз и без GTM', () => {
    const analytics = read('src/components/Analytics.astro');
    expect(analytics.match(/gtag\('config'/g)?.length ?? 0).toBe(1);
    expect(files.some((f) => read(f).includes('googletagmanager.com/gtm.js'))).toBe(false);
  });

  it('идентификаторы счётчиков непусты при незаданной PUBLIC-переменной', () => {
    // Фолбэк существует не для удобства: без него выражение схлопывалось в
    // undefined, условие становилось заведомо ложным и минификатор удалял
    // вызов цели целиком.
    const src = read('src/lib/analytics.ts');
    expect(src).toMatch(/METRIKA_ID\s*=\s*import\.meta\.env\.PUBLIC_METRIKA_ID\s*\|\|\s*'\d+'/);
    expect(src).toMatch(/GA_ID\s*=\s*import\.meta\.env\.PUBLIC_GA_ID\s*\|\|\s*'G-[A-Z0-9]+'/);
  });

  it('счётчик сборщика совпадает со счётчиком сайта', () => {
    const site = read('src/lib/analytics.ts');
    const collector = readFileSync('scripts/seo/collect.py', 'utf8');
    const counter = site.match(/METRIKA_ID = .*'(\d+)'/)?.[1];
    const ga = site.match(/GA_ID = .*'(G-[A-Z0-9]+)'/)?.[1];
    expect(counter).toBeTruthy();
    expect(collector).toContain(`EXPECTED_METRIKA_COUNTER = '${counter}'`);
    expect(collector).toContain(`EXPECTED_GA_MEASUREMENT_ID = '${ga}'`);
  });
});

describe('события', () => {
  it('data-ev подключён ровно одним обработчиком', () => {
    // Раньше обработчик стоял в каждой странице производителя. Стоило
    // вынести карточку тарифа в общий компонент — и её кнопки оказались
    // размеченными без слушателя. Правило то же, что у data-goal: один
    // обработчик на сайт, в макете.
    const binders = files.filter((f) => read(f).includes("closest?.('[data-ev]')")
                                     || read(f).includes("querySelectorAll('[data-ev]')"));
    expect(binders).toEqual(['src/layouts/BaseLayout.astro']);
  });

  it('цель уровня lead отправляется только после успешного ответа сервера', () => {
    // Событие заявки, отправленное до проверки res.ok, означало бы конверсию
    // там, где сервер заявку отклонил.
    for (const f of ['src/components/LeadForm.astro', 'src/components/QuestionForm.astro']) {
      const text = read(f);
      const okAt = text.indexOf('if (!res.ok)');
      const goalAt = text.indexOf("trackGoal('lead_sent'");
      expect(okAt, `${f}: нет проверки res.ok`).toBeGreaterThan(-1);
      expect(goalAt, `${f}: нет цели lead_sent`).toBeGreaterThan(okAt);
    }
    // Диалог КП переехал из страницы подборки в компонент 11.09.2026:
    // вход в него теперь не один (подборка, полка главной, наборы).
    const quote = read('src/components/QuoteDialog.astro');
    expect(quote.indexOf("trackGoal('quote_pdf'")).toBeGreaterThan(quote.indexOf('if (!res.ok)'));
  });

  it('data-goal подключён ровно одним обработчиком', () => {
    const binders = files.filter((f) => read(f).includes("closest?.('[data-goal]')")
                                     || read(f).includes("querySelectorAll('[data-goal]')"));
    expect(binders).toEqual(['src/layouts/BaseLayout.astro']);
  });

  it('одно действие не отправляет цель дважды', () => {
    // Кнопка с собственным вызовом trackGoal и с атрибутом data-goal
    // отправила бы событие и напрямую, и через делегированный обработчик.
    const doubles = files.filter((f) => {
      const text = read(f);
      const attrs = [...text.matchAll(/data-goal="([a-z0-9_]+)"/g)].map((m) => m[1]);
      return attrs.some((n) => text.includes(`trackGoal('${n}'`));
    });
    expect(doubles).toEqual([]);
  });

  it('одно понятие передаётся под одним именем параметра', () => {
    // lead_sent слал { source }, а form_start и form_error — { form_source }.
    // В GA4 это два разных custom dimension, и разрез «заявки по форме»
    // распался бы на два несопоставимых набора. Имя параметра — такая же
    // часть контракта, как имя события.
    const banned = /trackGoal\(\s*'[a-z0-9_]+',\s*\{[^}]*\bsource:/;
    const offenders = files.filter((f) => banned.test(read(f)));
    expect(offenders).toEqual([]);
  });

  it('в параметры событий не попадают персональные данные', () => {
    const forbidden = /trackGoal\([^)]*\b(email|phone|inn|fio|passport)\b\s*:/;
    const leaks = files.filter((f) => forbidden.test(read(f)));
    expect(leaks).toEqual([]);
  });

  it('ошибка формы фиксируется одним событием, а не двумя', () => {
    // Без цели ошибки «заявок не было» и «сервер отвечал 502» неотличимы.
    // Но целей должно быть ровно по одной на форму: пока рядом с целью в
    // catch стояла вторая в ветке !res.ok, throw из неё попадал в тот же
    // catch и один отказ 422 считался дважды.
    for (const [f, goal] of [['src/components/LeadForm.astro', 'lead_error'],
                             ['src/components/QuestionForm.astro', 'lead_error'],
                             ['src/components/QuoteDialog.astro', 'quote_error']] as const) {
      const calls = read(f).match(new RegExp(`trackGoal\\('${goal}'`, 'g')) ?? [];
      expect(calls.length, `${f}: ожидается ровно один вызов ${goal}`).toBe(1);
    }
  });
});

describe('атрибуция', () => {
  it('визит фиксируется на каждой странице', () => {
    expect(read('src/layouts/BaseLayout.astro')).toContain('captureVisit()');
  });

  it('первое касание не перезаписывается', () => {
    const src = read('src/lib/attribution.ts');
    expect(src).toMatch(/if \(!read\(FIRST_KEY\)\) write\(FIRST_KEY/);
  });

  it('пустое касание не затирает непустое', () => {
    // Прямой заход — это отсутствие сведений об источнике, а не канал.
    const src = read('src/lib/attribution.ts');
    expect(src).toMatch(/if \(!isMeaningful\(touch\)\) return;/);
  });

  it('каждая форма передаёт атрибуцию на сервер', () => {
    for (const f of ['src/components/LeadForm.astro', 'src/components/QuestionForm.astro',
                     'src/components/QuoteDialog.astro']) {
      expect(read(f), f).toContain('attributionPayload()');
      expect(read(f), f).toMatch(/body: JSON\.stringify\(\{[^}]*attribution/);
    }
  });

  it('канал заявки определяется одной функцией на весь бэкенд', () => {
    // Две копии разбора означали бы два разных определения одного канала.
    const impls = files.filter((f) => read(f).includes('export function attributionFields'));
    expect(impls).toEqual(['src/lib/quote-lead.ts']);
  });
});
