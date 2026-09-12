/**
 * Карточка товара: цена, призыв и первый экран (12.09.2026).
 *
 * Три дефекта, из которых родились проверки:
 *   — счётчик начинался с единицы даже там, где вендор продаёт от двух мест,
 *     и покупатель считал бюджет по заказу, который невозможно оформить;
 *   — главный призыв назывался «В расчёт»: он складывал позицию в подборку,
 *     а человек, пришедший за ценой, читал его как «получить расчёт»;
 *   — на телефоне цена и кнопка уезжали под описание и вопросы.
 *
 * Проверки статические: они смотрят на исходники и работают в CI без сети.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { commerceState, quoteCtaLabel, quoteProductRef, UNIT_FORMS } from '../src/lib/product-commerce';
import { VENDOR_CONTENT } from '../src/data/vendor-content';

const ROOT = resolve(__dirname, '..');
const page = readFileSync(resolve(ROOT, 'src/pages/product/[slug].astro'), 'utf8');

describe('цена не меньше реального заказа', () => {
  it('сумма считается от минимального объёма, а не от единицы', () => {
    const s = commerceState({ price: 1000, minQty: 2, qtyLabel: 'Мест' });
    expect(s.purchasePrice).toBe(2000);
    // Минимум больше единицы — значит показанная сумма это «от»: больший
    // заказ стоит дороже, и точной ценой она быть не может.
    expect(s.priceFrom).toBe(true);
  });

  it('без объявленного минимума ничего не выдумывается', () => {
    const s = commerceState({ price: 1000 });
    expect(s.minQty).toBe(1);
    expect(s.purchasePrice).toBe(1000);
    expect(s.priceFrom).toBe(false);
  });

  it('позиция без цены — договорная, а не бесплатная', () => {
    const s = commerceState({ price: 0 });
    expect(s.pricing).toBe('quote_only');
    expect(s.purchasePrice).toBe(0);
  });

  it('счётчик карточки не опускается ниже минимума', () => {
    // Жёсткое min="1" в разметке и было тем самым дефектом.
    expect(page).not.toMatch(/<input[^>]*type="number"[^>]*min="1"/);
    expect(page).toContain('min={commerce.minQty}');
    expect(page).toContain('value={commerce.minQty}');
  });

  it('прикидка на команду не предлагает объём ниже минимального', () => {
    expect(page).toContain('.filter((n) => n > commerce.minQty)');
  });

  it('крупным числом идёт сумма минимального заказа, а не цена единицы', () => {
    // Цена одного места крупным шрифтом обещает заказ, который нельзя
    // оформить; цена единицы остаётся, но строкой ниже.
    expect(page).toContain('commerce.minQty > 1 ? (');
    expect(page).toContain('от {formatRub(commerce.purchasePrice)}');
  });
});

describe('призыв называет результат', () => {
  it('цена за единицу — призыв называет объём', () => {
    const s = commerceState({ price: 1000, minQty: 2, qtyLabel: 'Мест' });
    expect(quoteCtaLabel(s, 5)).toBe('Получить КП на 5 мест');
    expect(quoteCtaLabel(s, 1)).toBe('Получить КП на 2 места');
    expect(quoteCtaLabel(commerceState({ price: 1000 }), 1)).toBe('Получить КП на 1 лицензию');
  });

  it('договорная цена и отсутствие товара — свои призывы', () => {
    expect(quoteCtaLabel(commerceState({ price: 0 }), 1)).toBe('Получить расчёт');
    expect(quoteCtaLabel(commerceState({ price: 1000, availability: 'out_of_stock' }), 1))
      .toBe('Подобрать аналог');
  });

  it('в заявку уезжает позиция с количеством, а не одно название', () => {
    const s = commerceState({ price: 1000, minQty: 2, qtyLabel: 'Мест' });
    expect(quoteProductRef('Claude Team', 'ANT-TEAM', s, 5)).toBe('Claude Team (ANT-TEAM) — 5 мест');
  });

  it('главный призыв карточки больше не называется «В расчёт»', () => {
    expect(page).not.toContain('>В расчёт<');
    expect(page).toContain('Добавить в расчёт');
  });

  it('окно заявки называет то, за чем пришли', () => {
    const form = readFileSync(resolve(ROOT, 'src/components/QuestionForm.astro'), 'utf8');
    expect(form).toContain('data-dialog-title');
    // Состав полей при этом не трогается: заявка и КП собирают одинаковые
    // реквизиты (решение 28.08.2026).
    expect(form).toContain('name="inn"');
    expect(form).toContain('name="company"');
  });

  it('каждая заведённая подпись единиц умеет склоняться', () => {
    // Без форм кнопка сказала бы «на 1 мест».
    const labels = new Set<string>();
    for (const entry of Object.values(VENDOR_CONTENT)) {
      for (const meta of Object.values(entry.cards || {})) {
        if (meta?.qtyLabel) labels.add(meta.qtyLabel.trim().toLowerCase());
      }
    }
    const missing = [...labels].filter((l) => !UNIT_FORMS[l]);
    expect(missing, `нет форм склонения: ${missing.join(', ')}`).toEqual([]);
  });
});

describe('первый экран и липкая полоса', () => {
  it('цена и призыв есть в первом экране узкого экрана', () => {
    expect(page).toContain('data-hero-cta');
    expect(page).toMatch(/\.hero-buy \{ display: none; \}/);
    expect(page).toMatch(/@media \(max-width: 900px\)[\s\S]*\.hero-buy \{\s*display: block/);
  });

  it('полоса показывается только когда призыв первого экрана ушёл из виду', () => {
    // Два одинаковых призыва на одном экране спорят друг с другом.
    expect(page).toContain('buyBar.hidden = e.isIntersecting');
    expect(page).toContain('io.observe(heroCta)');
  });
});

describe('воронка карточки', () => {
  it('первое осмысленное действие считается один раз', () => {
    expect(page).toContain("trackGoalOnce('product_interaction'");
    expect(page).not.toContain("trackGoal('product_interaction'");
  });

  it('события карточки помечены версией схемы воронки', () => {
    expect(page).toContain("analytics_schema_version: 'pcf_v3'");
  });
});

describe('путь до карточки', () => {
  it('крошки ведут на страницу производителя с выбором продукта', () => {
    expect(page).toContain('url: `/vendors/${vendorPageSlug}`');
    // Раздел каталога остаётся запасным вариантом для позиций без вендора.
    expect(page).toContain('vendorCrumb ? [vendorCrumb] : category');
  });
});
