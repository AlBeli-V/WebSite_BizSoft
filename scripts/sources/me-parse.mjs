#!/usr/bin/env node
/**
 * Разбор снимков магазина ManageEngine в структурированный манифест.
 *
 * Вход  — каталог снимков `data/sources/manageengine/<дата>/`, который
 *         оставляет `scripts/sources/me-crawl.mjs` (details.json + *.txt).
 * Выход — `manifest.json` в том же каталоге: иерархия
 *         семейство продуктов → продукт по способу развёртывания →
 *         коммерческое предложение → вариант предложения.
 *
 * Ничего не выдумывает: каждая строка манифеста собрана из текста снимка,
 * у каждого узла остаётся source_url, source_snapshot_id и source_checked_at.
 * Позиции, где вендор не публикует цену, помечаются price_status: 'on_request'
 * и цены не получают.
 *
 * Запуск: node scripts/sources/me-parse.mjs data/sources/manageengine/2026-08-20
 */

import fs from 'node:fs';
import path from 'node:path';

const PRICE_RE = /^(?:US\$|\$)\s?([\d][\d,]*)(?:\.(\d{2}))?$/;
const QUOTE_RE = /^(?:get (?:price )?quote|contact (?:us|sales)|on request|call us)$/i;

/** Цена или явный «по запросу»; иначе null. */
function parseMoney(line) {
  const text = (line || '').trim();
  const m = text.match(PRICE_RE);
  if (m) {
    const amount = Number(m[1].replace(/,/g, '') + (m[2] ? '.' + m[2] : ''));
    return Number.isFinite(amount) ? { amount_usd: amount, price_status: 'listed' } : null;
  }
  if (QUOTE_RE.test(text)) return { amount_usd: null, price_status: 'on_request' };
  return null;
}

/**
 * Способ развёртывания и модель лицензирования — из заголовка таблицы
 * и из подписи над ней. Если в тексте нет признака, возвращаем null:
 * додумывать за вендора нельзя.
 */
function classify(title, pageHint) {
  const t = `${title} ${pageHint}`.toLowerCase();
  let deployment = null;
  if (/\bcloud\b|\bsaas\b/.test(t)) deployment = 'saas';
  if (/on-?premise|on-?prem\b/.test(t)) deployment = 'on_prem';

  let licenseModel = null;
  if (/perpetual/.test(t)) licenseModel = 'perpetual';
  else if (/subscription/.test(t)) licenseModel = 'subscription';

  // Дополнением считается не только «Add-on»: вендор так же называет
  // таблицы «Additional Users», «Multi-Language Pack» и «Failover Service» —
  // это надстройки к уже купленной лицензии, а не отдельная поставка.
  const isAddon = /add[- ]?ons?\b|\badditional\b|multi[- ]?language pack|failover|pack license/.test(t);
  const isService = /training|onboarding|implementation|migration|certification/.test(t);

  let edition = null;
  const em = title.match(/\b(Free|Standard|Professional|Premium|Enterprise(?:\s*\(Distributed\))?|UEM|Security)\s+Edition\b/i);
  if (em) edition = em[1].replace(/\s+/g, ' ').trim();

  return { deployment, license_model: licenseModel, is_addon: isAddon, is_service: isService, edition };
}

/** «mailboxes» → «mailbox», «servers» → «server», «license» не трогаем. */
function singular(word) {
  if (/(?:x|s|ch|sh)es$/.test(word)) return word.slice(0, -2);
  if (/[^s]s$/.test(word)) return word.slice(0, -1);
  return word;
}

/** Лицензионная метрика из названия строки прайса: «10 Technicians» → {10, technicians}. */
function parseMetric(name) {
  const m = name.match(/^(\d[\d,]*)\s+([A-Za-z][A-Za-z\- ]*?)(?:\s*\(|$)/);
  if (!m) return null;
  const qty = Number(m[1].replace(/,/g, ''));
  const unit = singular(m[2].trim().toLowerCase());
  return Number.isFinite(qty) ? { quantity: qty, unit } : null;
}

/** Разбор одного текстового снимка на таблицы прайса. */
function parseSnapshot(lines) {
  // Подвал магазина («Resources / Blog / Insights…») лежит текстом сразу за
  // последней таблицей. Без явной границы строки подвала — в частности пара
  // «Newsletter / Contact sales» — читаются как позиция прайса «по запросу».
  let footer = lines.length;
  for (let i = 0; i < lines.length - 1; i += 1) {
    if (lines[i] === 'Resources' && /^(Blog|Insights|Academy)$/.test(lines[i + 1] || '')) {
      footer = i;
      break;
    }
  }

  // Шапка таблицы начинается со строки «Products», за ней идут подписи
  // денежных столбцов. Названия столбцов у вендора не одинаковые: на вкладке
  // подписки это «License Fee», на вкладке вечной лицензии — «Perpetual».
  // Поэтому подписи не перечисляем списком, а собираем до первой строки, за
  // которой стоит сумма: такая строка — уже название позиции, а не столбец.
  const tables = [];
  const heads = [];
  for (let i = 1; i < footer; i += 1) {
    if (lines[i] !== 'Products') continue;
    const title = (lines[i - 1] || '').trim();
    if (!title) continue;
    const cols = [];
    let j = i + 1;
    while (j < footer && cols.length < 3) {
      const cell = lines[j];
      if (!cell || cell.length > 40 || parseMoney(cell)) break;
      if (parseMoney(lines[j + 1])) break; // это уже позиция прайса
      cols.push(cell);
      j += 1;
    }
    if (!cols.length) continue;
    heads.push({ title, cols, start: j, at: i });
  }

  heads.forEach((h, idx) => {
    const stop = Math.min(idx + 1 < heads.length ? heads[idx + 1].at - 1 : footer, footer);
    const stride = 1 + h.cols.length;
    const rows = [];
    let j = h.start;
    while (j + 1 < stop) {
      const money = parseMoney(lines[j + 1]);
      if (!money) { j += 1; continue; }
      const name = (lines[j] || '').trim();
      if (!name || parseMoney(name)) { j += 1; continue; }
      rows.push({
        name,
        ...money,
        // Второй денежный столбец — сопровождение: «Included» у подписки,
        // отдельная сумма у вечной лицензии.
        ams: h.cols.length > 1 ? (lines[j + 2] || '').trim() : null,
      });
      j += stride;
    }
    if (rows.length) tables.push({ title: h.title, columns: h.cols, rows });
  });
  return tables;
}

/** Общее начало строк — для восстановления имени продукта из заголовков таблиц. */
function commonPrefix(list) {
  if (!list.length) return '';
  let out = list[0];
  for (const item of list.slice(1)) {
    let i = 0;
    while (i < out.length && i < item.length && out[i] === item[i]) i += 1;
    out = out.slice(0, i);
    if (!out) break;
  }
  return out;
}

/** Слаг из свободного текста. */
function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
}

function main() {
  const dir = process.argv[2];
  if (!dir || !fs.existsSync(path.join(dir, 'details.json'))) {
    console.error('укажите каталог снимков, например data/sources/manageengine/2026-08-20');
    process.exit(2);
  }
  const details = JSON.parse(fs.readFileSync(path.join(dir, 'details.json'), 'utf8'));

  const families = [];
  let offerCount = 0;
  let variantCount = 0;
  let onRequestCount = 0;

  for (const row of details.rows) {
    // Страница отдаёт несколько вкладок прайса: подписка и вечная лицензия,
    // облако и установка на свои серверы. Каждая вкладка снята отдельным
    // снимком; разбираем все и складываем в одно семейство.
    const views = [
      { id: row.source_snapshot_id, tab: null, checked_at: row.source_checked_at },
      ...(row.tabs || []).map((t) => ({
        id: t.source_snapshot_id, tab: t.tab, checked_at: t.source_checked_at,
      })),
    ];

    let familyName = '';
    let pageDeployment = null;
    const offers = [];
    const seenOffers = new Map();

    for (const view of views) {
      const txtPath = path.join(dir, 'details', `${view.id}.txt`);
      if (!fs.existsSync(txtPath)) continue;
      const lines = fs.readFileSync(txtPath, 'utf8').split('\n').map((l) => l.trim());
      const tables = parseSnapshot(lines);
      if (!tables.length) continue;

      // Подпись над таблицами («Pricing for cloud edition») задаёт способ
      // развёртывания для всей страницы, если в заголовке таблицы его нет.
      const pageHint = lines.filter((l) => /^Pricing for /i.test(l)).join(' ');
      if (!pageDeployment) pageDeployment = classify('', pageHint).deployment;
      if (!familyName) {
        familyName = (row.title || row.label || '')
          .replace(/\s*(Store|Pricing & Plans|\| Buy Online).*$/i, '')
          .replace(/^ManageEngine\s+/i, '')
          .trim();
      }

      for (const t of tables) {
        const meta = classify(t.title, `${pageHint} ${view.tab || ''}`);
        const variants = t.rows.map((r) => ({
          variant_name: r.name,
          metric: parseMetric(r.name),
          amount_usd: r.amount_usd,
          price_status: r.price_status,
          maintenance: r.ams,
        }));
        // Вкладка «по умолчанию» и вкладка «Subscription» отдают один и тот же
        // прайс. Различать их по модели лицензии нельзя: у вкладки по
        // умолчанию подписи нет, и одинаковые таблицы разошлись бы по двум
        // «разным» продуктам. Ключ — название таблицы и сами цены; при
        // повторе только уточняем модель и способ поставки.
        const fingerprint = `${t.title}|${variants.map((v) => `${v.variant_name}=${v.amount_usd}`).join(',')}`;
        const twin = seenOffers.get(fingerprint);
        if (twin) {
          if (!twin.license_model && meta.license_model) {
            twin.license_model = meta.license_model;
            twin.offer_slug = slugify(t.title) + (meta.license_model === 'perpetual' ? '-perpetual' : '');
          }
          if (!twin.deployment && meta.deployment) twin.deployment = meta.deployment;
          continue;
        }

        offerCount += 1;
        for (const v of variants) {
          variantCount += 1;
          if (v.price_status === 'on_request') onRequestCount += 1;
        }
        const offer = {
          offer_slug: slugify(t.title) + (meta.license_model === 'perpetual' ? '-perpetual' : ''),
          offer_name: t.title,
          edition: meta.edition,
          deployment: meta.deployment,
          license_model: meta.license_model,
          kind: meta.is_service ? 'service' : meta.is_addon ? 'addon' : 'base',
          source_snapshot_id: view.id,
          source_tab: view.tab,
          variants,
        };
        offers.push(offer);
        seenOffers.set(fingerprint, offer);
      }
    }
    if (!offers.length) continue;

    // Часть страниц магазина отдаёт в <title> просто «ManageEngine»: имя
    // продукта там только в заголовках таблиц прайса. Без этого две разные
    // страницы получили бы один слаг «manageengine» и слились бы в одно
    // семейство.
    if (!familyName || /^(ManageEngine( Store)?|Store)$/i.test(familyName)) {
      const baseTitles = offers.filter((o) => o.kind === 'base').map((o) => o.offer_name);
      const guess = commonPrefix(baseTitles).replace(/[\s\-–—:]+$/, '').trim();
      if (guess.length >= 4) familyName = guess;
      else familyName = slugify(new URL(row.source_url).pathname.replace(/\//g, ' ')).replace(/-/g, ' ').trim();
    }

    // Продукт поставки — это пара «способ развёртывания + модель лицензии».
    // Подписка в облаке и вечная лицензия на своих серверах у вендора
    // продаются как разные продукты, и на витрине это должны быть разные
    // страницы. Способ развёртывания берётся только оттуда, где вендор его
    // назвал: у перечня вечных лицензий он обычно не подписан, и ставить
    // «установка на свои серверы» по догадке нельзя.
    //
    // Дополнение вида «Analytics Plus On-Premise add-on» — это add-on со
    // своим способом поставки, а не отдельная поставка семейства; такие
    // строки приписываются к продукту страницы, а собственный признак
    // сохраняется в addon_deployment.
    const byProduct = new Map();
    const attach = (deployment, model, offer) => {
      const key = `${deployment}|${model}`;
      if (!byProduct.has(key)) byProduct.set(key, { deployment, license_model: model, offers: [] });
      byProduct.get(key).offers.push(offer);
    };
    for (const offer of offers) {
      const model = offer.license_model || 'unspecified';
      if (offer.kind === 'base') {
        attach(offer.deployment || pageDeployment || 'unspecified', model, offer);
      } else {
        offer.addon_deployment = offer.deployment;
        offer.deployment = pageDeployment;
        attach(pageDeployment || 'unspecified', model, offer);
      }
    }

    const famSlug = slugify(familyName);
    const suffix = (deployment, model) => {
      const parts = [];
      if (deployment !== 'unspecified') parts.push(deployment.replace('_', '-'));
      if (model !== 'unspecified') parts.push(model);
      return parts.length ? `-${parts.join('-')}` : '';
    };

    families.push({
      family_slug: famSlug,
      family_name: familyName,
      vendor: 'Zoho',
      brand_line: 'ManageEngine',
      source_url: row.source_url,
      source_snapshot_id: row.source_snapshot_id,
      source_checked_at: row.source_checked_at,
      deployment_products: [...byProduct.values()].map(({ deployment, license_model, offers: list }) => ({
        deployment,
        license_model,
        product_slug: `${famSlug}${suffix(deployment, license_model)}`,
        offers: list,
      })),
    });
  }

  // Один и тот же продукт попадает в обход по нескольким адресам, которые
  // различаются только строкой запроса. Оставляем полный снимок, лишние
  // отбрасываем — иначе семейство задвоится и получит один слаг на двоих.
  const byFamily = new Map();
  const dropped = [];
  for (const family of families) {
    const kept = byFamily.get(family.family_slug);
    const size = (f) => f.deployment_products.reduce(
      (s, dp) => s + dp.offers.reduce((n, o) => n + o.variants.length, 0), 0);
    if (!kept) { byFamily.set(family.family_slug, family); continue; }
    if (size(family) > size(kept)) {
      byFamily.set(family.family_slug, family);
      dropped.push(kept.source_url);
    } else {
      dropped.push(family.source_url);
    }
  }
  const unique = [...byFamily.values()];
  const recount = (key) => unique.reduce((s, f) => s + f.deployment_products.reduce(
    (n, dp) => n + (key === 'offers' ? dp.offers.length
      : key === 'variants' ? dp.offers.reduce((k, o) => k + o.variants.length, 0) : 0), 0), 0);

  const manifest = {
    generated_from: dir,
    source_collected_at: details.collected_at,
    counts: {
      families: unique.length,
      deployment_products: unique.reduce((s, f) => s + f.deployment_products.length, 0),
      offers: recount('offers'),
      variants: recount('variants'),
      variants_on_request: onRequestCount,
      duplicate_urls_dropped: dropped.length,
    },
    duplicate_urls: dropped,
    families: unique,
  };

  const out = path.join(dir, 'manifest.json');
  fs.writeFileSync(out, JSON.stringify(manifest, null, 2) + '\n');
  console.log(`манифест: ${out}`);
  console.log(JSON.stringify(manifest.counts, null, 2));
}

main();
