/**
 * Единый источник реквизитов и настроек бренда BizSoft.
 * Используется в подвале, контактах, документах, политике ПДн,
 * Organization/LocalBusiness-разметке и в PDF коммерческого предложения.
 * Меняем реквизиты — только здесь.
 */
import { VENDORS } from '../data/vendors';

export interface BankDetails {
  bankName: string;
  account: string; // расчётный счёт
  corrAccount: string; // корреспондентский счёт
  bik: string;
}

export interface SellerDetails {
  brand: string;
  legalName: string;
  shortName: string;
  address: string;
  phone: string;
  phoneHref: string;
  email: string;
  salesEmail: string;
  inn: string;
  ogrnip: string;
  okpo: string;
  okato: string;
  oktmo: string;
  registrationDate: string;
  bank: BankDetails;
}

export const seller: SellerDetails = {
  brand: 'BizSoft',
  legalName: 'Индивидуальный предприниматель Беляев Алексей Васильевич',
  shortName: 'ИП Беляев А.В.',
  address: '115569, Москва, Каширское шоссе 80К1',
  phone: '+7 (964) 716-11-11',
  phoneHref: '+79647161111',
  email: 'AVBelyaev@biz-soft.pro',
  salesEmail: 'hello@biz-soft.pro',
  inn: '507202054051',
  ogrnip: '322774600665109',
  okpo: '2019116499',
  okato: '45296577000',
  oktmo: '45921000',
  registrationDate: '07.11.2022',
  bank: {
    bankName: 'АО «ОТП Банк», г. Москва',
    account: '40802810100510000665',
    corrAccount: '30101810000000000311',
    bik: '044525311',
  },
};

export const site = {
  name: 'BizSoft',
  domain: 'biz-soft.pro',
  url: 'https://biz-soft.pro',
  tagline: 'Легальное ПО для бизнеса по договору и счёту',
  description:
    'BizSoft — поставка подписок и доступа к зарубежным ПО-сервисам для российских юрлиц: по договору, с оплатой по счёту и закрывающими документами через ЭДО.',
  // Срок действия коммерческого предложения по умолчанию (дней)
  quoteValidDays: 14,
  // Дефолтная наценка при привязке к курсу (страховка, если не задана у товара)
  defaultMarkupPercent: 0,
} as const;

/** Главная навигация сайта. */
export const mainNav: { label: string; href: string }[] = [
  { label: 'Каталог', href: '/catalog' },
  { label: 'Как мы работаем', href: '/how-we-work' },
  { label: 'Стоимость', href: '/pricing' },
  { label: 'Документы', href: '/documents' },
  { label: 'База знаний', href: '/blog' },
  { label: 'О нас', href: '/about' },
  { label: 'Контакты', href: '/contacts' },
];

/** Готовые посадочные страницы производителей (для меню «Производители» и /vendors). */
export const vendorLandings: { slug: string; name: string; description: string }[] = [
  // Bespoke-лендинги (отдельные страницы vendors/<slug>.astro)
  { slug: 'jetbrains', name: 'JetBrains', description: 'IDE для разработчиков: IntelliJ IDEA, PyCharm, GoLand, Rider, All Products Pack и 480+ плагинов.' },
  { slug: 'zoom', name: 'Zoom', description: 'Видеоконференцсвязь для бизнеса: тарифы Workplace, вебинары, телефония, КП и документы.' },
  { slug: 'openai', name: 'OpenAI', description: 'ChatGPT для бизнеса: Plus, Pro, Business, Enterprise и OpenAI API — по договору и счёту.' },
  { slug: 'figma', name: 'Figma', description: 'Дизайн-платформа Figma: посадочные места Full, Dev и Collab, Organization и Enterprise.' },
  // Шаблонные лендинги производителей (креативные индустрии) — из src/data/vendors.ts
  ...VENDORS.map((v) => ({ slug: v.slug, name: v.title || v.vendor, description: v.tagline })),
].sort((a, b) => a.name.localeCompare(b.name, 'ru'));

/** Подвал: дополнительные ссылки. */
export const footerNav: { label: string; href: string }[] = [
  { label: 'AI-сервисы для бизнеса', href: '/catalog/ai' },
  { label: 'Решения под задачу', href: '/solutions' },
  { label: 'Кейсы', href: '/cases' },
  { label: 'FAQ', href: '/faq' },
  { label: 'Политика обработки ПДн', href: '/privacy' },
  { label: 'Согласие на обработку ПДн', href: '/consent' },
];

/** ID интеграций аналитики (плейсхолдеры, реальные значения — в .env/прод). */
export const analytics = {
  metrikaId: import.meta.env.PUBLIC_METRIKA_ID || '',
  gaId: import.meta.env.PUBLIC_GA_ID || '',
} as const;
