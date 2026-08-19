/**
 * SEO-эксперимент «snippets-5-vendors» (P0-1, обновлён 19.08.2026):
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
};

/** Анкоры внутренней перелинковки эксперимента (для / и /catalog). */
export const SEO_EXPERIMENT_LINKS: { slug: string; anchor: string }[] = [
  { slug: 'canva', anchor: 'Canva — оплата для юрлиц' },
  { slug: 'depositphotos', anchor: 'Depositphotos — оплата по счёту' },
  { slug: 'coreldraw', anchor: 'CorelDRAW — лицензии для компаний' },
  { slug: 'heygen', anchor: 'HeyGen — тарифы для компаний' },
  { slug: 'marmoset', anchor: 'Marmoset Toolbag — лицензии для команд' },
];
