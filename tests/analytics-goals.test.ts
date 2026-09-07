/**
 * Реестр целей и код не должны расходиться.
 *
 * Цель, вызванная в коде, но не заведённая в кабинете, летит в пустоту:
 * счётчик её принимает, а в отчёте её нет. Обратное так же плохо — цель в
 * реестре без вызова выглядит как «ноль обращений», хотя её просто никто не
 * шлёт. Отсюда две проверки навстречу друг другу.
 */
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { GOALS, KEY_GOALS } from '../src/lib/analytics';

const ROOT = resolve(__dirname, '..');

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (/\.(ts|astro)$/.test(name)) out.push(full);
  }
  return out;
}

/**
 * Имена целей, реально встречающиеся в коде сайта.
 *
 * Ищем строковые литералы, а не только аргумент сразу после trackGoal(:
 * часть целей выбирается тернарником (результативный поиск против пустого),
 * часть приходит из таблицы соответствий (клики по контактам). Сканер по
 * одному лишь `trackGoal('...')` объявлял бы их мёртвыми.
 *
 * Сам реестр из выборки исключён — иначе он подтверждал бы сам себя.
 */
function calledGoals(): Set<string> {
  const names = Object.keys(GOALS);
  const found = new Set<string>();
  for (const f of walk(resolve(ROOT, 'src'))) {
    if (f.endsWith('/lib/analytics.ts')) continue;
    const src = readFileSync(f, 'utf8');
    // Цели механизма data-ev пишутся в двойных кавычках и мимо trackGoal(:
    // сканер по одним лишь одинарным кавычкам их не видел, и цель могла
    // годами уходить в счётчик, не значась в реестре (так было с
    // click_get_quote — главным призывом всех лендингов производителей).
    for (const m of src.matchAll(/data-ev(?:-view)?="([a-z0-9_]+)"/g)) {
      if (names.includes(m[1])) found.add(m[1]);
    }
    for (const m of src.matchAll(/'([a-z_]+)'/g)) {
      if (names.includes(m[1])) found.add(m[1]);
    }
  }
  return found;
}

/**
 * Цели, которые сайт отправляет через data-ev, но в реестре их нет.
 *
 * Такая цель уходит в счётчик незаведённой: события идут, а в отчёте их
 * не существует. Список зафиксирован как долг 07.09.2026 — он не должен
 * расти. Заводить их в кабинете (seo-goals-sync) — отдельное решение
 * руководителя, поэтому здесь они только перечислены.
 */
const UNREGISTERED_DATA_EV = [
  'click_buy_org', 'click_choose_plan', 'click_clarify_price', 'click_compare_app',
  'click_pick_licenses', 'click_plugins_catalog', 'click_product_card', 'click_related_link',
  'click_renew', 'click_request_invoice', 'expand_plugins_category', 'open_comparison_table',
  'quiz_complete', 'quiz_step',
];

function dataEvGoals(): Set<string> {
  const found = new Set<string>();
  for (const f of walk(resolve(ROOT, 'src'))) {
    for (const m of readFileSync(f, 'utf8').matchAll(/data-ev(?:-view)?="([a-z0-9_]+)"/g)) {
      found.add(m[1]);
    }
  }
  return found;
}

describe('реестр целей', () => {
  const called = calledGoals();

  it('незарегистрированных data-ev целей не прибавилось', () => {
    const unregistered = [...dataEvGoals()].filter((g) => !GOALS[g]).sort();
    expect(unregistered).toEqual([...UNREGISTERED_DATA_EV].sort());
  });

  it('шаги воронки заявки заведены в реестре', () => {
    for (const g of ['click_get_quote', 'form_open', 'form_start', 'lead_sent']) {
      expect(GOALS[g], g).toBeTruthy();
    }
  });

  it('каждая цель из кода описана в реестре', () => {
    const unknown = [...called].filter((g) => !GOALS[g]);
    expect(unknown).toEqual([]);
  });

  it('каждая цель реестра где-то вызывается', () => {
    const dead = Object.keys(GOALS).filter((g) => !called.has(g));
    expect(dead).toEqual([]);
  });

  it('у каждой цели есть имя для GA4 и человеческое описание', () => {
    for (const [name, spec] of Object.entries(GOALS)) {
      expect(spec.ga4, name).toBeTruthy();
      expect(spec.meaning, name).toBeTruthy();
    }
  });

  it('конверсиями считаются только обращения, а не просмотры', () => {
    expect(KEY_GOALS.sort()).toEqual(
      ['click_email', 'click_messenger', 'click_phone', 'lead_sent', 'quote_pdf'].sort());
  });

  it('лендинги вендоров шлют одну цель с параметром, а не цель на вендора', () => {
    // Пять целей вида view_openai_landing нельзя сравнить между собой и
    // нельзя завести одной строкой в кабинете.
    const perVendor = [...called].filter(
      (g) => /^view_.+_landing$/.test(g) && g !== 'view_vendor_landing');
    expect(perVendor).toEqual([]);
    expect(called.has('view_vendor_landing')).toBe(true);
  });

  it('воронка прослеживается от просмотра до обращения', () => {
    for (const step of ['view_product', 'add_to_cart', 'view_cart',
                        'begin_checkout', 'quote_pdf']) {
      expect(called.has(step), `нет шага ${step}`).toBe(true);
    }
  });

  it('сбой формы отличим от отказа клиента', () => {
    expect(called.has('lead_error')).toBe(true);
    expect(called.has('quote_error')).toBe(true);
  });

  it('пустой поиск фиксируется отдельно от результативного', () => {
    expect(called.has('search_no_results')).toBe(true);
    expect(called.has('search_used')).toBe(true);
  });
});

describe('цели контакта', () => {
  it('распознаются по адресу ссылки', async () => {
    const { goalForHref } = await import('../src/lib/contact-goals');
    expect(goalForHref('tel:+79647161111')?.goal).toBe('click_phone');
    expect(goalForHref('mailto:a@biz-soft.pro')?.goal).toBe('click_email');
    expect(goalForHref('https://t.me/bizsoft')?.goal).toBe('click_messenger');
    expect(goalForHref('https://wa.me/79647161111')?.goal).toBe('click_messenger');
    expect(goalForHref('/catalog')).toBeNull();
    expect(goalForHref('')).toBeNull();
  });
});
