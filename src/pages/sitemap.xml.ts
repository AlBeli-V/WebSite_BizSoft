export const prerender = false;

import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';
import { getCategories, getProducts } from '../lib/directus';
import { canonicalUrl } from '../lib/seo';
import { productNoindex } from '../lib/catalog';
import { solutions } from '../data/solutions';

// Только опубликованные индексируемые страницы. Без cart/consent/admin/api/draft/noindex.
const STATIC_ROUTES: { path: string; priority: number; changefreq: string }[] = [
  { path: '/', priority: 1.0, changefreq: 'weekly' },
  { path: '/catalog', priority: 0.9, changefreq: 'weekly' },
  { path: '/catalog/domestic', priority: 0.8, changefreq: 'weekly' },
  { path: '/catalog/foreign', priority: 0.8, changefreq: 'weekly' },
  { path: '/how-we-work', priority: 0.7, changefreq: 'monthly' },
  { path: '/pricing', priority: 0.8, changefreq: 'monthly' },
  { path: '/documents', priority: 0.6, changefreq: 'monthly' },
  { path: '/blog', priority: 0.7, changefreq: 'weekly' },
  { path: '/solutions', priority: 0.6, changefreq: 'monthly' },
  { path: '/vendors/zoom', priority: 0.9, changefreq: 'weekly' },
  { path: '/vendors/jetbrains', priority: 0.9, changefreq: 'weekly' },
  { path: '/about', priority: 0.5, changefreq: 'yearly' },
  { path: '/cases', priority: 0.5, changefreq: 'monthly' },
  { path: '/contacts', priority: 0.6, changefreq: 'yearly' },
  { path: '/faq', priority: 0.6, changefreq: 'monthly' },
  { path: '/privacy', priority: 0.3, changefreq: 'yearly' },
];

function urlEntry(path: string, priority: number, changefreq: string, lastmod?: string): string {
  const loc = canonicalUrl(path); // единый формат без завершающего слеша (кроме /)
  return `  <url><loc>${loc}</loc>${lastmod ? `<lastmod>${lastmod}</lastmod>` : ''}<changefreq>${changefreq}</changefreq><priority>${priority.toFixed(1)}</priority></url>`;
}

export const GET: APIRoute = async () => {
  const entries: string[] = [];

  for (const r of STATIC_ROUTES) entries.push(urlEntry(r.path, r.priority, r.changefreq));

  // Существующие наполненные посадочные solutions (реальный контент).
  for (const s of solutions) entries.push(urlEntry(`/solutions/${s.slug}`, 0.6, 'monthly'));

  // Блог — только опубликованные (не draft), lastmod из updated/date.
  try {
    const posts = await getCollection('blog', ({ data }) => !data.draft && !data.noindex);
    for (const p of posts) {
      const lastmod = (p.data.updated || p.data.date).toISOString().slice(0, 10);
      entries.push(urlEntry(`/blog/${p.id}`, 0.6, 'monthly', lastmod));
    }
  } catch (e) {
    console.error('sitemap blog', e);
  }

  // Каталог из БД — только опубликованные; товары с noindex исключаем.
  try {
    const categories = await getCategories();
    for (const c of categories) entries.push(urlEntry(`/catalog/${c.slug}`, 0.8, 'weekly'));
    const products = await getProducts();
    for (const p of products) {
      if (p.noindex || productNoindex(p.sku)) continue;
      const lastmod = p.date_updated ? String(p.date_updated).slice(0, 10) : undefined;
      entries.push(urlEntry(`/product/${p.slug}`, 0.7, 'weekly', lastmod));
    }
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
