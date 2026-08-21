/**
 * Единая точка отправки целей в Яндекс.Метрику и события в GA4.
 *
 * Раньше вызов был скопирован в десять мест, и идентификатор счётчика в
 * каждом читался напрямую из import.meta.env.PUBLIC_METRIKA_ID. В пяти
 * копиях к нему дописали фолбэк, в пяти забыли — а поскольку PUBLIC_*
 * не доходят до сборки (BLD-002), в этих пяти выражение схлопывалось в
 * `void 0`, условие становилось заведомо ложным и минификатор удалял
 * вызов цели целиком. Из отчётов пропадали ровно конверсии: заявки,
 * добавления в подборку и скачивания КП.
 *
 * Поэтому идентификаторы живут здесь и всегда имеют непустое значение:
 * даже при незаданной переменной окружения код остаётся достижимым.
 */

/** Счётчик Яндекс.Метрики biz-soft.pro. */
export const METRIKA_ID = import.meta.env.PUBLIC_METRIKA_ID || '110206070';
/** Поток Google Analytics 4 biz-soft.pro. */
export const GA_ID = import.meta.env.PUBLIC_GA_ID || 'G-V9BK2D1431';

type Ym = (id: number, action: string, goal?: string, params?: Record<string, unknown>) => void;
type Gtag = (command: string, event: string, params?: Record<string, unknown>) => void;

/**
 * Отправить цель. Безопасна до загрузки счётчика и при отключённой аналитике:
 * счётчик Метрики буферизует вызовы, а отсутствие gtag просто пропускается.
 */
export function trackGoal(name: string, params: Record<string, unknown> = {}): void {
  if (typeof window === 'undefined') return;
  const w = window as unknown as { ym?: Ym; gtag?: Gtag };
  try {
    if (typeof w.ym === 'function') w.ym(Number(METRIKA_ID), 'reachGoal', name, params);
    if (typeof w.gtag === 'function') w.gtag('event', name, params);
  } catch {
    // Аналитика не должна ломать сценарий пользователя: заявка уже отправлена.
  }
}
