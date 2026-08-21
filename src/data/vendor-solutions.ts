/**
 * Перелинковка страниц производителей с разделом «Решения под задачу»
 * (/solutions) — это раздел назначения ПО.
 *
 * Зачем: посетитель, пришедший по запросу вида «{вендор} купить», ищет не
 * продукт вообще, а способ оформить его на компанию. Ссылка на решение
 * отвечает именно на этот вопрос и удерживает его на сайте, а обратная
 * ссылка с решения даёт странице вендора внутренний вес.
 *
 * Ключ — slug вендора. Значение — slug-и решений в порядке уместности.
 * Вендоров без записи блок не рендерит: лучше пусто, чем ссылка не по теме.
 */
export const VENDOR_SOLUTIONS: Record<string, string[]> = {
  // AI-ассистенты
  anthropic: ['ai-servisy-dlya-biznesa', 'ai-dlya-biznesa', 'inostrannoe-po-po-dogovoru'],
  google: ['ai-servisy-dlya-biznesa', 'ai-dlya-analitikov', 'po-dlya-yurlic-po-schetu'],
  perplexity: ['ai-servisy-dlya-biznesa', 'ai-dlya-analitikov', 'ai-dlya-marketinga'],
  cursor: ['ai-dlya-razrabotchikov', 'ai-servisy-dlya-biznesa', 'it-companies'],
  github: ['ai-dlya-razrabotchikov', 'it-companies', 'ai-servisy-dlya-biznesa'],
  midjourney: ['ai-dlya-dizainerov', 'design-studios', 'ai-servisy-dlya-biznesa'],
  recraft: ['ai-dlya-dizainerov', 'design-studios'],
  runway: ['ai-dlya-marketinga', 'design-studios'],
  elevenlabs: ['ai-dlya-marketinga', 'ai-servisy-dlya-biznesa'],
  heygen: ['ai-dlya-marketinga', 'marketing-agencies'],
  descript: ['ai-dlya-marketinga', 'marketing-agencies'],

  // Совместная работа и офис
  notion: ['po-dlya-yurlic-po-schetu', 'it-companies', 'inostrannoe-po-po-dogovoru'],
  miro: ['design-studios', 'it-companies', 'po-dlya-yurlic-po-schetu'],
  dropbox: ['po-dlya-yurlic-po-schetu', 'inostrannoe-po-po-dogovoru'],
  microsoft: ['po-dlya-yurlic-po-schetu', 'ai-servisy-dlya-biznesa'],

  // Дизайн и графика
  adobe: ['design-studios', 'marketing-agencies', 'inostrannoe-po-po-dogovoru'],
  canva: ['marketing-agencies', 'design-studios', 'po-dlya-yurlic-po-schetu'],
  coreldraw: ['design-studios', 'inostrannoe-po-po-dogovoru'],
  framer: ['design-studios', 'marketing-agencies'],
  sketch: ['design-studios', 'it-companies'],
  procreate: ['design-studios', 'inostrannoe-po-po-dogovoru'],
  'clip-studio-paint': ['design-studios', 'inostrannoe-po-po-dogovoru'],
  freepik: ['marketing-agencies', 'design-studios'],
  shutterstock: ['marketing-agencies', 'design-studios'],
  depositphotos: ['marketing-agencies', 'design-studios'],
  envato: ['marketing-agencies', 'design-studios'],

  // Инженерное и медиа
  solidworks: ['inostrannoe-po-po-dogovoru', 'po-dlya-yurlic-po-schetu'],
  autodesk: ['inostrannoe-po-po-dogovoru', 'po-dlya-yurlic-po-schetu'],
  sketchup: ['inostrannoe-po-po-dogovoru', 'po-dlya-yurlic-po-schetu'],
  blackmagic: ['design-studios', 'inostrannoe-po-po-dogovoru'],
  avid: ['design-studios', 'inostrannoe-po-po-dogovoru'],

  // Партия 20.08.2026
  suno: ['ai-dlya-marketinga', 'ai-servisy-dlya-biznesa', 'marketing-agencies'],
  'kling-ai': ['ai-dlya-marketinga', 'ai-servisy-dlya-biznesa', 'design-studios'],
  'leonardo-ai': ['ai-dlya-dizainerov', 'design-studios', 'ai-servisy-dlya-biznesa'],
  capcut: ['ai-dlya-marketinga', 'marketing-agencies', 'inostrannoe-po-po-dogovoru'],
  cloudflare: ['it-companies', 'po-dlya-yurlic-po-schetu', 'inostrannoe-po-po-dogovoru'],
  principle: ['design-studios', 'it-companies', 'inostrannoe-po-po-dogovoru'],
  box: ['po-dlya-yurlic-po-schetu', 'it-companies', 'inostrannoe-po-po-dogovoru'],

  // Разработка
  unity: ['it-companies', 'inostrannoe-po-po-dogovoru'],
  'unreal-engine': ['it-companies', 'inostrannoe-po-po-dogovoru'],
  gitlab: ['it-companies', 'ai-dlya-razrabotchikov'],
  docker: ['it-companies', 'po-dlya-yurlic-po-schetu'],
  atlassian: ['it-companies', 'po-dlya-yurlic-po-schetu', 'inostrannoe-po-po-dogovoru'],
  postman: ['it-companies', 'ai-dlya-razrabotchikov', 'inostrannoe-po-po-dogovoru'],
  sentry: ['it-companies', 'ai-dlya-razrabotchikov', 'po-dlya-yurlic-po-schetu'],
  browserstack: ['it-companies', 'po-dlya-yurlic-po-schetu', 'inostrannoe-po-po-dogovoru'],
  n8n: ['it-companies', 'ai-servisy-dlya-biznesa', 'po-dlya-yurlic-po-schetu'],
  teamviewer: ['it-companies', 'po-dlya-yurlic-po-schetu', 'inostrannoe-po-po-dogovoru'],
  zoho: ['it-companies', 'po-dlya-yurlic-po-schetu', 'inostrannoe-po-po-dogovoru'],
};

/** Обратная карта: какие вендоры показывать плитками на странице решения. */
export function vendorsForSolution(solutionSlug: string): string[] {
  return Object.entries(VENDOR_SOLUTIONS)
    .filter(([, list]) => list.includes(solutionSlug))
    .map(([vendor]) => vendor);
}
