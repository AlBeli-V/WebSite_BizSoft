/**
 * Проверка структурированных данных по выборке страниц.
 *
 * Правила (единый слой Schema.org, см. docs/seo/structured-data-audit.md):
 *   1) каждый блок <script type="application/ld+json"> — валидный JSON;
 *   2) на странице не больше одного BreadcrumbList, FAQPage и Product;
 *   3) у Product: offers.price > 0 (у подарочной карты — AggregateOffer с
 *      lowPrice/highPrice/offerCount и видимыми ценами внутри диапазона),
 *      priceCurrency RUB, offers.url = canonical, name/sku/image
 *      присутствуют, абсолютные URL, возврат и доставка в обоих слоях;
 *   4) все узлы Organization несут один и тот же @id, но ни один
 *      идентификатор (@id JSON-LD либо itemid microdata) не встречается на
 *      странице дважды — иначе потребитель сливает узлы и видит дубли полей;
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
  '/product/app-store-itunes-gift-card',
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

      // Один узел — один идентификатор. Потребитель (Google — точно) сливает
      // узлы с общим идентификатором, включая разные синтаксисы: @id JSON-LD
      // и itemid microdata — одно и то же имя узла. Повтор идентификатора
      // означает, что у объединённой сущности каждое общее поле приходит
      // дважды: так возникла ошибка «Поле "brand" дублируется» (01.09.2026).
      const ids = [
        ...nodes.filter((n) => n && n['@id']).map((n) => String(n['@id'])),
        ...[...html.matchAll(/itemid="([^"]+)"/g)].map((m) => m[1]),
      ];
      const dupIds = [...new Set(ids.filter((id, i) => ids.indexOf(id) !== i))];
      if (dupIds.length) problems.push(`повтор идентификатора узла (@id/itemid): ${dupIds.join(' | ')}`);

      const product = ofType(nodes, 'Product')[0];
      if (product) {
        const offer = product.offers || {};
        if (!product.name) problems.push('Product без name');
        if (!product.sku) problems.push('Product без sku');
        if (!product.image) problems.push('Product без image');
        // Подарочная карта — один Product с AggregateOffer по номиналам:
        // цены у неё нет вовсе, есть диапазон. Проверять её правилами
        // обычного Offer нельзя — иначе законная разметка читается как
        // «Offer.price: undefined» (прогон ops-schema-check 08.09.2026).
        const isAggregate = offer['@type'] === 'AggregateOffer';
        if (isAggregate) {
          const low = Number(offer.lowPrice);
          const high = Number(offer.highPrice);
          if (!(low > 0)) problems.push(`AggregateOffer.lowPrice: ${offer.lowPrice}`);
          if (!(high >= low)) problems.push(`AggregateOffer.highPrice ${offer.highPrice} < lowPrice ${offer.lowPrice}`);
          if (!(Number(offer.offerCount) >= 1)) problems.push(`AggregateOffer.offerCount: ${offer.offerCount}`);
          const mdLow = html.match(/itemprop="lowPrice" content="([0-9.]+)"/)?.[1];
          const mdHigh = html.match(/itemprop="highPrice" content="([0-9.]+)"/)?.[1];
          if (mdLow !== String(offer.lowPrice)) problems.push(`microdata lowPrice ${mdLow} ≠ JSON-LD ${offer.lowPrice}`);
          if (mdHigh !== String(offer.highPrice)) problems.push(`microdata highPrice ${mdHigh} ≠ JSON-LD ${offer.highPrice}`);
          // Витрина показывает цены номиналов: каждая обязана лежать в
          // объявленном диапазоне, иначе разметка расходится с видимым.
          const domPrices = [...html.matchAll(/data-price="([0-9.]+)"/g)].map((m) => Number(m[1]));
          const outside = domPrices.filter((v) => v < low || v > high);
          if (outside.length) problems.push(`видимые цены вне диапазона ${low}–${high}: ${outside.join(', ')}`);
        } else {
          if (!(Number(offer.price) > 0)) problems.push(`Offer.price: ${offer.price}`);
          const domPrice = html.match(/data-price="([0-9.]+)"/)?.[1];
          if (domPrice && domPrice !== String(offer.price)) problems.push(`видимая цена ${domPrice} ≠ разметке ${offer.price}`);
          const mdPrice = html.match(/itemprop="price" content="([0-9.]+)"/)?.[1];
          if (mdPrice !== String(offer.price)) problems.push(`microdata price ${mdPrice} ≠ JSON-LD ${offer.price}`);
        }
        if (offer.priceCurrency !== 'RUB') problems.push(`priceCurrency: ${offer.priceCurrency}`);
        if (offer.url !== canonical) problems.push(`Offer.url ≠ canonical (${offer.url})`);
        for (const u of [product.url, offer.url].filter(Boolean)) {
          if (!String(u).startsWith('https://')) problems.push(`относительный URL: ${u}`);
        }
        // Рекомендованные Google поля Offer: без них элемент валиден, но
        // помечен предупреждением. Должны быть в обоих слоях (08.09.2026).
        for (const field of ['hasMerchantReturnPolicy', 'shippingDetails']) {
          if (!offer[field]) problems.push(`Offer без ${field} в JSON-LD`);
          if (!html.includes(`itemprop="${field}"`)) problems.push(`Offer без ${field} в microdata`);
        }
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
