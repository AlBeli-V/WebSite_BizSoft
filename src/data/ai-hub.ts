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
}

export const aiSubcategories: AiSubcategory[] = [
  { sub: 'text', categorySlug: 'ai-text', name: 'Текстовые AI', icon: '🧠', short: 'AI-ассистенты для текста, знаний и research.', intro: 'Корпоративные текстовые AI-ассистенты: ChatGPT Business, Claude Team/Enterprise, Perplexity Enterprise. Годовые лицензии на юрлицо по счёту, закрывающие через ЭДО.' },
  { sub: 'code', categorySlug: 'ai-code', name: 'Программирование', icon: '💻', short: 'AI для написания и ревью кода.', intro: 'AI-ассистенты для команд разработки: GitHub Copilot Business/Enterprise, Cursor Business. Оформление на юрлицо по счёту с закрывающими через ЭДО.' },
  { sub: 'image', categorySlug: 'ai-image', name: 'Изображения', icon: '🎨', short: 'Генерация и дизайн изображений.', intro: 'Генеративный AI для изображений: Midjourney, Adobe Firefly, Recraft. Коммерческое использование, годовые лицензии на юрлицо по счёту.' },
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
