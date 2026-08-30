/**
 * Два SEO-эксперимента на vendor-страницах.
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
  faq: { q: string; a: string }[];
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
  coreldraw: {
    title: 'Оплата CorelDRAW для юрлиц из России — счёт, договор, ЭДО | BIZSoft',
    description: desc('CorelDRAW'),
    faqTitle: 'Как купить CorelDRAW на юрлицо',
    faq: faqFor('CorelDRAW'),
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
];
