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

  const isAddon = /add-?on|addons?\b/.test(t);
  const isService = /training|onboarding|implementation/.test(t);

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

  const headers = [];
  for (let i = 1; i < footer; i += 1) {
    if (lines[i] === 'License Fee' && lines[i - 1] === 'Products') headers.push(i);
  }

  const tables = [];
  headers.forEach((h, idx) => {
    const title = (lines[h - 2] || '').trim();
    if (!title) return;
    // Третий столбец таблицы: обычно «AMS*», иногда «Maintenance».
    const thirdCol = (lines[h + 1] || '').trim();
    const hasThird = !parseMoney(thirdCol) && thirdCol.length > 0 && thirdCol.length < 40;
    const stop = Math.min(idx + 1 < headers.length ? headers[idx + 1] - 2 : lines.length, footer);

    const rows = [];
    let j = h + (hasThird ? 2 : 1);
    while (j + 1 < stop) {
      const money = parseMoney(lines[j + 1]);
      if (!money) { j += 1; continue; }
      const name = (lines[j] || '').trim();
      if (!name || parseMoney(name)) { j += 1; continue; }
      const third = hasThird ? (lines[j + 2] || '').trim() : null;
      rows.push({ name, ...money, ams: third });
      j += hasThird ? 3 : 2;
    }
    if (rows.length) tables.push({ title, third_column: hasThird ? thirdCol : null, rows });
  });
  return tables;
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
    const txtPath = path.join(dir, 'details', `${row.source_snapshot_id}.txt`);
    if (!fs.existsSync(txtPath)) continue;
    const lines = fs.readFileSync(txtPath, 'utf8').split('\n').map((l) => l.trim());
    const tables = parseSnapshot(lines);
    if (!tables.length) continue;

    // Подпись над таблицами («Pricing for cloud edition») задаёт способ
    // развёртывания для всей страницы, если в заголовке таблицы его нет.
    const pageHint = lines.filter((l) => /^Pricing for /i.test(l)).join(' ');
    const familyName = (row.title || row.label || '')
      .replace(/\s*(Store|Pricing & Plans|\| Buy Online).*$/i, '')
      .replace(/^ManageEngine\s+/i, '')
      .trim();

    const offers = tables.map((t) => {
      const meta = classify(t.title, pageHint);
      offerCount += 1;
      const variants = t.rows.map((r) => {
        variantCount += 1;
        if (r.price_status === 'on_request') onRequestCount += 1;
        return {
          variant_name: r.name,
          metric: parseMetric(r.name),
          amount_usd: r.amount_usd,
          price_status: r.price_status,
          maintenance: r.ams,
        };
      });
      return {
        offer_slug: slugify(t.title),
        offer_name: t.title,
        edition: meta.edition,
        deployment: meta.deployment,
        license_model: meta.license_model,
        kind: meta.is_service ? 'service' : meta.is_addon ? 'addon' : 'base',
        variants,
      };
    });

    // Способ развёртывания страницы — из подписи над таблицами.
    const pageDeployment = classify('', pageHint).deployment;

    // Продукт по способу развёртывания собирается ТОЛЬКО из базовых
    // предложений. Дополнение вида «Analytics Plus On-Premise add-on» — это
    // add-on со своим способом поставки, а не отдельная поставка семейства;
    // такие строки приписываются к продукту страницы, а собственный признак
    // сохраняется в addon_deployment.
    const byDeployment = new Map();
    const attach = (key, offer) => {
      if (!byDeployment.has(key)) byDeployment.set(key, []);
      byDeployment.get(key).push(offer);
    };
    for (const offer of offers) {
      if (offer.kind === 'base') {
        attach(offer.deployment || pageDeployment || 'unspecified', offer);
      } else {
        offer.addon_deployment = offer.deployment;
        offer.deployment = pageDeployment;
        attach(pageDeployment || 'unspecified', offer);
      }
    }

    families.push({
      family_slug: slugify(familyName),
      family_name: familyName,
      vendor: 'Zoho',
      brand_line: 'ManageEngine',
      source_url: row.source_url,
      source_snapshot_id: row.source_snapshot_id,
      source_checked_at: row.source_checked_at,
      deployment_products: [...byDeployment.entries()].map(([deployment, list]) => ({
        deployment,
        product_slug: `${slugify(familyName)}${deployment === 'unspecified' ? '' : `-${deployment.replace('_', '-')}`}`,
        offers: list,
      })),
    });
  }

  const manifest = {
    generated_from: dir,
    source_collected_at: details.collected_at,
    counts: {
      families: families.length,
      deployment_products: families.reduce((s, f) => s + f.deployment_products.length, 0),
      offers: offerCount,
      variants: variantCount,
      variants_on_request: onRequestCount,
    },
    families,
  };

  const out = path.join(dir, 'manifest.json');
  fs.writeFileSync(out, JSON.stringify(manifest, null, 2) + '\n');
  console.log(`манифест: ${out}`);
  console.log(JSON.stringify(manifest.counts, null, 2));
}

main();
