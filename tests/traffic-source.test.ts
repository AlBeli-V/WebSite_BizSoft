/**
 * Разбор источника обращения (решение руководителя 10.09.2026).
 *
 * Проверяется главное свойство разбора: он отвечает «органика, реклама или
 * внешняя площадка» и никогда не выдумывает того, чего в данных нет. Письмо
 * с придуманной фразой хуже письма без фразы: по нему принимают решения о
 * бюджете.
 */
import { describe, expect, it } from 'vitest';
import { explainSource, parseVisitPath, platformByReferrer } from '../src/lib/traffic-source';
import { attributionLines, attributionRows } from '../src/lib/email/layout';
import type { AttributionFields } from '../src/lib/quote-lead';

const empty: AttributionFields = {
  utm_source: '', utm_medium: '', utm_campaign: '', utm_content: '', utm_term: '',
  yclid: '', gclid: '', first_touch_source: '', first_touch_ts: '',
  last_touch_source: '', landing_path: '', ym_client_id: '', ga_client_id: '',
  first_touch_referrer: '', last_touch_referrer: '', visit_path: '',
};

const with_ = (over: Partial<AttributionFields>): AttributionFields => ({ ...empty, ...over });

describe('тип трафика по меткам браузера', () => {
  it('выдача Яндекса — органика, фраза не выдумывается', () => {
    const v = explainSource(with_({
      last_touch_source: 'yandex.ru / referral',
      last_touch_referrer: 'https://yandex.ru/search/?text=%D0%BA%D1%83%D0%BF%D0%B8%D1%82%D1%8C',
    }));
    expect(v.kind).toBe('organic');
    expect(v.system).toBe('Яндекс');
    expect(v.query).toBeUndefined();
    expect(v.queryNote).toContain('не передаёт поисковую фразу');
    expect(v.pending.join(' ')).toContain('уточнением');
  });

  it('выдача Google — органика Google', () => {
    const v = explainSource(with_({ last_touch_referrer: 'https://www.google.com/' }));
    expect(v.kind).toBe('organic');
    expect(v.system).toBe('Google');
  });

  it('карточка организации в Яндекс Бизнесе — не органика', () => {
    const v = explainSource(with_({
      last_touch_referrer: 'https://yandex.ru/maps/org/bizsoft/1234567890/',
    }));
    expect(v.kind).toBe('external');
    expect(v.system).toBe('Яндекс.Бизнес');
  });

  it('переход из Дзена — внешняя площадка из реестра', () => {
    const v = explainSource(with_({ last_touch_referrer: 'https://dzen.ru/a/abcdef' }));
    expect(v.kind).toBe('external');
    expect(v.system).toBe('Дзен');
  });

  it('автометка Директа — реклама, кампания и фраза из меток', () => {
    const v = explainSource(with_({
      yclid: '778899', utm_campaign: 'bs-test-2026-09', utm_content: 'k1',
      utm_term: 'claude для юрлиц',
    }));
    expect(v.kind).toBe('ads');
    expect(v.system).toBe('Яндекс Директ');
    expect(v.campaign).toBe('bs-test-2026-09');
    expect(v.query).toBe('claude для юрлиц');
    expect(v.evidence).toContain('yclid');
  });

  it('gclid — реклама Google Ads', () => {
    expect(explainSource(with_({ gclid: 'abc' })).system).toBe('Google Ads');
  });

  it('ни метки, ни реферера — источник не определён, без домыслов', () => {
    const v = explainSource(empty);
    expect(v.kind).toBe('unknown');
    expect(v.kindLabel).toBe('Источник не определён');
    expect(v.evidence).toContain('закладка');
  });

  it('путь по сайту из браузера читается шагами', () => {
    const v = explainSource(with_({ visit_path: '10.09 13:41~/catalog|10.09 13:44~/product/kling' }));
    expect(v.steps).toHaveLength(2);
    expect(v.steps[1].page).toBe('/product/kling');
    expect(v.stepsOrigin).toContain('браузер');
  });
});

describe('обогащение Метрикой и Директом', () => {
  it('Метрика главнее метки: карточка организации против «яндекс в реферере»', () => {
    const v = explainSource(with_({ last_touch_referrer: 'https://yandex.ru/' }), {
      available: true, trafficSource: 'referral', referralSource: 'dzen.ru',
    });
    expect(v.kind).toBe('external');
    expect(v.system).toBe('Дзен');
  });

  it('поисковая фраза органики приходит из Метрики', () => {
    const v = explainSource(with_({ last_touch_referrer: 'https://yandex.ru/search/' }), {
      available: true, trafficSource: 'organic', searchEngine: 'Яндекс',
      searchPhrase: 'kling ai оплата юрлицом',
      steps: [{ when: '2026-09-02', source: 'поиск', engine: 'Яндекс', page: '/' }],
    });
    expect(v.query).toBe('kling ai оплата юрлицом');
    expect(v.queryNote).toContain('Метрики');
    expect(v.steps[0].engine).toBe('Яндекс');
    expect(v.pending).toHaveLength(0);
  });

  it('Метрика молчит о фразе — письмо говорит об этом прямо', () => {
    const v = explainSource(with_({ last_touch_referrer: 'https://www.google.com/' }), {
      available: true, trafficSource: 'organic', searchEngine: 'Google',
      steps: [{ when: '2026-09-01', page: '/' }],
    });
    expect(v.query).toBeUndefined();
    expect(v.queryNote).toContain('скрыл');
  });

  it('цена клика — средняя по условию показа, и это названо', () => {
    const v = explainSource(with_({ yclid: '1' }), {
      available: true, trafficSource: 'ad', advEngine: 'Яндекс.Директ',
      direct: {
        campaign: 'bs-apple-gift-2026-09', group: 'gift-1', ad: '99887766',
        phrase: 'подарочная карта apple', avgCpcRub: 41.5, costDate: '2026-09-09',
      },
    });
    expect(v.cpcRub).toBe(41.5);
    expect(v.cpcNote).toContain('средняя цена клика');
    expect(v.query).toBe('подарочная карта apple');
    expect(v.ad).toBe('99887766');
  });

  it('обогащение не собралось — причина попадает в письмо дословно', () => {
    const v = explainSource(with_({ last_touch_referrer: 'https://yandex.ru/search/' }), {
      available: false, error: 'HTTP 403: доступ к счётчику закрыт',
    });
    expect(v.pending.join(' ')).toContain('HTTP 403');
  });
});

describe('блок источника в письме', () => {
  const a = with_({
    yclid: '5', utm_campaign: 'bs-test', last_touch_source: 'yandex / cpc',
    landing_path: '/vendors/anthropic',
  });

  it('первой строкой — тип трафика, ниже сырая метка', () => {
    const html = attributionRows(a);
    expect(html.indexOf('Тип трафика')).toBeLessThan(html.indexOf('Метка канала'));
    expect(html).toContain('Платная реклама');
    expect(html).toContain('yandex / cpc');
  });

  it('text-версия повторяет состав html-версии', () => {
    const lines = attributionLines(a).join('\n');
    expect(lines).toContain('Тип трафика: Платная реклама · Яндекс Директ');
    expect(lines).toContain('Вход на сайт: /vendors/anthropic');
  });

  it('данные посетителя экранируются', () => {
    const html = attributionRows(with_({ utm_campaign: '<script>alert(1)</script>', yclid: '1' }));
    expect(html).not.toContain('<script>');
  });
});

describe('реестр площадок', () => {
  it('домен опознаётся вместе с поддоменами', () => {
    expect(platformByReferrer('vc.ru')?.account.platform).toBe('VC.ru');
    expect(platformByReferrer('m.habr.com')?.account.platform).toBe('Habr');
  });

  it('правило с путём отличает карточку организации от выдачи', () => {
    expect(platformByReferrer('yandex.ru', '/maps/org/1')?.byPath).toBe(true);
    expect(platformByReferrer('yandex.ru', '/search/?text=x')).toBeNull();
  });

  it('пустой путь браузера — пустой список шагов', () => {
    expect(parseVisitPath('')).toEqual([]);
  });
});
