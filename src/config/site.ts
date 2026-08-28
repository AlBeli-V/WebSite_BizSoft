/**
 * Единый источник реквизитов и настроек бренда BIZSoft.
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

/**
 * Ответственный за заявки по умолчанию.
 *
 * Распоряжение руководителя 21.08.2026: ответственный всегда Беляев Алексей.
 * Живёт в общем конфиге, а не в модуле CRM: заявку заводит и сайт (форма,
 * скачивание КП), а витрине импортировать из src/crm запрещено — границу
 * между CRM и сайтом стережёт tests/crm-isolation.test.ts.
 */
export const defaultLeadOwner = 'Беляев Алексей';

export const seller: SellerDetails = {
  brand: 'BIZSoft',
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
  name: 'BIZSoft',
  domain: 'biz-soft.pro',
  url: 'https://biz-soft.pro',
  tagline: 'Единая точка доступа к ПО и AI-сервисам',
  description:
    'BIZSoft (Business Integration Zone) — единая точка доступа к зарубежным ПО- и AI-сервисам для российских юрлиц: по договору, с оплатой по счёту и закрывающими документами через ЭДО.',
  // Срок действия коммерческого предложения по умолчанию (дней)
  // Срок действия КП — распоряжение руководителя 21.08.2026: неделя от даты
  // скачивания. Дальше цены вендоров и курс расходятся с расчётом.
  quoteValidDays: 7,
  // Дефолтная наценка при привязке к курсу (страховка, если не задана у товара)
  defaultMarkupPercent: 0,
} as const;

/**
 * Налоговый режим продавца — один источник формулировок для всего сайта.
 *
 * С 01.01.2026 порог освобождения от НДС на УСН снижен с 60 до 20 млн ₽
 * дохода за предыдущий год (ст. 145 НК РФ). Оборот 2025 года порог превысил,
 * поэтому с 2026 года ИП — плательщик НДС и применяет пониженную ставку 5%
 * (п. 8 ст. 164 НК РФ): без вычета входящего налога, зато покупатель на
 * общих ставках предъявленный ему НДС к вычету принимает.
 *
 * Формулировки собраны здесь, а не рассыпаны по страницам: до этого на сайте
 * одновременно жили «в т.ч. НДС 5%» на карточке и «при спецрежиме счёт-фактура
 * не выставляется» в блоге. Клиент читает второе и делает вывод, что вычета
 * не будет, — то есть текст сайта работал против собственного предложения.
 */
export const taxation = {
  /** Ставка НДС в ценах, %. Налог включён в цену, не добавляется сверху. */
  vatPercent: 5,
  /** Дата, с которой применяется режим. */
  since: '2026-01-01',
  /** Короткая строка о цене — там, где о налоге говорится вскользь. */
  priceLine: 'Цены указаны с НДС 5% — налог включён, сверху не добавляется.',
  /** Что получает бухгалтерия. Основной документ — УПД. */
  docsLine:
    'Закрывающие: договор, счёт и УПД (или акт со счётом-фактурой) — '
    + 'сумма НДС выделена отдельной строкой.',
  /** Коммерческий довод: предъявленный налог покупатель принимает к вычету. */
  deductionLine:
    'НДС, который мы предъявляем, покупатель на общей системе принимает к вычету.',
} as const;

/**
 * Экономика сделки — ставки и базы расчёта прибыли по КП.
 *
 * Решения руководителя 28.08.2026:
 * - налоговая нагрузка 7% считается от ПОЛНОЙ выручки КП (с НДС);
 * - резерв на конвертацию валюты и международный платёж — 10% от суммы
 *   закупки (не от выручки: при высокой наценке иначе завышается расход);
 * - НДС выделяется из цены (5/105), входящего вычета нет — УСН с
 *   пониженной ставкой (см. taxation выше).
 *
 * Ставки живут в конфиге, а не в модуле расчёта: они меняются чаще формул.
 * Природа 7% в коде сознательно не зафиксирована — только имя строки.
 */
export const economics = {
  /** Налоговая нагрузка, % от полной выручки КП. */
  taxPercent: 7,
  /** Название строки в отчётах — без предположений о правовой природе. */
  taxLabel: 'Налоговая нагрузка',
  /** Резерв на конвертацию и международный платёж, % от суммы закупки. */
  fxReservePercent: 10,
  fxReserveLabel: 'Валютные и платёжные расходы',
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
