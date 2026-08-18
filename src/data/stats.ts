/**
 * ЕДИНЫЙ источник цифр сайта (Б4 аудита): все страницы берут значения
 * отсюда либо из живого каталога. Не дублировать числа в текстах.
 */
export const STATS = {
  /** Фолбэки, когда живой каталог недоступен (реальные значения тянутся из БД). */
  productsFallback: 1140,
  vendorsFallback: 60,
  sinceYear: 2022,
  aiDirections: 8,
  quoteDays: 1,
  deliveryDays: '1–3',
} as const;
