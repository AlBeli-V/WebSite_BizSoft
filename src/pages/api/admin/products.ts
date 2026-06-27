export const prerender = false;

import type { APIRoute } from 'astro';
import { getAllProductsAdmin } from '../../../lib/directus';
import { checkAdmin, unauthorized } from '../../../lib/admin-auth';

export const GET: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();
  try {
    const products = await getAllProductsAdmin();
    return new Response(JSON.stringify({ products }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  } catch (e) {
    console.error('admin products', e);
    return new Response(JSON.stringify({ error: 'не удалось получить товары' }), { status: 502 });
  }
};
