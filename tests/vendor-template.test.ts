/**
 * Универсальный шаблон страницы производителя — движок макета 15.09.2026.
 *
 * Макет показал шаблон на четырёх профилях вендоров, и главное в нём —
 * не блоки, а правила их появления: блок заводится контентом, а не правкой
 * разметки под конкретную страницу. Проверки статические: шаблон один на
 * сотню страниц, и цена ошибки в правиле — сотня страниц, а не одна.
 *
 * Пилот включён на Adobe: у остальных вендоров новых полей в контенте нет,
 * поэтому новые блоки у них не рендерятся. Это проверяется не перечнем
 * slug'ов (он устареет при тираже), а условиями в шаблоне.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { VENDOR_CONTENT } from '../src/data/vendor-content';

const landing = readFileSync('src/components/VendorLanding.astro', 'utf8');
const row = readFileSync('src/components/VendorTariffRow.astro', 'utf8');
const switchFile = readFileSync('src/lib/vendor-template.ts', 'utf8');

describe('рубильник движка', () => {
  it('гасится переменной окружения, не правкой кода', () => {
    expect(switchFile).toContain("import.meta.env.PUBLIC_VENDOR_TEMPLATE_V2 !== '0'");
    expect(landing).toContain("import { VENDOR_TEMPLATE_V2, ROW_LAYOUT_MIN } from '../lib/vendor-template'");
  });

  it('выключенный движок не показывает ни один новый блок', () => {
    // Все три производных состояния идут через рубильник: если он снят,
    // ценность, направления и дата проверки пусты, а строки не включаются
    // без направлений.
    expect(landing).toContain('const value = VENDOR_TEMPLATE_V2 ? content.businessValue : undefined');
    expect(landing).toContain('VENDOR_TEMPLATE_V2 ? content.categories || [] : []');
    expect(landing).toContain('const checkedLabel = VENDOR_TEMPLATE_V2 &&');
  });
});

describe('появление блоков решает контент', () => {
  it('ценность для бизнеса — только при своей записи', () => {
    expect(landing).toContain('{value && <p class="value-headline">');
    expect(landing).toContain('{value && (');
  });

  it('карта направлений — от трёх направлений с позициями', () => {
    expect(landing).toContain('const hasCatMap = catTiles.length >= 3');
    // Направление, которого нет в каталоге, плитки не получает: фильтр,
    // приводящий к пустому списку, — дефект, а не особенность.
    expect(landing).toContain('.filter((ct) => ct.count > 0)');
  });

  it('строками — только широкий хвост и только вместе с картой', () => {
    expect(landing).toContain('const useRows = hasCatMap && ungrouped.length >= ROW_LAYOUT_MIN');
    expect(switchFile).toMatch(/export const ROW_LAYOUT_MIN = \d+/);
  });

  it('флагманский раздел идёт первым и остаётся карточками', () => {
    expect(landing).toContain('const orderedGroups = [...groups.filter((g) => g.flagship), ...groups.filter((g) => !g.flagship)]');
  });
});

describe('фильтр сетки', () => {
  it('работает по двум осям одновременно, пересечением', () => {
    expect(landing).toContain('const state = { seg: \'\', cat: \'\' }');
    expect(landing).toContain('el.hidden = !(okSeg && okCat)');
  });

  it('позиция без пометки по оси эту ось проходит', () => {
    // Иначе правка случая или направления тихо уносит карточку со страницы,
    // а полный набор Creative Cloud исчезает при выборе любого направления.
    expect(landing).toContain('!state.seg || !el.dataset.segCard || el.dataset.segCard === state.seg');
    expect(landing).toContain('!state.cat || !el.dataset.catCard || el.dataset.catCard === state.cat');
  });

  it('прячет атрибутом hidden — без JavaScript видны все позиции', () => {
    expect(landing).not.toContain('display: none');
    expect(landing).toContain('el.hidden =');
  });

  it('пустой список называет себя и даёт сброс', () => {
    expect(landing).toContain('data-filter-empty');
    expect(landing).toContain('data-filter-reset');
    // Считаются только размеченные направлением позиции: флагман пометки не
    // несёт и виден всегда, поэтому по нему нельзя судить, пуст ли список.
    expect(landing).toContain("const scoped = items.filter((el) => el.dataset.catCard)");
    expect(landing).toContain('scoped.every((el) => el.hidden)');
  });

  it('не заводит вторую цель под уже считаемый шаг', () => {
    // Шаг подборщика считает vendor_selector_step: направление уходит в него
    // параметром. Своя цель разделила бы отчёт по воронке надвое.
    expect(landing).toContain("trackGoal('vendor_selector_step'");
    expect(landing).toContain('direction: state.cat');
    expect(landing.match(/trackGoal\('vendor_/g)?.length).toBe(1);
  });
});

describe('строка длинного хвоста', () => {
  it('ведёт к заявке тем же путём, что карточка', () => {
    expect(row).toContain("import TariffQty from './TariffQty.astro'");
    expect(row).toContain("import AddToCartButton from './AddToCartButton.astro'");
    expect(row).toContain('data-qty-scope');
  });

  it('не заводит своего поведения — его копия разъехалась бы с карточкой', () => {
    expect(row).not.toContain('<script>');
  });

  it('позиция без цены получает путь к КП, а не счётчик', () => {
    expect(row).toContain('{!c.byRequest && !c.gift && (');
    expect(row).toContain('Запросить цену');
  });
});

describe('дата проверки состава и цен', () => {
  it('берётся из данных каталога, а не литералом в тексте', () => {
    // Литерал устаревает молча: страница продолжает уверять, что цены
    // проверены, ещё год после того, как это перестало быть правдой.
    expect(landing).toContain('p.content_updated_at');
    expect(landing).not.toMatch(/проверены: \d{2}\.\d{2}\.\d{4}/);
  });

  it('называется по московскому времени', () => {
    expect(landing).toContain("timeZone: 'Europe/Moscow'");
  });
});

describe('контент пилота: Adobe', () => {
  const adobe = VENDOR_CONTENT.adobe;
  const cards = Object.keys(adobe.cards || {});

  it('несёт записи движка', () => {
    expect(adobe.businessValue?.headline).toBeTruthy();
    expect(adobe.businessValue?.elaboration).toBeTruthy();
    expect((adobe.categories || []).length).toBeGreaterThanOrEqual(3);
    expect((adobe.groups || []).some((g) => g.flagship)).toBe(true);
  });

  it('все ключи направлений, случаев и разделов есть в карточках', () => {
    const known = new Set(cards);
    const unknown = [
      ...(adobe.categories || []).flatMap((c) => c.keys),
      ...(adobe.segments || []).flatMap((s) => s.keys || []),
      ...(adobe.groups || []).flatMap((g) => g.items),
    ].filter((k) => !known.has(k));
    expect(unknown).toEqual([]);
  });

  it('каждая позиция попала ровно в одно направление', () => {
    const seen = new Map<string, number>();
    for (const c of adobe.categories || []) {
      for (const k of c.keys) seen.set(k, (seen.get(k) || 0) + 1);
    }
    expect([...seen.entries()].filter(([, n]) => n > 1)).toEqual([]);
  });

  it('флагманы направлений не занимают: полный набор закрывает их все', () => {
    const inCat = new Set((adobe.categories || []).flatMap((c) => c.keys));
    const flagship = (adobe.groups || []).filter((g) => g.flagship).flatMap((g) => g.items);
    expect(flagship.filter((k) => inCat.has(k))).toEqual([]);
  });

  it('ни одна позиция не осталась без направления и без раздела', () => {
    const covered = new Set([
      ...(adobe.categories || []).flatMap((c) => c.keys),
      ...(adobe.groups || []).flatMap((g) => g.items),
    ]);
    expect(cards.filter((k) => !covered.has(k))).toEqual([]);
  });

  it('каждая позиция отнесена к случаю: командному или индивидуальному', () => {
    const inSeg = new Set((adobe.segments || []).flatMap((s) => s.keys || []));
    expect(cards.filter((k) => !inSeg.has(k))).toEqual([]);
  });

  it('ценность написана механикой, а не обещанием процентов', () => {
    const text = `${adobe.businessValue?.headline} ${adobe.businessValue?.elaboration}`;
    expect(text).not.toMatch(/на \d+\s?%/);
    expect(text).not.toMatch(/\bв \d+ раза?\b/);
  });
});
