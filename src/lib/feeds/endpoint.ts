/**
 * Обёртка HTTP для фидов из реестра — единственное место, где механизм фидов
 * встречается с сайтом (SSR-эндпоинты только делегируют сюда).
 *
 * Сбой Directus → 503, а не пустой фид: площадка, получившая пустой файл
 * с кодом 200, снимает с публикации все товары; 503 она трактует как
 * «зайти позже» и оставляет предыдущую версию.
 */
import { getProducts } from '../directus';
import { isSourceUnavailable, serviceUnavailable } from '../http';
import { renderFeed, feedEnabled } from './registry';

export async function feedResponse(specId: string): Promise<Response> {
  // Фиды закрыты, пока руководитель не скомандует открыть (см. feedEnabled).
  // 404, а не 403: наружу фид «не существует». Заголовок X-Feed-Status
  // позволяет ночной проверке отличить «закрыт по решению» от поломки маршрута.
  if (!feedEnabled(specId)) {
    return new Response('Фид не опубликован.', {
      status: 404,
      headers: { 'Content-Type': 'text/plain; charset=utf-8', 'X-Feed-Status': 'disabled', 'Cache-Control': 'no-store' },
    });
  }
  let body: string;
  let contentType: string;
  try {
    const products = await getProducts();
    ({ body, contentType } = renderFeed(specId, products));
  } catch (e) {
    console.error(`feed ${specId}`, e);
    if (isSourceUnavailable(e)) return serviceUnavailable();
    throw e;
  }
  return new Response(body, {
    status: 200,
    headers: {
      'Content-Type': contentType,
      // Час кэша: площадки забирают фид несколько раз в сутки, чаще не нужно.
      'Cache-Control': 'public, max-age=3600',
    },
  });
}
