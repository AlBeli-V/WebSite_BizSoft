/**
 * Один путь заявки на лендинге производителя (решение руководителя 11.09.2026).
 *
 * Было три точки сбора контакта с пересекающимися полями: компактная форма
 * первого экрана, полная форма внизу и модальное окно «Задать вопрос». При
 * этом главный призыв «Получить расчёт и КП» открывал именно окно вопроса с
 * полем «Что хотите уточнить?» — подпись обещала одно, кнопка делала другое,
 * а выбранный тариф в заявку не доезжал вовсе.
 *
 * Проверка статическая: она держит не вёрстку, а три обещания — призыв ведёт
 * к форме, минимум вендора держится счётчиком, выбор покупателя уходит вместе
 * с заявкой.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { GOALS } from '../src/lib/analytics';
import { VENDOR_CONTENT } from '../src/data/vendor-content';

const landing = readFileSync('src/components/VendorLanding.astro', 'utf8');
const leadForm = readFileSync('src/components/LeadForm.astro', 'utf8');
const addToCart = readFileSync('src/components/AddToCartButton.astro', 'utf8');
// Поведение единого пути вынесено в компонент: им же пользуются bespoke-страницы.
const quotePath = readFileSync('src/components/VendorQuotePath.astro', 'utf8');
const qty = readFileSync('src/components/TariffQty.astro', 'utf8');
// Карточка тарифа вынесена в компонент: тот же вид нужен и в общем списке,
// и внутри раздела линейки.
const card = readFileSync('src/components/VendorTariffCard.astro', 'utf8');

describe('лендинг производителя: один путь заявки', () => {
  it('призыв «Получить расчёт и КП» ведёт к форме, а не в окно вопроса', () => {
    // Ветка под идущим замером первого экрана исключена сознательно:
    // страница под замером не правится. Маркер data-hero-form-cta и есть
    // отметка «сюда не ходить, пока считаем».
    const calls = (landing.match(/[^\n]*Получить расчёт и КП[^\n]*/g) ?? [])
      .filter((l) => !l.includes('data-hero-form-cta'))
      // Подпись кнопки самой формы — это уже точка назначения, а не призыв.
      .filter((l) => !l.includes('<LeadForm'));
    expect(calls.length).toBeGreaterThan(0);
    for (const line of calls) {
      expect(line, line).toContain('href="#lead"');
      expect(line, line).not.toContain('data-open-question');
    }
    // Якорь, к которому ведут призывы, обязан существовать.
    expect(landing).toContain('id="lead"');
  });

  it('модальное окно осталось только лёгким каналом', () => {
    // Вопрос эксперту и требования ИБ — да; расчёт и КП — нет.
    const modal = (landing.match(/[^\n]*data-open-question[^\n]*/g) ?? [])
      .filter((l) => !l.includes('data-hero-form-cta'));
    for (const line of modal) {
      expect(line, line).not.toContain('Получить расчёт и КП');
    }
  });

  it('форма на странице одна: вторая осталась только под замер первого экрана', () => {
    expect(landing.match(/<LeadForm/g)?.length).toBe(2);
    expect(landing).toContain('HERO_FORM_SLUGS');
    expect(landing).toContain('heroForm && (');
  });
});

describe('расчёт на карточке тарифа', () => {
  it('минимум вендора держится счётчиком, а не только текстом вопросов', () => {
    expect(card).toContain('minQty={c.minQty}');
    expect(qty).toContain('const min = Math.max(1, minQty)');
    expect(qty).toContain('min={min}');
    // Нижняя граница держится и кнопками счётчика, и потерей фокуса:
    // ввод руками иначе обошёл бы минимум.
    expect(quotePath).toContain('Math.max(min,');
    expect(quotePath).toContain('if (!Number.isFinite(n) || n < min) field.value = String(min)');
  });

  it('сумма пересчитывается на странице', () => {
    expect(quotePath).toContain('function repaintSum');
    expect(quotePath).toContain('formatRub(price * qty)');
  });

  it('количество с карточки уходит в подборку, а не теряется', () => {
    expect(addToCart).toContain('[data-qty-scope]');
    expect(addToCart).toMatch(/addToCart\(\{[\s\S]*?\}, qty\)/);
    expect(addToCart).toContain("trackGoal('add_to_cart', { sku: btn.dataset.sku || '', qty })");
  });

  it('состав расчёта доезжает до заявки', () => {
    // Скрытое поле есть в форме, страница его заполняет, сервер принимает.
    expect(leadForm).toContain('name="product_ref"');
    expect(leadForm).toContain('data-product-ref');
    expect(quotePath).toContain('ref.dataset.base');
    // Количество мест собиралось формой и терялось: в payload /api/lead поля
    // seats нет, поэтому оно дописывается к составу.
    expect(leadForm).toContain("`количество: ${seats}`");
  });
});

describe('необязательные блоки шаблона', () => {
  it('абзац «какой тариф кому» и блок ИБ рендерятся только при контенте', () => {
    expect(landing).toContain('{content.intro && (');
    expect(landing).toContain('{content.security && (');
  });

  it('минимумы Anthropic заведены данными, а не текстом', () => {
    const cards = VENDOR_CONTENT.anthropic.cards!;
    // Минимум вендора для командного тарифа — два места, для Enterprise — 20.
    expect(cards['anthropic-team'].minQty).toBe(2);
    expect(cards['anthropic-team-premium'].minQty).toBe(2);
    expect(cards['anthropic-enterprise'].minQty).toBe(20);
  });
});

describe('цели новых шагов воронки заведены в реестре', () => {
  it('шаг «дошёл до цен» и шаг «назвал сомнение» есть', () => {
    // Цель, не заведённая в реестре, уходит в счётчик и в отчёте её нет:
    // ровно так уже терялись click_get_quote и весь набор data-ev.
    for (const goal of ['view_tariffs', 'faq_expand']) {
      expect(GOALS[goal], goal).toBeDefined();
    }
  });
});

describe('состав расчёта доезжает до каждой формы заявки', () => {
  it('заполняются все поля состава, а не первое найденное в DOM', () => {
    // На посадочной с формой первого экрана форм заявки две. Пока состав
    // писался в первое найденное поле, форма внизу страницы уходила с
    // пустым product_ref: менеджер получал заявку без выбранных позиций и
    // переспрашивал то, что покупатель уже отметил счётчиком.
    expect(quotePath).toContain("document.querySelectorAll('[data-lead-form] [data-product-ref]')");
    expect(quotePath).toContain('refs.forEach((ref) => { ref.dataset.base = base; ref.value = base; })');
  });

  it('окно вопроса свой контекст не теряет', () => {
    // У модального окна поле состава своё, и ставит его QuestionForm:
    // состав подборки затёр бы вопрос по конкретному товару.
    expect(quotePath).not.toContain("querySelectorAll('[data-product-ref]')");
  });
});
