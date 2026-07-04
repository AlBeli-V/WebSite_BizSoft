/**
 * Редакторский контент посадочной страницы JetBrains (/vendors/jetbrains).
 * Цены и slug берутся ЖИВЫМИ из Directus (по sku JB-*, кроме плагинов JB-PLG-*);
 * здесь — бейджи, «для кого», ключевые функции, таблицы сравнения, decision matrix,
 * быстрый подбор, блоки AI / Team tools / плагины / управление лицензиями,
 * сценарии, сегменты, возражения и FAQ.
 * Спорные характеристики помечены «уточняется перед КП» — без обещаний.
 * Структура контента — по ТЗ TZ-lending-JetBrains.md (разделы C, D, F, G, H, I).
 */

export const JETBRAINS_VENDOR = {
  legalName: 'JetBrains s.r.o.',
  brand: 'JetBrains',
  brandColor: '#FB0F60',
  site: 'https://www.jetbrains.com',
};

/** Мета карточек по sku (порядок отображения — по sort из БД). */
export interface JetBrainsCardMeta {
  badge: string;
  forWhom: string;
  features: string[];
  /** короткое примечание-предупреждение (если есть) */
  check?: string;
  /** CTA-подпись на карточке */
  cta?: string;
}

export const JETBRAINS_CARD_META: Record<string, JetBrainsCardMeta> = {
  'JB-ALL-PACK-ORG': {
    badge: 'все продукты',
    forWhom: 'Команды с разнородным стеком и несколькими языками',
    features: ['Все настольные IDE JetBrains', 'Инструменты для .NET и AI Pro *', 'Все языки и платформы', 'Управление лицензиями', 'Годовая подписка на пользователя'],
    cta: 'Получить КП на All Products Pack',
    check: 'Состав пакета уточняется перед КП — может обновляться вендором.',
  },
  'JB-IDEA-ULT-ORG': {
    badge: 'Java / Kotlin',
    forWhom: 'Backend- и fullstack-команды на JVM-стеке',
    features: ['Java, Kotlin, Scala, Groovy', 'Spring и Jakarta EE', 'Работа с базами данных', 'Встроенный профилировщик', 'Docker и Kubernetes'],
    cta: 'Получить КП на IntelliJ IDEA Ultimate',
  },
  'JB-DOTULTIMATE-ORG': {
    badge: '.NET',
    forWhom: 'Команды .NET: разработка, анализ и профилирование',
    features: ['Rider и ReSharper', 'Профилировщики dotTrace и dotMemory', 'Покрытие тестами dotCover', 'C#, F#, VB.NET', 'Поставка по договору'],
    cta: 'Получить КП на dotUltimate',
  },
  'JB-RIDER-ORG': {
    badge: '.NET / Unity',
    forWhom: '.NET- и геймдев-команды, кроссплатформенная разработка',
    features: ['Кроссплатформенная IDE для .NET', 'Поддержка Unity и Unreal', 'Редактирование C# и F#', 'Встроенный отладчик', 'Windows, macOS, Linux'],
    cta: 'Получить КП на Rider',
  },
  'JB-RESHARPER-ORG': {
    badge: 'Visual Studio',
    forWhom: '.NET-команды, работающие в Visual Studio',
    features: ['Расширение для Visual Studio', 'Сотни инспекций кода', 'Рефакторинг C#', 'Навигация и генерация кода', 'Модульное тестирование'],
    cta: 'Получить КП на ReSharper',
    check: 'Требуется установленная Visual Studio.',
  },
  'JB-PYCHARM-PRO-ORG': {
    badge: 'Python',
    forWhom: 'Python-разработчики и дата-сайентисты',
    features: ['Python, Django, Flask', 'Поддержка Jupyter', 'Работа с базами данных', 'Виртуальные окружения', 'Научные библиотеки'],
    cta: 'Получить КП на PyCharm Pro',
  },
  'JB-GOLAND-ORG': {
    badge: 'Go',
    forWhom: 'Backend- и DevOps-команды на Go',
    features: ['Разработка на Go', 'Отладчик и профилировщик', 'Поддержка Go Modules', 'Работа с Docker', 'gRPC и микросервисы'],
    cta: 'Получить КП на GoLand',
  },
  'JB-WEBSTORM-ORG': {
    badge: 'JS / TS',
    forWhom: 'Frontend- и fullstack-команды',
    features: ['JavaScript и TypeScript', 'React, Angular, Vue', 'Node.js', 'Отладка и тесты', 'Интеграция с npm'],
    cta: 'Получить КП на WebStorm',
  },
  'JB-PHPSTORM-ORG': {
    badge: 'PHP',
    forWhom: 'Веб-команды на PHP',
    features: ['Разработка на PHP', 'Laravel и Symfony', 'WordPress и Drupal', 'Отладка с Xdebug', 'Поддержка фронтенда'],
    cta: 'Получить КП на PhpStorm',
  },
  'JB-RUBYMINE-ORG': {
    badge: 'Ruby',
    forWhom: 'Команды на Ruby и Ruby on Rails',
    features: ['Разработка на Ruby', 'Поддержка Ruby on Rails', 'Отладчик и тесты', 'Работа с базами данных', 'RVM/rbenv и Docker'],
    cta: 'Получить КП на RubyMine',
  },
  'JB-RUSTROVER-ORG': {
    badge: 'Rust',
    forWhom: 'Команды системного и сетевого ПО на Rust',
    features: ['Разработка на Rust', 'Интеграция с Cargo', 'Встроенный отладчик', 'Анализ ошибок компилятора', 'WebAssembly и embedded'],
    cta: 'Получить КП на RustRover',
  },
  'JB-CLION-ORG': {
    badge: 'C / C++',
    forWhom: 'Команды системного, прикладного и embedded ПО',
    features: ['Разработка на C и C++', 'Поддержка CMake', 'Встроенный отладчик (GDB/LLDB)', 'Статический анализ', 'Google Test и Catch'],
    cta: 'Получить КП на CLion',
  },
  'JB-DATAGRIP-ORG': {
    badge: 'SQL / БД',
    forWhom: 'Инженеры данных, аналитики и разработчики',
    features: ['Работа с SQL и СУБД', 'Десятки баз данных', 'Умное автодополнение SQL', 'Редактор данных', 'Диаграммы связей'],
    cta: 'Получить КП на DataGrip',
  },
};

/** Таблица сравнения: All Products Pack vs отдельная IDE. «*» — проверить перед КП. */
export const JETBRAINS_COMPARISON = {
  cols: ['All Products Pack', 'Отдельная IDE', 'dotUltimate'],
  rows: [
    { label: 'Когда выгоднее', values: ['Смешанный стек, fullstack', 'Один язык или задача', '.NET-команды'] },
    { label: 'Состав', values: ['Все настольные IDE + .NET-инструменты + AI Pro *', 'Одна выбранная IDE', 'Rider + ReSharper + профилировщики'] },
    { label: 'Языки / стек', values: ['Все языки', 'Один язык/стек', 'Только .NET'] },
    { label: 'Профилировщики', values: ['входят *', 'зависит от IDE *', 'dotTrace, dotMemory, dotCover'] },
    { label: 'Работа с БД', values: ['DataGrip входит', 'зависит от IDE *', 'через Rider'] },
    { label: 'Лицензия', values: ['на пользователя в год', 'на пользователя в год', 'на пользователя в год'] },
    { label: 'Управление лицензиями', values: ['JetBrains Account / сервер', 'JetBrains Account / сервер', 'JetBrains Account / сервер'] },
  ],
};

/**
 * Decision matrix «Какой JetBrains выбрать» (раздел F ТЗ).
 * scenario — язык/стек/сценарий; product — рекомендуемый; alt — альтернатива;
 * note — объяснение простым языком; slug = sku.toLowerCase() для ссылки на карточку.
 */
export const JETBRAINS_DECISION: { scenario: string; product: string; alt?: string; slug?: string; note: string }[] = [
  { scenario: 'Java / Kotlin (JVM)', product: 'IntelliJ IDEA Ultimate', alt: 'All Products Pack', slug: 'jb-idea-ult-org', note: 'Лучшая IDE для серверной разработки на JVM: Spring, Jakarta EE, базы данных и профилирование.' },
  { scenario: 'Python (web / скрипты)', product: 'PyCharm Pro', alt: 'All Products Pack', slug: 'jb-pycharm-pro-org', note: 'Профессиональная среда для Python и web: Django, Flask, работа с данными.' },
  { scenario: 'Data science / ноутбуки', product: 'PyCharm Pro + Datalore', alt: 'PyCharm Pro', slug: 'jb-pycharm-pro-org', note: 'PyCharm для кода, Datalore для совместных Jupyter-ноутбуков в браузере.' },
  { scenario: 'Frontend JS / TS', product: 'WebStorm', alt: 'All Products Pack', slug: 'jb-webstorm-org', note: 'Заточена под React, Angular, Vue и Node.js.' },
  { scenario: 'PHP', product: 'PhpStorm', alt: 'All Products Pack', slug: 'jb-phpstorm-org', note: 'Понимает Laravel, Symfony и CMS, поддерживает фронтенд в одном окне.' },
  { scenario: '.NET в отдельной IDE', product: 'Rider', alt: 'dotUltimate', slug: 'jb-rider-org', note: 'Кроссплатформенная IDE для C# и F# на Windows, macOS и Linux.' },
  { scenario: '.NET в Visual Studio', product: 'ReSharper', alt: 'dotUltimate', slug: 'jb-resharper-org', note: 'Усиливает уже используемую Visual Studio: инспекции, рефакторинг, навигация.' },
  { scenario: 'Unity / геймдев', product: 'Rider', alt: 'dotUltimate', slug: 'jb-rider-org', note: 'Глубокая интеграция с Unity и Unreal Engine.' },
  { scenario: 'C / C++ / embedded', product: 'CLion', alt: 'All Products Pack', slug: 'jb-clion-org', note: 'CMake, отладчик GDB/LLDB и нативный код для системного и встраиваемого ПО.' },
  { scenario: 'Go', product: 'GoLand', alt: 'All Products Pack', slug: 'jb-goland-org', note: 'Заточена под Go, микросервисы, gRPC и Kubernetes.' },
  { scenario: 'Ruby / Rails', product: 'RubyMine', alt: 'All Products Pack', slug: 'jb-rubymine-org', note: 'Понимает динамику Ruby и Rails, поддерживает RSpec и базы данных.' },
  { scenario: 'Rust', product: 'RustRover', alt: 'CLion', slug: 'jb-rustrover-org', note: 'Учитывает владение и заимствование Rust, интеграция с Cargo и WebAssembly.' },
  { scenario: 'SQL / базы данных', product: 'DataGrip', alt: 'IDE со встроенной БД', slug: 'jb-datagrip-org', note: 'Один клиент для десятков СУБД: PostgreSQL, MySQL, Oracle, SQL Server и других.' },
  { scenario: 'Несколько языков / весь стек', product: 'All Products Pack', alt: 'Несколько отдельных IDE', slug: 'jb-all-pack-org', note: 'Один SKU вместо набора лицензий — когда команда работает с разными технологиями.' },
  { scenario: 'AI-ассистент', product: 'JetBrains AI (Pro / Ultimate)', alt: 'AI Free', note: 'ИИ в IDE; доступность и лимиты зависят от региона и провайдеров — уточняется перед КП.' },
  { scenario: 'CI/CD', product: 'TeamCity', alt: 'внешний CI', note: 'Сервер непрерывной интеграции и доставки. Цена по запросу.' },
  { scenario: 'Трекер задач', product: 'YouTrack', alt: 'внешний трекер', note: 'Гибкий трекер задач и проектов; для небольших команд есть бесплатный тариф.' },
  { scenario: 'Статанализ в CI/CD', product: 'Qodana', alt: 'внешний линтер', note: 'Инспекции JetBrains в пайплайне; есть бесплатная Community-версия.' },
  { scenario: 'Покупка на 10 пользователей', product: 'All Products Pack', alt: 'Набор отдельных IDE', note: 'Для смешанного стека часто выгоднее единый пакет — посчитаем оба варианта в КП.' },
  { scenario: 'Продление', product: 'Продление текущей подписки', alt: 'Апгрейд до APP', note: 'Сохраняем непрерывность подписки — уточните текущий состав и дату окончания.' },
];

/**
 * Быстрый подбор по стеку (раздел D2 ТЗ): язык/задача → рекомендуемый продукт.
 * target — slug карточки (#products) или якорь секции для прокрутки.
 */
export interface JetBrainsPick {
  label: string;
  product: string;
  /** slug карточки для прокрутки к ней; либо якорь секции (#ai, #team) */
  target?: string;
  /** значение для предзаполнения формы КП */
  query: string;
}

export const JETBRAINS_QUICK_PICKS: JetBrainsPick[] = [
  { label: 'Java / Kotlin', product: 'IntelliJ IDEA Ultimate', target: 'jb-idea-ult-org', query: 'IntelliJ IDEA Ultimate (Java/Kotlin)' },
  { label: 'Python', product: 'PyCharm Pro', target: 'jb-pycharm-pro-org', query: 'PyCharm Pro (Python)' },
  { label: 'JS / TS', product: 'WebStorm', target: 'jb-webstorm-org', query: 'WebStorm (JavaScript/TypeScript)' },
  { label: 'PHP', product: 'PhpStorm', target: 'jb-phpstorm-org', query: 'PhpStorm (PHP)' },
  { label: '.NET', product: 'Rider или ReSharper', target: 'jb-rider-org', query: '.NET — Rider / ReSharper / dotUltimate' },
  { label: 'C / C++', product: 'CLion', target: 'jb-clion-org', query: 'CLion (C/C++)' },
  { label: 'Go', product: 'GoLand', target: 'jb-goland-org', query: 'GoLand (Go)' },
  { label: 'Ruby', product: 'RubyMine', target: 'jb-rubymine-org', query: 'RubyMine (Ruby)' },
  { label: 'Rust', product: 'RustRover', target: 'jb-rustrover-org', query: 'RustRover (Rust)' },
  { label: 'SQL / данные', product: 'DataGrip', target: 'jb-datagrip-org', query: 'DataGrip (SQL/БД)' },
  { label: 'CI/CD', product: 'TeamCity', target: '#team', query: 'TeamCity (CI/CD)' },
  { label: 'Управление задачами', product: 'YouTrack', target: '#team', query: 'YouTrack (трекер задач)' },
  { label: 'Контроль качества', product: 'Qodana', target: '#team', query: 'Qodana (статанализ)' },
  { label: 'ИИ-ассистент', product: 'JetBrains AI', target: '#ai', query: 'JetBrains AI (Pro/Ultimate)' },
  { label: 'Смешанный стек', product: 'All Products Pack', target: 'jb-all-pack-org', query: 'All Products Pack (мультистек)' },
];

/**
 * IDE и инструменты по стеку разработки (раздел G ТЗ).
 * Короткое описание продукта под язык — для блока «по стеку».
 */
export const JETBRAINS_STACK: { lang: string; product: string; text: string }[] = [
  { lang: 'Java / Kotlin', product: 'IntelliJ IDEA Ultimate', text: 'Spring, Jakarta EE, профилирование и работа с базами данных для серверной и fullstack-разработки на JVM.' },
  { lang: 'Python', product: 'PyCharm Pro', text: 'Django и Flask, Jupyter и работа с данными — для веб-разработки и анализа данных на Python.' },
  { lang: 'JS / TS', product: 'WebStorm', text: 'React, Angular, Vue и Node.js, отладка и тесты — для современного фронтенда и fullstack.' },
  { lang: 'PHP', product: 'PhpStorm', text: 'Laravel, Symfony, WordPress и Drupal, Xdebug и фронтенд в одном окне.' },
  { lang: '.NET', product: 'Rider / ReSharper / dotUltimate', text: 'Rider — кроссплатформенная IDE; ReSharper — для Visual Studio; dotUltimate — полный набор инструментов.' },
  { lang: 'C / C++', product: 'CLion', text: 'CMake, отладчик и статический анализ для системного, прикладного и встраиваемого ПО.' },
  { lang: 'Go', product: 'GoLand', text: 'Go Modules, отладчик, профилировщик, Docker и Kubernetes — для микросервисов и сетевых приложений.' },
  { lang: 'Ruby', product: 'RubyMine', text: 'Ruby on Rails, RSpec и базы данных — для веб-приложений и API на Ruby.' },
  { lang: 'Rust', product: 'RustRover', text: 'Cargo, отладчик и анализ ошибок компилятора — для безопасного системного и сетевого кода.' },
  { lang: 'SQL / БД', product: 'DataGrip', text: 'Десятки СУБД из единого интерфейса: PostgreSQL, MySQL, Oracle, SQL Server, ClickHouse и другие.' },
];

/**
 * JetBrains AI — тарифы и региональный caveat (раздел D4 / N ТЗ).
 * Цены AI Pro / Ultimate — «по запросу», без конкретных чисел.
 */
export const JETBRAINS_AI = {
  intro:
    'JetBrains AI — это ИИ-ассистент, встроенный в IDE JetBrains: контекстное автодополнение, генерация и объяснение кода, рефакторинг, написание тестов и работа с документацией. Автодополнение в большинстве случаев не расходует квоту; чат, генерация кода и продвинутые функции используют ИИ-кредиты.',
  tiers: [
    { name: 'AI Free', price: 'Бесплатно', text: 'Базовый тариф: автодополнение без расхода кредитов и небольшая квота на чат и генерацию.' },
    { name: 'AI Pro', price: 'Цена по запросу', text: 'Расширенные лимиты и доступ к облачным моделям; по данным JetBrains входит в All Products Pack.' },
    { name: 'AI Ultimate', price: 'Цена по запросу', text: 'Максимальные лимиты и агентные сценарии для интенсивной ИИ-нагрузки.' },
  ],
  caveat:
    'Важно: доступность ИИ-функций зависит от региона и условий сторонних провайдеров. Мы не обещаем работу ИИ в конкретной локации — доступность и актуальные лимиты уточняйте у менеджера перед покупкой.',
  caveatUrl: 'https://www.jetbrains.com/legal/docs/terms/jetbrains-ai/service-territory/',
};

/**
 * Командные инструменты JetBrains (раздел E / G ТЗ).
 * Все — «цена по запросу»; у YouTrack и Qodana есть бесплатные тарифы.
 */
export const JETBRAINS_TEAM: { name: string; sku: string; tagline: string; text: string; note: string }[] = [
  { name: 'TeamCity', sku: 'JB-TEAMCITY', tagline: 'CI/CD-сервер', text: 'Сервер непрерывной интеграции и доставки: пайплайны, параллельные и распределённые сборки, доставка релизов.', note: 'Цена по запросу' },
  { name: 'YouTrack', sku: 'JB-YOUTRACK', tagline: 'Трекер задач и PM', text: 'Гибкий трекер задач и управление проектами: Scrum и Kanban, язык запросов, отчёты и автоматизация.', note: 'Есть бесплатный тариф · поставка по запросу' },
  { name: 'Qodana', sku: 'JB-QODANA', tagline: 'Статанализ в CI/CD', text: 'Платформа статического анализа кода в пайплайне: инспекции JetBrains, проверки безопасности и дашборды качества.', note: 'Есть Community-версия · расширенные по запросу' },
  { name: 'Datalore', sku: 'JB-DATALORE', tagline: 'Совместные ноутбуки', text: 'Облачная платформа для совместной работы с данными и Jupyter-ноутбуками в браузере.', note: 'Цена по запросу' },
];

/**
 * Категории плагинов JetBrains Marketplace (раздел D5 ТЗ).
 * НЕ выводим 867 карточек — только категории и вход в каталог.
 * Плагины — сторонние продукты Marketplace, правообладатель ≠ JetBrains.
 */
export const JETBRAINS_PLUGIN_CATEGORIES: { name: string; text: string }[] = [
  { name: 'AI-плагины', text: 'Ассистенты, генерация и ревью кода, интеграции с моделями поверх IDE.' },
  { name: 'Темы и UI / иконки', text: 'Цветовые схемы, наборы иконок и оформление редактора.' },
  { name: 'Логи и консоль', text: 'Подсветка, фильтрация и навигация по логам и выводу консоли.' },
  { name: 'DevOps и инфраструктура', text: 'Docker, Kubernetes, Ansible и облачные инструменты прямо в IDE.' },
  { name: 'Тестирование', text: 'Раннеры, отчёты и помощники для модульных и интеграционных тестов.' },
  { name: 'Безопасность', text: 'Проверки уязвимостей, секретов и зависимостей.' },
  { name: 'Языки и фреймворки', text: 'Поддержка дополнительных языков, синтаксиса и фреймворков.' },
  { name: 'Productivity', text: 'Навигация, шорткаты и инструменты для ускорения ежедневной работы.' },
];

export const JETBRAINS_PLUGINS_NOTE =
  'Плагины JetBrains Marketplace — сторонние дополнения; правообладатель — не JetBrains. Мы оформим покупку нужного плагина на организацию вместе с основными продуктами; точная цена — в карточке или КП.';

/**
 * Управление лицензиями, безопасность и администрирование (раздел D6 ТЗ).
 * Конкретные технические механизмы — без гарантий, «уточняется перед КП».
 */
export const JETBRAINS_LICENSE_MANAGEMENT: { title: string; text: string }[] = [
  { title: 'JetBrains Account', text: 'Центр управления подписками: распределение мест между сотрудниками и контроль использования лицензий.' },
  { title: 'Назначение и продление', text: 'Назначение лицензий пользователям, продление подписок и помощь при разворачивании в команде.' },
  { title: 'Передача лицензий', text: 'Перераспределение мест между сотрудниками при ротации в команде (условия уточняются перед КП).' },
  { title: 'Сервер лицензий и офлайн', text: 'Для организаций возможны централизованные сценарии управления и офлайн-активации (уточняется перед КП).' },
  { title: 'Единый счёт и документы', text: 'Учёт всех лицензий на одном счёте, договор и закрывающие документы для бухгалтерии.' },
  { title: 'Сопровождение IT-отдела', text: 'Помощь при настройке, продлении и контроле лицензий силами Biz-Soft.' },
];

/** Сценарии использования (раздел C блок 12). */
export const JETBRAINS_SCENARIOS: { title: string; text: string }[] = [
  { title: 'Backend-разработка', text: 'IntelliJ IDEA Ultimate, GoLand или PyCharm Pro для серверной логики, API и микросервисов.' },
  { title: 'Frontend-разработка', text: 'WebStorm для React, Angular, Vue и Node.js: отладка, тесты и интеграция с npm.' },
  { title: '.NET-команды', text: 'Rider, ReSharper и dotUltimate для C#, F#, ASP.NET и игр на Unity.' },
  { title: 'Работа с данными', text: 'DataGrip для SQL и десятков СУБД, плюс PyCharm Pro и Datalore для анализа и ноутбуков.' },
  { title: 'DevOps и качество', text: 'TeamCity для CI/CD и Qodana для статанализа кода в пайплайне.' },
  { title: 'Смешанный стек', text: 'All Products Pack, когда команда одновременно работает с несколькими языками.' },
];

/** Сегменты «для каких команд / отраслей» (раздел C блок 13). */
export const JETBRAINS_SEGMENTS: { title: string; text: string }[] = [
  { title: 'Стартапы и продуктовые команды', text: 'Несколько продуктов на разном стеке — обычно выгоднее All Products Pack.' },
  { title: 'Backend-команды', text: 'Серверная разработка на Java/Kotlin, Go или Python — профильная IDE под язык.' },
  { title: '.NET-команды', text: 'Разработка на C# и F#: Rider, ReSharper или комплект dotUltimate.' },
  { title: 'Аналитика и данные', text: 'Инженерам данных и аналитикам — DataGrip, PyCharm Pro и Datalore для SQL, Python и Jupyter.' },
  { title: 'Геймдев', text: 'Rider с интеграцией Unity и Unreal для команд, делающих игры.' },
  { title: 'Аутсорс и студии', text: 'Проекты на разных языках — гибкое перекрытие потребностей через All Products Pack.' },
];

/** Частые возражения (раздел C блок 16 / G). */
export const JETBRAINS_OBJECTIONS: { q: string; a: string }[] = [
  { q: 'Дорого / непонятна цена', a: 'Цена зависит от продукта, числа пользователей и курса евро. Пришлём прозрачный расчёт в КП; финальная сумма фиксируется в счёте.' },
  { q: 'А документы для бухгалтерии будут?', a: 'Да: договор, счёт, акт или УПД. Документооборот ведём через ЭДО.' },
  { q: 'Можно ли продлить текущую подписку?', a: 'Да, помогаем с продлением. Уточните текущий продукт, состав и дату окончания.' },
  { q: 'Нам нужен только один язык', a: 'Тогда пакет не нужен — подберём профильную IDE и сэкономим бюджет.' },
  { q: 'Будет ли работать ИИ?', a: 'Доступность ИИ-функций зависит от региона и сторонних провайдеров. Мы не обещаем работу в конкретной локации — уточняйте перед покупкой.' },
  { q: 'Это легально для юрлица?', a: 'Поставка оформляется по договору с полным пакетом документов; лицензия — годовая подписка на пользователя.' },
];

/**
 * Сравнение: All Products Pack vs отдельная IDE — текстовое пояснение
 * для блока сравнения (раздел G ТЗ). Цены здесь не указываем — берутся из Directus.
 */
export const JETBRAINS_COMPARISON_INTRO =
  'Если команда работает с несколькими языками, обычно выгоднее один All Products Pack: по данным JetBrains пакет включает настольные IDE, инструменты для .NET (ReSharper, ReSharper C++, dotCover, dotTrace, dotMemory) и подписку AI Pro. Если все разработчики используют один язык — как правило, достаточно профильной IDE. Поможем сравнить варианты по числу пользователей; состав пакета уточняется в КП, он может обновляться вендором.';

/** FAQ (видимый на странице → размечается FAQPage). 20–25 Q&A, раздел H ТЗ. */
export const JETBRAINS_FAQ: { q: string; a: string }[] = [
  { q: 'Можно ли купить JetBrains на юридическое лицо?', a: 'Да. Biz-Soft оформляет поставку по договору, выставляет счёт и предоставляет закрывающие документы (акт или УПД), работает через ЭДО.' },
  { q: 'Какие документы вы предоставляете?', a: 'Договор, счёт, акт или УПД. Документооборот ведём через ЭДО.' },
  { q: 'Как формируется цена?', a: 'Цена — годовая подписка на пользователя; зависит от продукта, числа пользователей, типа лицензии и курса евро. Финальная сумма фиксируется в КП и счёте.' },
  { q: 'Что входит в All Products Pack?', a: 'По данным JetBrains — настольные IDE, инструменты для .NET (ReSharper, ReSharper C++, dotCover, dotTrace, dotMemory) и подписка AI Pro. Состав уточняйте в КП — он может обновляться вендором.' },
  { q: 'Что выгоднее: All Products Pack или отдельная IDE?', a: 'Для смешанного стека обычно выгоднее пакет, для одного языка — профильная IDE. Поможем сравнить оба варианта по числу пользователей.' },
  { q: 'Чем отличается лицензия «для организаций» от индивидуальной?', a: 'Организационная покупается компанией на юрлицо по договору, выставляется счёт, обмен закрывающими идёт через ЭДО. Индивидуальная оформляется на одного человека для личного использования; доступна оплата для физлиц и ИП. Это разные карточки с разной ценой.' },
  { q: 'Можно ли продлить существующую подписку?', a: 'Да. Уточните текущий продукт, состав лицензий и дату окончания — подготовим продление.' },
  { q: 'Можно ли апгрейдить отдельную IDE до All Products Pack?', a: 'Уточняйте у менеджера — рассчитаем вариант перехода. Условия апгрейда определяются вендором.' },
  { q: 'Сколько стоит IntelliJ IDEA Ultimate для организации?', a: 'Цена указана на карточке как ориентир за пользователя в год; финальная стоимость фиксируется в КП.' },
  { q: 'Какую IDE выбрать для Python?', a: 'PyCharm Pro: Django, Flask, Jupyter и работа с данными. Для совместной работы с данными — дополнительно Datalore.' },
  { q: 'Какую IDE выбрать для .NET?', a: 'Rider — кроссплатформенная IDE; ReSharper — если работаете в Visual Studio; полный набор инструментов — dotUltimate.' },
  { q: 'Что выбрать для фронтенда?', a: 'WebStorm — для React, Angular, Vue и Node.js, с отладкой, тестами и интеграцией с npm.' },
  { q: 'Есть ли инструмент для баз данных?', a: 'Да, DataGrip — поддерживает PostgreSQL, MySQL, Oracle, SQL Server, ClickHouse и десятки других СУБД из единого интерфейса.' },
  { q: 'Что такое JetBrains AI и сколько стоит?', a: 'ИИ-ассистент в IDE с тарифами Free, Pro и Ultimate. Pro и Ultimate — по запросу; стоимость зависит от числа пользователей.' },
  { q: 'Будет ли JetBrains AI работать в нашем регионе?', a: 'Доступность ИИ-функций зависит от региона и условий сторонних провайдеров. Мы не гарантируем работу в конкретной локации — уточняйте перед покупкой.' },
  { q: 'Что такое TeamCity?', a: 'Сервер непрерывной интеграции и доставки (CI/CD) для автоматизации сборки, тестов и развёртывания. Цена по запросу.' },
  { q: 'Что такое YouTrack?', a: 'Гибкий трекер задач и управление проектами. Для небольших команд есть бесплатный тариф; корпоративная поставка — по запросу.' },
  { q: 'Что такое Qodana?', a: 'Платформа статического анализа кода в CI/CD. Есть бесплатная Community-версия; расширенные редакции — по запросу.' },
  { q: 'Что такое Datalore?', a: 'Облачная платформа для совместной работы с данными и Jupyter-ноутбуками. Цена по запросу.' },
  { q: 'Продаёте ли вы плагины JetBrains Marketplace?', a: 'Да, можем оформить покупку плагина на организацию. Это сторонние дополнения; правообладатель — не JetBrains.' },
  { q: 'На сколько пользователей можно купить?', a: 'На любое число — от одного до десятков. Для 5, 10 или 50+ рассчитываем стоимость в КП.' },
  { q: 'Как управлять лицензиями в команде?', a: 'Через JetBrains Account: распределение мест и контроль подписок; для организаций возможны централизованные инструменты управления.' },
  { q: 'Работаете ли вы с ИП?', a: 'Да. Поставщик — ИП Беляев А.В.; работаем с организациями и ИП.' },
  { q: 'Как быстро вы пришлёте КП?', a: 'Подготовим расчёт после уточнения продуктов и числа пользователей; срок согласуем при обращении.' },
  { q: 'Можно ли вернуть или отменить?', a: 'Условия возврата и отмены уточняйте у менеджера до оплаты — они зависят от типа лицензии и вендора.' },
];

/** Краткий прямой ответ (для GEO/AEO, выводится в начале). */
export const JETBRAINS_SUMMARY =
  'Biz-Soft подбирает и оформляет лицензии JetBrains для юридических лиц и ИП: All Products Pack, IntelliJ IDEA Ultimate, dotUltimate, а также отдельные IDE — PyCharm Pro, WebStorm, PhpStorm, GoLand, Rider, CLion, RubyMine, RustRover, DataGrip и ReSharper. Доступны JetBrains AI, командные инструменты (TeamCity, YouTrack, Qodana, Datalore) и плагины Marketplace. Оформляем КП, счёт, договор и закрывающие документы через ЭДО; финальная стоимость фиксируется в КП или счёте.';
