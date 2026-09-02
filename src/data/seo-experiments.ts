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
 * «snippets-10-expand» (02.09.2026): тираж коммерческой формулы SEO-EXP-001
 * по решению руководителя 02.09.2026 (EXPAND). Десять карточек с наибольшим
 * замеренным спросом вне действующих экспериментов — список выдан
 * expand_candidates() вердикт-движка. Формула та же, что в snippets-5-vendors
 * и snippets-6-demand: менять её при тираже нельзя, иначе тиражируется не то,
 * что оценивалось.
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
  procreate: {
    // «купить procreate» — 823 запроса в месяц, кластер 2 412
    title: 'Procreate для компании — покупка по счёту и договору | BIZSoft',
    description: desc('Procreate'),
    faqTitle: 'Как купить Procreate на юрлицо',
    faq: faqFor('Procreate'),
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
    // «clip studio paint купить» — 417 запросов в месяц, кластер 985
    title: 'Clip Studio Paint для студии — счёт и договор | BIZSoft',
    description: desc('Clip Studio Paint'),
    faqTitle: 'Как купить Clip Studio Paint на юрлицо',
    faq: faqFor('Clip Studio Paint'),
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
  { slug: 'procreate', anchor: 'Procreate — покупка по счёту' },
  { slug: 'blackmagic', anchor: 'DaVinci Resolve Studio — лицензия для студии' },
  { slug: 'midjourney', anchor: 'Midjourney — подписка для юрлиц' },
  { slug: 'clip-studio-paint', anchor: 'Clip Studio Paint — лицензии для студии' },
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
