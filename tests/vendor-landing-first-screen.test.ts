/**
 * Первый экран лендинга производителя (решение руководителя 04.09.2026).
 *
 * Замер кампании bs-test-2026-09: 226 визитов рекламы, ни одного
 * form_start, глубина 1,04 страницы и 16 секунд. Отказы при этом
 * разошлись по типу страницы: bespoke /vendors/openai — 22 %, типовые
 * /vendors/anthropic — 40 % и /vendors/adobe — 42 %. Разница ровно в
 * первом экране: у bespoke там цена «от», у типового её не было, а вторая
 * кнопка уводила на общий список производителей.
 *
 * Проверка статическая: типовой лендинг обязан показывать цену «от» в
 * первом экране и вести второй кнопкой к тарифам этой же страницы.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';

const landing = readFileSync('src/components/VendorGenericLanding.astro', 'utf8');
const hero = landing.slice(0, landing.indexOf('<div class="summary">'));

describe('Типовой лендинг производителя: первый экран', () => {
  it('считает минимальную цену по позициям с ценой', () => {
    expect(landing).toContain('const minPrice = priced.length');
    expect(landing).toContain("effectivePrice(p).price > 0");
  });

  it('показывает цену «от» до блока «Коротко»', () => {
    expect(hero).toContain('Цены от');
    expect(hero).toContain('formatRub(minPrice)');
  });

  it('второй кнопкой ведёт к тарифам, а не прочь с посадочной', () => {
    expect(hero).toContain('href="#tariffs"');
    expect(hero).not.toContain('href="/vendors"');
  });

  it('секция тарифов несёт якорь, на который ссылается кнопка', () => {
    expect(landing).toContain('id="tariffs"');
  });
});
