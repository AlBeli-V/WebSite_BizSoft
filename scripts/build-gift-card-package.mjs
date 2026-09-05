// Собирает пакет каталога подарочных карт scripts/catalog/<slug>.json из
// таблицы номиналов: один родительский товар (страница) и по варианту на каждый
// номинал каждого региона. Правило пакета то же, что у остальных вендоров:
// sku = slug в верхнем регистре, закупка в base_price_usd, коэффициент 3,0
// (стратегия gift_card, см. docs/gift-cards.md). Номинал в цене не участвует.
//
// Запуск: node scripts/build-gift-card-package.mjs
// Изменились закупочные цены — правится таблица ниже и пересобирается пакет;
// в Directus изменения доезжают штатным ops-import-vendors (upsert по sku).
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const CHECKED_AT = '2026-09-05';
const MARKUP = 3.0;

// Закупочная стоимость кода в USD — задание руководителя 05.09.2026.
// Соответствие «номинал → закупка» контрольное (1000 RUB = 13.83, 900 RUB = 13.65),
// его стережёт tests/gift-cards.test.ts.
const REGIONS = [
  { code: 'RU', name: 'Россия', currency: 'RUB', account: 'с регионом Россия', costs: [
    [9000, 138.88], [8000, 123.32], [7000, 107.77], [6000, 92.21], [5000, 69.26], [4000, 55.42],
    [3000, 42.18], [2000, 27.30], [1500, 20.47], [1000, 13.83], [900, 13.65], [800, 12.33],
    [700, 10.72], [500, 7.02],
  ] },
  { code: 'TR', name: 'Турция', currency: 'TRY', account: 'с регионом Турция', costs: [
    [2000, 41.76], [1750, 36.51], [1500, 30.87], [1250, 25.72], [1000, 20.58], [799, 17.40],
    [750, 15.45], [600, 12.36], [500, 10.29], [400, 8.24],
  ] },
  { code: 'KZ', name: 'Казахстан', currency: 'KZT', account: 'с регионом Казахстан', costs: [
    [10000, 36.36], [5000, 16.16], [3000, 10.10], [2000, 7.58],
  ] },
];

const PARENT_SKU = 'APP-STORE-ITUNES-GIFT-CARD';
const PARENT_SLUG = 'app-store-itunes-gift-card';

const vendor_entry = {
  slug: 'apple', vendor: 'Apple', legalName: 'Apple Inc.', brandColor: '#1D1D1F', site: 'https://www.apple.com',
  catSeg: 'gift-cards', catLabel: 'Подарочные карты и пополнение баланса', domain: 'gift',
  tagline: 'Цифровые Apple Gift Card для пополнения баланса Apple Account: коды для аккаунтов России, Казахстана и Турции, номиналы от малых до крупных.',
  about: 'Apple Gift Card (App Store & iTunes Gift Card) — цифровой код, который зачисляет свой номинал на баланс Apple Account. С баланса оплачиваются приложения и игры в App Store, покупки внутри приложений и подписки Apple, доступные в стране учётной записи. Карта действует только для аккаунта того региона, для которого выпущена, поэтому регион выбирается до заказа.',
};

const minCost = Math.min(...REGIONS.flatMap((r) => r.costs.map(([, c]) => c)));

const parent = {
  sku: PARENT_SKU,
  slug: PARENT_SLUG,
  name: 'Apple App Store & iTunes Gift Card',
  official_name: 'Apple Gift Card (App Store & iTunes)',
  category: 'gift-cards',
  license_type: 'org',
  product_type: 'gift_card',
  short_description: 'Цифровая Apple Gift Card для пополнения баланса Apple Account: выбираете регион аккаунта (Россия, Казахстан или Турция) и номинал, получаете код после оплаты по счёту.',
  description: [
    'Apple Gift Card (прежнее название — App Store & iTunes Gift Card) — цифровой код, который после активации зачисляет свой номинал на баланс Apple Account. С баланса оплачиваются приложения и игры в App Store, покупки внутри приложений и подписки Apple, доступные в стране учётной записи.',
    'Регион и номинал — варианты одного товара. Сначала выбирается регион Apple Account (Россия, Казахстан или Турция), затем номинал: сумма, которая будет зачислена на баланс после активации. Номинал и цена BIZSoft — разные величины: цена в рублях считается от закупочной стоимости кода по курсу ЦБ РФ и фиксируется в счёте.',
    'Важно: карта предназначена только для Apple Account соответствующего региона. Перед заказом проверьте страну или регион своей учётной записи Apple — карта другого региона может не активироваться.',
    'Количество кодов отдельных номиналов может быть ограничено. Если карты выбранного номинала нет, заказ может быть исполнен несколькими кодами того же региона, суммарный номинал которых обеспечивает оплаченный объём. BIZSoft не является авторизованным реселлером Apple.',
  ].join('\n\n'),
  keywords: 'apple gift card, apple gift card купить, app store gift card, itunes gift card, подарочная карта apple, карта пополнения apple, пополнение apple id, пополнение apple account, пополнение app store, apple gift card россия, apple gift card казахстан, apple gift card турция',
  features: [
    'Три региона Apple Account: Россия (RUB), Казахстан (KZT), Турция (TRY)',
    'Номинал зачисляется на баланс Apple Account после активации кода',
    'Цифровой код передаём после оплаты по счёту, договор и закрывающие через ЭДО',
    'Активация в App Store: «Погасить подарочную карту или код»',
  ],
  base_price_usd: minCost,
  markup_coeff: MARKUP,
  price_from: true,
  billing: 'за код выбранного номинала; цена «от» — минимальный номинал',
  min_quantity: 1,
  price_confidence: 'owner-table',
  checked_at: CHECKED_AT,
  notes: `Родительская карточка: страница /product/${PARENT_SLUG}, выбор региона и номинала на ней. Закупка родителя = минимальная закупка варианта (${minCost} USD, 500 RUB) — даёт цену «от» и переоценивается вместе с вариантами; при изменении таблицы пересобрать пакет. Коэффициент 3,0 — стратегия gift_card (задание руководителя 05.09.2026).`,
  status: 'published',
  sort: 0,
  availability: 'in_stock',
};

const variants = [];
for (const r of REGIONS) {
  for (const [denomination, cost] of r.costs) {
    const nominal = `${denomination} ${r.currency}`;
    const sku = `${PARENT_SKU}-${r.code}-${denomination}`;
    variants.push({
      sku,
      slug: sku.toLowerCase(),
      name: `Apple Gift Card ${nominal}, ${r.name}`,
      official_name: `Apple Gift Card ${nominal} (${r.code})`,
      category: 'gift-cards',
      license_type: 'org',
      product_type: 'gift_card',
      parent_sku: PARENT_SKU,
      region_code: r.code,
      region_name: r.name,
      denomination,
      denomination_currency: r.currency,
      availability: 'in_stock',
      short_description: `Цифровой код Apple Gift Card номиналом ${nominal} для Apple Account ${r.account}: сумма зачисляется на баланс аккаунта после активации.`,
      description: [
        `Apple Gift Card номиналом ${nominal} — цифровой код для Apple Account ${r.account}. После активации в App Store на баланс аккаунта зачисляется ${nominal}; с баланса оплачиваются приложения, покупки внутри приложений и подписки Apple, доступные в этой стране.`,
        `Номинал ${nominal} — это сумма зачисления, а не цена покупки: цена BIZSoft в рублях считается от закупочной стоимости кода по курсу ЦБ РФ и фиксируется в счёте.`,
        `Карта предназначена только для Apple Account ${r.account}. Аккаунту другого региона код может не подойти — регион учётной записи проверяется до заказа в настройках Apple Account.`,
        'Количество кодов этого номинала может быть ограничено: при отсутствии заказ исполняется несколькими кодами того же региона с требуемым суммарным номиналом. Активированный код повторно применить нельзя.',
      ].join('\n\n'),
      keywords: `apple gift card ${denomination} ${r.currency.toLowerCase()}, подарочная карта apple ${r.name.toLowerCase()} ${denomination}, пополнение apple account ${nominal.toLowerCase()}, app store gift card ${r.code.toLowerCase()}`,
      features: [
        `Номинал ${nominal} зачисляется на баланс Apple Account`,
        `Только для Apple Account ${r.account}`,
        'Цифровой код — передаём после оплаты по счёту',
        'Активация в App Store: «Погасить подарочную карту или код»',
      ],
      base_price_usd: cost,
      markup_coeff: MARKUP,
      billing: `за один код номиналом ${nominal}`,
      min_quantity: 1,
      price_confidence: 'owner-table',
      checked_at: CHECKED_AT,
      notes: `Закупка ${cost} USD за код — таблица руководителя 05.09.2026; цена = закупка × курс ЦБ × 3,0. Вариант родителя ${PARENT_SKU}: своей страницы нет (301 на родителя), в sitemap и фиды не идёт.`,
      status: 'published',
    });
  }
}

const out = resolve(__dir, 'catalog/apple.json');
writeFileSync(out, JSON.stringify({ vendor_entry, products: [parent, ...variants] }, null, 1) + '\n');
console.log(`apple.json: 1 родитель + ${variants.length} вариантов`);
