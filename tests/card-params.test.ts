/**
 * Блок «Основные параметры» карточки (постановка руководителя 14.09.2026).
 *
 * Проверки статические и модульные: структура одна на весь каталог, поэтому
 * порядок и правила заполнения стерегутся здесь, а не глазами на карточке.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { PARAM_ORDER, SKU_UNIT_LABEL, cardParams, paramTerm, unitLabel } from '../src/lib/card-params';
import { TERM } from '../src/lib/card-display';
import { vendorLegal } from '../src/lib/catalog';
import { VENDORS } from '../src/data/vendors';
import { SKU_UNITS } from '../src/lib/sku';

const ROOT = resolve(__dirname, '..');
const page = readFileSync(resolve(ROOT, 'src/pages/product/[slug].astro'), 'utf8');

const BASE = {
  vendorLegal: 'OpenAI, L.L.C.',
  category: 'Текстовые AI',
  planShort: 'Командный',
  term: '1 год',
  sku: 'OPAI-LIC-CHATGPTBUS-TEAM-1Y-USER-STD',
  qtyLabel: 'Рабочих мест',
  minQty: 2,
  transfer: 'Да',
  management: 'Централизованная консоль',
  vat: 5,
};

describe('порядок параметров един для каталога', () => {
  it('строки идут в утверждённой последовательности', () => {
    expect([...PARAM_ORDER]).toEqual([
      'Производитель', 'Категория', 'Тип плана', 'Срок', 'Расчётная единица',
      'Мин. кол-во', 'Трансфер', 'Управление', 'НДС', 'Артикул',
    ]);
    expect(cardParams(BASE).map((r) => r.key)).toEqual([...PARAM_ORDER]);
  });

  it('длинные подписи заменены короткими: строка не ложится в два яруса', () => {
    // «Минимальное количество» и «Переназначение пользователей» переносились
    // на телефоне — постановка руководителя 14.09.2026.
    expect(PARAM_ORDER).not.toContain('Минимальное количество');
    expect(PARAM_ORDER).not.toContain('Переназначение пользователей');
    for (const key of PARAM_ORDER) expect(key.length, key).toBeLessThanOrEqual(18);
  });

  it('строки вида позиции встают после «Управления» и не рвут порядок', () => {
    const keys = cardParams({
      ...BASE,
      extra: [{ key: 'Регионы', value: 'Global (USD)' }, { key: 'Номиналов', value: '4' }],
    }).map((r) => r.key);
    expect(keys.indexOf('Регионы')).toBe(keys.indexOf('Управление') + 1);
    // Канонические НДС и артикул остаются последними.
    expect(keys.slice(-2)).toEqual(['НДС', 'Артикул']);
  });

  it('пустое значение строку не создаёт', () => {
    // У договорной позиции срока нет — выдумывать его нельзя.
    const keys = cardParams({ ...BASE, term: null, category: '', management: null }).map((r) => r.key);
    expect(keys).not.toContain('Срок');
    expect(keys).not.toContain('Категория');
    // Управление заводится не у каждого вендора — пустого поля в таблице нет.
    expect(keys).not.toContain('Управление');
    // Без НДС (позиция по запросу) строки налога тоже нет.
    expect(cardParams({ ...BASE, vat: 0 }).map((r) => r.key)).not.toContain('НДС');
  });

  it('шаблон печатает то, что вернул cardParams, и ничего сверх', () => {
    expect(page).toContain('const params = cardParams({');
    expect(page).toContain('{params.map((row) => (');
    // Прежние строки блока убраны постановкой.
    expect(page).not.toContain('Тип использования:');
    expect(page).not.toContain('Переназначение пользователей:');
    expect(page).not.toContain('Артикул BIZSoft');
  });
});

describe('значения семантически верны для вида позиции', () => {
  it('тип плана: командный, индивидуальный, а без деления — универсальный', () => {
    expect(cardParams(BASE).find((r) => r.key === 'Тип плана')?.value).toBe('Командный');
    expect(cardParams({ ...BASE, planShort: '' }).find((r) => r.key === 'Тип плана')?.value)
      .toBe('Универсальный');
  });

  it('расчётная единица берётся из сегмента артикула, а не назначается всем', () => {
    // Механическое «Рабочее место» всему каталогу — как раз то, ради чего
    // появилось это правило.
    expect(unitLabel('OPAI-LIC-CHATGPTBUS-TEAM-1Y-USER', null, 'Лицензий')).toBe('Рабочее место');
    expect(unitLabel('OPAI-CRD-API-UNI-BAL-NOM-100', null, 'Лицензий')).toBe('Сумма');
    expect(unitLabel('KASP-LIC-ENDPOINTSEC-TEAM-1Y-DEV', null, 'Лицензий')).toBe('Устройство');
    expect(unitLabel('PHTN-LIC-FUSION-UNI-1Y-CCU', null, 'Лицензий')).toBe('Плавающая лицензия');
    // Слово оператора старше сегмента: им размечают пакеты кредитов.
    expect(unitLabel('OPAI-CRD-API-UNI-BAL-NOM-100', 'кредит', 'Лицензий')).toBe('Кредит');
    // Несистемный артикул — подпись счётчика из контента вендора.
    expect(unitLabel('INT-AI-CLAUDE', null, 'Рабочих мест')).toBe('Рабочее место');
  });

  it('у каждой единицы артикула есть подпись', () => {
    // Без неё карточка показала бы пустую строку или чужое слово.
    for (const unit of Object.keys(SKU_UNITS)) {
      expect(SKU_UNIT_LABEL[unit as keyof typeof SKU_UNITS], unit).toBeTruthy();
    }
  });

  it('минимум и трансфер — те же значения, что в блоке фактов', () => {
    expect(cardParams(BASE).find((r) => r.key === 'Мин. кол-во')?.value).toBe('2');
    expect(cardParams({ ...BASE, minQty: 0 }).find((r) => r.key === 'Мин. кол-во')?.value).toBe('1');
    expect(cardParams(BASE).find((r) => r.key === 'Трансфер')?.value).toBe('Да');
    expect(cardParams({ ...BASE, transfer: 'Нет' }).find((r) => r.key === 'Трансфер')?.value).toBe('Нет');
  });

  it('срок в параметрах — месяцами, бессрочный — знаком бесконечности', () => {
    // В подзаголовке под H1 срок остаётся годами: там он читается фразой,
    // здесь — значением таблицы, и месяцы сравнимы между позициями.
    expect(paramTerm(TERM.year)).toBe('12 месяцев');
    expect(paramTerm('2 года')).toBe('24 месяца');
    expect(paramTerm('3 года')).toBe('36 месяцев');
    expect(paramTerm(TERM.perpetual)).toBe('∞');
    expect(paramTerm(TERM.balance)).toBe('до истечения баланса');
    expect(paramTerm('3 месяца')).toBe('3 месяца');
    expect(paramTerm(null)).toBe('');
  });

  it('НДС — только значение, без пояснения под строкой', () => {
    expect(cardParams(BASE).find((r) => r.key === 'НДС')?.value).toBe('5% (включено в стоимость)');
    expect(page).not.toContain('vat-note');
    expect(page).not.toContain('сверху не добавляется');
  });

  it('артикул выводится как есть', () => {
    expect(cardParams(BASE).find((r) => r.key === 'Артикул')?.value).toBe(BASE.sku);
  });
});

describe('производитель называется юридическим лицом', () => {
  it('имя берётся из профиля производителя, а не из марки', () => {
    // До 14.09.2026 карточка читала словарь на сорок имён, и эти три
    // показывали марку вместо юрлица.
    expect(vendorLegal('OpenAI')).toBe('OpenAI, L.L.C.');
    expect(vendorLegal('Anthropic')).toBe('Anthropic PBC');
    expect(vendorLegal('Figma')).toBe('Figma, Inc.');
  });

  it('юридическое имя есть у каждой записи реестра', () => {
    const blank = VENDORS.filter((v) => !v.legalName?.trim());
    expect(blank.map((v) => v.slug)).toEqual([]);
    for (const v of VENDORS) expect(vendorLegal(v.vendor), v.slug).toBe(v.legalName);
  });

  it('строка производителя — знак и название одной ссылкой на его раздел', () => {
    expect(page).toContain("row.key === 'Производитель' && vendorPageSlug");
    expect(page).toContain('<VendorLogo slug={vendorPageSlug} name={row.value} size={18} fluid />');
    expect(page).toContain('<a class="v-vendor" href={`/vendors/${vendorPageSlug}`}>');
    // Без подчёркивания и цвета ссылки — как в строке первого экрана.
    const rule = page.slice(page.indexOf('.v-vendor {'));
    expect(rule.slice(0, rule.indexOf('}'))).toContain('text-decoration: none');
  });
});

describe('строка параметра остаётся строкой', () => {
  const styles = page.slice(page.indexOf('  .params {'));

  it('подпись и значение на одной оси, а не в два яруса', () => {
    const prow = styles.slice(styles.indexOf('.prow {'));
    const decl = prow.slice(0, prow.indexOf('}'));
    expect(decl).toContain('display: flex');
    expect(decl).toContain('align-items: center');
    // Телефонный режим, складывавший строку в два яруса, снят постановкой.
    expect(page).not.toContain('.prow { grid-template-columns: minmax(0, 1fr)');
  });

  it('подпись не ломается внутри слова, значение — может', () => {
    const k = styles.slice(styles.indexOf('.prow .k {'));
    expect(k.slice(0, k.indexOf('}'))).toContain('overflow-wrap: normal');
    // На узком экране подпись сжимается по содержимому, но не уже слова.
    expect(page).toContain('.prow .k { flex: 0 1 auto; min-width: min-content; }');
  });
});

describe('правило записано в свод и в файл правил', () => {
  it('свод ссылается на правило, правило называет порядок и источники', () => {
    const claude = readFileSync(resolve(ROOT, 'CLAUDE.md'), 'utf8');
    expect(claude).toContain('docs/rules/card-params.md');
    const rule = readFileSync(resolve(ROOT, 'docs/rules/card-params.md'), 'utf8');
    for (const key of PARAM_ORDER) expect(rule, key).toContain(key);
    expect(rule).toContain('12 месяцев');
    expect(rule).toContain('legalName');
    expect(rule).toContain('unit_label');
  });
});
