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
export const vendors: ScaffoldEntry[] = [
  { slug: 'openai', title: 'OpenAI', description: 'Продукты OpenAI (ChatGPT) для бизнеса по договору и счёту.' },
  { slug: 'figma', title: 'Figma', description: 'Лицензии Figma для команд дизайна по договору и счёту.' },
];

export const docs: ScaffoldEntry[] = [
  { slug: 'dogovor', title: 'Договор', description: 'Как устроен договор поставки ПО для юрлица.' },
  { slug: 'edo', title: 'ЭДО', description: 'Обмен закрывающими документами через электронный документооборот.' },
  { slug: 'zakryvayushchie-dokumenty', title: 'Закрывающие документы', description: 'Какие закрывающие документы получает юрлицо.' },
];

/** Будущие посадочные solutions (пока заготовки). */
export const plannedSolutions: ScaffoldEntry[] = [
  { slug: 'po-dlya-yurlic-po-schetu', title: 'ПО для юрлиц по счёту', description: 'Поставка ПО для юридических лиц с оплатой по счёту.' },
  { slug: 'inostrannoe-po-po-dogovoru', title: 'Иностранное ПО по договору', description: 'Зарубежное ПО для российских компаний по договору.' },
  { slug: 'ai-servisy-dlya-biznesa', title: 'AI-сервисы для бизнеса', description: 'AI-сервисы для компаний по договору и счёту.' },
];
