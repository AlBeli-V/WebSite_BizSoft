/**
 * Реестр посадочных страниц производителей (шаблонные лендинги /vendors/<slug>).
 * Цены и карточки берутся ЖИВЫМИ из Directus по полю vendor (точное совпадение);
 * здесь — только редакторская обвязка (юр-название, цвет, интро, домен для копирайта).
 * Zoom и JetBrains — отдельные bespoke-страницы (vendors/zoom.astro, vendors/jetbrains.astro).
 */

export type VendorDomain = 'design' | 'games' | 'video' | 'ai';

export interface VendorEntry {
  slug: string;
  /** Точное значение поля `vendor` в Directus (для выборки товаров). */
  vendor: string;
  /** Отображаемое имя (по умолчанию = vendor). */
  title?: string;
  legalName: string;
  brandColor: string;
  site: string;
  /** Основная категория каталога (для хлебных крошек и ссылки). */
  catSeg: string;
  catLabel: string;
  domain: VendorDomain;
  tagline: string;
  about: string;
}

export const VENDORS: VendorEntry[] = [
  // ─── Блок 1: графический дизайн / AI-графика ───
  { slug: 'adobe', vendor: 'Adobe', title: 'Adobe', legalName: 'Adobe Inc.', brandColor: '#FA0F00', site: 'https://www.adobe.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'design',
    tagline: 'Creative Cloud для бизнеса: Photoshop, Illustrator, Premiere Pro, After Effects, Acrobat и весь набор — тарифы для команд и Enterprise.',
    about: 'Adobe Creative Cloud — набор профессиональных инструментов для дизайна, фото, вёрстки, видео и работы с PDF: Photoshop, Illustrator, InDesign, Premiere Pro, After Effects, Lightroom, Acrobat Pro и другие. Индустриальный стандарт в маркетинге, дизайне и продакшене.' },
  { slug: 'canva', vendor: 'Canva', legalName: 'Canva Pty Ltd', brandColor: '#00C4CC', site: 'https://www.canva.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'design',
    tagline: 'Онлайн-платформа для дизайна и брендинга: тарифы Pro, Business и Enterprise для команд.',
    about: 'Canva — облачный редактор для быстрого создания графики, презентаций, соцсетей и брендовых материалов. Подходит маркетинговым и дизайн-командам, которым нужен единый инструмент с шаблонами, брендкитом и совместной работой.' },
  { slug: 'coreldraw', vendor: 'CorelDRAW', legalName: 'Corel Corporation (Alludo)', brandColor: '#111111', site: 'https://www.coreldraw.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'design',
    tagline: 'Профессиональный пакет векторной графики: подписка и бессрочные лицензии CorelDRAW и Painter.',
    about: 'CorelDRAW Graphics Suite — набор для векторной иллюстрации, вёрстки и обработки изображений. Востребован в полиграфии, наружной рекламе, дизайне упаковки и производстве.' },
  { slug: 'sketch', vendor: 'Sketch', legalName: 'Sketch B.V.', brandColor: '#F7B500', site: 'https://www.sketch.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'design',
    tagline: 'Инструмент UI/UX-дизайна для macOS: подписки для команд и бессрочная Mac-лицензия.',
    about: 'Sketch — редактор интерфейсов для дизайнеров на Mac с совместной работой, дизайн-системами и передачей макетов в разработку.' },
  { slug: 'framer', vendor: 'Framer', legalName: 'Framer B.V.', brandColor: '#0099FF', site: 'https://www.framer.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'design',
    tagline: 'Дизайн и публикация сайтов без кода: тарифы Basic, Pro, Scale и Enterprise.',
    about: 'Framer — платформа для дизайна и публикации сайтов с CMS, анимациями и хостингом. Подходит студиям и продуктовым командам для лендингов и промо-сайтов.' },
  { slug: 'miro', vendor: 'Miro', legalName: 'RealtimeBoard, Inc. dba Miro', brandColor: '#FFD02F', site: 'https://miro.com', catSeg: 'collaboration', catLabel: 'Доски и совместная работа', domain: 'design',
    tagline: 'Онлайн-доска для совместной работы: тарифы Starter и Business для команд.',
    about: 'Miro — бесконечная онлайн-доска для брейнштормов, воркшопов, карт пользовательских путей и дизайн-операций. Незаменима для распределённых креативных и продуктовых команд.' },
  { slug: 'zeplin', vendor: 'Zeplin', legalName: 'Zeplin, Inc.', brandColor: '#FDBD39', site: 'https://zeplin.io', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'design',
    tagline: 'Передача макетов в разработку: тарифы Advanced и Enterprise.',
    about: 'Zeplin — платформа связи дизайна и разработки: спецификации, ассеты, стайлгайды и единое пространство для дизайнеров и инженеров.' },
  { slug: 'clip-studio-paint', vendor: 'Clip Studio Paint', legalName: 'CELSYS, Inc.', brandColor: '#00A0E9', site: 'https://www.clipstudio.net', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'design',
    tagline: 'Рисование, иллюстрация и комиксы: бессрочные лицензии PRO/EX и подписки.',
    about: 'Clip Studio Paint — профессиональный инструмент цифрового рисования, иллюстрации, комиксов и анимации. Стандарт для художников и студий концепт-арта.' },
  { slug: 'procreate', vendor: 'Procreate', legalName: 'Savage Interactive Pty Ltd', brandColor: '#111111', site: 'https://procreate.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'design',
    tagline: 'Рисование и 2D-анимация на iPad: разовые покупки Procreate и Procreate Dreams.',
    about: 'Procreate — приложение для рисования и иллюстрации на iPad с разовой покупкой. Популярно у иллюстраторов, концепт-художников и дизайнеров.' },
  { slug: 'astute-graphics', vendor: 'Astute Graphics', legalName: 'Astute Graphics Ltd', brandColor: '#FF5A00', site: 'https://astutegraphics.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'design',
    tagline: 'Набор плагинов для Adobe Illustrator: годовая подписка на полный комплект.',
    about: 'Astute Graphics — набор из десятков плагинов, ускоряющих векторную работу в Adobe Illustrator: точное рисование, динамические кисти, работа с цветом и узорами.' },
  { slug: 'freepik', vendor: 'Freepik', legalName: 'Freepik Company S.L.', brandColor: '#1273EB', site: 'https://www.freepik.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'design',
    tagline: 'Стоковые ресурсы и AI-генерация: тарифы Premium и Premium+.',
    about: 'Freepik — библиотека фото, векторов, PSD и AI-инструментов для дизайнеров, маркетологов и агентств с коммерческой лицензией.' },
  { slug: 'envato', vendor: 'Envato', legalName: 'Envato Pty Ltd', brandColor: '#82B541', site: 'https://elements.envato.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'design',
    tagline: 'Безлимитные ассеты Envato Elements: индивидуальные и командные тарифы.',
    about: 'Envato Elements — подписка на безлимитные загрузки шаблонов, графики, видео, музыки и шрифтов с пожизненной коммерческой лицензией на скачанное.' },
  { slug: 'shutterstock', vendor: 'Shutterstock', legalName: 'Shutterstock, Inc.', brandColor: '#EE2A24', site: 'https://www.shutterstock.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'design',
    tagline: 'Сток фото, видео и музыки: планы на 10, 50 и 350 изображений в месяц.',
    about: 'Shutterstock — крупная библиотека стоковых изображений, видео и музыки со стандартной royalty-free лицензией для рекламы и контента.' },
  { slug: 'depositphotos', vendor: 'Depositphotos', legalName: 'Depositphotos Inc.', brandColor: '#39A85B', site: 'https://depositphotos.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'design',
    tagline: 'Сток-контент: безлимитные подписки и пакеты изображений.',
    about: 'Depositphotos — сток фото, векторов и видео с гибкими подписками и разовыми пакетами для дизайнеров и агентств.' },
  { slug: 'monotype', vendor: 'Monotype', legalName: 'Monotype Imaging Holdings Inc.', brandColor: '#FF3C00', site: 'https://www.monotype.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'design',
    tagline: 'Лицензирование шрифтов: подписки Monotype Fonts и покупка на MyFonts.',
    about: 'Monotype и MyFonts — крупнейшая экосистема лицензирования шрифтов для брендинга, дизайна и веба, с подписками для команд и покупкой отдельных начертаний.' },
  { slug: 'midjourney', vendor: 'Midjourney', legalName: 'Midjourney, Inc.', brandColor: '#111111', site: 'https://www.midjourney.com', catSeg: 'ai', catLabel: 'AI-сервисы', domain: 'ai',
    tagline: 'AI-генерация изображений: тарифы Basic, Standard, Pro и Mega.',
    about: 'Midjourney — генеративная нейросеть для создания изображений по текстовому описанию. Используется в концепт-арте, рекламе, мудбордах и визуальных исследованиях.' },
  { slug: 'recraft', vendor: 'Recraft', legalName: 'Recraft, Inc.', brandColor: '#111111', site: 'https://www.recraft.ai', catSeg: 'ai', catLabel: 'AI-сервисы', domain: 'ai',
    tagline: 'AI-дизайн с экспортом в вектор: тарифы Basic, Advanced, Pro и Team.',
    about: 'Recraft — генеративный ИИ для дизайнеров с поддержкой брендовых стилей и экспортом в SVG/вектор. Подходит для иконок, иллюстраций и айдентики.' },

  // ─── Блок 2: игры / 3D ───
  { slug: 'unity', vendor: 'Unity', legalName: 'Unity Technologies', brandColor: '#111111', site: 'https://unity.com', catSeg: 'development', catLabel: 'Средства разработки', domain: 'games',
    tagline: 'Игровой движок Unity: подписки Pro и Enterprise для студий.',
    about: 'Unity — один из ведущих движков для разработки игр и интерактивных приложений на всех платформах, включая мобильные, ПК, консоли и AR/VR.' },
  { slug: 'unreal-engine', vendor: 'Unreal Engine', legalName: 'Epic Games, Inc.', brandColor: '#0E1128', site: 'https://www.unrealengine.com', catSeg: 'development', catLabel: 'Средства разработки', domain: 'games',
    tagline: 'Unreal Engine для студий: посадочная подписка и RealityScan.',
    about: 'Unreal Engine — движок Epic Games с фотореалистичной графикой для игр, кино, архвиза и вещания; для неигрового применения продаётся по подписке на рабочее место.' },
  { slug: 'autodesk', vendor: 'Autodesk', legalName: 'Autodesk, Inc.', brandColor: '#111111', site: 'https://www.autodesk.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'games',
    tagline: 'Maya, 3ds Max и Media & Entertainment Collection для 3D-продакшена.',
    about: 'Autodesk Media & Entertainment — индустриальный стандарт 3D-моделирования, анимации и VFX (Maya, 3ds Max, MotionBuilder, Mudbox) для игр, кино и ТВ.' },
  { slug: 'maxon', vendor: 'Maxon', legalName: 'Maxon Computer GmbH', brandColor: '#E5006D', site: 'https://www.maxon.net', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'games',
    tagline: 'Cinema 4D, ZBrush, Redshift и Red Giant: подписки Maxon.',
    about: 'Maxon — набор для 3D и моушн-дизайна: Cinema 4D, скульптинг ZBrush, GPU-рендер Redshift и VFX-инструменты Red Giant. Объединены в подписке Maxon One.' },
  { slug: 'houdini', vendor: 'SideFX Houdini', title: 'Houdini', legalName: 'Side Effects Software Inc.', brandColor: '#FF6600', site: 'https://www.sidefx.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'games',
    tagline: 'Houdini для VFX и процедурной графики: Core, FX, Indie и Engine.',
    about: 'SideFX Houdini — процедурный пакет для VFX, симуляций и генеративной графики. Индустриальный стандарт для эффектов разрушений, жидкостей, дыма и частиц.' },
  { slug: 'speedtree', vendor: 'SpeedTree', legalName: 'Unity Technologies (IDV Inc.)', brandColor: '#5AAF2A', site: 'https://store.speedtree.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'games',
    tagline: 'Создание растительности: тарифы Indie, Pro и Enterprise.',
    about: 'SpeedTree — инструмент моделирования и анимации деревьев и растительности для игр и VFX с библиотекой готовых моделей и экспортом в движки.' },
  { slug: 'marmoset', vendor: 'Marmoset', legalName: 'Marmoset LLC', brandColor: '#E8562B', site: 'https://marmoset.co', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'games',
    tagline: 'Toolbag для рендера и бейкинга: бессрочные лицензии и подписки.',
    about: 'Marmoset Toolbag — инструмент запекания карт, текстурирования и рендеринга портфолио 3D-художников и игровых студий.' },
  { slug: 'marvelous-designer', vendor: 'Marvelous Designer', legalName: 'CLO Virtual Fashion Inc.', brandColor: '#00C4B3', site: 'https://www.marvelousdesigner.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'games',
    tagline: 'Симуляция 3D-одежды: тарифы Personal и Enterprise.',
    about: 'Marvelous Designer — инструмент создания и симуляции 3D-одежды и тканей для персонажей игр, кино и анимации.' },
  { slug: 'reallusion', vendor: 'Reallusion', legalName: 'Reallusion Inc.', brandColor: '#F26722', site: 'https://www.reallusion.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'games',
    tagline: 'Character Creator и iClone: бессрочные лицензии и подписки.',
    about: 'Reallusion — инструменты создания 3D-персонажей (Character Creator) и анимации в реальном времени (iClone) для игр, анимации и виртуального продакшена.' },
  { slug: 'perforce', vendor: 'Perforce', legalName: 'Perforce Software, Inc.', brandColor: '#0F1B4C', site: 'https://www.perforce.com', catSeg: 'development', catLabel: 'Средства разработки', domain: 'games',
    tagline: 'Helix Core — контроль версий для геймдева: Cloud, Scale и Platform.',
    about: 'Perforce Helix Core (P4) — система контроля версий для кода и больших бинарных файлов, стандарт в игровых студиях с большими арт-пайплайнами.' },
  { slug: 'wwise', vendor: 'Audiokinetic', title: 'Wwise (Audiokinetic)', legalName: 'Audiokinetic Inc.', brandColor: '#00AEEF', site: 'https://www.audiokinetic.com', catSeg: 'media', catLabel: 'Звук, видео и медиа', domain: 'games',
    tagline: 'Wwise — движок игрового аудио: лицензии Pro, Premium и Platinum.',
    about: 'Audiokinetic Wwise — ведущее middleware интерактивного игрового аудио: адаптивный звук, микс в реальном времени и интеграция с движками.' },
  { slug: 'fmod', vendor: 'FMOD', legalName: 'Firelight Technologies Pty Ltd', brandColor: '#DA2128', site: 'https://www.fmod.com', catSeg: 'media', catLabel: 'Звук, видео и медиа', domain: 'games',
    tagline: 'FMOD — игровое аудио: лицензии Indie, Basic и Premium по бюджету проекта.',
    about: 'FMOD — популярное middleware игрового аудио с адаптивным звуком и интеграцией в Unity, Unreal и собственные движки; лицензии по бюджету проекта.' },
  { slug: 'spine', vendor: 'Spine', legalName: 'Esoteric Software LLC', brandColor: '#FF4646', site: 'http://esotericsoftware.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'games',
    tagline: '2D-скелетная анимация: бессрочные лицензии Essential и Professional.',
    about: 'Spine — редактор 2D-скелетной анимации для игр: экономичные ассеты, плавные движения и рантаймы для всех популярных движков.' },
  { slug: 'rive', vendor: 'Rive', legalName: 'Rive App, Inc.', brandColor: '#57A5E0', site: 'https://rive.app', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'games',
    tagline: 'Интерактивная анимация в реальном времени: Cadet, Voyager и Enterprise.',
    about: 'Rive — инструмент интерактивной векторной анимации со стейт-машинами и рантаймами для игр, приложений и веба.' },
  { slug: 'gaea', vendor: 'QuadSpinner Gaea', title: 'Gaea', legalName: 'QuadSpinner Inc.', brandColor: '#F5A623', site: 'https://quadspinner.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'games',
    tagline: 'Процедурные ландшафты: бессрочные лицензии Indie, Pro и Enterprise.',
    about: 'QuadSpinner Gaea — инструмент процедурной генерации террейнов для игр и VFX с высокой детализацией и экспортом карт высот.' },
  { slug: 'rizomuv', vendor: 'RizomUV', legalName: 'Rizom-Lab', brandColor: '#2AA3C7', site: 'https://www.rizom-lab.com', catSeg: 'design', catLabel: 'Дизайн и графика', domain: 'games',
    tagline: 'UV-развёртка: Virtual Spaces и Real Space, бессрочно и по подписке.',
    about: 'RizomUV — специализированный инструмент быстрой и точной UV-развёртки 3D-моделей для игр, кино и product-визуализации.' },
  { slug: 'photon', vendor: 'Photon Engine', title: 'Photon', legalName: 'Exit Games GmbH', brandColor: '#00A3E0', site: 'https://www.photonengine.com', catSeg: 'development', catLabel: 'Средства разработки', domain: 'games',
    tagline: 'Сетевой мультиплеер: планы Fusion по количеству игроков (CCU).',
    about: 'Photon Engine (Exit Games) — сервис мультиплеерного нетворкинга для игр: синхронизация, комнаты и облачная инфраструктура с тарификацией по CCU.' },

  // ─── Блок 3: видео / VFX / аудио ───
  { slug: 'blackmagic', vendor: 'Blackmagic Design', title: 'DaVinci Resolve', legalName: 'Blackmagic Design Pty Ltd', brandColor: '#FF9E1E', site: 'https://www.blackmagicdesign.com', catSeg: 'media', catLabel: 'Звук, видео и медиа', domain: 'video',
    tagline: 'DaVinci Resolve Studio: монтаж, цвет, VFX и звук в одной лицензии.',
    about: 'DaVinci Resolve Studio — профессиональная система монтажа, цветокоррекции, VFX (Fusion) и звука (Fairlight) с разовой бессрочной лицензией и бесплатными обновлениями.' },
  { slug: 'avid', vendor: 'Avid', legalName: 'Avid Technology, Inc.', brandColor: '#00A758', site: 'https://www.avid.com', catSeg: 'media', catLabel: 'Звук, видео и медиа', domain: 'video',
    tagline: 'Media Composer и Pro Tools: подписки и бессрочные лицензии.',
    about: 'Avid — индустриальные стандарты видеомонтажа (Media Composer) и аудиопроизводства (Pro Tools) для кино, ТВ и музыкального продакшена.' },
  { slug: 'foundry', vendor: 'Foundry', legalName: 'The Foundry Visionmongers Ltd', brandColor: '#FFCC00', site: 'https://www.foundry.com', catSeg: 'media', catLabel: 'Звук, видео и медиа', domain: 'video',
    tagline: 'Nuke, Mari и Katana: подписки для VFX-студий.',
    about: 'Foundry — набор для высококлассного VFX: композитинг Nuke, текстурирование Mari и look development Katana. Используется в кино и на телевидении.' },
  { slug: 'boris-fx', vendor: 'Boris FX', legalName: 'Boris FX, Inc.', brandColor: '#0A66C2', site: 'https://borisfx.com', catSeg: 'media', catLabel: 'Звук, видео и медиа', domain: 'video',
    tagline: 'Sapphire, Continuum, Mocha Pro и Silhouette: подписки и бессрочные.',
    about: 'Boris FX — наградные VFX-плагины: эффекты Sapphire, набор Continuum, планарный трекинг Mocha Pro и ротоскопинг Silhouette для Adobe, Avid, Resolve и Nuke.' },
  { slug: 'topaz-labs', vendor: 'Topaz Labs', legalName: 'Topaz Labs LLC', brandColor: '#00AEEF', site: 'https://www.topazlabs.com', catSeg: 'media', catLabel: 'Звук, видео и медиа', domain: 'video',
    tagline: 'ИИ-улучшение фото и видео: Photo, Video, Gigapixel и Studio.',
    about: 'Topaz Labs — ИИ-инструменты повышения качества: апскейл и восстановление видео и изображений, устранение шума и увеличение разрешения.' },
  { slug: 'wondershare', vendor: 'Wondershare', title: 'Wondershare Filmora', legalName: 'Wondershare Technology Group Co., Ltd.', brandColor: '#46A0FA', site: 'https://filmora.wondershare.com', catSeg: 'media', catLabel: 'Звук, видео и медиа', domain: 'video',
    tagline: 'Filmora — видеоредактор: годовые, бессрочные и командные лицензии.',
    about: 'Wondershare Filmora — доступный видеоредактор с ИИ-инструментами, эффектами и кросс-платформенными лицензиями для авторов, SMM и небольших студий.' },
  { slug: 'vegas', vendor: 'MAGIX Vegas', title: 'VEGAS Pro', legalName: 'MAGIX Software GmbH', brandColor: '#E5231B', site: 'https://www.vegascreativesoftware.com', catSeg: 'media', catLabel: 'Звук, видео и медиа', domain: 'video',
    tagline: 'VEGAS Pro: редакции Edit, Post и Suite, подписка и бессрочно.',
    about: 'VEGAS Pro (MAGIX) — профессиональный видеоредактор с монтажом 4K/HDR, цветокоррекцией и инструментами постпродакшена.' },
  { slug: 'telestream', vendor: 'Telestream', legalName: 'Telestream, LLC', brandColor: '#00A0DF', site: 'https://www.telestream.net', catSeg: 'media', catLabel: 'Звук, видео и медиа', domain: 'video',
    tagline: 'ScreenFlow, Wirecast и Vantage: запись, стриминг и транскодинг.',
    about: 'Telestream — инструменты записи экрана (ScreenFlow), прямых трансляций (Wirecast) и корпоративного медиа-транскодинга (Vantage).' },
  { slug: 'native-instruments', vendor: 'Native Instruments', legalName: 'Native Instruments GmbH', brandColor: '#00A0DC', site: 'https://www.native-instruments.com', catSeg: 'media', catLabel: 'Звук, видео и медиа', domain: 'video',
    tagline: 'Komplete и iZotope RX/Ozone: инструменты и мастеринг звука.',
    about: 'Native Instruments и iZotope — экосистема музыкального производства: инструменты и эффекты Komplete, реставрация RX и мастеринг Ozone для саунд-дизайна и постпродакшена.' },
  { slug: 'epidemic-sound', vendor: 'Epidemic Sound', legalName: 'Epidemic Sound AB', brandColor: '#1D1D1D', site: 'https://www.epidemicsound.com', catSeg: 'media', catLabel: 'Звук, видео и медиа', domain: 'video',
    tagline: 'Музыка и звуковые эффекты без роялти: Personal и Commercial.',
    about: 'Epidemic Sound — библиотека музыки и SFX без авторских претензий для видео, рекламы и брендов с простой лицензией.' },
  { slug: 'artlist', vendor: 'Artlist', legalName: 'Artlist Ltd', brandColor: '#00E5B0', site: 'https://artlist.io', catSeg: 'media', catLabel: 'Звук, видео и медиа', domain: 'video',
    tagline: 'Музыка, SFX и футаж: тарифы Social, Pro и Teams.',
    about: 'Artlist — платформа лицензирования музыки, звуковых эффектов и видеофутажа для авторов, агентств и команд с коммерческими правами.' },
  { slug: 'motion-array', vendor: 'Motion Array', legalName: 'Motion Array LLC', brandColor: '#7C4DFF', site: 'https://motionarray.com', catSeg: 'media', catLabel: 'Звук, видео и медиа', domain: 'video',
    tagline: 'All-in-one для видео: шаблоны, музыка, футаж и плагины.',
    about: 'Motion Array — единая подписка на видеошаблоны, пресеты, музыку, стоковое видео и плагины для монтажёров и моушн-дизайнеров.' },
  { slug: 'runway', vendor: 'Runway', legalName: 'Runway AI, Inc.', brandColor: '#111111', site: 'https://runwayml.com', catSeg: 'ai', catLabel: 'AI-сервисы', domain: 'video',
    tagline: 'Генеративное ИИ-видео: тарифы Standard, Pro и Max.',
    about: 'Runway — генеративный ИИ для видео: создание и редактирование роликов, апскейл и креативные инструменты для продакшена и рекламы.' },
  { slug: 'elevenlabs', vendor: 'ElevenLabs', legalName: 'ElevenLabs Inc.', brandColor: '#111111', site: 'https://elevenlabs.io', catSeg: 'ai', catLabel: 'AI-сервисы', domain: 'video',
    tagline: 'ИИ-озвучка и клонирование голоса: Starter, Creator, Pro и Scale.',
    about: 'ElevenLabs — генерация речи и клонирование голоса на десятках языков для дубляжа, озвучки видео и аудиоконтента.' },
  { slug: 'descript', vendor: 'Descript', legalName: 'Descript, Inc.', brandColor: '#2C2C2C', site: 'https://www.descript.com', catSeg: 'ai', catLabel: 'AI-сервисы', domain: 'video',
    tagline: 'Монтаж видео как текста: Hobbyist, Creator и Business.',
    about: 'Descript — редактор видео и подкастов с транскрипцией, ИИ-инструментами, перевод и дубляж; монтаж как редактирование текста.' },
  { slug: 'heygen', vendor: 'HeyGen', legalName: 'HeyGen, Inc.', brandColor: '#7A5AF8', site: 'https://www.heygen.com', catSeg: 'ai', catLabel: 'AI-сервисы', domain: 'video',
    tagline: 'ИИ-видео с аватарами: тарифы Creator, Pro и Business.',
    about: 'HeyGen — генерация видео с ИИ-аватарами и синхронной озвучкой на 175+ языках для обучения, маркетинга и локализации.' },
];

export function vendorBySlug(slug: string): VendorEntry | undefined {
  return VENDORS.find((v) => v.slug === slug);
}

/** Аудитория/копирайт по домену. */
export const DOMAIN_AUDIENCE: Record<VendorDomain, string> = {
  design: 'дизайн-студий, брендинговых и рекламных агентств, продуктовых команд',
  games: 'игровых студий, разработчиков и 3D-художников',
  video: 'видеопродакшн-студий, моушн-дизайнеров и монтажёров',
  ai: 'креативных команд, использующих генеративный ИИ',
};
