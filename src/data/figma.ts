/**
 * Редакторский контент bespoke-лендинга Figma (/vendors/figma).
 * Цены и slug берутся ЖИВЫМИ из Directus по sku FIGMA-*; здесь — обвязка:
 * пояснение по типам мест, сравнение планов, сценарии, FAQ.
 */

export const FIGMA_VENDOR = {
  legalName: 'Figma, Inc.',
  brand: 'Figma',
  brandColor: '#F24E1E',
  site: 'https://www.figma.com',
};

export const FIGMA_SUMMARY =
  'BIZSoft подбирает и оформляет подписки Figma для юридических лиц по новой модели посадочных мест: Full (дизайн), Dev (разработка) и Collab (просмотр и комментирование) на планах Professional, Organization и Enterprise. Доступны договор, счёт и закрывающие документы; оплата в рублях по курсу ЦБ, финальная стоимость фиксируется в КП.';

/** Типы посадочных мест Figma (модель 2024+). */
export const FIGMA_SEATS: { title: string; text: string }[] = [
  { title: 'Full seat (дизайн)', text: 'Полный доступ: создание и редактирование дизайна, прототипы, дизайн-системы и Dev Mode. Для дизайнеров.' },
  { title: 'Dev seat (разработка)', text: 'Dev Mode: инспекция макетов, спецификации, ассеты и хендофф. Для разработчиков без полного редактирования.' },
  { title: 'Collab seat (совместная работа)', text: 'Просмотр, комментирование и работа в FigJam. Для менеджеров, стейкхолдеров и заказчиков.' },
];

/** Мета карточек по sku. badge = план. */
export interface FigmaCardMeta { badge: string; forWhom: string; features: string[] }
export const FIGMA_CARD_META: Record<string, FigmaCardMeta> = {
  'FIGMA-PROF-FULL': { badge: 'Professional', forWhom: 'Дизайнеры небольших команд', features: ['Полный редактор и прототипы', 'Dev Mode', 'Безлимит файлов и проектов', 'Командные библиотеки'] },
  'FIGMA-PROF-DEV': { badge: 'Professional', forWhom: 'Разработчики, хендофф', features: ['Dev Mode: инспекция и хендофф', 'Спецификации и ассеты', 'Комментарии и задачи', 'Экспорт кода и ресурсов'] },
  'FIGMA-PROF-COLLAB': { badge: 'Professional', forWhom: 'Стейкхолдеры, менеджеры', features: ['Просмотр и комментирование', 'Работа в FigJam', 'Участие в воркшопах', 'Без редактирования дизайна'] },
  'FIGMA-ORG-FULL': { badge: 'Organization', forWhom: 'Дизайн-команды организации', features: ['Всё из Professional', 'Общие библиотеки между командами', 'Централизованное администрирование', 'Только годовая оплата'] },
  'FIGMA-ORG-DEV': { badge: 'Organization', forWhom: 'Разработчики организации', features: ['Dev Mode и хендофф', 'Централизованное управление доступом', 'Аналитика использования', 'Только годовая оплата'] },
  'FIGMA-ORG-COLLAB': { badge: 'Organization', forWhom: 'Стейкхолдеры организации', features: ['Просмотр и комментирование', 'FigJam', 'Контроль доступа', 'Только годовая оплата'] },
  'FIGMA-ENT-FULL': { badge: 'Enterprise', forWhom: 'Крупные дизайн-организации', features: ['Всё из Organization', 'Несколько воркспейсов', 'SSO и расширенная безопасность', 'Максимальные AI-кредиты'] },
  'FIGMA-ENT-DEV': { badge: 'Enterprise', forWhom: 'Разработчики Enterprise', features: ['Dev Mode и хендофф', 'SSO и безопасность', 'Централизованное администрирование', 'Только годовая оплата'] },
  'FIGMA-ENT-COLLAB': { badge: 'Enterprise', forWhom: 'Стейкхолдеры Enterprise', features: ['Просмотр и комментирование', 'FigJam', 'SSO и контроль доступа', 'Только годовая оплата'] },
};

/** Порядок карточек. */
export const FIGMA_ORDER = [
  'FIGMA-PROF-FULL', 'FIGMA-PROF-DEV', 'FIGMA-PROF-COLLAB',
  'FIGMA-ORG-FULL', 'FIGMA-ORG-DEV', 'FIGMA-ORG-COLLAB',
  'FIGMA-ENT-FULL', 'FIGMA-ENT-DEV', 'FIGMA-ENT-COLLAB',
];

/** Сравнение планов (цена за Full seat/мес, годовая оплата). */
export const FIGMA_COMPARISON = {
  cols: ['Professional', 'Organization', 'Enterprise'],
  rows: [
    { label: 'Full seat (дизайн)', values: ['$16', '$55', '$90'] },
    { label: 'Dev seat (разработка)', values: ['$12', '$25', '$35'] },
    { label: 'Collab seat (просмотр)', values: ['$3', '$5', '$5'] },
    { label: 'Библиотеки между командами', values: ['—', 'да', 'да'] },
    { label: 'SSO', values: ['—', '—', 'да'] },
    { label: 'Несколько воркспейсов', values: ['—', '—', 'да'] },
    { label: 'Централизованное админ.', values: ['базовое', 'да', 'расширенное'] },
    { label: 'Оплата', values: ['год/месяц', 'только год', 'только год'] },
  ],
};

/** «Что выбрать» — сценарии. */
export const FIGMA_DECISION: { scenario: string; product: string; note: string }[] = [
  { scenario: 'Дизайн-студия до ~15 человек', product: 'Professional (Full + Collab)', note: 'Full места дизайнерам, Collab — менеджерам и клиентам.' },
  { scenario: 'Компания с несколькими командами', product: 'Organization', note: 'Общие библиотеки между командами и централизованное управление.' },
  { scenario: 'Крупная организация с ИБ-требованиями', product: 'Enterprise', note: 'SSO, несколько воркспейсов, расширенная безопасность и аналитика.' },
  { scenario: 'Только передача макетов разработчикам', product: 'Dev seat', note: 'Разработчикам достаточно Dev-мест без полного редактирования дизайна.' },
  { scenario: 'Заказчики и стейкхолдеры', product: 'Collab seat', note: 'Просмотр, комментирование и FigJam без оплаты полного места.' },
];

export const FIGMA_SCENARIOS: { title: string; text: string }[] = [
  { title: 'Продуктовый дизайн', text: 'UI/UX-дизайн интерфейсов, прототипы и дизайн-системы для продуктовых команд.' },
  { title: 'Брендинг и графика', text: 'Айдентика, презентации, маркетинговые материалы и общие библиотеки бренда.' },
  { title: 'Разработка', text: 'Передача макетов в разработку через Dev Mode: спецификации, ассеты, код.' },
  { title: 'Воркшопы', text: 'Брейнштормы, карты пути и совместная работа в FigJam.' },
];

export const FIGMA_FAQ: { q: string; a: string }[] = [
  { q: 'Как купить Figma для юридического лица в России?', a: 'Через BIZSoft: заключаем договор, выставляем счёт, оплата в рублях по безналичному расчёту. Закрывающие документы — в том числе через ЭДО. Подберём набор мест и подготовим КП.' },
  { q: 'Как устроены места (seats) в Figma?', a: 'С 2024 года Figma использует раздельные места: Full (дизайн), Dev (разработка) и Collab (просмотр и комментирование). Вы платите только за нужный тип места каждому сотруднику.' },
  { q: 'Чем отличаются Professional, Organization и Enterprise?', a: 'Professional — для небольших команд. Organization добавляет общие библиотеки между командами и централизованное управление. Enterprise — SSO, несколько воркспейсов, расширенная безопасность и аналитика.' },
  { q: 'Сколько стоит Figma?', a: 'Цена зависит от плана и типа мест. Стоимость в рублях считается от прайса Figma по курсу ЦБ РФ; актуальные цены — в карточках выше, финальная сумма фиксируется в КП.' },
  { q: 'Нужно ли всем покупать Full seat?', a: 'Нет. Дизайнерам — Full, разработчикам — Dev, а менеджерам и заказчикам обычно достаточно Collab-мест. Это заметно снижает стоимость.' },
  { q: 'Можно ли оплатить Figma с расчётного счёта?', a: 'Да. Работаем с юрлицами и ИП по договору и счёту, предоставляем закрывающие документы для бухгалтерии.' },
  { q: 'Входит ли FigJam?', a: 'FigJam доступен в рамках оплаченных мест (в том числе Collab). Отдельная лицензия обычно не требуется.' },
  { q: 'Что нужно для КП?', a: 'Реквизиты компании, контактное лицо, email, план (Professional/Organization/Enterprise) и количество мест каждого типа (Full/Dev/Collab).' },
];
