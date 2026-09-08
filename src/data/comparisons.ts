/**
 * Данные страниц сравнения AI-сервисов (/compare/[slug]).
 * SEO/GEO-кластер: сравнения — источник цитирования у ИИ-поисковиков.
 * Структура страницы: H1 → TL;DR (summaryAnswer) → таблица → «кому что» → FAQ → CTA.
 * Ссылки на карточки: slug = sku.toLowerCase() (см. bulk-import); неизвестные —
 * ведут на подкатегорию каталога.
 */
export interface CompareSide {
  name: string;
  href: string;
  tagline: string;
  bestFor: string[];
}

export interface Comparison {
  slug: string;
  /**
   * Дата последнего содержательного изменения записи — источник lastmod в
   * sitemap. Проставляется при правке записи; даты задним числом не
   * выдумываются. Первичное заполнение 08.09.2026 снято из истории git
   * (git log -L по строкам записи), поэтому каждая дата отражает реальную
   * правку, а не дату файла.
   */
  updated: string;
  metaTitle: string;
  metaDescription: string;
  h1: string;
  /** Прямой краткий вывод для сниппета и ИИ-выдачи. */
  summaryAnswer: string;
  a: CompareSide;
  b: CompareSide;
  /** Строки таблицы сравнения. */
  rows: { label: string; a: string; b: string }[];
  faq: { q: string; a: string }[];
  /** Другие релевантные сравнения. */
  relatedCompare: { label: string; href: string }[];
  category: { name: string; slug: string };
}

const PROC = '/product';
const CAT = '/catalog/ai';

export const comparisons: Comparison[] = [
  {
    slug: 'chatgpt-vs-claude',
    updated: "2026-09-04",
    metaTitle: 'ChatGPT Business vs Claude Team: что выбрать бизнесу',
    metaDescription: 'Сравнение ChatGPT Business и Claude Team для команд: тарифы, годовая цена, безопасность, места. Оформление на юрлицо по счёту, закрывающие через ЭДО.',
    h1: 'ChatGPT Business vs Claude Team',
    summaryAnswer: 'ChatGPT Business — сильнее по экосистеме (GPTs, Codex, генерация изображений и Deep Research) и стартует от 2 мест; Claude Team — глубже в работе с длинным контекстом, анализе документов и разработке через Claude Code, и тоже стартует от 2 мест. Данные не используются для обучения; актуальные рублёвые цены — в карточках каталога BIZSoft. Обе подписки BIZSoft оформляет на юрлицо по счёту с закрывающими через ЭДО.',
    a: { name: 'ChatGPT Business', href: `${PROC}/chatgpt-business`, tagline: 'AI-ассистент OpenAI для команд с широкой экосистемой инструментов.', bestFor: ['Команды, которым нужны GPTs, Codex и генерация изображений', 'Быстрый старт от 2 мест', 'Маркетинг, поддержка, продуктовые команды'] },
    b: { name: 'Claude Team', href: `${PROC}/anthropic-team`, tagline: 'AI-ассистент Anthropic с упором на длинный контекст и работу с кодом.', bestFor: ['Работа с большими документами и длинным контекстом', 'Разработка через Claude Code', 'Аналитика, юристы, R&D'] },
    rows: [
      { label: 'Минимум мест', a: 'от 2', b: 'от 2' },
      { label: 'Данные для обучения моделей', a: 'Не используются', b: 'Не используются' },
      { label: 'Сильные стороны', a: 'GPTs, Codex, Deep Research, генерация изображений', b: 'Длинный контекст, анализ документов, Claude Code' },
      { label: 'SSO', a: 'Только в Enterprise', b: 'Только в Enterprise' },
      { label: 'Оплата по счёту на юрлицо (РФ)', a: 'Да, через BIZSoft', b: 'Да, через BIZSoft' },
    ],
    faq: [
      { q: 'Что выбрать для команды разработки?', a: 'Claude Team — за счёт Claude Code и глубокой работы с длинным контекстом. Для смешанных задач с генерацией изображений и GPTs подойдёт ChatGPT Business.' },
      { q: 'Можно оформить на российское юрлицо?', a: 'Да. BIZSoft оформляет обе подписки на организацию с оплатой по счёту в рублях и закрывающими документами через ЭДО.' },
      { q: 'Используются ли данные компании для обучения?', a: 'Нет. И в ChatGPT Business, и в Claude Team данные рабочих пространств не используются для обучения моделей.' },
    ],
    relatedCompare: [{ label: 'Claude vs Gemini', href: '/compare/claude-vs-gemini' }, { label: 'Perplexity vs ChatGPT', href: '/compare/perplexity-vs-chatgpt' }],
    category: { name: 'Текстовые AI', slug: 'ai/text' },
  },
  {
    slug: 'claude-vs-gemini',
    updated: "2026-09-04",
    metaTitle: 'Claude Team vs Google Gemini for Workspace: сравнение',
    metaDescription: 'Claude Team или Gemini for Workspace для бизнеса: контекст, интеграция с офисом, безопасность, цена за год. Оформление на юрлицо по счёту.',
    h1: 'Claude Team vs Google Gemini for Workspace',
    summaryAnswer: 'Claude Team — самостоятельный AI-ассистент с сильной работой по длинному контексту и коду; Gemini for Workspace встроен в Gmail, Docs, Sheets и Meet и выгоден, если компания уже работает в Google Workspace. Claude Team стартует от 2 мест; актуальные рублёвые цены — в карточках каталога BIZSoft. Обе оформляются на юрлицо по счёту через BIZSoft.',
    a: { name: 'Claude Team', href: `${PROC}/anthropic-team`, tagline: 'Отдельный AI-ассистент Anthropic для команд.', bestFor: ['Длинный контекст и анализ документов', 'Разработка через Claude Code', 'Команды, которым не нужен привязанный офис'] },
    b: { name: 'Gemini for Workspace', href: `${PROC}/gemini-workspace-standard`, tagline: 'AI внутри Google Workspace (Gmail, Docs, Meet).', bestFor: ['Компании на Google Workspace', 'AI прямо в почте и документах', 'Единый админ и защита данных'] },
    rows: [
      { label: 'Формат', a: 'Отдельное приложение/веб', b: 'Встроен в Google Workspace' },
      { label: 'Интеграция с офисом', a: 'Через загрузку файлов', b: 'Нативно в Gmail/Docs/Sheets/Meet' },
      { label: 'Длинный контекст', a: 'Очень сильный', b: 'Хороший' },
      { label: 'Данные для обучения', a: 'Не используются', b: 'Не используются' },
    ],
    faq: [
      { q: 'Что выгоднее, если мы уже в Google Workspace?', a: 'Gemini for Workspace — он встроен в привычные Gmail, Docs и Meet и управляется из той же админ-консоли.' },
      { q: 'А если нужен максимально сильный анализ документов?', a: 'Claude Team — за счёт длинного контекста и качества работы с большими текстами.' },
      { q: 'Как оплатить на юрлицо?', a: 'BIZSoft оформит любую из подписок на организацию по счёту в рублях с закрывающими через ЭДО.' },
    ],
    relatedCompare: [{ label: 'ChatGPT vs Claude', href: '/compare/chatgpt-vs-claude' }, { label: 'Copilot vs Gemini', href: '/compare/copilot-vs-gemini' }],
    category: { name: 'Текстовые AI', slug: 'ai/text' },
  },
  {
    slug: 'cursor-vs-copilot',
    updated: "2026-08-19",
    metaTitle: 'Cursor Business vs GitHub Copilot Business: что выбрать',
    metaDescription: 'Cursor Business или GitHub Copilot Business для команды разработки: возможности, безопасность, цена за год, SSO. Оформление на юрлицо по счёту.',
    h1: 'Cursor Business vs GitHub Copilot Business',
    summaryAnswer: 'Cursor Business — это полноценный AI-редактор кода с агентными правками и командным контекстом; GitHub Copilot Business — AI-ассистент внутри привычных IDE и GitHub с org-политиками и IP-индемнификацией. Актуальные рублёвые цены обеих подписок — в карточках каталога BIZSoft. Обе — с SSO и оформлением на юрлицо по счёту через BIZSoft.',
    a: { name: 'Cursor Business', href: `${PROC}/cursor-business`, tagline: 'AI-редактор кода с агентными правками и командным контекстом.', bestFor: ['Команды, готовые перейти на AI-first IDE', 'Агентные правки по всей кодовой базе', 'Принудительный режим приватности'] },
    b: { name: 'GitHub Copilot Business', href: `${PROC}/ghcopilot-business`, tagline: 'AI-ассистент в привычных IDE и на GitHub.', bestFor: ['Команды на VS Code / JetBrains / GitHub', 'IP-индемнификация и org-политики', 'Минимальная смена процессов'] },
    rows: [
      { label: 'Формат', a: 'Отдельный AI-редактор (форк VS Code)', b: 'Плагин в IDE, CLI, на GitHub' },
      { label: 'SSO', a: 'SAML/OIDC', b: 'Да' },
      { label: 'IP-индемнификация', a: '—', b: 'Да' },
      { label: 'Приватность/политики', a: 'Принудительный режим приватности', b: 'Org-политики, исключения контента' },
      { label: 'Оплата по счёту (РФ)', a: 'Да, через BIZSoft', b: 'Да, через BIZSoft' },
    ],
    faq: [
      { q: 'Нужно ли менять IDE ради Cursor?', a: 'Да, Cursor — отдельный редактор (форк VS Code). Copilot встраивается в уже используемые IDE и не требует смены инструмента.' },
      { q: 'У кого лучше юридическая защита кода?', a: 'GitHub Copilot Business включает IP-индемнификацию и исключения контента на уровне организации.' },
      { q: 'Можно оформить на компанию?', a: 'Да, BIZSoft оформляет обе подписки на юрлицо по счёту в рублях с закрывающими через ЭДО.' },
    ],
    relatedCompare: [{ label: 'ChatGPT vs Claude', href: '/compare/chatgpt-vs-claude' }],
    category: { name: 'Программирование', slug: 'ai/code' },
  },
  {
    slug: 'midjourney-vs-firefly',
    updated: "2026-08-18",
    metaTitle: 'Midjourney vs Adobe Firefly: сравнение для бизнеса',
    metaDescription: 'Midjourney или Adobe Firefly для команды: качество генерации, коммерческая безопасность, интеграции, лицензии. Оформление на юрлицо по счёту.',
    h1: 'Midjourney vs Adobe Firefly',
    summaryAnswer: 'Midjourney даёт наиболее художественное качество генерации и подходит для концептов, рекламных визуалов и мудбордов; Adobe Firefly обучен на лицензионном контенте, безопасен для коммерции, встроен в Creative Cloud и предлагает индемнификацию по IP на корпоративных тарифах. Обе оформляются на юрлицо по счёту через BIZSoft.',
    a: { name: 'Midjourney', href: `${CAT}/image`, tagline: 'Художественная генерация изображений высокого качества.', bestFor: ['Концепт-арт и рекламные визуалы', 'Мудборды и референсы', 'Студии и агентства (Pro/Mega, Stealth)'] },
    b: { name: 'Adobe Firefly', href: `${PROC}/adobe-ff-teams`, tagline: 'Генеративный AI, безопасный для коммерческого использования.', bestFor: ['Коммерческая безопасность контента', 'Работа внутри Creative Cloud', 'Enterprise с требованием индемнификации'] },
    rows: [
      { label: 'Качество/стиль', a: 'Художественный, фотореализм', b: 'Коммерчески «чистый», предсказуемый' },
      { label: 'Обучение на лицензионном контенте', a: 'Нет данных', b: 'Да (безопасно для коммерции)' },
      { label: 'IP-индемнификация', a: '—', b: 'Да (enterprise)' },
      { label: 'Интеграция', a: 'Discord/веб', b: 'Creative Cloud, Express' },
      { label: 'Приватность генераций', a: 'Stealth в Pro/Mega', b: 'Корпоративные контроли' },
    ],
    faq: [
      { q: 'Что безопаснее с точки зрения авторских прав?', a: 'Adobe Firefly — он обучен на лицензионном контенте, а на корпоративных тарифах предоставляет индемнификацию по IP.' },
      { q: 'Что даёт более креативный результат?', a: 'Midjourney традиционно сильнее в художественном качестве и стилистике.' },
      { q: 'Как купить на юрлицо?', a: 'BIZSoft оформит обе подписки на компанию по счёту в рублях с закрывающими через ЭДО.' },
    ],
    relatedCompare: [{ label: 'Midjourney vs Recraft', href: '/compare/midjourney-vs-recraft' }, { label: 'Firefly vs Canva', href: '/compare/firefly-vs-canva' }],
    category: { name: 'Изображения', slug: 'ai/image' },
  },
  {
    slug: 'perplexity-vs-chatgpt',
    updated: "2026-08-19",
    metaTitle: 'Perplexity Enterprise vs ChatGPT Business: сравнение',
    metaDescription: 'Perplexity Enterprise Pro или ChatGPT Business: поиск с источниками vs универсальный ассистент. Цена за год, безопасность, оформление на юрлицо.',
    h1: 'Perplexity Enterprise vs ChatGPT Business',
    summaryAnswer: 'Perplexity Enterprise Pro — это ответный поисковик с проверяемыми источниками и работой по внутренним файлам, идеален для research и аналитики; ChatGPT Business — универсальный ассистент с GPTs, Codex и генерацией контента. Актуальные рублёвые цены обеих подписок — в карточках каталога BIZSoft. Обе оформляются на юрлицо по счёту через BIZSoft.',
    a: { name: 'Perplexity Enterprise Pro', href: `${PROC}/perplexity-enterprise-pro`, tagline: 'Ответный AI-поиск с проверяемыми источниками.', bestFor: ['Research и конкурентная аналитика', 'Ответы со ссылками на источники', 'Поиск по внутренним файлам'] },
    b: { name: 'ChatGPT Business', href: `${PROC}/chatgpt-business`, tagline: 'Универсальный AI-ассистент для команд.', bestFor: ['Генерация и редактирование контента', 'GPTs, Codex, изображения', 'Широкий спектр задач'] },
    rows: [
      { label: 'Главный сценарий', a: 'Поиск и research с источниками', b: 'Универсальный ассистент' },
      { label: 'Источники в ответах', a: 'Да, со ссылками', b: 'Частично (в режиме поиска)' },
      { label: 'Безопасность', a: 'SSO, SOC 2, SCIM', b: 'SSO — в Enterprise' },
      { label: 'Данные для обучения', a: 'Не используются', b: 'Не используются' },
    ],
    faq: [
      { q: 'Что выбрать для аналитиков?', a: 'Perplexity Enterprise Pro — за проверяемые источники и поиск по внутренним данным компании.' },
      { q: 'А для универсальных задач и контента?', a: 'ChatGPT Business — за счёт широкой экосистемы (GPTs, Codex, генерация изображений).' },
      { q: 'Оформление на юрлицо?', a: 'Да, обе подписки BIZSoft оформляет на организацию по счёту с закрывающими через ЭДО.' },
    ],
    relatedCompare: [{ label: 'ChatGPT vs Claude', href: '/compare/chatgpt-vs-claude' }],
    category: { name: 'Текстовые AI', slug: 'ai/text' },
  },
  {
    slug: 'copilot-vs-gemini',
    updated: "2026-08-19",
    metaTitle: 'Microsoft 365 Copilot vs Gemini for Workspace',
    metaDescription: 'Microsoft 365 Copilot или Google Gemini for Workspace: AI в офисе. Цена за год, интеграции, безопасность. Оформление на юрлицо по счёту.',
    h1: 'Microsoft 365 Copilot vs Gemini for Workspace',
    summaryAnswer: 'Выбор определяется вашим офисным стеком: Microsoft 365 Copilot встроен в Word, Excel, PowerPoint, Outlook и Teams и подходит компаниям на Microsoft 365; Gemini for Workspace встроен в Gmail, Docs, Sheets и Meet для компаний на Google Workspace. Актуальные рублёвые цены обеих подписок — в карточках каталога BIZSoft. Обе — на юрлицо по счёту через BIZSoft.',
    a: { name: 'Microsoft 365 Copilot', href: `${PROC}/mscopilot-m365`, tagline: 'AI внутри Microsoft 365 (Word, Excel, Teams).', bestFor: ['Компании на Microsoft 365', 'AI в Excel/PowerPoint/Outlook', 'Агенты Copilot Studio'] },
    b: { name: 'Gemini for Workspace', href: `${PROC}/gemini-workspace-standard`, tagline: 'AI внутри Google Workspace (Gmail, Docs, Meet).', bestFor: ['Компании на Google Workspace', 'AI в почте и документах Google', 'Единый админ Workspace'] },
    rows: [
      { label: 'Офисный стек', a: 'Microsoft 365', b: 'Google Workspace' },
      { label: 'Требует базовую подписку', a: 'Да, лицензию M365', b: 'Входит в тарифы Workspace' },
      { label: 'Агенты/автоматизация', a: 'Copilot Studio', b: 'Gemini в Apps Script/Workspace' },
      { label: 'Данные для обучения', a: 'Не используются', b: 'Не используются' },
    ],
    faq: [
      { q: 'Как выбрать между ними?', a: 'По вашему офисному стеку: на Microsoft 365 — Copilot, на Google Workspace — Gemini. Смешивать смысла мало — AI встроен в разные экосистемы.' },
      { q: 'Нужна ли базовая подписка?', a: 'Microsoft 365 Copilot требует квалифицирующую лицензию M365. Gemini включён в соответствующие тарифы Google Workspace.' },
      { q: 'Оплата на юрлицо?', a: 'Да, BIZSoft оформит обе на организацию по счёту в рублях с закрывающими через ЭДО.' },
    ],
    relatedCompare: [{ label: 'ChatGPT vs Gemini', href: '/compare/chatgpt-vs-gemini' }, { label: 'Claude vs Gemini', href: '/compare/claude-vs-gemini' }],
    category: { name: 'Офисная продуктивность', slug: 'ai/office' },
  },
  {
    slug: 'chatgpt-vs-gemini',
    updated: "2026-08-19",
    metaTitle: 'ChatGPT Business vs Gemini for Workspace: сравнение',
    metaDescription: 'ChatGPT Business или Gemini for Workspace для бизнеса: универсальный ассистент vs AI в офисе Google. Цена за год, оформление на юрлицо.',
    h1: 'ChatGPT Business vs Gemini for Workspace',
    summaryAnswer: 'ChatGPT Business — универсальный ассистент с богатой экосистемой (GPTs, Codex, генерация изображений), не привязанный к офисному пакету; Gemini for Workspace встроен в Google Workspace и выгоден компаниям, уже работающим в Gmail и Docs. Актуальные рублёвые цены обеих подписок — в карточках каталога BIZSoft. Обе — на юрлицо по счёту через BIZSoft.',
    a: { name: 'ChatGPT Business', href: `${PROC}/chatgpt-business`, tagline: 'Универсальный AI-ассистент для команд.', bestFor: ['Универсальные задачи и контент', 'GPTs, Codex, изображения', 'Команды вне Google-экосистемы'] },
    b: { name: 'Gemini for Workspace', href: `${PROC}/gemini-workspace-standard`, tagline: 'AI внутри Google Workspace.', bestFor: ['Компании на Google Workspace', 'AI в почте и документах', 'Единый админ и защита данных'] },
    rows: [
      { label: 'Привязка к офису', a: 'Независим', b: 'Google Workspace' },
      { label: 'Экосистема', a: 'GPTs, Codex, изображения', b: 'Gmail, Docs, Sheets, Meet' },
      { label: 'Данные для обучения', a: 'Не используются', b: 'Не используются' },
    ],
    faq: [
      { q: 'Что универсальнее?', a: 'ChatGPT Business — за счёт GPTs, Codex и генерации изображений, и он не привязан к офисному пакету.' },
      { q: 'А если мы в Google Workspace?', a: 'Тогда Gemini for Workspace удобнее: AI прямо в Gmail и Docs, единый админ.' },
      { q: 'Оформление на компанию?', a: 'Да, обе подписки — на юрлицо по счёту в рублях с закрывающими через ЭДО.' },
    ],
    relatedCompare: [{ label: 'Copilot vs Gemini', href: '/compare/copilot-vs-gemini' }, { label: 'ChatGPT vs Claude', href: '/compare/chatgpt-vs-claude' }],
    category: { name: 'Текстовые AI', slug: 'ai/text' },
  },
  {
    slug: 'runway-vs-heygen',
    updated: "2026-08-18",
    metaTitle: 'Runway vs HeyGen: сравнение AI-видео для бизнеса',
    metaDescription: 'Runway или HeyGen: генеративное видео vs AI-аватары и озвучка. Тарифы, места, коммерческое использование. Оформление на юрлицо по счёту.',
    h1: 'Runway vs HeyGen',
    summaryAnswer: 'Runway — генеративное видео и VFX для креативного продакшна (текст-в-видео, редактирование, эффекты); HeyGen — AI-аватары и говорящие головы для обучающих, маркетинговых и локализованных роликов. Обе имеют командные и Enterprise-тарифы и оформляются на юрлицо по счёту через BIZSoft.',
    a: { name: 'Runway', href: `${CAT}/video`, tagline: 'Генеративное видео и VFX.', bestFor: ['Креативный видеопродакшн', 'Text-to-video и эффекты', 'Студии и агентства'] },
    b: { name: 'HeyGen', href: `${CAT}/video`, tagline: 'AI-аватары и озвучка для видео.', bestFor: ['Обучающие и маркетинговые ролики', 'Локализация и говорящие головы', 'Масштабное производство видео'] },
    rows: [
      { label: 'Главный сценарий', a: 'Генеративное видео/VFX', b: 'Аватары и озвучка' },
      { label: 'Командные тарифы', a: 'Да, за место + Enterprise', b: 'Business + места, Enterprise' },
      { label: 'Коммерческое использование', a: 'На платных тарифах', b: 'На платных тарифах' },
      { label: 'Безопасность (Enterprise)', a: 'Enterprise (annual)', b: 'SAML SSO, SCIM, audit' },
    ],
    faq: [
      { q: 'Что выбрать для обучающих видео с ведущим?', a: 'HeyGen — за счёт AI-аватаров, озвучки и локализации.' },
      { q: 'А для креативного видео и эффектов?', a: 'Runway — генеративное видео и инструменты VFX.' },
      { q: 'Оформление на юрлицо?', a: 'Да, BIZSoft оформит обе на организацию по счёту с закрывающими через ЭДО.' },
    ],
    relatedCompare: [{ label: 'ElevenLabs vs Descript', href: '/compare/elevenlabs-vs-descript' }],
    category: { name: 'Видео', slug: 'ai/video' },
  },
  {
    slug: 'grammarly-vs-jasper',
    updated: "2026-08-19",
    metaTitle: 'Grammarly Business vs Jasper: сравнение для маркетинга',
    metaDescription: 'Grammarly Business или Jasper: помощник письма vs платформа маркетингового контента. Цена за год, безопасность. Оформление на юрлицо по счёту.',
    h1: 'Grammarly Business vs Jasper',
    summaryAnswer: 'Grammarly Business улучшает уже написанные тексты (грамматика, стиль, единый тон бренда) во всех приложениях; Jasper генерирует маркетинговый контент с нуля в фирменном стиле и строит кампании. Актуальные рублёвые цены обеих подписок — в карточках каталога BIZSoft. Обе оформляются на юрлицо по счёту через BIZSoft.',
    a: { name: 'Grammarly Business', href: `${PROC}/grammarly-business`, tagline: 'AI-помощник письма и единый тон бренда.', bestFor: ['Улучшение готовых текстов', 'Единый тон во всех каналах', 'Поддержка, продажи, маркетинг'] },
    b: { name: 'Jasper', href: `${PROC}/jasper-pro`, tagline: 'Платформа генерации маркетингового контента.', bestFor: ['Генерация контента с нуля', 'Кампании и рабочие процессы', 'Маркетинговые команды и агентства'] },
    rows: [
      { label: 'Главная задача', a: 'Улучшение и проверка текста', b: 'Генерация контента и кампаний' },
      { label: 'Где работает', a: 'Браузер и приложения', b: 'Платформа Jasper + интеграции' },
      { label: 'Безопасность (старший тариф)', a: 'SAML SSO, SCIM, SOC 2, ISO', b: 'SSO, API, Agent Builder' },
    ],
    faq: [
      { q: 'Что выбрать для создания контента с нуля?', a: 'Jasper — он генерирует маркетинговые тексты и кампании в фирменном стиле.' },
      { q: 'А для чистоты и единого тона текстов?', a: 'Grammarly Business — проверка, стиль и единый голос бренда во всех приложениях.' },
      { q: 'Оплата на юрлицо?', a: 'Да, обе подписки — на организацию по счёту в рублях с закрывающими через ЭДО.' },
    ],
    relatedCompare: [{ label: 'ChatGPT vs Claude', href: '/compare/chatgpt-vs-claude' }],
    category: { name: 'Маркетинг', slug: 'ai/marketing' },
  },
  {
    slug: 'elevenlabs-vs-descript',
    updated: "2026-08-18",
    metaTitle: 'ElevenLabs vs Descript: сравнение AI-аудио',
    metaDescription: 'ElevenLabs или Descript: синтез голоса vs редактирование подкастов и видео. Тарифы, места, коммерческое использование. Оформление на юрлицо.',
    h1: 'ElevenLabs vs Descript',
    summaryAnswer: 'ElevenLabs — лучший синтез и клонирование голоса, озвучка и дубляж на многих языках; Descript — редактор подкастов и видео с транскрипцией, где текст правит аудио. ElevenLabs берут для генерации речи, Descript — для монтажа и продакшна. Обе имеют командные/Enterprise-тарифы и оформляются на юрлицо через BIZSoft.',
    a: { name: 'ElevenLabs', href: `${CAT}/audio`, tagline: 'Синтез и клонирование голоса, дубляж.', bestFor: ['Озвучка и дубляж', 'Голосовые продукты и IVR', 'Мультиязычный контент'] },
    b: { name: 'Descript', href: `${CAT}/video`, tagline: 'Редактор подкастов и видео с транскрипцией.', bestFor: ['Монтаж подкастов и видео', 'Правка аудио через текст', 'Контент-команды'] },
    rows: [
      { label: 'Главная задача', a: 'Генерация речи', b: 'Редактирование аудио/видео' },
      { label: 'Командные тарифы', a: 'Scale (3), Business (10), Enterprise', b: 'Business, Enterprise (пул мест)' },
      { label: 'Коммерческое использование', a: 'На платных тарифах', b: 'На платных тарифах' },
      { label: 'Годовая экономия', a: '~2 месяца бесплатно', b: 'Годовые тарифы' },
    ],
    faq: [
      { q: 'Что выбрать для озвучки роликов?', a: 'ElevenLabs — за качество синтеза, клонирование голоса и дубляж.' },
      { q: 'А для монтажа подкаста?', a: 'Descript — правка аудио через текст, транскрипция и совместная работа.' },
      { q: 'Оформление на компанию?', a: 'Да, BIZSoft оформит обе на юрлицо по счёту с закрывающими через ЭДО.' },
    ],
    relatedCompare: [{ label: 'Runway vs HeyGen', href: '/compare/runway-vs-heygen' }],
    category: { name: 'Аудио', slug: 'ai/audio' },
  },
  {
    slug: 'midjourney-vs-recraft',
    updated: "2026-08-18",
    metaTitle: 'Midjourney vs Recraft: сравнение генерации изображений',
    metaDescription: 'Midjourney или Recraft: художественная генерация vs брендовый дизайн и вектор. Тарифы, команды, права. Оформление на юрлицо по счёту.',
    h1: 'Midjourney vs Recraft',
    summaryAnswer: 'Midjourney — художественная генерация растровых изображений для концептов и рекламы; Recraft — дизайнерский AI с векторной графикой, единым стилем бренда и командными тарифами (Team от 3 мест, Enterprise). Для айдентики и повторяемого стиля берут Recraft, для креативных визуалов — Midjourney. Обе — на юрлицо через BIZSoft.',
    a: { name: 'Midjourney', href: `${CAT}/image`, tagline: 'Художественная генерация изображений.', bestFor: ['Концепт-арт и реклама', 'Мудборды и референсы', 'Креативные студии'] },
    b: { name: 'Recraft', href: `${CAT}/image`, tagline: 'Дизайнерский AI с вектором и брендстилем.', bestFor: ['Векторная графика и иконки', 'Единый стиль бренда', 'Команды (Team/Enterprise)'] },
    rows: [
      { label: 'Тип графики', a: 'Растр, художественный', b: 'Растр + вектор, брендовый' },
      { label: 'Единый стиль бренда', a: 'Ограниченно', b: 'Да (стили)' },
      { label: 'Командные тарифы', a: 'Bulk 50+', b: 'Team (от 3), Enterprise' },
      { label: 'Коммерческие права', a: 'На платных тарифах', b: 'Полные права на платных' },
    ],
    faq: [
      { q: 'Что выбрать для айдентики и вектора?', a: 'Recraft — он умеет вектор, иконки и повторяемый брендовый стиль.' },
      { q: 'А для креативных визуалов?', a: 'Midjourney — за художественное качество и стилистику.' },
      { q: 'Оплата на юрлицо?', a: 'Да, обе — на организацию по счёту в рублях с закрывающими через ЭДО.' },
    ],
    relatedCompare: [{ label: 'Midjourney vs Firefly', href: '/compare/midjourney-vs-firefly' }],
    category: { name: 'Изображения', slug: 'ai/image' },
  },
  {
    slug: 'notion-vs-chatgpt',
    updated: "2026-08-19",
    metaTitle: 'Notion AI vs ChatGPT Business: сравнение',
    metaDescription: 'Notion AI или ChatGPT Business: AI в базе знаний vs универсальный ассистент. Цена за год, безопасность. Оформление на юрлицо по счёту.',
    h1: 'Notion AI vs ChatGPT Business',
    summaryAnswer: 'Notion AI работает внутри вашей базы знаний и документов Notion — поиск, генерация и автоматизация по корпоративным данным; ChatGPT Business — универсальный ассистент вне конкретного хранилища. Если команда живёт в Notion — берут Notion AI, для универсальных задач — ChatGPT Business. Обе подписки — на юрлицо через BIZSoft; рублёвые цены — в карточках каталога.',
    a: { name: 'Notion AI', href: `${PROC}/notion-business`, tagline: 'AI внутри базы знаний и документов Notion.', bestFor: ['Команды на Notion', 'Поиск и генерация по своим данным', 'Автоматизация задач'] },
    b: { name: 'ChatGPT Business', href: `${PROC}/chatgpt-business`, tagline: 'Универсальный AI-ассистент.', bestFor: ['Универсальные задачи', 'GPTs, Codex, изображения', 'Команды вне Notion'] },
    rows: [
      { label: 'Где работает', a: 'Внутри Notion', b: 'Отдельное приложение/веб' },
      { label: 'Работа по своим данным', a: 'Да, по базе Notion', b: 'Через загрузку/Company Knowledge' },
      { label: 'Данные для обучения', a: 'Не используются', b: 'Не используются' },
    ],
    faq: [
      { q: 'Что выбрать, если мы уже в Notion?', a: 'Notion AI — он работает прямо в вашей базе знаний и документах.' },
      { q: 'А для универсального ассистента?', a: 'ChatGPT Business — за счёт GPTs, Codex и широкой экосистемы.' },
      { q: 'Оформление на юрлицо?', a: 'Да, обе подписки — на компанию по счёту с закрывающими через ЭДО.' },
    ],
    relatedCompare: [{ label: 'ChatGPT vs Claude', href: '/compare/chatgpt-vs-claude' }],
    category: { name: 'Офисная продуктивность', slug: 'ai/office' },
  },
  {
    slug: 'gamma-vs-canva',
    updated: "2026-08-18",
    metaTitle: 'Gamma vs Canva AI: сравнение для презентаций и дизайна',
    metaDescription: 'Gamma или Canva AI: AI-презентации vs визуальный дизайн-редактор. Тарифы, команды, брендинг. Оформление на юрлицо по счёту.',
    h1: 'Gamma vs Canva AI',
    summaryAnswer: 'Gamma генерирует презентации, документы и сайты из текста одним промптом; Canva AI — визуальный редактор с Magic Studio для дизайна, соцсетей и брендов. Для быстрых AI-презентаций берут Gamma, для широкого визуального дизайна — Canva. Обе имеют командные тарифы с SSO и оформляются на юрлицо через BIZSoft.',
    a: { name: 'Gamma', href: `${PROC}/gamma-pro`, tagline: 'AI-генерация презентаций, документов, сайтов.', bestFor: ['Быстрые презентации из текста', 'Питчи и документы', 'Команды с SSO (Business)'] },
    b: { name: 'Canva AI', href: `${CAT}/marketing`, tagline: 'Визуальный дизайн-редактор с AI (Magic Studio).', bestFor: ['Соцсети и маркетинг-дизайн', 'Брендкит и шаблоны', 'Широкий визуальный контент'] },
    rows: [
      { label: 'Главный формат', a: 'Презентации/документы/сайты', b: 'Любой визуальный дизайн' },
      { label: 'AI-генерация из текста', a: 'Ядро продукта', b: 'Magic Studio' },
      { label: 'Командные тарифы', a: 'Business (SSO/SAML)', b: 'Business, Enterprise' },
      { label: 'Брендинг', a: 'Кастомный брендинг', b: 'Brand Kit, контроли' },
    ],
    faq: [
      { q: 'Что быстрее для презентаций?', a: 'Gamma — она собирает презентацию из текстового промпта за минуты.' },
      { q: 'А для широкого дизайна и соцсетей?', a: 'Canva AI — большой редактор с шаблонами, брендкитом и Magic Studio.' },
      { q: 'Оформление на компанию?', a: 'Да, BIZSoft оформит обе на юрлицо по счёту с закрывающими через ЭДО.' },
    ],
    relatedCompare: [{ label: 'Firefly vs Canva', href: '/compare/firefly-vs-canva' }],
    category: { name: 'Офисная продуктивность', slug: 'ai/office' },
  },
  {
    slug: 'firefly-vs-canva',
    updated: "2026-08-29",
    metaTitle: 'Adobe Firefly vs Canva AI: сравнение',
    metaDescription: 'Adobe Firefly или Canva AI: генеративный AI Adobe vs дизайн-платформа с Magic Studio. Коммерческая безопасность, команды. Оформление на юрлицо.',
    h1: 'Adobe Firefly vs Canva AI',
    summaryAnswer: 'Adobe Firefly — генеративный AI, безопасный для коммерции, с интеграцией в Creative Cloud и индемнификацией по IP на enterprise; Canva AI — доступная дизайн-платформа с Magic Studio для соцсетей, презентаций и маркетинга. Профессиональному продакшну ближе Firefly, массовому визуальному контенту — Canva. Обе — на юрлицо через BIZSoft.',
    a: { name: 'Adobe Firefly', href: `${PROC}/adobe-ff-teams`, tagline: 'Генеративный AI, безопасный для коммерции.', bestFor: ['Профессиональный дизайн-продакшн', 'Creative Cloud', 'Enterprise с индемнификацией'] },
    b: { name: 'Canva AI', href: `${CAT}/marketing`, tagline: 'Дизайн-платформа с Magic Studio.', bestFor: ['Соцсети и маркетинг', 'Быстрый дизайн без навыков', 'Команды и брендкит'] },
    rows: [
      { label: 'Позиционирование', a: 'Профессиональный генеративный AI', b: 'Массовая дизайн-платформа' },
      { label: 'Коммерческая безопасность', a: 'Обучен на лицензионном, IP-индемнификация', b: 'Коммерческое использование включено' },
      { label: 'Интеграция', a: 'Creative Cloud, Express', b: 'Собственная платформа' },
      { label: 'Порог входа', a: 'Выше (проф. инструменты)', b: 'Низкий' },
    ],
    faq: [
      { q: 'Что безопаснее для коммерции?', a: 'Adobe Firefly — обучен на лицензионном контенте и предлагает индемнификацию по IP на enterprise.' },
      { q: 'А что проще и быстрее для маркетинга?', a: 'Canva AI — низкий порог входа, шаблоны, брендкит и Magic Studio.' },
      { q: 'Оплата на юрлицо?', a: 'Да, обе — на организацию по счёту в рублях с закрывающими через ЭДО.' },
    ],
    relatedCompare: [{ label: 'Midjourney vs Firefly', href: '/compare/midjourney-vs-firefly' }, { label: 'Gamma vs Canva', href: '/compare/gamma-vs-canva' }],
    category: { name: 'Изображения', slug: 'ai/image' },
  },
  // ─── Партия этапа 1 (29.08.2026): сравнения по измеренным кластерам спроса ───
  {
    slug: 'cursor-vs-windsurf',
    updated: "2026-08-29",
    metaTitle: 'Cursor vs Windsurf: какой AI-редактор выбрать команде',
    metaDescription: 'Сравнение Cursor и Windsurf для команд разработки: агент Cascade, режимы приватности, командные тарифы. Оформление на юрлицо по счёту, закрывающие через ЭДО.',
    h1: 'Cursor vs Windsurf',
    summaryAnswer: 'Оба редактора построены на VS Code и закрывают одну задачу — AI-помощь в разработке. Cursor силён интерактивной работой с кодом и зрелыми командными функциями; Windsurf делает ставку на автономность агента Cascade, который сам доводит многошаговые задачи до результата. Обе подписки BIZSoft оформляет на юрлицо по счёту с закрывающими через ЭДО.',
    a: { name: 'Cursor Business', href: '/vendors/cursor', tagline: 'AI-редактор с сильной интерактивной работой и командным управлением.', bestFor: ['Интерактивные правки и рефакторинг с контролем каждого шага', 'Команды, которым важен зрелый корпоративный тариф', 'Переезд с VS Code без переучивания'] },
    b: { name: 'Windsurf Teams', href: '/vendors/windsurf', tagline: 'AI-среда с агентом Cascade, который ведёт задачи автономно.', bestFor: ['Делегирование задач агенту целиком', 'Многофайловые изменения с минимумом ручной работы', 'Команды, пробующие агентную разработку'] },
    rows: [
      { label: 'База', a: 'VS Code', b: 'VS Code' },
      { label: 'Модель работы', a: 'Интерактивная: разработчик ведёт, AI помогает', b: 'Агентная: Cascade планирует и выполняет сам' },
      { label: 'Приватность кода', a: 'Режим приватности политикой организации', b: 'Zero-data retention политикой организации' },
      { label: 'Командный тариф', a: 'Business: единый счёт, статистика', b: 'Teams: единый счёт, аналитика' },
      { label: 'Оплата по счёту на юрлицо (РФ)', a: 'Да, через BIZSoft', b: 'Да, через BIZSoft' },
    ],
    faq: [
      { q: 'Что выбрать, если команда впервые внедряет AI-редактор?', a: 'Обычно начинают с Cursor — привычный интерактивный процесс. Если цель — отдавать агенту задачи целиком, Windsurf с Cascade раскрывается сильнее.' },
      { q: 'Можно попробовать оба?', a: 'Да: оформим пилотные места на оба редактора в одном договоре — сравните на своих задачах и оставите подходящий.' },
      { q: 'Оплата на российское юрлицо?', a: 'Да. Обе подписки оформляем на организацию с оплатой по счёту в рублях и закрывающими через ЭДО.' },
    ],
    relatedCompare: [{ label: 'Cursor vs GitHub Copilot', href: '/compare/cursor-vs-copilot' }, { label: 'ChatGPT vs Claude', href: '/compare/chatgpt-vs-claude' }],
    category: { name: 'Программирование', slug: 'ai/code' },
  },
  {
    slug: 'chatgpt-vs-grok',
    updated: "2026-08-29",
    metaTitle: 'ChatGPT vs Grok: что выбрать компании',
    metaDescription: 'Сравнение ChatGPT и Grok (xAI) для бизнеса: экосистема инструментов против данных реального времени. Оформление подписок на юрлицо по счёту, закрывающие через ЭДО.',
    h1: 'ChatGPT vs Grok',
    summaryAnswer: 'ChatGPT — самая широкая экосистема рабочих инструментов (GPTs, Codex, генерация изображений, Deep Research) и командные тарифы с управлением местами. Grok выигрывает там, где важна живая повестка: модель xAI опирается на данные реального времени. Для офисных задач и команд чаще берут ChatGPT Business; Grok добавляют аналитике и маркетингу, работающим с актуальными событиями. Обе подписки BIZSoft оформляет на юрлицо.',
    a: { name: 'ChatGPT Business', href: '/product/chatgpt-business', tagline: 'AI-ассистент OpenAI с самой широкой экосистемой инструментов.', bestFor: ['Универсальные офисные задачи и документы', 'Команды от 2 мест с управлением доступом', 'GPTs, Codex, генерация изображений'] },
    b: { name: 'SuperGrok', href: '/vendors/grok', tagline: 'AI-ассистент xAI с данными реального времени.', bestFor: ['Мониторинг новостной и социальной повестки', 'Контент по свежим инфоповодам', 'Режимы углублённого рассуждения'] },
    rows: [
      { label: 'Данные реального времени', a: 'Ограниченно (поиск)', b: 'Да, фирменная сильная сторона' },
      { label: 'Экосистема инструментов', a: 'GPTs, Codex, изображения, Deep Research', b: 'Ассистент и режимы рассуждения' },
      { label: 'Командное управление', a: 'Business: места, консоль, от 2 мест', b: 'Подписки на пользователей' },
      { label: 'Оплата по счёту на юрлицо (РФ)', a: 'Да, через BIZSoft', b: 'Да, через BIZSoft' },
    ],
    faq: [
      { q: 'Что выбрать для отдела маркетинга?', a: 'Если работа строится на актуальных событиях и трендах — Grok. Для универсальной работы с текстами, изображениями и документами — ChatGPT Business.' },
      { q: 'Можно ли купить Grok на компанию из России?', a: 'Да: оформим подписку SuperGrok на ваше юрлицо — договор, счёт в рублях, закрывающие через ЭДО. Цену тарифа подтверждаем на день покупки в КП.' },
      { q: 'А если нужны обе?', a: 'Оформим в одном договоре: ChatGPT Business на команду и SuperGrok на тех, кто работает с повесткой.' },
    ],
    relatedCompare: [{ label: 'ChatGPT vs Claude', href: '/compare/chatgpt-vs-claude' }, { label: 'Kimi vs ChatGPT', href: '/compare/kimi-vs-chatgpt' }],
    category: { name: 'Текстовые AI', slug: 'ai/text' },
  },
  {
    slug: 'kimi-vs-chatgpt',
    updated: "2026-08-29",
    metaTitle: 'Kimi vs ChatGPT: экономичная альтернатива для компании',
    metaDescription: 'Сравнение Kimi (Moonshot AI) и ChatGPT для бизнеса: стоимость владения, длинный контекст, экосистема. Оформление подписок на юрлицо по счёту, закрывающие через ЭДО.',
    h1: 'Kimi vs ChatGPT',
    summaryAnswer: 'Kimi (Moonshot AI) — экономичная альтернатива: на типовых задачах генерации сопоставимое качество при заметно меньшей стоимости владения, плюс фирменный длинный контекст для больших документов. ChatGPT остаётся шире по экосистеме (GPTs, Codex, изображения) и зрелее в командном управлении. Обе подписки BIZSoft оформляет на юрлицо по счёту с закрывающими через ЭДО.',
    a: { name: 'Kimi (подписка)', href: '/vendors/kimi', tagline: 'Ассистент Moonshot AI: длинный контекст и низкая стоимость владения.', bestFor: ['Большие объёмы генерации при ограниченном бюджете', 'Работа с очень длинными документами', 'Агентства и контент-команды'] },
    b: { name: 'ChatGPT Business', href: '/product/chatgpt-business', tagline: 'AI-ассистент OpenAI с самой широкой экосистемой.', bestFor: ['Универсальные офисные сценарии', 'Команды с управлением местами', 'GPTs, Codex и генерация изображений'] },
    rows: [
      { label: 'Стоимость владения', a: 'Заметно ниже на типовых задачах', b: 'Выше, но шире возможности' },
      { label: 'Длинный контекст', a: 'Фирменная сильная сторона', b: 'Есть, лимиты зависят от тарифа' },
      { label: 'Экосистема инструментов', a: 'Ассистент, агентные сценарии, код', b: 'GPTs, Codex, изображения, Deep Research' },
      { label: 'Оплата по счёту на юрлицо (РФ)', a: 'Да, через BIZSoft', b: 'Да, через BIZSoft' },
    ],
    faq: [
      { q: 'Насколько Kimi дешевле?', a: 'На типовых задачах стоимость владения заметно ниже западных аналогов; точное сравнение под ваш объём приложим к КП вместе с актуальными тарифами обоих вендоров.' },
      { q: 'Кому Kimi подходит лучше всего?', a: 'Агентствам и командам с большим объёмом генерации, где экономика важнее экосистемы, и тем, кто работает с очень длинными документами.' },
      { q: 'Оплата на российское юрлицо?', a: 'Да. Обе подписки оформляем на организацию: договор, счёт в рублях, закрывающие через ЭДО.' },
    ],
    relatedCompare: [{ label: 'ChatGPT vs Grok', href: '/compare/chatgpt-vs-grok' }, { label: 'ChatGPT vs Claude', href: '/compare/chatgpt-vs-claude' }],
    category: { name: 'Текстовые AI', slug: 'ai/text' },
  },
  {
    slug: 'fl-studio-vs-ableton',
    updated: "2026-08-29",
    metaTitle: 'FL Studio vs Ableton Live: какую DAW выбрать',
    metaDescription: 'Сравнение FL Studio и Ableton Live для студий: модель лицензий, сценарии, редакции и цены. Оформление покупки на юрлицо по счёту, закрывающие через ЭДО.',
    h1: 'FL Studio vs Ableton Live',
    summaryAnswer: 'FL Studio силён в продюсировании электронной музыки из MIDI и сэмплов, с бессрочной лицензией и пожизненными бесплатными обновлениями. Ableton Live — единственная DAW, одинаково рассчитанная на студию и живое выступление (сессионный режим). Обе лицензии бессрочные; BIZSoft оформляет покупку на юрлицо по счёту с закрывающими через ЭДО.',
    a: { name: 'FL Studio Producer', href: '/product/fl-studio-producer', tagline: 'Культовая DAW c пожизненными бесплатными обновлениями.', bestFor: ['Продюсирование электронной музыки', 'Учебные центры и студии', 'Покупка «раз и навсегда» — все версии бесплатно'] },
    b: { name: 'Ableton Live 12 Standard', href: '/product/ableton-live-standard', tagline: 'DAW для студии и сцены с сессионным режимом.', bestFor: ['Живые выступления и диджеинг', 'Экспериментальный саунд-дизайн', 'Работа с Max for Live (Suite)'] },
    rows: [
      { label: 'Модель лицензии', a: 'Бессрочная + все будущие версии бесплатно', b: 'Бессрочная, апгрейд версии со скидкой' },
      { label: 'Живое выступление', a: 'Возможно', b: 'Сессионный режим — фирменная сила' },
      { label: 'Сильная сторона', a: 'Секвенсор и пиано-ролл, скорость идей', b: 'Сцена + студия, Max for Live' },
      { label: 'Редакции', a: 'Fruity / Producer / Signature / All Plugins', b: 'Intro / Standard / Suite' },
      { label: 'Оплата по счёту на юрлицо (РФ)', a: 'Да, через BIZSoft', b: 'Да, через BIZSoft' },
    ],
    faq: [
      { q: 'Что выбрать студии электронной музыки?', a: 'Для чистого продюсирования из MIDI чаще берут FL Studio; если артисты выступают живьём — Ableton Live с сессионным режимом.' },
      { q: 'Обе лицензии бессрочные?', a: 'Да. У FL Studio все будущие версии бесплатны (Lifetime Free Updates), у Ableton апгрейд на следующую версию — со скидкой вендора.' },
      { q: 'Можно оформить на организацию?', a: 'Да: договор, счёт в рублях, закрывающие через ЭДО. Поставим пакет лицензий на класс или студию.' },
    ],
    relatedCompare: [{ label: 'ElevenLabs vs Descript', href: '/compare/elevenlabs-vs-descript' }],
    category: { name: 'Звук, видео и медиа', slug: 'media' },
  },
];

export function getComparison(slug: string): Comparison | undefined {
  return comparisons.find((c) => c.slug === slug);
}
