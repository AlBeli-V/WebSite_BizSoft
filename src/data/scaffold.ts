/**
 * Архитектурные заготовки будущих разделов. Страницы рендерятся как noindex
 * («в подготовке») и НЕ попадают в sitemap, пока не наполнены контентом.
 * Когда раздел готов — снять noindex и добавить в sitemap.
 */
export interface ScaffoldEntry {
  slug: string;
  title: string;
  description: string;
}

// ВАЖНО: вендоры с готовой посадочной (своя страница vendors/<slug>.astro) сюда НЕ добавлять,
// иначе [slug].astro пререндерит заглушку и перекроет реальную SSR-страницу.
// Готовые лендинги (zoom, jetbrains) — в config/site.ts → vendorLandings.
// OpenAI и Figma переехали в готовые bespoke-лендинги (vendors/openai.astro, vendors/figma.astro).
export const vendors: ScaffoldEntry[] = [];

export const docs: ScaffoldEntry[] = [
  { slug: 'dogovor', title: 'Договор', description: 'Как устроен договор поставки ПО для юрлица.' },
  { slug: 'edo', title: 'ЭДО', description: 'Обмен закрывающими документами через электронный документооборот.' },
  { slug: 'zakryvayushchie-dokumenty', title: 'Закрывающие документы', description: 'Какие закрывающие документы получает юрлицо.' },
];

/** Будущие посадочные solutions (пока заготовки).
 *
 * Пусто с 20.08.2026: три заготовки — «ПО для юрлиц по счёту», «Иностранное ПО
 * по договору» и «AI-сервисы для бизнеса» — наполнены содержанием и переехали
 * в src/data/solutions.ts. Замер Вордстата показал по их теме 15 947 запросов
 * в месяц с растущим трендом, и держать эти адреса под noindex было потерей.
 */
export const plannedSolutions: ScaffoldEntry[] = [];
