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
import { commerceState, quoteCtaLabel, quoteProductRef, unitNoun, unitPhrase, UNIT_FORMS } from '../src/lib/product-commerce';
import { PROCUREMENT_FLOW, TRUST_LINES } from '../src/data/policies';
import { cardComposition } from '../src/lib/product-composition';
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
    expect(page).toContain('commerce.minQty > 1 ? `от ${formatRub(commerce.purchasePrice)}`');
    expect(page).toContain('цена за {unitPhrase(1, commerce.qtyLabel)}');
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
    expect(page).toContain('Добавить в подборку');
  });

  it('подборка — обратимое действие с видимым состоянием', () => {
    // Одноразовое «Добавлено ✓» не давало ни состояния, ни способа
    // передумать: человек шёл искать корзину.
    expect(page).toContain('Исключить из подборки');
    expect(page).toContain('removeFromCart');
    expect(page).toContain('data-coll-check');
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
  it('на узком экране карточка покупки идёт сразу за первым экраном', () => {
    // Второго блока цены под описанием больше нет: порядок в разметке
    // (экран → покупка → остальное) сам даёт цену до первой прокрутки.
    expect(page).not.toContain('hero-buy');
    const hero = page.indexOf('class="col-hero"');
    const aside = page.indexOf('class="product-aside"');
    const rest = page.indexOf('class="col-rest"');
    expect(hero).toBeGreaterThan(0);
    expect(aside).toBeGreaterThan(hero);
    expect(rest).toBeGreaterThan(aside);
    expect(page).toMatch(/@media \(max-width: 900px\)[\s\S]*\.product-layout \{ grid-template-columns: minmax\(0, 1fr\); \}/);
  });

  it('полоса показывается только когда призыв карточки ушёл из виду', () => {
    // Два одинаковых призыва на одном экране спорят друг с другом.
    expect(page).toContain('buyBar.hidden = e.isIntersecting');
    expect(page).toContain('io.observe(heroCta)');
  });
});

describe('вид позиции задаёт композицию', () => {
  const base = { sku: 'X', price: 1000, product_type: null, parent_sku: null };

  it('подписка за расчётную единицу — эталонная композиция', () => {
    expect(cardComposition(base)).toBe('unit_subscription');
  });

  it('подарочная карта и её номинал — не подписка', () => {
    expect(cardComposition({ ...base, product_type: 'gift_card' })).toBe('balance_topup');
    expect(cardComposition({ ...base, parent_sku: 'PARENT' })).toBe('balance_topup');
  });

  it('дополнение к основному продукту опознаётся по артикулу', () => {
    expect(cardComposition({ ...base, sku: 'JB-PLG-RIDER' })).toBe('addon');
    expect(cardComposition({ ...base, sku: 'ZOOM-PHONE-PRO' })).toBe('addon');
    expect(cardComposition({ ...base, sku: 'OPENAI-CREDITS-100' })).toBe('addon');
  });

  it('позиция без цены — договорная, а не подписка', () => {
    expect(cardComposition({ ...base, price: 0 })).toBe('quote_only');
  });

  it('карточка не показывает счётчик мест там, где мест нет', () => {
    // Счётчик рабочих мест на пополнении баланса — неверный вопрос.
    expect(page).toContain('const isUnitPlan = composition');
    expect(page).toContain("k: 'Расчётная единица'");
    expect(page).toContain('data-composition={composition}');
  });
});

describe('расхождения выката 12.09.2026 закрыты', () => {
  const topup = { sku: 'OPENAI-CREDITS-100', price: 19531, product_type: null, parent_sku: null };

  it('у пополнения баланса призыв не обещает лицензию', () => {
    // На живой карточке стояло «Получить КП на 1 лицензию» и «Количество
    // лицензий»: лицензий у пополнения баланса нет.
    const s = commerceState({ price: 19531 });
    expect(quoteCtaLabel(s, 1, false)).toBe('Получить КП');
    expect(quoteProductRef('Пополнение', 'OPENAI-CREDITS-100', s, 2, false))
      .toBe('Пополнение (OPENAI-CREDITS-100) — 2 шт.');
    expect(cardComposition(topup)).not.toBe('unit_subscription');
    expect(page).toContain("isUnitPlan ? `Количество ${commerce.qtyLabel.toLowerCase()}` : 'Количество'");
    expect(page).toContain('quoteCtaLabel(commerce, commerce.minQty, isUnitPlan)');
    // Клиентский скрипт пересчитывает подпись тем же правилом.
    expect(page).toContain("const namedUnit = layout?.dataset.composition === 'unit_subscription'");
    expect(page).toContain('quoteCtaLabel(commerce, q, namedUnit)');
  });

  it('подзаголовок не тянет тематическую плашку вендора', () => {
    // `badge` — подпись линейки («VFX и моушн», «для команд», «API»), из
    // неё получалось «Командный план · VFX и моушн».
    // Срок берётся из контента вендора, плашка линейки в подзаголовок не идёт.
    expect(page).toContain('const subtitleParts = [planMarker, cardMeta?.term]');
    expect(page).not.toContain('cardMeta?.badge');
  });

  it('строка типа использования не выводится без подписи', () => {
    expect(page).toContain('product.license_type && LICENSE_LABEL[product.license_type]');
  });

  it('хвостовой призыв страницы убран: он дублирует помощь с выбором', () => {
    expect(page).not.toContain('CTASection');
  });

  it('доверительные признаки есть и у подарочной карты', () => {
    const gift = page.slice(page.indexOf('<GiftCardSelector'), page.indexOf('class="card buy-card"'));
    expect(gift).toContain('TRUST_LINES');
  });

  it('командные планы Maxon считаются местами, а не лицензиями', () => {
    // Состав плана в контенте вендора сам называет единицу: «места
    // принадлежат компании и переназначаются».
    const maxon = VENDOR_CONTENT['maxon']?.cards || {};
    for (const [sku, meta] of Object.entries(maxon)) {
      if (!sku.endsWith('-TEAMS')) continue;
      if (!(meta?.features || []).some((f) => f.includes('еста'))) continue;
      expect(meta.qtyLabel, sku).toBe('Рабочих мест');
    }
  });
});

describe('композиция, одобренная 12.09.2026', () => {
  it('разделы страницы идут в утверждённом порядке', () => {
    const order = [
      'Что входит в план',
      'Основные параметры',
      'Как организовано взаимодействие',
      'Подробно о продукте и условиях использования',
    ];
    let prev = -1;
    for (const title of order) {
      const at = page.indexOf(title);
      expect(at, title).toBeGreaterThan(prev);
      prev = at;
    }
  });

  it('условия поставки берутся из единого источника, а не из шаблона', () => {
    // Строка условий, заведённая в шаблоне мимо policies.ts, разъедется с
    // ответом агента при первой же правке.
    expect(page).toContain('PROCUREMENT_FLOW');
    expect(page).toContain('TRUST_LINES');
    expect(page).not.toContain('Закрывающие бухгалтерские документы');
    expect(PROCUREMENT_FLOW).toHaveLength(5);
    expect(TRUST_LINES.length).toBeGreaterThan(2);
  });

  it('артикул ушёл из первого экрана в параметры', () => {
    const hero = page.slice(page.indexOf('class="col-hero"'), page.indexOf('class="product-aside"'));
    expect(hero).not.toContain('product.sku}');
    expect(page).toContain('Артикул BIZSoft:');
  });

  it('интерфейсные решения не выводятся из слага, названия или вендора', () => {
    expect(page).not.toMatch(/slug\.includes\(/);
    expect(page).not.toMatch(/vendor === '/);
  });

  it('карточка 1:1 с макетом: срок, переназначение, состав и вопросы', () => {
    // Ничего из этого нет в схеме каталога — всё ведётся в контенте вендора.
    const rg = VENDOR_CONTENT['maxon']?.cards?.['MAXON-REDGIANT-TEAMS'];
    expect(rg?.term).toBe('1Y / 1 (один) год');
    expect(rg?.termShort).toBe('1 год');
    expect(rg?.reassign).toBe('Да');
    expect(rg?.management).toBe('Централизованная консоль');
    expect(rg?.shortName).toBe('Red Giant');
    expect(rg?.includes).toHaveLength(5);
    expect(rg?.faq).toHaveLength(9);
    // Шаблон обязан их показывать, а не молча игнорировать.
    expect(page).toContain("k: 'Срок', v: cardMeta.termShort");
    expect(page).toContain("k: 'Переназначение', v: cardMeta.reassign");
    expect(page).toContain('Переназначение пользователей:');
    expect(page).toContain('Управление:');
    expect(page).toContain('cardMeta.includes.map');
    expect(page).toContain('cardMeta?.faq');
  });

  it('короткое имя меняет только H1, разметка называет товар полностью', () => {
    // Иначе microdata назвала бы товар иначе, чем JSON-LD, и слои разошлись.
    expect(page).toContain('const h1Text = cardMeta?.shortName || product.name');
    expect(page).toContain('h1Text !== product.name && <meta itemprop="name"');
  });

  it('единица расчёта названа одним словом, а не винительным падежом', () => {
    expect(unitNoun('Мест')).toBe('Рабочее место');
    expect(unitNoun('Рабочих мест')).toBe('Рабочее место');
    expect(unitPhrase(1, 'Рабочих мест')).toBe('1 рабочее место');
    expect(unitPhrase(3, 'Рабочих мест')).toBe('3 рабочих места');
    expect(unitNoun('Лицензий')).toBe('Лицензия');
    // Незнакомая подпись возвращается как есть, а не подменяется догадкой.
    expect(unitNoun('Серверов')).toBe('Серверов');
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
  it('путь ровно из трёх уровней: главная → производитель → продукт', () => {
    // Правило docs/rules/breadcrumbs.md: глобально, на все карточки — и на
    // те, что появятся позже. Состав крошек уезжает в BreadcrumbList,
    // поэтому лишний уровень — это правка поискового слоя.
    const crumbs = page.slice(page.indexOf('<Breadcrumbs'), page.indexOf('/>', page.indexOf('<Breadcrumbs')));
    expect(crumbs).not.toContain('ORIGIN_LABEL');
    expect(crumbs).not.toContain('category.slug');
    // Компонент сам добавляет «Главная», в items остаётся два уровня.
    expect(crumbs.match(/\{ name:/g) ?? []).toHaveLength(2);
    expect(crumbs).toContain("vendorCrumb ?? { name: 'Каталог', url: '/catalog' }");
    // Последний уровень — короткое имя, как в заголовке страницы.
    expect(crumbs).toContain('{ name: h1Text, url: `/product/${product.slug}` }');
  });

  it('второй уровень — страница производителя, имя из реестра вендоров', () => {
    expect(page).toContain("url: `/vendors/${vendorPageSlug}`");
    expect(page).toContain('vendorEntry?.title || vendorEntry?.vendor || product.vendor');
  });

  it('правило пути записано в свод и в файл правил', () => {
    // Глобальное правило живёт не только в шаблоне: его читает каждая
    // сессия, в том числе та, что заводит нового вендора или товар.
    const claude = readFileSync(resolve(ROOT, 'CLAUDE.md'), 'utf8');
    expect(claude).toContain('docs/rules/breadcrumbs.md');
    const rule = readFileSync(resolve(ROOT, 'docs/rules/breadcrumbs.md'), 'utf8');
    expect(rule).toContain('Главная / <Производитель> / <Продукт>');
    expect(rule).toContain('src/data/vendors.ts');
  });
});
