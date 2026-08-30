/**
 * Проверка структурированных данных по выборке страниц.
 *
 * Правила (единый слой Schema.org, см. docs/seo/structured-data-audit.md):
 *   1) каждый блок <script type="application/ld+json"> — валидный JSON;
 *   2) на странице не больше одного BreadcrumbList, FAQPage и Product;
 *   3) у Product: offers.price > 0, priceCurrency RUB, offers.url = canonical,
 *      name/sku/image присутствуют, абсолютные URL;
 *   4) все узлы Organization несут один и тот же @id;
 *   5) microdata-цена карточки (itemprop="price") равна цене JSON-LD;
 *   6) видимая цена (data-price) равна цене разметки;
 *   7) canonical присутствует и абсолютен.
 *
 * Запуск: node scripts/seo/check-structured-data.mjs [--base http://127.0.0.1:4399]
 *         [--urls /a,/b,/c]
 * По умолчанию база — локальный смоук-порт, список — представители всех
 * классов страниц. Для прода: --base https://biz-soft.pro (запускается с
 * раннера GitHub — из сессии egress к проду закрыт).
 * Код выхода 1, если есть нарушения.
 */

const args = process.argv.slice(2);
const argVal = (name, def) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : def;
};

const BASE = argVal('--base', 'http://127.0.0.1:4399').replace(/\/$/, '');

/** Представители всех классов страниц (лендинги/товары — слаги стаба). */
const DEFAULT_URLS = [
  '/',
  '/catalog',
  '/catalog/design',
  '/catalog/ai',
  '/catalog/ai/text',
  '/product/chatgpt-business',
  '/product/figma-organization',
  '/product/tovar-s-akciej',
  '/product/tovar-po-zaprosu',
  '/vendors',
  '/vendors/jetbrains',
  '/vendors/zoom',
  '/vendors/openai',
  '/vendors/figma',
  '/vendors/maxon',
  '/vendors/adobe',
  '/vendors/canva',
  '/vendors/miro',
  '/vendors/zoho',
  '/compare/chatgpt-vs-claude',
  '/compare/cursor-vs-copilot',
  '/blog',
  '/blog/kak-oformit-korporativnuyu-ai-podpisku-na-yurlico',
  '/blog/bezopasnost-dannyh-v-korporativnyh-ai',
  '/solutions',
  '/faq',
  '/pricing',
  '/how-we-work',
  '/contacts',
  '/about',
  '/cases',
  '/documents',
];

const urls = (argVal('--urls', '') || '').split(',').filter(Boolean).length
  ? argVal('--urls', '').split(',').map((s) => s.trim())
  : DEFAULT_URLS;

function ldNodes(html) {
  const nodes = [];
  for (const m of html.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/gs)) {
    const parsed = JSON.parse(m[1]); // бросит при битом JSON — ловим выше
    nodes.push(...(Array.isArray(parsed) ? parsed : [parsed]));
  }
  return nodes;
}
const ofType = (nodes, t) => nodes.filter((n) => n['@type'] === t || (Array.isArray(n['@type']) && n['@type'].includes(t)));

let bad = 0;
let checked = 0;

for (const path of urls) {
  const problems = [];
  let status = 0;
  try {
    const res = await fetch(BASE + path, { redirect: 'manual' });
    status = res.status;
    if (status !== 200) {
      problems.push(`HTTP ${status}`);
    } else {
      const html = await res.text();
      let nodes = [];
      try {
        nodes = ldNodes(html);
      } catch (e) {
        problems.push(`битый JSON-LD: ${e.message}`);
      }

      for (const [type, max] of [['BreadcrumbList', 1], ['FAQPage', 1], ['Product', 1]]) {
        const n = ofType(nodes, type).length;
        if (n > max) problems.push(`${type}: ${n} шт. (дубль)`);
      }

      const canonical = html.match(/<link rel="canonical" href="([^"]+)"/)?.[1];
      if (!canonical || !canonical.startsWith('https://')) problems.push(`canonical: ${canonical || 'нет'}`);

      const orgIds = [...new Set(ofType(nodes, 'Organization').map((o) => o['@id']))];
      if (orgIds.length > 1) problems.push(`Organization с разными @id: ${orgIds.join(' | ')}`);

      const product = ofType(nodes, 'Product')[0];
      if (product) {
        const offer = product.offers || {};
        if (!product.name) problems.push('Product без name');
        if (!product.sku) problems.push('Product без sku');
        if (!product.image) problems.push('Product без image');
        if (!(Number(offer.price) > 0)) problems.push(`Offer.price: ${offer.price}`);
        if (offer.priceCurrency !== 'RUB') problems.push(`priceCurrency: ${offer.priceCurrency}`);
        if (offer.url !== canonical) problems.push(`Offer.url ≠ canonical (${offer.url})`);
        for (const u of [product.url, offer.url].filter(Boolean)) {
          if (!String(u).startsWith('https://')) problems.push(`относительный URL: ${u}`);
        }
        const domPrice = html.match(/data-price="([0-9.]+)"/)?.[1];
        if (domPrice && domPrice !== String(offer.price)) problems.push(`видимая цена ${domPrice} ≠ разметке ${offer.price}`);
        const mdPrice = html.match(/itemprop="price" content="([0-9.]+)"/)?.[1];
        if (mdPrice !== String(offer.price)) problems.push(`microdata price ${mdPrice} ≠ JSON-LD ${offer.price}`);
      }

      // Страница «цены по запросу» не должна нести Product ни в одном слое.
      if (html.includes('Цена по запросу') && path.startsWith('/product/')) {
        if (product) problems.push('Product на странице «цена по запросу»');
        if (html.includes('itemtype="https://schema.org/Product"')) problems.push('microdata Product на «цене по запросу»');
      }
    }
  } catch (e) {
    problems.push(`запрос не удался: ${e.message}`);
  }

  checked++;
  if (problems.length) {
    bad++;
    console.log(`❌ ${path} — ${problems.join('; ')}`);
  } else {
    console.log(`✅ ${path}`);
  }
}

console.log(`\nИтог: ${checked - bad}/${checked} страниц без нарушений`);
process.exit(bad ? 1 : 0);
