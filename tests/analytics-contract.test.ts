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
  it('каждый data-ev имеет обработчик в своём файле', () => {
    const orphans = files.filter((f) => {
      const text = read(f);
      return text.includes('data-ev=') && !text.includes("querySelectorAll('[data-ev]')");
    });
    expect(orphans).toEqual([]);
  });

  it('все отправляемые цели объявлены в плане измерений', () => {
    // План — единственный список того, что сайт имеет право отправлять.
    // Новое имя, не попавшее в него, означает цель, которую никто не заведёт.
    const plan = readFileSync('reports/marketing/measurement-plan.md', 'utf8');
    const missing = [...declaredGoals()].filter((n) => !plan.includes(`\`${n}\``));
    expect(missing).toEqual([]);
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
    const cart = read('src/pages/cart/index.astro');
    expect(cart.indexOf("trackGoal('quote_pdf'")).toBeGreaterThan(cart.indexOf('if (!res.ok)'));
  });

  it('каждый data-goal есть в реестре целей', () => {
    // Атрибут data-goal стоял на главных CTA сайта и не имел обработчика ни
    // одного: разметка была, событий не было. Теперь привязка одна на весь
    // сайт, а реестр не даёт появиться имени, которого никто не ждёт.
    const registry = read('src/lib/goals.ts');
    const names = new Set<string>();
    for (const f of files) {
      for (const m of read(f).matchAll(/data-goal="([a-z0-9_]+)"/g)) names.add(m[1]);
    }
    expect(names.size).toBeGreaterThan(0);
    expect([...names].filter((n) => !registry.includes(`${n}:`))).toEqual([]);
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

  it('в параметры событий не попадают персональные данные', () => {
    const forbidden = /trackGoal\([^)]*\b(email|phone|inn|fio|passport)\b\s*:/;
    const leaks = files.filter((f) => forbidden.test(read(f)));
    expect(leaks).toEqual([]);
  });

  it('ошибка формы фиксируется отдельным событием', () => {
    // Без form_error «заявок не было» и «сервер отвечал 502» неотличимы.
    for (const f of ['src/components/LeadForm.astro', 'src/components/QuestionForm.astro',
                     'src/pages/cart/index.astro']) {
      expect(read(f), f).toContain("trackGoal('form_error'");
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
                     'src/pages/cart/index.astro']) {
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
