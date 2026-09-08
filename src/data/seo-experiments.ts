/**
 * SEO-эксперименты на vendor-страницах.
 *
 * «snippets-5-vendors» (19.08.2026): Canva, Depositphotos, CorelDRAW, HeyGen,
 * Marmoset. Метрика снимается 26.08 и 02.09.
 *
 * «snippets-6-demand» (20.08.2026): Adobe, Autodesk, Procreate, Blackmagic,
 * Midjourney, Clip Studio Paint — отобраны по измеренному коммерческому спросу
 * Вордстата, у всех шести ноль фраз в топ-10 Яндекса при заметной частотности.
 * Эксперименты разведены по датам старта и считаются раздельно; остальные
 * vendor-страницы остаются контрольной группой.
 *
 * Исходная запись эксперимента P0-1 (обновлён 19.08.2026):
 * точечные title/description и FAQ-блок «Как купить {Vendor} на юрлицо»
 * для 5 vendor-страниц. Остальные страницы — контрольная группа, не трогаем.
 *
 * «snippets-3-gap-d» (01.09.2026): Artlist и Motion Array — случай GAP-D по
 * методике (позиция в топ-10, показы есть, переходов нет). Здесь меняется не
 * общая коммерческая формула, а запросная: точная формулировка запроса
 * «оплата {vendor} юридическим лицом» ставится в начало title, description и
 * первого вопроса FAQ. Bespoke-FAQ страницы при этом сохраняется — вопрос
 * добавляется первым (faqAdd), а не заменяет блок целиком.
 * CorelDRAW («оплата coreldraw для россиян», 69 показов, позиция 9,06)
 * добавлен в группу 02.09.2026 — после того как руководитель принял решение
 * по SEO-EXP-001 и страница освободилась от незавершённого эксперимента.
 *
 * Перезапуск SEO-EXP-002 «snippets-2-price-intent» (решение руководителя
 * 03.09.2026). Разбор показал, что у четырёх из шести страниц snippets-6-demand
 * показов в Яндексе нет вовсе (сниппет-тест там невозможен: кликать нечего),
 * а показы кластера Adobe шли на карточки товаров. Две страницы с реальной
 * экспозицией — Clip Studio Paint и Procreate — переведены на запросную
 * формулу под ценовой интент их фактических запросов Вебмастера («сколько
 * стоит … в рублях», «купить … в России», «бессрочная лицензия»): фраза идёт
 * первой в title, description и первом вопросе FAQ (механика faqAdd, как в
 * snippets-3-gap-d). Adobe, Autodesk, Blackmagic и Midjourney остаются с
 * прежними сниппетами вне эксперимента (решение KEEP 03.09.2026); их
 * кластеры — кандидаты на контентный приём, не на сниппет.
 *
 * «snippets-10-expand» (02.09.2026): тираж коммерческой формулы SEO-EXP-001
 * по решению руководителя 02.09.2026 (EXPAND). Десять карточек с наибольшим
 * замеренным спросом вне действующих экспериментов — список выдан
 * expand_candidates() вердикт-движка. Формула та же, что в snippets-5-vendors
 * и snippets-6-demand: менять её при тираже нельзя, иначе тиражируется не то,
 * что оценивалось.
 *
 * «money-a1-query-phrase» (08.09.2026): Capture One, Magnific (Freepik) и
 * Zoom (у Zoom своя страница — правка в src/pages/vendors/zoom.astro).
 * Кластеры отобраны Money Query Opportunity Model
 * (scripts/seo/money_queries.py): свободны от идущих экспериментов, проходят
 * порог экспозиции 3,6 показа в день и не помечены как всплеск или затухание.
 * Меняется только текст в выдаче: во внутреннюю перелинковку
 * (SEO_EXPERIMENT_LINKS) эти страницы намеренно не добавлены — ссылки меняют
 * ранжирование, и тогда вывод о сниппете сделать было бы нельзя.
 *
 * title передаётся с брендом «| BIZSoft» — SeoHead не добавляет суффикс,
 * если бренд уже есть в title (бренд в итоговом HTML ровно один раз).
 * Длина title до 65 символов без учёта «| BIZSoft», description ≤160.
 * Журнал эксперимента: reports/seo/intelligence/seo-experiments.json.
 */
export interface SeoExperiment {
  title: string;
  description: string;
  /** Заголовок FAQ-блока страницы. */
  faqTitle: string;
  /** 3–4 вопроса: счёт и договор, ЭДО, сроки, оплата в рублях по курсу ЦБ. */
  faq?: { q: string; a: string }[];
  /**
   * Вопросы, которые добавляются первыми к собственному FAQ страницы
   * (snippets-3-gap-d). Нужны там, где bespoke-FAQ ценнее шаблонного и
   * заменять его целиком нельзя. Взаимоисключающи с `faq`.
   */
  faqAdd?: { q: string; a: string }[];
}

const desc = (vendor: string) =>
  `Оплатим подписку ${vendor} на вашу компанию в рублях по счёту. Договор, закрывающие документы через ЭДО, доступ за 1–3 дня.`;

const faqFor = (vendor: string): { q: string; a: string }[] => [
  {
    q: `Как купить ${vendor} на юрлицо — по счёту и договору?`,
    a: `Оставьте заявку с тарифом ${vendor} и количеством пользователей. BIZSoft подготовит КП, заключит договор и выставит счёт на вашу организацию — оплата с расчётного счёта, без зарубежной карты.`,
  },
  {
    q: 'Какие закрывающие документы вы предоставляете?',
    a: 'Полный комплект для бухгалтерии: договор, счёт, акт или УПД. Закрывающие документы передаём через ЭДО (Диадок).',
  },
  {
    q: `Как быстро появится доступ к ${vendor} после оплаты?`,
    a: 'Доступ или лицензию передаём в течение 1–3 рабочих дней после поступления оплаты; КП и счёт готовим за 1 рабочий день.',
  },
  {
    q: 'В какой валюте оплата и как считается цена?',
    a: 'Оплата в рублях по безналичному расчёту. Рублёвая цена рассчитывается от прайса вендора по курсу ЦБ РФ на дату счёта.',
  },
];

/**
 * Описание под запросную формулу «оплата {vendor} юридическим лицом»:
 * точная формулировка запроса идёт первой, оффер «счёт, договор, ЭДО» —
 * сразу за ней. Длина ≤160.
 */
const descQuery = (phrase: string) =>
  `${phrase}: счёт, договор и закрывающие документы через ЭДО. Оформим подписку на вашу компанию, оплата в рублях, доступ за 1–3 дня.`;

const descLegal = (vendor: string) => descQuery(`Оплата ${vendor} юридическим лицом`);

/**
 * Первый вопрос FAQ под ценовой интент (перезапуск SEO-EXP-002): запрос
 * «сколько стоит {vendor}» в самом вопросе, в ответе — модель лицензии,
 * рублёвая цена по курсу ЦБ и штатный оффер (счёт, договор, ЭДО, 1–3 дня).
 */
const faqPrice = (vendor: string, tail: string, licensing: string) => [
  {
    q: `Сколько стоит ${vendor} ${tail}?`,
    a: `${licensing} Цена в рублях считается от прайса вендора по курсу ЦБ РФ на дату счёта. BIZSoft заключает договор, выставляет счёт на вашу организацию и передаёт закрывающие документы через ЭДО; доступ — за 1–3 рабочих дня после оплаты.`,
  },
];

/** Вопрос под ту же запросную формулу — добавляется первым к FAQ страницы. */
const faqLegalPay = (vendor: string) => [
  {
    q: `Как оплатить ${vendor} юридическим лицом из России?`,
    a: `Оплата ${vendor} юридическим лицом идёт по безналичному расчёту: BIZSoft заключает договор, выставляет счёт на вашу организацию и передаёт закрывающие документы (акт или УПД) через ЭДО. Зарубежная карта не нужна, рублёвая цена считается от прайса вендора по курсу ЦБ РФ на дату счёта, доступ — за 1–3 рабочих дня после оплаты.`,
  },
];

/**
 * Вопрос под формулу «оплата {vendor} для россиян»: запрос спрашивает не про
 * юрлицо, а про то, что зарубежная оплата из России не проходит, — вопрос
 * отвечает ровно на это, оставаясь в том же оффере.
 */
const faqRussiansPay = (vendor: string) => [
  {
    q: `Как оплатить ${vendor} для россиян, если зарубежная карта не проходит?`,
    a: `Оплата ${vendor} для россиян и российских компаний идёт через BIZSoft по безналичному расчёту: мы заключаем договор, выставляем счёт на вашу организацию и передаём закрывающие документы (акт или УПД) через ЭДО. Зарубежная карта не нужна, рублёвая цена считается от прайса вендора по курсу ЦБ РФ на дату счёта, доступ — за 1–3 рабочих дня после оплаты.`,
  },
];

export const SEO_EXPERIMENTS: Record<string, SeoExperiment> = {
  canva: {
    title: 'Оплата Canva для юридических лиц из России — счёт, договор, ЭДО | BIZSoft',
    description: desc('Canva'),
    faqTitle: 'Как купить Canva на юрлицо',
    faq: faqFor('Canva'),
  },
  depositphotos: {
    title: 'Оплата Depositphotos для юрлиц из России — счёт, договор, ЭДО | BIZSoft',
    description: desc('Depositphotos'),
    faqTitle: 'Как купить Depositphotos на юрлицо',
    faq: faqFor('Depositphotos'),
  },
  // CorelDRAW переведён на запросную формулу 02.09.2026 (см. snippets-3-gap-d
  // ниже): решение по SEO-EXP-001 принято, страница освободилась.
  coreldraw: {
    // «оплата coreldraw для россиян» — 69 показов за период, средняя позиция
    // 9,06, переходов 0; кластер CorelDRAW — 131 087 запросов/мес.
    title: 'Оплата CorelDRAW для россиян — счёт, договор, ЭДО | BIZSoft',
    description: descQuery('Оплата CorelDRAW для россиян'),
    faqTitle: 'Оплата CorelDRAW для россиян',
    faqAdd: faqRussiansPay('CorelDRAW'),
  },
  heygen: {
    title: 'HeyGen — тарифы и оплата на юрлицо в рублях | BIZSoft',
    description: desc('HeyGen'),
    faqTitle: 'Как купить HeyGen на юрлицо',
    faq: faqFor('HeyGen'),
  },
  marmoset: {
    title: 'Marmoset Toolbag 5 — купить лицензию на компанию | BIZSoft',
    description: desc('Marmoset Toolbag'),
    faqTitle: 'Как купить Marmoset Toolbag на юрлицо',
    faq: faqFor('Marmoset Toolbag'),
  },

  // ─── snippets-6-demand, старт 20.08.2026 ───
  // Отобраны по измеренному спросу Вордстата; в скобках — целевая фраза с частотностью.
  adobe: {
    // «adobe купить» — 3 887 запросов в месяц, кластер 23 322
    title: 'Оплата Adobe для юрлиц из России — счёт, договор, ЭДО | BIZSoft',
    description: desc('Adobe Creative Cloud'),
    faqTitle: 'Как купить Adobe на юрлицо',
    faq: faqFor('Adobe'),
  },
  autodesk: {
    // «autodesk license» — 1 800 запросов в месяц, кластер 7 391
    title: 'Лицензии Autodesk для юрлиц из России — счёт и договор | BIZSoft',
    description: desc('Autodesk'),
    faqTitle: 'Как купить Autodesk на юрлицо',
    faq: faqFor('Autodesk'),
  },
  // Adobe, Autodesk, Blackmagic и Midjourney: сниппеты snippets-6-demand
  // оставлены как есть (KEEP 03.09.2026), эксперимент на них закрыт —
  // показов у этих страниц нет, сниппет проверить нечем.
  procreate: {
    // Перезапуск SEO-EXP-002 (snippets-2-price-intent). Реальные запросы
    // Вебмастера: «procreate цена» (5 показов за окно), «прокриэйт цена» (4),
    // «procreate купить в россии» (3), «сколько стоит procreate»; позиции
    // 5–14, переходов 0. Прежняя цель «купить procreate» (823/мес) — B2C
    // (iPad и книги на маркетплейсах), сайт по ней не показывается.
    title: 'Procreate: цена в рублях и покупка в России на компанию | BIZSoft',
    description: 'Сколько стоит Procreate (Прокриэйт) в рублях и как купить в России: разовая покупка для iPad на юрлицо через Apple Business Manager, счёт и ЭДО за 1–3 дня.',
    faqTitle: 'Сколько стоит Procreate и как купить в России',
    faqAdd: faqPrice(
      'Procreate',
      'и как купить его в России на компанию',
      'Procreate и Procreate Dreams — разовая покупка без подписки; для организации закупку проводим через Apple Business Manager (VPP) на юрлицо.',
    ),
  },
  blackmagic: {
    // «davinci resolve купить» — 531 запрос в месяц, кластер 1 354
    title: 'DaVinci Resolve Studio — лицензия на юрлицо по счёту | BIZSoft',
    description: desc('DaVinci Resolve Studio'),
    faqTitle: 'Как купить DaVinci Resolve на юрлицо',
    faq: faqFor('DaVinci Resolve'),
  },
  midjourney: {
    // «midjourney подписка» — 380 запросов в месяц, кластер 1 233
    title: 'Подписка Midjourney для юрлиц — счёт, договор, ЭДО | BIZSoft',
    description: desc('Midjourney'),
    faqTitle: 'Как купить Midjourney на юрлицо',
    faq: faqFor('Midjourney'),
  },
  'clip-studio-paint': {
    // Перезапуск SEO-EXP-002 (snippets-2-price-intent). Реальные запросы
    // Вебмастера: «купить подписку на клип студио пейнт» (7 показов за окно),
    // «клип студио купить лицензию навсегда» (5), «сколько стоит подписка
    // в клип студио» (4), «сколько стоит клип студио в рублях» (3),
    // «бессрочная лицензия клип студио» (3); позиции 6–12, переходов 0.
    // Кириллическое написание бренда — в описании: так спрашивают.
    title: 'Clip Studio Paint: цена бессрочной лицензии и подписки в рублях | BIZSoft',
    description: 'Сколько стоит Clip Studio Paint (Клип Студио Пейнт) в рублях: бессрочная лицензия PRO и EX или подписка. Оформим на компанию по счёту, ЭДО, доступ за 1–3 дня.',
    faqTitle: 'Сколько стоит Clip Studio Paint в рублях',
    faqAdd: faqPrice(
      'Clip Studio Paint',
      'в рублях — бессрочная лицензия или подписка',
      'Бессрочная лицензия PRO или EX — разовый платёж за приобретённую версию; подписка — регулярный платёж на 1 устройство с актуальной версией.',
    ),
  },
  // «snippet-anthropic-demand» (29.08.2026): GAP-D по данным замера 29.08 —
  // кластер «claude купить» 9 944 показов/мес (весь кластер anthropic — 27 231),
  // позиция 7,44, CTR ≈ 0. Точечный title под запрос вместо общего описания.
  anthropic: {
    title: 'Купить Claude для компании — Team и Enterprise на юрлицо | BIZSoft',
    description: desc('Claude'),
    faqTitle: 'Как купить Claude на юрлицо',
    faq: faqFor('Claude'),
  },

  // ─── snippets-3-gap-d, старт 01.09.2026 ───
  // GAP-D по данным Яндекс.Вебмастера за период: позиция в топ-10, показы
  // есть, переходов нет. Частотность указана по каждой правке.
  artlist: {
    // «оплата artlist юридическим лицом» — 66 показов за период, средняя
    // позиция 3,39, переходов 0; кластер Artlist — 4 609 запросов/мес
    // (Вордстат, src/data/vendor-demand.json).
    title: 'Оплата Artlist юридическим лицом — счёт, договор, ЭДО | BIZSoft',
    description: descLegal('Artlist'),
    faqTitle: 'Оплата Artlist юридическим лицом',
    faqAdd: faqLegalPay('Artlist'),
  },
  'motion-array': {
    // «оплата motion array юридическим лицом» — 63 показа за период, средняя
    // позиция 3,13, переходов 0; кластер Motion Array — 990 запросов/мес
    // (Вордстат, src/data/vendor-demand.json).
    title: 'Оплата Motion Array юридическим лицом — счёт, договор, ЭДО | BIZSoft',
    description: descLegal('Motion Array'),
    faqTitle: 'Оплата Motion Array юридическим лицом',
    faqAdd: faqLegalPay('Motion Array'),
  },

  // ─── money-a1-query-phrase, партия 08.09.2026 ───
  // Money Query Opportunity Model (scripts/seo/money_queries.py, разбор —
  // reports/seo/yandex-money-growth-plan.md). Отобраны три кластера, которые
  // одновременно свободны от идущих экспериментов, проходят порог экспозиции
  // 3,6 показа в день и не помечены моделью как всплеск или затухание.
  // Формула не общая: у каждой страницы в заголовок идёт та формулировка,
  // которой спрашивает её собственный кластер, а не единый шаблон.
  'capture-one': {
    // Кластер 211 показов за окно (17,6/день; появился 31.08 и рос в каждой
    // выгрузке), средняя позиция 6,97, переходов 0. Четверть показов кластера
    // (56 из 211) — про то, что платёж не проходит: «оплата capture one без
    // vpn» (13 показов),
    // «оплата capture one российской картой» (11), «capture one для россиян
    // оплата» (16), «продление подписки capture one из россии» (16). В топ-5
    // выдачи — гайды «как оплатить картой» и ключи с Авито и WildBerries;
    // ни один сосед не предлагает продление на юрлицо по счёту.
    title: 'Оплата Capture One юридическим лицом — продление без карты | BIZSoft',
    description: 'Оплата Capture One юридическим лицом и продление подписки без зарубежной карты: счёт в рублях, договор, закрывающие документы через ЭДО, доступ за 1–3 дня.',
    faqTitle: 'Оплата и продление Capture One для юрлица',
    faqAdd: [
      {
        q: 'Как оплатить или продлить Capture One юридическим лицом, если карта не проходит?',
        a: 'Зарубежная карта и VPN не нужны: BIZSoft заключает договор, выставляет счёт на вашу организацию и оформляет подписку или продление Capture One на её аккаунт. Оплата в рублях по безналичному расчёту, рублёвая цена считается от прайса вендора по курсу ЦБ РФ на дату счёта, закрывающие документы передаём через ЭДО, доступ — за 1–3 рабочих дня после оплаты.',
      },
    ],
  },
  freepik: {
    // Кластер 64 показа за окно (5,3/день), средняя позиция 5,14. Ядро —
    // «оплата magnific ai юридическим лицом» (48 показов, позиция 4,58,
    // переходов 0): страница ранжируется по Magnific, а описание говорило
    // про стоковую библиотеку Freepik — текст отвечал не на тот вопрос.
    // Вторая линия запросов — про коммерческую лицензию на генерации
    // («лицензия magnific.com для коммерческого использования»), и это то,
    // чего платёжные сервисы в топ-5 не дают в принципе.
    title: 'Оплата Magnific AI юридическим лицом — счёт, договор, ЭДО | BIZSoft',
    description: 'Оплата Magnific AI юридическим лицом: счёт в рублях, договор и закрывающие через ЭДО. Подписка Freepik Premium с коммерческой лицензией, доступ за 1–3 дня.',
    faqTitle: 'Оплата Magnific AI юридическим лицом',
    faqAdd: [
      {
        q: 'Как оплатить Magnific AI юридическим лицом из России?',
        a: 'Оплата Magnific AI юридическим лицом идёт по безналичному расчёту: BIZSoft заключает договор, выставляет счёт на вашу организацию и оформляет подписку Freepik с доступом к Magnific на её аккаунт. Зарубежная карта не нужна, рублёвая цена считается от прайса вендора по курсу ЦБ РФ на дату счёта, закрывающие документы передаём через ЭДО, доступ — за 1–3 рабочих дня после оплаты.',
      },
      {
        q: 'Подходит ли подписка для коммерческих проектов?',
        a: 'Да: тарифы Freepik Premium и Premium+ дают коммерческую лицензию на материалы и генерации сервиса. Подписка оформляется на вашу организацию, поэтому право использования подтверждается договором и закрывающими документами, а не скриншотом личного кабинета.',
      },
    ],
  },

  // ─── snippets-10-expand, старт 02.09.2026 ───
  // Тираж формулы snippets-5-vendors по решению руководителя 02.09.2026
  // (EXPAND). Страницы — десять карточек с наибольшим замеренным спросом вне
  // действующих экспериментов (expand_candidates(), src/data/vendor-demand.json);
  // в скобках — спрос кластера в месяц. Формула не менялась: тиражируется
  // ровно то, что оценивалось.
  google: {
    // Google — 14 845 866; продаём Google Workspace и Gemini для Workspace
    title: 'Оплата Google Workspace для юрлиц из России — счёт, договор, ЭДО | BIZSoft',
    description: desc('Google Workspace'),
    faqTitle: 'Как купить Google Workspace на юрлицо',
    faq: faqFor('Google Workspace'),
  },
  microsoft: {
    // Microsoft — 4 178 821
    title: 'Оплата Microsoft 365 для юрлиц из России — счёт, договор, ЭДО | BIZSoft',
    description: desc('Microsoft 365'),
    faqTitle: 'Как купить Microsoft 365 на юрлицо',
    faq: faqFor('Microsoft 365'),
  },
  github: {
    // GitHub — 3 636 435
    title: 'Оплата GitHub Copilot для юрлиц из России — счёт, договор, ЭДО | BIZSoft',
    description: desc('GitHub Copilot'),
    faqTitle: 'Как купить GitHub Copilot на юрлицо',
    faq: faqFor('GitHub Copilot'),
  },
  unity: {
    // Unity — 558 386
    title: 'Оплата Unity Pro для юрлиц из России — счёт, договор, ЭДО | BIZSoft',
    description: desc('Unity Pro'),
    faqTitle: 'Как купить Unity Pro на юрлицо',
    faq: faqFor('Unity Pro'),
  },
  docker: {
    // Docker — 451 482
    title: 'Оплата Docker для юрлиц из России — счёт, договор, ЭДО | BIZSoft',
    description: desc('Docker'),
    faqTitle: 'Как купить Docker на юрлицо',
    faq: faqFor('Docker'),
  },
  runway: {
    // Runway — 188 544
    title: 'Оплата Runway для юрлиц из России — счёт, договор, ЭДО | BIZSoft',
    description: desc('Runway'),
    faqTitle: 'Как купить Runway на юрлицо',
    faq: faqFor('Runway'),
  },
  solidworks: {
    // SOLIDWORKS — 164 050
    title: 'Оплата SOLIDWORKS для юрлиц из России — счёт, договор, ЭДО | BIZSoft',
    description: desc('SOLIDWORKS'),
    faqTitle: 'Как купить SOLIDWORKS на юрлицо',
    faq: faqFor('SOLIDWORKS'),
  },
  acronis: {
    // Acronis — 152 256
    title: 'Оплата Acronis для юрлиц из России — счёт, договор, ЭДО | BIZSoft',
    description: desc('Acronis'),
    faqTitle: 'Как купить Acronis на юрлицо',
    faq: faqFor('Acronis'),
  },
  'unreal-engine': {
    // Unreal Engine — 148 486
    title: 'Оплата Unreal Engine для юрлиц из России — счёт, договор, ЭДО | BIZSoft',
    description: desc('Unreal Engine'),
    faqTitle: 'Как купить Unreal Engine на юрлицо',
    faq: faqFor('Unreal Engine'),
  },
  perplexity: {
    // Perplexity — 147 403
    title: 'Оплата Perplexity для юрлиц из России — счёт, договор, ЭДО | BIZSoft',
    description: desc('Perplexity'),
    faqTitle: 'Как купить Perplexity на юрлицо',
    faq: faqFor('Perplexity'),
  },
};

/** Анкоры внутренней перелинковки эксперимента (для / и /catalog). */
export const SEO_EXPERIMENT_LINKS: { slug: string; anchor: string }[] = [
  { slug: 'canva', anchor: 'Canva — оплата для юрлиц' },
  { slug: 'depositphotos', anchor: 'Depositphotos — оплата по счёту' },
  { slug: 'coreldraw', anchor: 'CorelDRAW — лицензии для компаний' },
  { slug: 'heygen', anchor: 'HeyGen — тарифы для компаний' },
  { slug: 'marmoset', anchor: 'Marmoset Toolbag — лицензии для команд' },
  { slug: 'adobe', anchor: 'Adobe Creative Cloud — оплата на юрлицо' },
  { slug: 'autodesk', anchor: 'Autodesk — лицензии для компаний' },
  { slug: 'procreate', anchor: 'Procreate — цена в рублях и покупка в России' },
  { slug: 'blackmagic', anchor: 'DaVinci Resolve Studio — лицензия для студии' },
  { slug: 'midjourney', anchor: 'Midjourney — подписка для юрлиц' },
  { slug: 'clip-studio-paint', anchor: 'Clip Studio Paint — цена лицензии и подписки в рублях' },
  { slug: 'anthropic', anchor: 'Claude — подписка Team для компании' },
  { slug: 'artlist', anchor: 'Artlist — оплата юридическим лицом' },
  { slug: 'motion-array', anchor: 'Motion Array — оплата юридическим лицом' },
  { slug: 'google', anchor: 'Google Workspace — оплата на юрлицо' },
  { slug: 'microsoft', anchor: 'Microsoft 365 — подписка для компании' },
  { slug: 'github', anchor: 'GitHub Copilot — оплата для команды' },
  { slug: 'unity', anchor: 'Unity Pro — подписка для студии' },
  { slug: 'docker', anchor: 'Docker — тарифы Pro и Team по счёту' },
  { slug: 'runway', anchor: 'Runway — оплата на юрлицо' },
  { slug: 'solidworks', anchor: 'SOLIDWORKS — лицензии для предприятия' },
  { slug: 'acronis', anchor: 'Acronis — резервное копирование по счёту' },
  { slug: 'unreal-engine', anchor: 'Unreal Engine — подписка для студии' },
  { slug: 'perplexity', anchor: 'Perplexity — Enterprise Pro для команды' },
];
