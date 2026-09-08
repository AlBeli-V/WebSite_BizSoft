export const prerender = false;

import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';
import { getCategories, getProducts, getVendors } from '../lib/directus';
import { canonicalUrl } from '../lib/seo';
import { isSourceUnavailable, serviceUnavailable } from '../lib/http';
import { productNoindex } from '../lib/catalog';
import { solutions } from '../data/solutions';
import { comparisons } from '../data/comparisons';
import { alternativesPages } from '../data/alternatives';
import { aiSubcategories } from '../data/ai-hub';
import { VENDORS } from '../data/vendors';
import { vendorSlug } from '../lib/vendor-links';
import { collectTags, tagSlug } from '../lib/blog-tags';

// Только опубликованные индексируемые страницы. Без cart/consent/admin/api/draft/noindex.
const STATIC_ROUTES: { path: string; priority: number; changefreq: string }[] = [
  { path: '/', priority: 1.0, changefreq: 'weekly' },
  { path: '/catalog', priority: 0.9, changefreq: 'weekly' },
  { path: '/how-we-work', priority: 0.7, changefreq: 'monthly' },
  { path: '/pricing', priority: 0.8, changefreq: 'monthly' },
  { path: '/documents', priority: 0.6, changefreq: 'monthly' },
  { path: '/blog', priority: 0.7, changefreq: 'weekly' },
  { path: '/solutions', priority: 0.6, changefreq: 'monthly' },
  // Хабы сравнений и аналогов (IDX-001): сами страницы разделов в карте были,
  // а точек входа в них не было ни в карте, ни в навигации.
  { path: '/compare', priority: 0.7, changefreq: 'monthly' },
  { path: '/alternatives', priority: 0.7, changefreq: 'monthly' },
  // Раздел «Производители» — точка входа во все лендинги вендоров. Её не было
  // в карте вовсе, хотя она собирает внутренние ссылки на весь раздел.
  { path: '/vendors', priority: 0.8, changefreq: 'weekly' },
  { path: '/vendors/zoom', priority: 0.9, changefreq: 'weekly' },
  { path: '/vendors/jetbrains', priority: 0.9, changefreq: 'weekly' },
  { path: '/vendors/openai', priority: 0.9, changefreq: 'weekly' },
  { path: '/vendors/figma', priority: 0.9, changefreq: 'weekly' },
  { path: '/vendors/maxon', priority: 0.9, changefreq: 'weekly' },
  { path: '/about', priority: 0.5, changefreq: 'yearly' },
  // Страница публичного эксперта (ENT-001): узел Person, на который ссылаются
  // founder организации и author каждой статьи.
  { path: '/authors/alexey-belyaev', priority: 0.5, changefreq: 'monthly' },
  { path: '/cases', priority: 0.5, changefreq: 'monthly' },
  { path: '/contacts', priority: 0.6, changefreq: 'yearly' },
  { path: '/faq', priority: 0.6, changefreq: 'monthly' },
  { path: '/privacy', priority: 0.3, changefreq: 'yearly' },
];

/** Убрать повторяющиеся <loc>: дубль в карте — ошибка разметки, а не мелочь. */
function dedupeByLoc(entries: string[]): string[] {
  const seen = new Set<string>();
  return entries.filter((e) => {
    const loc = e.match(/<loc>([^<]+)<\/loc>/)?.[1];
    if (!loc || seen.has(loc)) return false;
    seen.add(loc);
    return true;
  });
}

function urlEntry(path: string, priority: number, changefreq: string, lastmod?: string): string {
  const loc = canonicalUrl(path); // единый формат без завершающего слеша (кроме /)
  return `  <url><loc>${loc}</loc>${lastmod ? `<lastmod>${lastmod}</lastmod>` : ''}<changefreq>${changefreq}</changefreq><priority>${priority.toFixed(1)}</priority></url>`;
}

export const GET: APIRoute = async () => {
  const entries: string[] = [];

  // Лендинги вендоров из STATIC_ROUTES отдаются ниже, вместе с остальными:
  // их lastmod считается по карточкам, а каталог читается дальше по коду.
  // dedupeByLoc оставляет первое вхождение <loc>, поэтому если выпустить их
  // здесь без даты, датированная запись ниже будет отброшена — и без даты
  // остались бы ровно пять самых значимых страниц раздела.
  for (const r of STATIC_ROUTES) {
    if (r.path.startsWith('/vendors/')) continue;
    entries.push(urlEntry(r.path, r.priority, r.changefreq));
  }

  // Существующие наполненные посадочные solutions (реальный контент).
  for (const s of solutions) entries.push(urlEntry(`/solutions/${s.slug}`, 0.6, 'monthly', s.updated));

  // Страницы сравнения AI-сервисов (/compare/*).
  for (const c of comparisons) entries.push(urlEntry(`/compare/${c.slug}`, 0.7, 'monthly', c.updated));

  // Страницы «Аналоги X» (/alternatives/*) — слой Alternatives, PAGES-EXP-001.
  for (const a of alternativesPages) entries.push(urlEntry(`/alternatives/${a.slug}`, 0.7, 'monthly', a.updated));

  // Шаблонные посадочные производителей (креативные индустрии).
  //
  // Множество заполняется slug'ами bespoke-лендингов из STATIC_ROUTES: они уже
  // добавлены выше. Прежде оно начиналось пустым, и вендор из базы с тем же
  // именем давал второй <loc> — figma, jetbrains и openai попадали в карту
  // дважды. Дубль в sitemap поисковик считает ошибкой разметки карты.
  // Каталог читаем ДО лендингов: из карточек собираются даты содержательного
  // изменения для страниц вендоров и разделов. Прежде lastmod был только у
  // блога и части карточек — 411 из 729 URL карты (все 112 вендоров, все
  // разделы, solutions, compare, alternatives) уходили в Google вообще без
  // даты. Для Google lastmod — основной вход в планирование обхода, и при
  // 2–8 скачиваниях в сутки (замер 08.09.2026) его отсутствие означает, что
  // приоритет обхода поисковик определяет без нашего участия.
  //
  // Дата страницы вендора/раздела — максимум content_updated_at по её
  // карточкам: страница целиком собирается из них, и другого честного
  // источника даты у неё нет. Правило то же, что для карточки: date_updated
  // не годится (его двигает ежедневная переоценка по курсу ЦБ), а когда
  // штампа нет ни у одной карточки, дата не отдаётся вовсе.
  let products: Awaited<ReturnType<typeof getProducts>> = [];
  const vendorLastmod = new Map<string, string>();
  const categoryLastmod = new Map<string, string>();
  let catalogFailed = false;
  try {
    products = await getProducts();
  } catch (e) {
    console.error('sitemap catalog', e);
    catalogFailed = true;
    if (isSourceUnavailable(e)) return serviceUnavailable();
  }
  for (const p of products) {
    if (p.noindex || productNoindex(p.sku)) continue;
    const stamp = p.content_updated_at ? String(p.content_updated_at).slice(0, 10) : null;
    if (!stamp) continue;
    const vs = p.vendor ? vendorSlug(p.vendor) : null;
    if (vs && (vendorLastmod.get(vs) ?? '') < stamp) vendorLastmod.set(vs, stamp);
    const cs = typeof p.category === 'object' && p.category ? p.category.slug : null;
    if (cs && (categoryLastmod.get(cs) ?? '') < stamp) categoryLastmod.set(cs, stamp);
  }

  const vendorSeen = new Set<string>();
  for (const r of STATIC_ROUTES) {
    if (!r.path.startsWith('/vendors/')) continue;
    const slug = r.path.slice('/vendors/'.length);
    vendorSeen.add(slug);
    entries.push(urlEntry(r.path, r.priority, r.changefreq, vendorLastmod.get(slug)));
  }
  for (const v of VENDORS) {
    vendorSeen.add(v.slug);
    entries.push(urlEntry(`/vendors/${v.slug}`, 0.8, 'weekly', vendorLastmod.get(v.slug)));
  }
  // Типовые лендинги для остальных вендоров каталога (живой список из БД).
  // Сбой любого обращения к БД делает карту неполной. Отдавать её с кодом 200
  // опаснее, чем не отдавать вовсе: поисковик воспримет исчезнувшие URL как
  // снятые с публикации и начнёт выводить их из индекса. Поэтому 503.
  try {
    for (const r of await getVendors()) {
      const s = vendorSlug(r.vendor);
      if (vendorSeen.has(s)) continue;
      vendorSeen.add(s);
      entries.push(urlEntry(`/vendors/${s}`, 0.8, 'weekly', vendorLastmod.get(s)));
    }
  } catch (e) {
    console.error('sitemap vendors', e);
    if (isSourceUnavailable(e)) return serviceUnavailable();
  }

  // Блог — только опубликованные (не draft), lastmod из updated/date.
  try {
    const posts = await getCollection('blog', ({ data }) => !data.draft && !data.noindex);
    for (const p of posts) {
      const lastmod = (p.data.updated || p.data.date).toISOString().slice(0, 10);
      entries.push(urlEntry(`/blog/${p.id}`, 0.6, 'monthly', lastmod));
    }
    // Подборки статей по тегам (/blog/tag/*): в карту идут только те, где
    // статей не меньше порога — остальные отдают noindex (src/lib/blog-tags.ts).
    // Дата подборки — дата самой свежей статьи в ней: подборка целиком
    // собирается из статей, другого содержания у неё нет.
    const tagStamp = new Map<string, string>();
    for (const p of posts) {
      const stamp = (p.data.updated || p.data.date).toISOString().slice(0, 10);
      for (const tag of p.data.tags || []) {
        const slug = tagSlug(tag);
        if ((tagStamp.get(slug) ?? '') < stamp) tagStamp.set(slug, stamp);
      }
    }
    for (const t of collectTags(posts.map((p) => ({ tags: p.data.tags })))) {
      if (!t.indexed) continue;
      entries.push(urlEntry(`/blog/tag/${t.slug}`, 0.5, 'weekly', tagStamp.get(t.slug)));
    }
  } catch (e) {
    // Блог собирается из локальных файлов: сбой здесь означает поломку сборки,
    // а не временную недоступность источника — карта всё равно неполна.
    console.error('sitemap blog', e);
    return serviceUnavailable();
  }

  // Каталог из БД — только опубликованные; товары с noindex исключаем.
  // Карточки уже прочитаны выше (products); здесь остаются разделы.
  if (!catalogFailed) {
    try {
      const categories = await getCategories();
      for (const c of categories) {
        // AI-подкатегории каноничны по вложенному URL (/catalog/ai/text),
        // плоский slug (/catalog/ai-text) отдаёт 301 — в sitemap не попадает.
        const aiSub = aiSubcategories.find((s) => s.categorySlug === c.slug);
        entries.push(urlEntry(
          aiSub ? `/catalog/ai/${aiSub.sub}` : `/catalog/${c.slug}`,
          0.8, 'weekly', categoryLastmod.get(c.slug)));
      }
    } catch (e) {
      console.error('sitemap categories', e);
      if (isSourceUnavailable(e)) return serviceUnavailable();
    }
  }
  for (const p of products) {
    if (p.noindex || productNoindex(p.sku)) continue;
    // lastmod — дата содержательного изменения (content_updated_at), а не
    // date_updated: тот сдвигается ежедневной переоценкой по курсу ЦБ у
    // всего каталога разом (02.09.2026 — у 537 карточек из 593 одна дата),
    // и Google перестаёт учитывать lastmod при выборе, что обходить. Пока
    // штампа нет, честнее не отдавать дату вовсе, чем отдавать ложную.
    const lastmod = p.content_updated_at ? String(p.content_updated_at).slice(0, 10) : undefined;
    entries.push(urlEntry(`/product/${p.slug}`, 0.7, 'weekly', lastmod));
  }

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${dedupeByLoc(entries).join('\n')}
</urlset>`;

  return new Response(xml, {
    status: 200,
    headers: { 'Content-Type': 'application/xml; charset=utf-8', 'Cache-Control': 'public, max-age=3600' },
  });
};
