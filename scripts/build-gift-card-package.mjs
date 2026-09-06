// Собирает пакеты каталога подарочных карт scripts/catalog/<slug>.json из
// таблиц номиналов: у каждого вендора один или несколько родительских товаров
// (страница) и по варианту на каждый номинал каждого региона. Правило пакета
// то же, что у остальных вендоров: sku = slug в верхнем регистре, закупка в
// base_price_usd, коэффициент 3,0 (стратегия gift_card, docs/gift-cards.md).
// Номинал в цене не участвует.
//
// Запуск: node scripts/build-gift-card-package.mjs [slug ...]
// Изменились закупочные цены — правится таблица ниже и пересобирается пакет;
// в Directus изменения доезжают штатным ops-import-vendors (upsert по sku).
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const MARKUP = 3.0;
const GLOBAL = { code: 'GLOBAL', name: 'Все страны (Global)', account: 'любого региона' };

/**
 * Вендор → родители → регионы → варианты. Поля варианта:
 *   [denomination, cost_usd]                      — денежный номинал в валюте региона;
 *   [denomination, cost_usd, { code, label }]     — не денежный (подписка): код в sku,
 *                                                   подпись на витрине, denomination —
 *                                                   срок в месяцах для сортировки.
 * cost_usd — закупка кода в USD (прайс поставщика, снят руководителем).
 */
const VENDORS = [
  {
    slug: 'apple', checked_at: '2026-09-05', source: 'таблица руководителя 05.09.2026',
    vendor_entry: {
      slug: 'apple', vendor: 'Apple', legalName: 'Apple Inc.', brandColor: '#1D1D1F', site: 'https://www.apple.com',
      catSeg: 'gift-cards', catLabel: 'Подарочные карты и пополнение баланса', domain: 'gift',
      tagline: 'Цифровые Apple Gift Card для пополнения баланса Apple Account: коды для аккаунтов России, Казахстана и Турции, номиналы от малых до крупных.',
      about: 'Apple Gift Card (App Store & iTunes Gift Card) — цифровой код, который зачисляет свой номинал на баланс Apple Account. С баланса оплачиваются приложения и игры в App Store, покупки внутри приложений и подписки Apple, доступные в стране учётной записи. Карта действует только для аккаунта того региона, для которого выпущена, поэтому регион выбирается до заказа.',
    },
    parents: [{
      sku: 'APP-STORE-ITUNES-GIFT-CARD', slug: 'app-store-itunes-gift-card',
      name: 'Apple App Store & iTunes Gift Card', official_name: 'Apple Gift Card (App Store & iTunes)',
      short: 'Apple Gift Card', account: 'Apple Account', balance: 'баланс Apple Account',
      redeem: 'Активация в App Store: «Погасить подарочную карту или код»',
      short_description: 'Цифровая Apple Gift Card для пополнения баланса Apple Account: выбираете регион аккаунта (Россия, Казахстан или Турция) и номинал, получаете код после оплаты по счёту.',
      description: [
        'Apple Gift Card (прежнее название — App Store & iTunes Gift Card) — цифровой код, который после активации зачисляет свой номинал на баланс Apple Account. С баланса оплачиваются приложения и игры в App Store, покупки внутри приложений и подписки Apple, доступные в стране учётной записи.',
        'Регион и номинал — варианты одного товара. Сначала выбирается регион Apple Account (Россия, Казахстан или Турция), затем номинал: сумма, которая будет зачислена на баланс после активации. Номинал и цена BIZSoft — разные величины: цена в рублях считается от закупочной стоимости кода по курсу ЦБ РФ и фиксируется в счёте.',
        'Важно: карта предназначена только для Apple Account соответствующего региона. Перед заказом проверьте страну или регион своей учётной записи Apple — карта другого региона может не активироваться.',
        'Количество кодов отдельных номиналов может быть ограничено. Если карты выбранного номинала нет, заказ может быть исполнен несколькими кодами того же региона, суммарный номинал которых обеспечивает оплаченный объём. BIZSoft не является авторизованным реселлером Apple.',
      ],
      keywords: 'apple gift card, apple gift card купить, app store gift card, itunes gift card, подарочная карта apple, карта пополнения apple, пополнение apple id, пополнение apple account, пополнение app store, apple gift card россия, apple gift card казахстан, apple gift card турция',
      features: [
        'Три региона Apple Account: Россия (RUB), Казахстан (KZT), Турция (TRY)',
        'Номинал зачисляется на баланс Apple Account после активации кода',
        'Цифровой код передаём после оплаты по счёту, договор и закрывающие через ЭДО',
        'Активация в App Store: «Погасить подарочную карту или код»',
      ],
      // Тексты вариантов Apple зафиксированы в формулировках первого импорта
      // (05.09.2026, уже в проде): общий шаблон ниже их не переписывает.
      variantTexts: (nominal, r, denomination) => ({
        official_name: `Apple Gift Card ${nominal} (${r.code})`,
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
      }),
      regions: [
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
      ],
    }],
  },
  {
    slug: 'airalo', checked_at: '2026-09-05', source: 'прайс поставщика (снимок экрана руководителя 05.09.2026)',
    vendor_entry: {
      slug: 'airalo', vendor: 'Airalo', legalName: 'Airalo Technologies Inc.', brandColor: '#E8412C', site: 'https://www.airalo.com',
      catSeg: 'gift-cards', catLabel: 'Подарочные карты и пополнение баланса', domain: 'gift',
      tagline: 'Ваучеры Airalo для оплаты eSIM в поездках: код пополняет баланс аккаунта Airalo, номиналы 5–50 USD, регион Global.',
      about: 'Airalo — магазин eSIM для поездок: тарифы мобильного интернета в 200+ странах покупаются в приложении без физической SIM-карты. Ваучер Airalo — цифровой код, который зачисляет свой номинал на баланс аккаунта Airalo; с баланса оплачиваются eSIM-тарифы. Удобен, когда компания оплачивает связь сотрудникам в командировках, не привязывая корпоративную карту к сервису.',
    },
    parents: [{
      sku: 'AIRALO-GIFT-CARD', slug: 'airalo-gift-card',
      name: 'Airalo Voucher (ваучер на eSIM)', official_name: 'Airalo Voucher',
      short: 'ваучер Airalo', account: 'аккаунт Airalo', balance: 'баланс аккаунта Airalo',
      redeem: 'Активация в приложении Airalo: профиль → «Погасить ваучер» (Redeem voucher)',
      short_description: 'Цифровой ваучер Airalo: код зачисляет номинал в USD на баланс аккаунта Airalo, с которого оплачиваются eSIM-тарифы для поездок. Регион Global, номиналы 5–50 USD.',
      description: [
        'Ваучер Airalo — цифровой код, который после активации в приложении Airalo зачисляет свой номинал на баланс аккаунта. С баланса оплачиваются eSIM-тарифы мобильного интернета для поездок: локальные, региональные и глобальные.',
        'Номинал — сумма в долларах США, которая появится на балансе. Цена BIZSoft в рублях считается от закупочной стоимости кода по курсу ЦБ РФ и фиксируется в счёте; она не равна номиналу, пересчитанному по курсу.',
        'Ваучер выпущен для региона Global и активируется в аккаунте Airalo без привязки к стране. Какие тарифы и в каких странах доступны, определяет Airalo.',
        'Количество кодов отдельных номиналов может быть ограничено: при отсутствии заказ исполняется несколькими кодами с требуемым суммарным номиналом. BIZSoft не является авторизованным партнёром Airalo.',
      ],
      keywords: 'airalo voucher, airalo купить, ваучер airalo, airalo gift card, пополнение airalo, esim airalo оплата, esim для поездок купить юрлицу',
      features: [
        'Регион Global: активируется в аккаунте Airalo без привязки к стране',
        'Номинал в USD зачисляется на баланс Airalo после активации кода',
        'Цифровой код передаём после оплаты по счёту, договор и закрывающие через ЭДО',
        'Активация в приложении Airalo: «Погасить ваучер»',
      ],
      regions: [{ ...GLOBAL, currency: 'USD', costs: [[50, 42.67], [20, 17.07], [10, 8.53], [5, 4.27]] }],
    }],
  },
  {
    slug: 'binance', checked_at: '2026-09-05', source: 'прайс поставщика (снимок экрана руководителя 05.09.2026); часть номиналов вне кадра — не заведены',
    vendor_entry: {
      slug: 'binance', vendor: 'Binance', legalName: 'Binance Holdings Ltd.', brandColor: '#F0B90B', site: 'https://www.binance.com',
      catSeg: 'gift-cards', catLabel: 'Подарочные карты и пополнение баланса', domain: 'gift',
      tagline: 'Binance Gift Card: цифровой код, который зачисляет выбранный актив (BTC, USDC или USDT) на счёт Binance получателя; номиналы в USD, регион Global.',
      about: 'Binance Gift Card — цифровой код биржи Binance, который после погашения зачисляет на счёт получателя актив, указанный в карте (BTC, USDC или USDT), в объёме, соответствующем номиналу в USD. Погашается в приложении или на сайте Binance в разделе Gift Card владельцем верифицированного аккаунта. Доступность сервиса Binance в конкретной стране и требования к аккаунту определяет Binance.',
    },
    parents: ['BTC', 'USDC', 'USDT'].map((asset) => ({
      sku: `BINANCE-${asset}-GIFT-CARD`, slug: `binance-${asset.toLowerCase()}-gift-card`,
      name: `Binance Gift Card (${asset})`, official_name: `Binance Gift Card ${asset}`,
      short: `Binance Gift Card (${asset})`, account: 'аккаунт Binance', balance: `счёт Binance в ${asset}`,
      redeem: 'Погашение в приложении Binance: Gift Card → «Погасить» (Redeem) → ввод кода',
      short_description: `Цифровая Binance Gift Card в ${asset}: код зачисляет актив ${asset} на сумму номинала в USD на счёт Binance получателя. Регион Global, погашение в приложении Binance.`,
      description: [
        `Binance Gift Card (${asset}) — цифровой код, который после погашения зачисляет на счёт Binance получателя актив ${asset} в объёме, соответствующем номиналу карты в долларах США. Код погашается владельцем аккаунта Binance в разделе Gift Card приложения или сайта.`,
        'Номинал — сумма в USD, эквивалент которой в выбранном активе появится на счёте. Цена BIZSoft в рублях считается от закупочной стоимости кода по курсу ЦБ РФ и фиксируется в счёте; она не равна номиналу, пересчитанному по курсу.',
        'Карта выпущена для региона Global. Требования к аккаунту получателя (верификация, доступность сервиса в стране) устанавливает Binance; перед заказом убедитесь, что получатель может погасить карту.',
        'Количество кодов отдельных номиналов может быть ограничено: при отсутствии заказ исполняется несколькими кодами с требуемым суммарным номиналом. BIZSoft не является партнёром Binance.',
      ],
      keywords: `binance gift card, binance gift card ${asset.toLowerCase()}, подарочная карта binance, binance код купить, пополнение binance ${asset.toLowerCase()}, binance gift card купить`,
      features: [
        `Актив ${asset}: на счёт получателя зачисляется ${asset} на сумму номинала в USD`,
        'Регион Global: погашается владельцем аккаунта Binance в разделе Gift Card',
        'Цифровой код передаём после оплаты по счёту, договор и закрывающие через ЭДО',
        'Требования к аккаунту получателя определяет Binance',
      ],
      regions: [{ ...GLOBAL, currency: 'USD', costs: {
        BTC: [[100, 104.03], [50, 52.02], [40, 41.61], [15, 15.60]],
        USDC: [[60, 61.81], [50, 51.51], [25, 25.75], [20, 20.60]],
        USDT: [[500, 517.50], [300, 309.06], [250, 260.07], [200, 207.00]],
      }[asset] }],
    })),
  },
  {
    slug: 'discord', checked_at: '2026-09-05', source: 'прайс поставщика (снимок экрана руководителя 05.09.2026)',
    vendor_entry: {
      slug: 'discord', vendor: 'Discord', legalName: 'Discord Inc.', brandColor: '#5865F2', site: 'https://discord.com',
      catSeg: 'gift-cards', catLabel: 'Подарочные карты и пополнение баланса', domain: 'gift',
      tagline: 'Подписки Discord Nitro и Nitro Basic по подарочной ссылке: 1 и 12 месяцев, регион Global, оформление на компанию по счёту.',
      about: 'Discord — платформа голосового, видео- и текстового общения для сообществ и команд. Подписка Nitro расширяет возможности аккаунта: качество стрима, размер загружаемых файлов, кастомизация профиля и бусты серверов; Nitro Basic — младший тариф с частью этих возможностей. Подписка передаётся подарочной ссылкой Discord: получатель открывает её в своём аккаунте и активирует срок.',
    },
    parents: [{
      sku: 'DISCORD-NITRO-GIFT-CARD', slug: 'discord-nitro-gift-card',
      name: 'Discord Nitro (подарочная подписка)', official_name: 'Discord Nitro Gift',
      short: 'подписка Discord Nitro', account: 'аккаунт Discord', balance: 'аккаунт Discord',
      redeem: 'Активация: открыть подарочную ссылку в аккаунте Discord и подтвердить принятие подарка',
      short_description: 'Подписка Discord Nitro или Nitro Basic подарочной ссылкой: 1 или 12 месяцев, регион Global. Получатель активирует подарок в своём аккаунте Discord.',
      description: [
        'Discord Nitro — платная подписка Discord: улучшенное качество стрима и видео, увеличенный размер загружаемых файлов, кастомизация профиля, бусты серверов. Nitro Basic — младший тариф с частью возможностей. Подписка передаётся подарочной ссылкой Discord: получатель открывает её, будучи авторизованным в своём аккаунте, и подтверждает принятие подарка.',
        'Варианты — тариф и срок: Nitro Basic на 1 месяц, Nitro на 1 месяц, Nitro на 12 месяцев. Цена BIZSoft в рублях считается от закупочной стоимости подарка по курсу ЦБ РФ и фиксируется в счёте.',
        'Подарок выпущен для региона Global и не привязан к стране аккаунта. Доступность Discord и его платных функций в конкретной стране определяют сам сервис и местное законодательство; условия активации устанавливает Discord.',
        'Подарочная ссылка одноразовая: после принятия подарка повторно применить её нельзя. Количество подарков отдельных вариантов может быть ограничено. BIZSoft не является партнёром Discord.',
      ],
      keywords: 'discord nitro купить, discord nitro подписка, discord nitro gift, подарок discord nitro, discord nitro basic, discord nitro 12 месяцев, discord nitro оплата',
      features: [
        'Три варианта: Nitro Basic на 1 месяц, Nitro на 1 месяц, Nitro на 12 месяцев',
        'Регион Global: подарочная ссылка активируется в любом аккаунте Discord',
        'Ссылку передаём после оплаты по счёту, договор и закрывающие через ЭДО',
        'Активация: открыть подарочную ссылку и принять подарок в своём аккаунте',
      ],
      regions: [{ ...GLOBAL, currency: 'MONTH', costs: [
        [12, 87.50, { code: 'NITRO-12M', label: 'Discord Nitro, 12 месяцев' }],
        [1, 8.88, { code: 'NITRO-1M', label: 'Discord Nitro, 1 месяц' }],
        [1, 4.32, { code: 'BASIC-1M', label: 'Discord Nitro Basic, 1 месяц' }],
      ] }],
    }],
  },
];

const want = process.argv.slice(2);
for (const v of VENDORS) {
  if (want.length && !want.includes(v.slug)) continue;
  const products = [];
  for (const parent of v.parents) {
    const allCosts = parent.regions.flatMap((r) => r.costs.map((c) => c[1]));
    const minCost = Math.min(...allCosts);
    const variants = [];
    for (const r of parent.regions) {
      for (const [denomination, cost, extra] of r.costs) {
        const monetary = !extra;
        const nominal = monetary ? `${denomination} ${r.currency}` : extra.label;
        const suffix = monetary ? String(denomination) : extra.code;
        const sku = `${parent.sku}-${r.code}-${suffix}`;
        const texts = parent.variantTexts && monetary ? parent.variantTexts(nominal, r, denomination) : {};
        variants.push({
          sku,
          slug: sku.toLowerCase(),
          name: monetary ? `${parent.short.charAt(0).toUpperCase() + parent.short.slice(1)} ${nominal}, ${r.name}` : `${extra.label} (${r.name})`,
          official_name: monetary ? `${parent.official_name} ${nominal} (${r.code})` : `${extra.label} (${r.code})`,
          category: 'gift-cards',
          license_type: 'org',
          product_type: 'gift_card',
          parent_sku: parent.sku,
          region_code: r.code,
          region_name: r.name,
          denomination,
          denomination_currency: r.currency,
          ...(monetary ? {} : { variant_label: extra.label }),
          availability: 'in_stock',
          short_description: monetary
            ? `Цифровой код: ${parent.short} номиналом ${nominal} для ${parent.account} ${r.account}; сумма зачисляется на ${parent.balance} после активации.`
            : `${extra.label}: подарочная ссылка для ${parent.account} ${r.account}; срок активируется после принятия подарка.`,
          description: [
            monetary
              ? `${parent.short.charAt(0).toUpperCase() + parent.short.slice(1)} номиналом ${nominal} — цифровой код для ${parent.account} ${r.account}. После активации на ${parent.balance} зачисляется ${nominal}.`
              : `${extra.label} — подарочная ссылка для ${parent.account} ${r.account}. После принятия подарка в аккаунте активируется указанный срок подписки.`,
            monetary
              ? `Номинал ${nominal} — это сумма зачисления, а не цена покупки: цена BIZSoft в рублях считается от закупочной стоимости кода по курсу ЦБ РФ и фиксируется в счёте.`
              : 'Цена BIZSoft в рублях считается от закупочной стоимости подарка по курсу ЦБ РФ и фиксируется в счёте.',
            `${parent.redeem}. Условия активации и доступность сервиса в стране получателя определяет правообладатель.`,
            'Количество кодов этого варианта может быть ограничено: при отсутствии заказ исполняется несколькими кодами того же региона с требуемым суммарным номиналом. Активированный код повторно применить нельзя.',
          ].join('\n\n'),
          keywords: monetary
            ? `${parent.official_name.toLowerCase()} ${denomination} ${r.currency.toLowerCase()}, ${parent.short.toLowerCase()} ${r.name.toLowerCase()} ${denomination}, пополнение ${parent.account.toLowerCase()} ${nominal.toLowerCase()}`
            : `${extra.label.toLowerCase()}, ${parent.short.toLowerCase()} купить, ${parent.official_name.toLowerCase()}`,
          features: [
            monetary ? `Номинал ${nominal} зачисляется на ${parent.balance}` : `${extra.label}: срок активируется в аккаунте получателя`,
            `Для ${parent.account} ${r.account}`,
            'Цифровой код — передаём после оплаты по счёту',
            parent.redeem,
          ],
          ...texts,
          base_price_usd: cost,
          markup_coeff: MARKUP,
          billing: monetary ? `за один код номиналом ${nominal}` : `за один подарок: ${extra.label}`,
          min_quantity: 1,
          price_confidence: 'owner-table',
          checked_at: v.checked_at,
          notes: `Закупка ${cost} USD за код — ${v.source}; цена = закупка × курс ЦБ × 3,0. Вариант родителя ${parent.sku}: своей страницы нет (301 на родителя), в sitemap и фиды не идёт.`,
          status: 'published',
        });
      }
    }
    products.push({
      sku: parent.sku,
      slug: parent.slug,
      name: parent.name,
      official_name: parent.official_name,
      category: 'gift-cards',
      license_type: 'org',
      product_type: 'gift_card',
      short_description: parent.short_description,
      description: parent.description.join('\n\n'),
      keywords: parent.keywords,
      features: parent.features,
      base_price_usd: minCost,
      markup_coeff: MARKUP,
      price_from: true,
      billing: parent.regions.every((r) => r.costs.every((c) => !c[2]))
        ? 'за код выбранного номинала; цена «от» — минимальный номинал'
        : 'за код выбранного варианта; цена «от» — минимальный вариант',
      min_quantity: 1,
      price_confidence: 'owner-table',
      checked_at: v.checked_at,
      notes: `Родительская карточка: страница /product/${parent.slug}, выбор региона и варианта на ней. Закупка родителя = минимальная закупка варианта (${minCost} USD) — даёт цену «от» и переоценивается вместе с вариантами; при изменении таблицы пересобрать пакет. Коэффициент 3,0 — стратегия gift_card. Источник закупок: ${v.source}.`,
      status: 'published',
      sort: 0,
      availability: 'in_stock',
    }, ...variants);
  }
  writeFileSync(resolve(__dir, `catalog/${v.slug}.json`), JSON.stringify({ vendor_entry: v.vendor_entry, products }, null, 1) + '\n');
  console.log(`${v.slug}.json: родителей ${v.parents.length}, позиций ${products.length}`);
}
