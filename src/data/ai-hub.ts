/**
 * Единый источник данных AI-хаба (/catalog/ai) и подкатегорий (/catalog/ai/[sub]).
 * См. docs/ai-catalog-redesign.md (Этапы 2 и 8).
 *
 * categorySlug — slug категории в Directus (ai-text, ai-code, …). URL-сегмент sub
 * короче (text, code, …). Пока категории не заведены в Directus, страница подкатегории
 * рендерится как «в подготовке» (noindex).
 */
export interface AiSubcategory {
  /** URL-сегмент: /catalog/ai/<sub> */
  sub: string;
  /** slug категории в Directus */
  categorySlug: string;
  name: string;
  /** короткое описание для плитки */
  short: string;
  /** лид страницы подкатегории */
  intro: string;
  icon: string;
  /** свой title/description вместо шаблонных «<имя> — AI-сервисы для бизнеса» */
  metaTitle?: string;
  metaDescription?: string;
  /** блок «Как выбрать» под карточками: подзаголовок + абзац */
  guide?: { title: string; text: string }[];
  /** свой FAQ вместо двух типовых вопросов про покупку */
  faq?: { q: string; a: string }[];
}

export const aiSubcategories: AiSubcategory[] = [
  { sub: 'text', categorySlug: 'ai-text', name: 'Текстовые AI', icon: '🧠', short: 'AI-ассистенты для текста, знаний и research.', intro: 'Корпоративные текстовые AI-ассистенты: ChatGPT Business, Claude Team/Enterprise, Perplexity Enterprise. Годовые лицензии на юрлицо по счёту, закрывающие через ЭДО.' },
  { sub: 'code', categorySlug: 'ai-code', name: 'Программирование', icon: '💻', short: 'AI для написания и ревью кода.', intro: 'AI-ассистенты для команд разработки: GitHub Copilot Business/Enterprise, Cursor Business. Оформление на юрлицо по счёту с закрывающими через ЭДО.' },
  {
    sub: 'image', categorySlug: 'ai-image', name: 'Изображения', icon: '🎨', short: 'Генерация и дизайн изображений.',
    intro: 'Генеративный AI для изображений: Midjourney, Adobe Firefly, Recraft. Коммерческое использование, годовые лицензии на юрлицо по счёту.',
    // Страница снята Яндексом как малоценная 28.08.2026 (лид + карточки + два
    // типовых вопроса). Текст ниже — разбор «что для чего» и права на результат;
    // план docs/seo/thin-pages-plan-2026-09-03.md, группа F.
    metaTitle: 'Нейросети для изображений: Midjourney, Firefly, Recraft',
    metaDescription: 'Midjourney, Adobe Firefly, Recraft, Leonardo и Krea для компаний: что выбрать под задачу, права на изображения, командные тарифы. Оформление на юрлицо по счёту.',
    guide: [
      {
        title: 'Пять сервисов закрывают разные задачи',
        text: 'Midjourney даёт самый выразительный художественный результат и подходит для концептов, обложек и рекламных визуалов. Adobe Firefly обучен на лицензионном контенте и встроен в Photoshop и Illustrator: его берут там, где юристы спрашивают о происхождении картинки. Recraft умеет вектор, иконки и повторяемый фирменный стиль, поэтому его выбирают для айдентики и иллюстраций к интерфейсам. Leonardo AI позволяет обучать собственные модели и работать через API, Krea — генерировать в реальном времени и повышать разрешение готовых изображений.',
      },
      {
        title: 'Права на результат зависят от тарифа',
        text: 'На платных тарифах сервисы разрешают коммерческое использование сгенерированных изображений, но условия различаются. У Midjourney компаниям с годовой выручкой выше 1 млн долларов по условиям вендора нужен тариф Pro или Mega, а скрытая генерация без публикации в общей ленте доступна только на них. Adobe на корпоративных тарифах Firefly предоставляет защиту от претензий по интеллектуальной собственности. Формулировку по конкретному сервису покажем до оформления, а вопрос о том, охраняется ли результат как объект авторского права в вашей юрисдикции, стоит согласовать с юристом.',
      },
      {
        title: 'Личная подписка или командная',
        text: 'Личный тариф привязан к человеку: при увольнении уходят и доступ, и история генераций. Командные и корпоративные тарифы (Recraft Team и Enterprise, Krea Business, Adobe Firefly для команд) оформляются на организацию, места назначает администратор, счёт один на компанию. У Midjourney командного тарифа нет: места оформляются по числу сотрудников, а работу в общем пространстве организуют через Discord-сервер компании.',
      },
      {
        title: 'Как считать объём',
        text: 'Сервисы лимитируют не количество картинок, а время генерации или запас токенов в месяц. Midjourney продаёт часы быстрой генерации, Leonardo и Recraft — токены или кредиты, Krea — вычислительные единицы. Для оценки достаточно посчитать, сколько итераций делает один дизайнер в день: как правило, младшего тарифа хватает для эпизодической работы, а потоковая генерация под рекламу требует старшего.',
      },
    ],
    faq: [
      { q: 'Какой сервис выбрать для рекламных визуалов, а какой — для иллюстраций в интерфейсе?', a: 'Для рекламных и художественных визуалов чаще берут Midjourney. Для иконок, векторных иллюстраций и единого стиля бренда — Recraft. Если изображения дорабатываются в Photoshop и Illustrator, естественнее Adobe Firefly внутри этих приложений.' },
      { q: 'Можно использовать сгенерированные изображения в коммерческих проектах?', a: 'На платных тарифах — да, с оговорками по каждому сервису: у Midjourney для компаний с выручкой выше 1 млн долларов требуется тариф Pro или Mega, Adobe Firefly на корпоративных тарифах даёт защиту от претензий по интеллектуальной собственности. Условия вендора покажем до счёта.' },
      { q: 'Чтобы генерации не были видны другим пользователям, что нужно?', a: 'У Midjourney скрытый режим генерации входит в тарифы Pro и Mega. У Recraft, Leonardo и Krea изображения по умолчанию видны только в рабочем пространстве владельца или команды, публикация в галерею — по желанию.' },
      { q: 'Подписка оформляется на компанию или на каждого дизайнера?', a: 'Командные тарифы (Recraft Team, Krea Business, Firefly для команд) оформляются на организацию с местами для сотрудников. У Midjourney и Leonardo подписки именные, но оплату и документы всё равно оформляем на юрлицо: одним счётом на нужное число подписок.' },
      { q: 'Цена указана за год?', a: 'Да, для корпоративных AI-подписок мы ориентируемся на годовые тарифы. Рублёвая цена считается от годовой цены вендора по курсу ЦБ РФ на дату счёта; итог фиксируется в счёте.' },
    ],
  },
  { sub: 'video', categorySlug: 'ai-video', name: 'Видео', icon: '🎬', short: 'Генеративное видео и AI-аватары.', intro: 'AI для видео: Runway, HeyGen, Descript. Генеративное видео, аватары и монтаж. Оформление на юрлицо по счёту с закрывающими через ЭДО.' },
  { sub: 'audio', categorySlug: 'ai-audio', name: 'Аудио', icon: '🎙️', short: 'Синтез голоса и обработка звука.', intro: 'AI для аудио: ElevenLabs. Синтез и клонирование голоса, дубляж на многих языках. Годовые лицензии на юрлицо по счёту.' },
  { sub: 'office', categorySlug: 'ai-office', name: 'Офисная продуктивность', icon: '📊', short: 'AI в офисных документах и презентациях.', intro: 'AI для офиса: Microsoft 365 Copilot, Gemini for Workspace, Notion AI, Gamma. Оформление на юрлицо по счёту с закрывающими через ЭДО.' },
  { sub: 'marketing', categorySlug: 'ai-marketing', name: 'Маркетинг', icon: '📣', short: 'AI для контента и креатива.', intro: 'AI для маркетинга: Jasper, Grammarly Business, Canva AI. Контент, единый тон бренда и визуалы. Годовые лицензии на юрлицо по счёту.' },
  { sub: 'enterprise', categorySlug: 'ai-enterprise', name: 'Корпоративные AI', icon: '🏢', short: 'Enterprise-тарифы с SSO и комплаенсом.', intro: 'Корпоративные AI с SSO, SCIM, аудитом и комплаенсом (SOC 2): ChatGPT Enterprise, Claude Enterprise, Microsoft 365 Copilot, Gemini Enterprise, Perplexity Enterprise, GitHub Copilot Enterprise.' },
];

export function getAiSubcategory(sub: string): AiSubcategory | undefined {
  return aiSubcategories.find((s) => s.sub === sub);
}

/**
 * Кросс-коллекция «Корпоративные AI» (/catalog/ai/enterprise).
 *
 * У товара в Directus одна категория, и enterprise-тарифы живут в своих
 * тематических подкатегориях (ai-text, ai-code, ai-office) — иначе они
 * пропали бы из профильной выдачи. Страницу «Корпоративные AI» наполняет
 * этот явный список слагов (замысел — docs/ai-catalog-redesign.md,
 * «кросс-коллекция»): порядок списка задаёт порядок карточек, отсутствующий
 * в базе слаг просто не выводится. Реализовано 30.08.2026 по решению
 * руководителя; до этого страница отдавала «в подготовке» с noindex.
 */
export const aiEnterpriseSlugs: string[] = [
  'openai-enterprise',
  'anthropic-enterprise',
  'mscopilot-m365',
  'gemini-workspace-enterprise',
  'ghcopilot-enterprise',
  'cursor-enterprise',
  'perplexity-enterprise-pro',
  'perplexity-enterprise-max',
  'notion-enterprise',
  'grammarly-enterprise',
];

/**
 * Витрина популярных мировых AI-сервисов в порядке приоритета (Этап 2).
 * href ведёт на карточку товара (slug = sku.toLowerCase()) или на подкатегорию,
 * если карточка ещё не импортирована. Используется на будущей полной странице-хабе.
 */
export interface AiFlagship {
  name: string;
  href: string;
  sub: string;
}

export const aiFlagships: AiFlagship[] = [
  { name: 'ChatGPT Business', href: '/product/chatgpt-business', sub: 'text' },
  { name: 'Claude Team', href: '/product/anthropic-team', sub: 'text' },
  { name: 'Claude Enterprise', href: '/product/anthropic-enterprise', sub: 'enterprise' },
  { name: 'Microsoft 365 Copilot', href: '/product/mscopilot-m365', sub: 'office' },
  { name: 'GitHub Copilot Business', href: '/product/ghcopilot-business', sub: 'code' },
  { name: 'Google Gemini for Workspace', href: '/product/gemini-workspace-standard', sub: 'office' },
  { name: 'Perplexity Enterprise', href: '/product/perplexity-enterprise-pro', sub: 'text' },
  { name: 'Cursor Business', href: '/product/cursor-business', sub: 'code' },
  { name: 'Midjourney', href: '/catalog/ai/image', sub: 'image' },
  { name: 'Adobe Firefly', href: '/product/adobe-ff-teams', sub: 'image' },
  { name: 'Canva AI', href: '/catalog/ai/marketing', sub: 'marketing' },
  { name: 'Runway', href: '/catalog/ai/video', sub: 'video' },
  { name: 'ElevenLabs', href: '/catalog/ai/audio', sub: 'audio' },
  { name: 'Notion AI', href: '/product/notion-business', sub: 'office' },
  { name: 'Grammarly Business', href: '/product/grammarly-business', sub: 'marketing' },
  { name: 'Jasper', href: '/product/jasper-pro', sub: 'marketing' },
  { name: 'Gamma', href: '/product/gamma-pro', sub: 'office' },
];
