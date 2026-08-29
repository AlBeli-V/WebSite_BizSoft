export const prerender = false;

/**
 * Чистая товарная картинка для фидов площадок (2ГИС): знак продукта по
 * центру на белом фоне, без цены и надписей — og-карточка с ценой и брендом
 * для таких площадок запрещена. Логика — src/lib/feeds/product-image.ts.
 */
import type { APIRoute } from 'astro';
import { getProductBySlug } from '../../../lib/directus';
import { isSourceUnavailable, serviceUnavailable } from '../../../lib/http';
import { loadProductIconSvg, renderIconPng } from '../../../lib/feeds/product-image';

export const GET: APIRoute = async ({ params }) => {
  const slug = params.slug || '';
  let product = null;
  try {
    product = await getProductBySlug(slug);
  } catch (e) {
    if (isSourceUnavailable(e)) return serviceUnavailable();
  }
  if (!product) return new Response(null, { status: 404 });

  const svg = await loadProductIconSvg(slug, product.vendor);
  if (!svg) return new Response(null, { status: 404 });

  const png = renderIconPng(svg);
  return new Response(new Uint8Array(png), {
    status: 200,
    headers: {
      'Content-Type': 'image/png',
      // Знаки меняются редко; сутки кэша + неделя stale достаточно.
      'Cache-Control': 'public, max-age=86400, stale-while-revalidate=604800',
    },
  });
};
