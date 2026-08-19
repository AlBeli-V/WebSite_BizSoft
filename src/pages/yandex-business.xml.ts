export const prerender = false;

/**
 * Прайс-лист для Яндекс Бизнеса: /yandex-business.xml
 *
 * Живая выгрузка каталога из Directus в формате YML по шаблону Яндекса.
 * Ссылку на этот URL указываем в Яндекс Бизнесе (Товары и услуги →
 * загрузка прайс-листа по ссылке) — тогда цены и состав каталога
 * обновляются сами, без ручной перезаливки файла.
 *
 * Параметры:
 *   ?all=1 — включить и скрытые от индексации позиции (плагины JB-PLG-*,
 *            личные лицензии *-IND, товары с noindex).
 */
import type { APIRoute } from 'astro';
import { getCategories, getProducts } from '../lib/directus';
import { buildYmlCatalog } from '../lib/yml-feed';
import { site } from '../config/site';

export const GET: APIRoute = async ({ url }) => {
  const includeNoindex = ['1', 'true', 'yes'].includes((url.searchParams.get('all') || '').toLowerCase());

  let xml: string;
  try {
    const [products, categories] = await Promise.all([getProducts(), getCategories()]);
    xml = buildYmlCatalog(products, categories, { siteUrl: site.url, includeNoindex });
  } catch (e) {
    console.error('yandex-business.xml', e);
    return new Response('Catalog is temporarily unavailable', { status: 503 });
  }

  return new Response(xml, {
    status: 200,
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Content-Disposition': 'inline; filename="yandex-business.xml"',
      'Cache-Control': 'public, max-age=3600',
    },
  });
};
