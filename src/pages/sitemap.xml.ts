export const prerender = false;

import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';
import { getCategories, getProducts } from '../lib/directus';
import { site } from '../config/site';
import { solutions } from '../data/solutions';

// Статические маршруты с приоритетами
const STATIC_ROUTES: { path: string; priority: number; changefreq: string }[] = [
  { path: '/', priority: 1.0, changefreq: 'weekly' },
  { path: '/catalog/', priority: 0.9, changefreq: 'weekly' },
  { path: '/how-we-work/', priority: 0.7, changefreq: 'monthly' },
  { path: '/pricing/', priority: 0.8, changefreq: 'monthly' },
  { path: '/documents/', priority: 0.6, changefreq: 'monthly' },
  { path: '/blog/', priority: 0.7, changefreq: 'weekly' },
  { path: '/about/', priority: 0.5, changefreq: 'yearly' },
  { path: '/cases/', priority: 0.5, changefreq: 'monthly' },
  { path: '/contacts/', priority: 0.6, changefreq: 'yearly' },
  { path: '/faq/', priority: 0.6, changefreq: 'monthly' },
  { path: '/privacy/', priority: 0.3, changefreq: 'yearly' },
];

function url(loc: string, priority: number, changefreq: string, lastmod?: string): string {
  return `  <url><loc>${site.url}${loc}</loc>${lastmod ? `<lastmod>${lastmod}</lastmod>` : ''}<changefreq>${changefreq}</changefreq><priority>${priority.toFixed(1)}</priority></url>`;
}

export const GET: APIRoute = async () => {
  const entries: string[] = [];

  for (const r of STATIC_ROUTES) entries.push(url(r.path, r.priority, r.changefreq));

  for (const s of solutions) entries.push(url(`/solutions/${s.slug}/`, 0.6, 'monthly'));

  try {
    const posts = await getCollection('blog', ({ data }) => !data.draft);
    for (const p of posts) {
      const lastmod = (p.data.updated || p.data.date).toISOString().slice(0, 10);
      entries.push(url(`/blog/${p.id}/`, 0.6, 'monthly', lastmod));
    }
  } catch (e) {
    console.error('sitemap blog', e);
  }

  try {
    const categories = await getCategories();
    for (const c of categories) entries.push(url(`/catalog/${c.slug}/`, 0.8, 'weekly'));
    const products = await getProducts();
    for (const p of products) entries.push(url(`/product/${p.slug}/`, 0.7, 'weekly'));
  } catch (e) {
    console.error('sitemap catalog', e);
  }

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${entries.join('\n')}
</urlset>`;

  return new Response(xml, {
    status: 200,
    headers: { 'Content-Type': 'application/xml; charset=utf-8', 'Cache-Control': 'public, max-age=3600' },
  });
};
