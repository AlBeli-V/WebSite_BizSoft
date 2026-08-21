/**
 * Ответы страниц при недоступности источника данных.
 *
 * Раньше сбой Directus на карточке товара молча превращался в 404: исключение
 * логировалось, product оставался null, и страница отдавала «не найдено».
 * Для поискового робота 404 — сигнал удалить страницу из индекса, поэтому
 * получасовой сбой БД мог стоить позиций по всему каталогу. 503 с Retry-After
 * означает «временно недоступно, зайдите позже» и индексацию не рушит.
 */
import { DirectusError } from './directus';

/** Сколько секунд робот должен подождать перед повторным обходом. */
const RETRY_AFTER_S = 120;

/**
 * Отличить «источник недоступен» от «данных нет».
 * Недоступность — сетевая ошибка, таймаут или 5xx от Directus. Ответ 404 от
 * самого Directus означает именно отсутствие записи и недоступностью не является.
 */
export function isSourceUnavailable(e: unknown): boolean {
  if (e instanceof DirectusError) return e.status === 0 || e.status >= 500;
  return e instanceof Error; // сетевой сбой, таймаут, разбор ответа
}

/** 503 с Retry-After — «зайдите позже», страница не удаляется из индекса. */
export function serviceUnavailable(): Response {
  return new Response(
    'Сервис временно недоступен. Обновите страницу через пару минут.',
    {
      status: 503,
      statusText: 'Service Unavailable',
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Retry-After': String(RETRY_AFTER_S),
        'Cache-Control': 'no-store',
      },
    },
  );
}
