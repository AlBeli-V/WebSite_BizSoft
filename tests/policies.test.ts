/**
 * База условий работы: один источник для страниц и для агента.
 *
 * Проверка нужна потому, что тексты об условиях уже жили тремя копиями в
 * `.astro` и разъезжались молча: страница правилась, ответ агенту — нет.
 * Здесь фиксируется и обратное направление — что страницы не заводят
 * собственных массивов условий мимо src/data/policies.ts.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { ALL_POLICIES, POLICIES, PROCESS_POLICY, PROCESS_STEPS, policyFaq } from '../src/data/policies';
import { searchPolicies } from '../src/lib/policy-search';

const ROOT = resolve(__dirname, '..');
const read = (rel: string) => readFileSync(resolve(ROOT, rel), 'utf8');

describe('база условий', () => {
  it('id уникальны — по ним ссылаются агент и тесты', () => {
    const ids = ALL_POLICIES.map((p) => p.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('каждая запись заполнена и ведёт на существующую страницу сайта', () => {
    for (const p of ALL_POLICIES) {
      expect(p.question.length, p.id).toBeGreaterThan(8);
      expect(p.answer.length, p.id).toBeGreaterThan(20);
      expect(p.path, p.id).toMatch(/^\/(faq|how-we-work|pricing)$/);
    }
  });

  it('порядок сделки собран из PROCESS_STEPS, второй копии шагов нет', () => {
    expect(PROCESS_STEPS).toHaveLength(7);
    for (const s of PROCESS_STEPS) expect(PROCESS_POLICY.answer).toContain(s.t);
  });
});

describe('страницы берут условия из общего источника', () => {
  const pages: [string, string, number][] = [
    ['src/pages/faq.astro', '/faq', 7],
    ['src/pages/how-we-work.astro', '/how-we-work', 3],
    ['src/pages/pricing.astro', '/pricing', 3],
  ];

  it.each(pages)('%s рендерит записи своей страницы', (file, path, count) => {
    const src = read(file);
    expect(src).toContain(`policyFaq('${path}')`);
    expect(policyFaq(path)).toHaveLength(count);
  });

  it('своих массивов вопрос-ответов страницы условий не заводят', () => {
    for (const [file] of pages) {
      // Литерал { q: '…' } в файле означает, что текст снова разъедется
      // с ответом агента: правка страницы не дойдёт до search_policies.
      expect(read(file), `${file}: условия должны жить в src/data/policies.ts`).not.toMatch(/\{\s*q:\s*'/);
    }
  });

  it('how-we-work берёт шаги оттуда же', () => {
    expect(read('src/pages/how-we-work.astro')).toContain('PROCESS_STEPS');
  });
});

describe('searchPolicies', () => {
  it('находит по словам вопроса, а не по подстроке', () => {
    const r = searchPolicies(ALL_POLICIES, 'можно ли оплатить с расчётного счёта');
    expect(r.length).toBeGreaterThan(0);
    expect(r.map((p) => p.id)).toContain('payment-currency');
  });

  it('вопрос про закрывающие документы ведёт к ответу про ЭДО', () => {
    const r = searchPolicies(ALL_POLICIES, 'дадите закрывающие документы для бухгалтерии');
    expect(r[0].id).toBe('contract-and-docs');
  });

  it('вопрос про сроки находит ответ про поставку', () => {
    const ids = searchPolicies(ALL_POLICIES, 'какие сроки поставки').map((p) => p.id);
    expect(ids).toContain('delivery-time');
  });

  it('при отсутствии всех слов отдаёт ближайшее, а не пустоту', () => {
    const r = searchPolicies(ALL_POLICIES, 'договор и совершенно посторонний термин');
    expect(r.length).toBeGreaterThan(0);
  });

  it('запрос из одних служебных слов ничего не находит (иначе выдача — шум)', () => {
    expect(searchPolicies(ALL_POLICIES, 'а что если')).toEqual([]);
    expect(searchPolicies(ALL_POLICIES, '   ')).toEqual([]);
  });

  it('ничего не совпало — пустой список, выдумывать ответ нечем', () => {
    expect(searchPolicies(POLICIES, 'ямб хорей амфибрахий')).toEqual([]);
  });
});
