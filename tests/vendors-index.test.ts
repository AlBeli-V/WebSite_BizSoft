/**
 * Каталог производителей (/vendors): инструмент выбора, а не копия меню.
 *
 * Проверки статические — они смотрят на шаблон и на чистые функции, а не на
 * живую базу, и потому работают в CI без секретов и без сети.
 *
 * Главная из них — про ссылки. Список на этой странице остаётся основным
 * донором внутренних ссылок на 110+ лендингов вендоров: вторая точка входа
 * только мега-меню шапки. Поиск и фильтр обязаны прятать строки, а не
 * вырезать их из разметки; список, дорисованный скриптом, увёл бы весь
 * раздел из обхода так же тихо, как это случилось со слоем «Аналоги X».
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { groupVendors, vendorTier, VENDOR_GROUPS } from '../src/lib/vendor-groups';
import { TOP_VENDORS } from '../src/data/vendor-top';
import { GOALS } from '../src/lib/analytics';

const ROOT = resolve(__dirname, '..');
const page = readFileSync(resolve(ROOT, 'src/pages/vendors/index.astro'), 'utf8');
const header = readFileSync(resolve(ROOT, 'src/components/Header.astro'), 'utf8');

describe('назначение вендора считается из каталога', () => {
  const facets = (pairs: [string, string][]) =>
    pairs.map(([vendor, slug]) => ({ vendor, category: { slug } }));

  it('основное назначение — там, где у вендора больше позиций', () => {
    const { groupByVendor } = groupVendors(facets([
      ['Microsoft', 'office'], ['Microsoft', 'office'], ['Microsoft', 'ai-office'],
      ['Adobe', 'design'],
    ]));
    expect(groupByVendor.get('Microsoft')).toBe('work');
    expect(groupByVendor.get('Adobe')).toBe('design');
  });

  it('при равенстве побеждает назначение, которое выше в порядке показа', () => {
    const { groupByVendor } = groupVendors(facets([['Google', 'office'], ['Google', 'ai-text']]));
    expect(groupByVendor.get('Google')).toBe('ai');
  });

  it('вендор попадает ровно в одно назначение', () => {
    const { groups } = groupVendors(facets([
      ['Microsoft', 'office'], ['Microsoft', 'ai-text'], ['Microsoft', 'security'],
    ]));
    expect(groups.reduce((sum, g) => sum + g.vendors, 0)).toBe(1);
  });

  it('раздел вне укрупнения не исчезает молча, а становится своей группой', () => {
    const { groups, groupByVendor } = groupVendors(
      facets([['Новый', 'quantum']]), { quantum: 'Квантовые вычисления' });
    expect(groupByVendor.get('Новый')).toBe('quantum');
    expect(groups.find((g) => g.key === 'quantum')?.label).toBe('Квантовые вычисления');
  });

  it('пустые назначения в фильтр не выводятся', () => {
    const { groups } = groupVendors(facets([['Adobe', 'design']]));
    expect(groups).toHaveLength(1);
    expect(groups[0].key).toBe('design');
  });

  it('разделы каталога разложены по назначениям без пересечений', () => {
    const seen = new Set<string>();
    for (const g of VENDOR_GROUPS) {
      for (const c of g.categories) {
        expect(seen.has(c), `раздел ${c} назначен дважды`).toBe(false);
        seen.add(c);
      }
    }
  });
});

describe('ступень веса вендора', () => {
  it('сотни, десятки и единицы позиций различаются', () => {
    expect(vendorTier(901)).toBe('major');
    expect(vendorTier(100)).toBe('major');
    expect(vendorTier(99)).toBe('mid');
    expect(vendorTier(10)).toBe('mid');
    expect(vendorTier(9)).toBe('niche');
    expect(vendorTier(1)).toBe('niche');
  });
});

describe('перелинковка страницы производителей', () => {
  it('список берётся из живого каталога, а не из шаблона', () => {
    expect(page).toMatch(/getVendors\(\)/);
    // Имя вендора, вписанное в шаблон, устаревает молча: карточка уходит из
    // каталога, а ссылка на её лендинг остаётся.
    const listSection = page.slice(page.indexOf('data-vendor-list'), page.indexOf('</style>'));
    expect(listSection).not.toMatch(/href="\/vendors\/[a-z]/);
  });

  it('каждая строка списка — обычная ссылка на лендинг вендора', () => {
    expect(page).toMatch(/byCount\.map\(/);
    expect(page).toMatch(/href=\{v\.href\}/);
  });

  it('фильтр прячет строки, а не удаляет их из разметки', () => {
    expect(page).toMatch(/row\.hidden = !show/);
    expect(page).not.toMatch(/\.remove\(\)/);
    expect(page).not.toMatch(/innerHTML\s*=/);
  });

  it('список в микроразметке полный, а не первые несколько десятков', () => {
    const ld = page.slice(page.indexOf("'@type': 'ItemList'"), page.indexOf('---\n<BaseLayout'));
    expect(ld).toMatch(/itemListElement: byCount\.map\(/);
    expect(ld).not.toMatch(/\.slice\(/);
  });

  it('алфавитный указатель остался как режим показа', () => {
    expect(page).toMatch(/data-letter=\{l\}/);
    expect(page).toMatch(/data-sort="alpha"/);
  });
});

describe('подбор нескольких производителей', () => {
  it('отметки живут отдельно от корзины товаров', () => {
    expect(page).toMatch(/from '@\/lib\/vendor-picks'/);
    expect(page).not.toMatch(/cart-client/);
  });

  it('отмеченные вендоры уходят в штатную форму заявки', () => {
    expect(page).toMatch(/data-open-question/);
    expect(page).toMatch(/dataset\.product = picks\.length/);
  });
});

describe('аналитика страницы производителей', () => {
  const REQUIRED = ['vendors_search', 'vendors_filter_click', 'vendors_card_click',
    'vendors_multiselect_add', 'vendors_multiselect_submit'];

  it('все пять целей раздела заведены в реестре', () => {
    for (const goal of REQUIRED) expect(GOALS[goal], goal).toBeTruthy();
  });

  it('все пять целей отправляются со страницы', () => {
    for (const goal of REQUIRED) expect(page.includes(`'${goal}'`), goal).toBe(true);
  });
});

describe('топ производителей', () => {
  it('страница и мега-меню шапки берут его из одного места', () => {
    expect(page).toMatch(/from '\.\.\/\.\.\/data\/vendor-top'/);
    expect(header).toMatch(/from '\.\.\/data\/vendor-top'/);
    expect(header).not.toMatch(/const TOP_ORDER/);
  });

  it('в топе только слаги существующих лендингов', () => {
    for (const slug of TOP_VENDORS) expect(slug).toMatch(/^[a-z0-9-]+$/);
    expect(new Set(TOP_VENDORS).size).toBe(TOP_VENDORS.length);
  });
});
