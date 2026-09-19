/**
 * Cookie-механизм: аналитика не грузится до выбора, ПДн не уходят в счётчики.
 *
 * Ключевая проверка — первая: до 16.09.2026 оба счётчика стартовали на
 * первом же визите, а плашка лишь сообщала об этом постфактум. Регрессия
 * сюда возвращается одной строкой (вынести вызов загрузчика из-под
 * согласия), и заметить её по поведению сайта невозможно — только по коду.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { sanitizeGoalParams } from '../src/lib/analytics';
import { COOKIE_UI } from '../src/config/legal';

const ROOT = resolve(__dirname, '..');
const read = (rel: string) => readFileSync(resolve(ROOT, rel), 'utf8');
const analytics = read('src/components/Analytics.astro');
/** Код без комментариев: пояснения не должны проходить проверки за код. */
const code = analytics.split('\n').filter((l) => !l.trim().startsWith('//') && !l.trim().startsWith('*')).join('\n');

describe('теги не грузятся до выбора пользователя', () => {
  it('загрузка Метрики и GA возможна только изнутри функций старта', () => {
    const metrika = code.slice(code.indexOf('function startMetrika'), code.indexOf('function startGa'));
    expect(metrika).toContain('mc.yandex.ru/metrika/tag.js');
    const ga = code.slice(code.indexOf('function startGa'), code.indexOf('window.__bzAnalyticsConsent'));
    expect(ga).toContain('googletagmanager.com/gtag/js');
    // Вне функций старта адресов тегов нет.
    const outside = code.slice(0, code.indexOf('function startMetrika'))
      + code.slice(code.indexOf('window.__bzAnalyticsConsent'));
    expect(outside).not.toContain('mc.yandex.ru/metrika/tag.js');
    expect(outside).not.toContain('googletagmanager.com/gtag/js');
  });

  it('старт вызывается только по сохранённому или новому согласию', () => {
    const apply = code.slice(code.indexOf('window.__bzAnalyticsConsent'));
    expect(apply).toMatch(/choices\.yandex_analytics\)\s*startMetrika\(\)/);
    expect(apply).toMatch(/choices\.google_analytics\)\s*startGa\(\)/);
    // Единственное безусловное обращение — применение уже сделанного выбора.
    expect(apply).toMatch(/var saved = storedChoices\(\);\s*\n\s*if \(saved\) window\.__bzAnalyticsConsent\(saved\)/);
  });

  it('очередь ym создаётся вместе с разрешением, а не заранее', () => {
    const beforeStart = code.slice(0, code.indexOf('function startMetrika'));
    expect(beforeStart).not.toContain('window.ym');
  });

  it('испорченная запись в хранилище равносильна отсутствию согласия', () => {
    expect(code).toMatch(/catch \(e\) \{ return null; \}/);
    expect(code).toMatch(/p\.v !== schemaVersion/);
  });

  it('noscript-пиксель Метрики снят: без JavaScript согласие спросить не у чего', () => {
    expect(analytics).not.toContain('mc.yandex.ru/watch/');
  });
});

describe('Consent Mode', () => {
  it('значения по умолчанию — запрет, и выставляются до всего остального', () => {
    expect(code).toMatch(/gtag\('consent', 'default', \{[\s\S]*?analytics_storage: 'denied'/);
    expect(code).toMatch(/ad_storage: 'denied'/);
    expect(code).toMatch(/ad_user_data: 'denied'/);
    expect(code).toMatch(/ad_personalization: 'denied'/);
    expect(code.indexOf("gtag('consent', 'default'")).toBeLessThan(code.indexOf('function startGa'));
  });

  it('разрешение приходит обновлением при включении GA', () => {
    const ga = code.slice(code.indexOf('function startGa'));
    expect(ga).toMatch(/gtag\('consent', 'update', \{ analytics_storage: 'granted' \}\)/);
  });

  it('рекламные сигналы Google выключены явно', () => {
    expect(code).toContain('allow_google_signals: false');
    expect(code).toContain('allow_ad_personalization_signals: false');
  });
});

describe('интерфейс выбора', () => {
  const banner = read('src/components/CookieConsent.astro');

  it('три ответа первого визита — как в документе 05', () => {
    expect(banner).toContain('data-cookie-accept-all');
    expect(banner).toContain('data-cookie-necessary');
    expect(banner).toContain('data-cookie-open-settings');
    expect(COOKIE_UI.acceptAll).toBe('Принять все');
    expect(COOKIE_UI.necessaryOnly).toBe('Отклонить аналитику');
    expect(COOKIE_UI.settings).toBe('Настроить');
  });

  it('кнопка называет отказ, а не только его результат', () => {
    // Внешняя проверка 18.09.2026 нашла на странице адреса счётчиков и не
    // нашла отказа: «Только необходимые» описывало результат верно, но слова
    // отказа в нём не было. Оба корня — в подписи кнопки и в её описании.
    expect(COOKIE_UI.necessaryOnly).toMatch(/отклонить/i);
    expect(COOKIE_UI.necessaryOnlyHint).toMatch(/отказ/i);
    expect(banner).toContain('aria-label={COOKIE_UI.necessaryOnlyHint}');
  });

  it('раздельные тумблеры Метрики и Google Analytics', () => {
    const ids = COOKIE_UI.categories.map((c) => c.id);
    expect(ids).toContain('yandex_analytics');
    expect(ids).toContain('google_analytics');
    expect(banner).toContain('data-cookie-category');
  });

  it('необязательные категории по умолчанию выключены, необходимые — заблокированы', () => {
    for (const c of COOKIE_UI.categories) {
      if (c.id === 'necessary') expect(c.locked).toBe(true);
      else expect(c.locked).toBe(false);
    }
    // `checked` ставится только у заблокированной категории.
    expect(banner).toMatch(/checked=\{c\.locked\}/);
  });

  it('отказ — кнопка того же веса, что согласие', () => {
    // Разный вес здесь означал бы, что отказаться труднее, чем согласиться:
    // обе кнопки получают один класс, размер задаёт `.cc-btn`.
    const button = (marker: string) =>
      banner.match(new RegExp(`<button[^>]*${marker}[^>]*>`))?.[0] || '';
    expect(button('data-cookie-accept-all')).toContain('cc-btn');
    expect(button('data-cookie-necessary')).toContain('cc-btn');
    expect(banner).toMatch(/\.cc-btn\s*\{[^}]*min-height/s);
  });

  it('плашка отдаётся видимой: отказ читается без исполнения скриптов', () => {
    // Регрессия сюда возвращается одним словом `hidden` в разметке корня, и
    // по поведению сайта она незаметна — заметна только внешней проверке,
    // которая читает HTML и не исполняет скрипты.
    const root = banner.match(/<div class="cc-root"[^>]*>/)?.[0] || '';
    expect(root).toContain('data-cookie-consent');
    expect(root).not.toMatch(/\bhidden\b/);
    // Скрывает плашку стиль по атрибуту на <html> — и ставит его синхронный
    // скрипт, стоящий выше блока, чтобы вернувшийся не увидел мелькания.
    expect(banner).toMatch(/:global\(html\[data-cookie-decided\]\) \.cc-root \{ display: none; \}/);
    const boot = banner.slice(0, banner.indexOf('<div class="cc-root"'));
    expect(boot).toContain('is:inline');
    expect(boot).toContain("setAttribute('data-cookie-decided'");
    expect(boot).toContain('p.v === schemaVersion');
  });

  it('видимостью управляет один механизм, а не два', () => {
    // `root.hidden` рядом с атрибутом на <html> означал бы два состояния
    // одного и того же — однажды они разойдутся.
    expect(banner).not.toContain('root.hidden');
    expect(banner).toContain('const setDecided = (decided: boolean)');
  });

  it('вход в настройки есть в подвале и на странице правового раздела', () => {
    expect(read('src/components/Footer.astro')).toContain('data-cookie-settings');
    expect(read('src/pages/legal/index.astro')).toContain('data-cookie-settings');
  });

  it('выбор уходит в журнал согласий отдельным событием на категорию', () => {
    const api = read('src/pages/api/consent/analytics.ts');
    expect(api).toContain('yandex_analytics');
    expect(api).toContain('google_analytics');
    expect(api).toMatch(/action: value === true \? 'granted' : 'denied'/);
    // Персональных данных в этих событиях нет — субъект технический.
    expect(api).toContain('anonymousSubjectId');
    expect(api).not.toMatch(/subject:\s*\{\s*email/);
  });
});

describe('в аналитику не уходят персональные данные', () => {
  it('поля форм выбрасываются по имени', () => {
    const out = sanitizeGoalParams({
      email: 'k@romashka.ru',
      phone: '+79167898651',
      inn: '7701234567',
      name: 'Кувшинова Екатерина',
      company: 'ООО «Ромашка»',
      message: 'нужен расчёт',
      form_source: 'pricing',
    });
    expect(out).toEqual({ form_source: 'pricing' });
  });

  it('почта, телефон и длинные номера маскируются в любом текстовом значении', () => {
    const out = sanitizeGoalParams({
      reason: 'Не удалось отправить на k@romashka.ru, телефон +7 916 789-86-51',
      wanted: 'ИНН 7701234567',
    });
    expect(out.reason).not.toContain('k@romashka.ru');
    expect(out.reason).toContain('[email]');
    expect(out.reason).toContain('[phone]');
    expect(out.wanted).not.toContain('7701234567');
  });

  it('обычные параметры целей проходят без изменений', () => {
    const out = sanitizeGoalParams({ form_source: 'pricing', total: 120000, email_rent: 1, sku: 'ANTH-LIC-CLAUDE-TEAM-1Y-SEAT' });
    expect(out).toEqual({ form_source: 'pricing', total: 120000, email_rent: 1, sku: 'ANTH-LIC-CLAUDE-TEAM-1Y-SEAT' });
  });

  it('вложенные объекты отбрасываются: их состав проверить нечем', () => {
    expect(sanitizeGoalParams({ lead: { email: 'k@romashka.ru' }, ok: 1 })).toEqual({ ok: 1 });
  });

  it('очистка применяется в самой отправке, а не оставлена на вызывающего', () => {
    const src = read('src/lib/analytics.ts');
    const track = src.slice(src.indexOf('export function trackGoal'));
    expect(track).toContain('const safe = sanitizeGoalParams(params)');
    expect(track).not.toMatch(/reachGoal', name, params\)/);
    expect(track).not.toMatch(/\{ \.\.\.params, bz_goal/);
  });
});
