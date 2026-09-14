/**
 * Блок фактов под описанием и «Подробнее» (правило docs/rules/card-lede-facts.md):
 * три колонки у любой позиции, значения из данных, подсказки к заголовкам.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { FACT_HEADS, factTerm, factMin, factTransfer, splitLede, creditsLabel, MIN_BALANCE } from '../src/lib/card-facts';
import { TERM } from '../src/lib/card-display';

const ROOT = resolve(__dirname, '..');
const page = readFileSync(resolve(ROOT, 'src/pages/product/[slug].astro'), 'utf8');

describe('значения блока фактов', () => {
  it('срок: год — «1 год», бессрочно — ∞, баланс — «до истечения»', () => {
    expect(factTerm(TERM.year)).toBe('1 год');
    expect(factTerm('2 года')).toBe('2 года');
    expect(factTerm(TERM.perpetual)).toBe('∞');
    expect(factTerm(TERM.balance)).toBe('до истечения');
    expect(factTerm('3 месяца')).toBe('3 месяца');
    expect(factTerm(null)).toBe('по договору');
  });

  it('минимум: из данных карточки, у пополнения — сумма', () => {
    expect(factMin('unit_subscription', 1, TERM.year)).toBe('1');
    expect(factMin('unit_subscription', 2, TERM.year)).toBe('2');
    expect(factMin('balance_topup', 1, TERM.balance)).toBe(MIN_BALANCE);
    // Пакет кредитов — дополнение по композиции, но минимум у него как у пополнения.
    expect(factMin('addon', 1, TERM.balance)).toBe(MIN_BALANCE);
    expect(factMin('addon', 1, TERM.year)).toBe('1');
    expect(factMin('quote_only', 1, null)).toBe('по запросу');
    // Наименьший номинал линейки старше умолчания «50 $/€».
    expect(factMin('balance_topup', 1, TERM.balance, '1 000 ₽')).toBe('1 000 ₽');
    expect(creditsLabel(50, 'OpenAI API — пополнение баланса на 100 $')).toBe('50 $');
    expect(creditsLabel(330, 'Kling AI — пакет 1 320 кредитов')).toBe('330 кредитов');
    // Intl ставит неразрывный пробел между разрядами — в ячейке таблицы это и нужно.
    expect(creditsLabel(1320, 'пакет кредитов').replace(/\s/g, ' ')).toBe('1 320 кредитов');
  });

  it('переназначение: команда — да, остальные — нет', () => {
    expect(factTransfer('unit_subscription', 'team')).toBe('Да');
    expect(factTransfer('unit_subscription', 'individual')).toBe('Нет');
    // Без деления на планы (лицензия ManageEngine, Office) — «Нет», как у индивидуальных.
    expect(factTransfer('unit_subscription', null)).toBe('Нет');
    expect(factTransfer('balance_topup', null)).toBe('Нет');
    expect(factTransfer('addon', 'team')).toBe('Нет');
    // Отметка оператора старше правила.
    expect(factTransfer('unit_subscription', 'individual', 'Да')).toBe('Да');
  });

  it('три заголовка с короткой и полной формой и пояснением', () => {
    expect(FACT_HEADS.map((h) => h.short)).toEqual(['Срок', 'MIN', 'Трансфер']);
    expect(FACT_HEADS.map((h) => h.long)).toEqual(['Срок действия плана', 'Минимальное количество', 'Возможность переназначения']);
    for (const h of FACT_HEADS) expect(h.hint.length).toBeGreaterThan(20);
  });
});

describe('описание: видимая часть и «Подробнее»', () => {
  it('короткий текст показывается целиком', () => {
    const r = splitLede('Короткое описание продукта.');
    expect(r.head).toBe('Короткое описание продукта.');
    expect(r.tail).toEqual([]);
  });

  it('абзацы: первый виден, остальные под раскрытием', () => {
    const r = splitLede('Первый абзац.\n\nВторой абзац.\n\nТретий.');
    expect(r.head).toBe('Первый абзац.');
    expect(r.tail).toEqual(['Второй абзац.', 'Третий.']);
  });

  it('длинный сплошной текст режется по границе предложения', () => {
    const sentence = 'Предложение о продукте с деталями и пояснениями для покупателя. ';
    const r = splitLede(sentence.repeat(12).trim());
    expect(r.head.endsWith('.')).toBe(true);
    expect(r.head.length).toBeLessThanOrEqual(360);
    expect(r.tail).toHaveLength(1);
    expect(r.head + ' ' + r.tail[0]).toBe(sentence.repeat(12).trim());
  });
});

describe('карточка использует блок фактов и раскрытие', () => {
  it('таблица из трёх равных колонок у любой позиции', () => {
    expect(page).toContain('const heroFacts = FACT_HEADS.map(');
    expect(page).toContain('grid-template-columns: repeat(3, minmax(0, 1fr))');
    expect(page).toContain('<dl class="facts">');
    expect(page).not.toContain('!isGift && (\n          <dl class="facts">');
    // Минимум пополнения — наименьший номинал линейки.
    expect(page).toContain('balanceMin = formatDenomination(least)');
    expect(page).toContain("product.sku.slice(0, product.sku.lastIndexOf('-') + 1)");
    // Заголовки и значения — в одну строку, по центру.
    expect(page).toMatch(/\.fact dt \{[^}]*white-space: nowrap/);
    expect(page).toMatch(/\.fact dd \{[^}]*white-space: nowrap/);
    expect(page).toMatch(/\.fact \{[^}]*text-align: center/);
  });

  it('подсказка у каждого заголовка: по наведению и по тычку', () => {
    expect(page).toContain('class="hint-btn"');
    expect(page).toContain('role="tooltip"');
    expect(page).toContain('.hint:hover .hint-box, .hint:focus-within .hint-box, .hint-btn[aria-expanded="true"] + .hint-box { display: block; }');
    // Скрытая подсказка не занимает места: на 320px она давала прокрутку вбок.
    expect(page).toMatch(/\.hint-box \{ display: none;/);
    expect(page).toContain("document.querySelectorAll<HTMLButtonElement>('[data-hint]')");
  });

  it('полные заголовки — на широком экране, короткие — на остальных', () => {
    expect(page).toContain('class="fact-short"');
    expect(page).toContain('class="fact-long"');
    expect(page).toMatch(/@media \(min-width: 1101px\) \{\s*\.fact-long \{ display: inline; \}/);
  });

  it('описание целиком остаётся в разметке, раскрытие — кнопкой', () => {
    expect(page).toContain('const lede = splitLede(product.short_description || \'\')');
    expect(page).toContain('<div class="lede-more" id="lede-more" hidden>');
    expect(page).toContain('data-lede-toggle');
    expect(page).toContain('aria-controls="lede-more"');
  });

  it('правило записано в свод и в файл правил', () => {
    const claude = readFileSync(resolve(ROOT, 'CLAUDE.md'), 'utf8');
    expect(claude).toContain('docs/rules/card-lede-facts.md');
    const rule = readFileSync(resolve(ROOT, 'docs/rules/card-lede-facts.md'), 'utf8');
    expect(rule).toContain('Трансфер');
    expect(rule).toContain('Подробнее');
  });
});
