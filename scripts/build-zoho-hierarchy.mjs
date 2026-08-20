// Собирает src/data/zoho-hierarchy.ts из снимков магазина ManageEngine.
//
// Вход:
//   data/sources/manageengine/<дата>/taxonomy.json — десять групп витрины
//   data/sources/manageengine/<дата>/manifest.json — прайс по семействам
//   scripts/content/zoho-groups.json — русские названия и подводки групп
//   scripts/content/zoho-rules.json  — правила совместимости
//
// Выход: src/data/zoho-hierarchy.ts (автогенерация, руками не править).
//
// Запуск: node scripts/build-zoho-hierarchy.mjs [дата]
import { readFileSync, writeFileSync, existsSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dir, '..');
const SRC = resolve(ROOT, 'data/sources/manageengine');
const OUT = resolve(ROOT, 'src/data/zoho-hierarchy.ts');

/** Последний по дате каталог снимков, если дата не задана явно. */
function pickDay(arg) {
  if (arg) return arg;
  const days = readdirSync(SRC).filter((d) => /^\d{4}-\d{2}-\d{2}$/.test(d)).sort();
  if (!days.length) throw new Error(`нет снимков в ${SRC}`);
  return days[days.length - 1];
}

const day = pickDay(process.argv[2]);
const dir = resolve(SRC, day);
for (const f of ['taxonomy.json', 'manifest.json']) {
  if (!existsSync(resolve(dir, f))) throw new Error(`нет ${dir}/${f}`);
}
const taxonomy = JSON.parse(readFileSync(resolve(dir, 'taxonomy.json'), 'utf8'));
const manifest = JSON.parse(readFileSync(resolve(dir, 'manifest.json'), 'utf8'));
const groupCopy = JSON.parse(readFileSync(resolve(__dir, 'content/zoho-groups.json'), 'utf8'));
const rulesFile = resolve(__dir, 'content/zoho-rules.json');
const rules = existsSync(rulesFile) ? JSON.parse(readFileSync(rulesFile, 'utf8')).rules || [] : [];

/** Названия у витрины и у страницы магазина расходятся тире и регистром. */
const norm = (s) => (s || '')
  .toLowerCase()
  .replace(/[‐-―]/g, '-')
  .replace(/[^a-z0-9]+/g, ' ')
  .trim();

// Семейства из манифеста — по URL страницы и по нормализованному названию.
const byUrl = new Map(manifest.families.map((f) => [f.source_url, f]));
const byName = new Map(manifest.families.map((f) => [norm(f.family_name), f]));

const copyBySource = new Map(groupCopy.groups.map((g) => [g.source, g]));
const missingCopy = taxonomy.groups.map((g) => g.group).filter((g) => !copyBySource.has(g));
if (missingCopy.length) throw new Error(`нет русского названия для групп: ${missingCopy.join('; ')}`);

/**
 * Артикул и адрес позиции. Собираются здесь, чтобы витрина и импорт брали их
 * из одного места: разойдись они — на странице появилась бы кнопка «в
 * корзину» для несуществующего товара.
 *
 * Две позиции ServiceDesk Plus уже опубликованы и проиндексированы. Их
 * артикулы и адреса закреплены: смена слага дала бы 404 на живой странице.
 */
const PINNED = {
  'servicedesk-plus|servicedesk-plus-standard-edition-annual-subscription|10 Technicians':
    'MANAGEENGINE-SERVICEDESK-STANDARD-10',
  'servicedesk-plus|servicedesk-plus-professional-edition-annual-subscription|5 Technicians (500 IT Assets)':
    'MANAGEENGINE-SERVICEDESK-PROFESSIONAL-5',
};

const token = (text) => (text || '')
  .toUpperCase()
  .replace(/[^A-Z0-9]+/g, '-')
  .replace(/^-+|-+$/g, '');

const usedSkus = new Set();

function makeSku(familySlug, offer, variant) {
  const pinned = PINNED[`${familySlug}|${offer.offer_slug}|${variant.variant_name}`];
  if (pinned) { usedSkus.add(pinned); return pinned; }

  // Различающая часть предложения: редакция плюс то, что вендор дописал к
  // ней сверх названия семейства. Одной редакции мало: «PAM360 Enterprise
  // Edition» и «PAM360 Enterprise Edition Multi-Language» — разные прайсы.
  const familyRe = new RegExp(familySlug.replace(/-/g, '[ -]'), 'ig');
  const noiseRe = /\b(annual|subscription|perpetual|edition|add-?ons?|model|store|pricing)\b/ig;
  const rest = offer.offer_name
    .replace(/\([^)]*\)/g, ' ')
    .replace(familyRe, ' ')
    .replace(offer.edition ? new RegExp(`\\b${offer.edition.replace(/[()]/g, '')}\\b`, 'ig') : /$^/, ' ')
    .replace(noiseRe, ' ');
  const offerPart = [token(offer.edition), token(rest).slice(0, 26)]
    .filter(Boolean).join('-');
  // Название позиции целиком, без скобочных уточнений: по одной лишь метрике
  // «1 Domain» четыре разные строки прайса ADManager Plus дали бы один и тот
  // же артикул с безликими хвостами -2, -3, -4.
  const variantPart = token(variant.variant_name.replace(/\([^)]*\)/g, ' ')).slice(0, 44);
  const model = offer.license_model === 'perpetual' ? '-PERP' : '';

  const base = ['ME', token(familySlug), offerPart, variantPart]
    .filter(Boolean).join('-').replace(/-{2,}/g, '-').slice(0, 96) + model;
  let sku = base;
  let n = 2;
  while (usedSkus.has(sku)) { sku = `${base}-${n}`; n += 1; }
  usedSkus.add(sku);
  return sku;
}

let withPrice = 0;
let withoutPrice = 0;

const groups = taxonomy.groups.map((tg) => {
  const copy = copyBySource.get(tg.group);
  const families = tg.products.map((p) => {
    const m = byUrl.get(p.url) || byName.get(norm(p.name)) || null;
    if (m) withPrice += 1; else withoutPrice += 1;
    return {
      slug: m ? m.family_slug : norm(p.name).replace(/ /g, '-'),
      name: p.name,
      tagline: p.tagline,
      subgroup: p.subgroup,
      storeUrl: p.url,
      // Прайс есть не у всех: часть продуктов витрины уводит на страницу
      // вендора без публичных цен. Такие семейства показываем, но заказать
      // их можно только расчётом — выдумывать цену нельзя.
      priced: Boolean(m),
      sourceUrl: m?.source_url ?? p.url,
      sourceSnapshotId: m?.source_snapshot_id ?? null,
      sourceCheckedAt: m?.source_checked_at ?? null,
      deployments: (m?.deployment_products ?? []).map((dp) => ({
        deployment: dp.deployment,
        licenseModel: dp.license_model === 'unspecified' ? null : dp.license_model,
        slug: dp.product_slug,
        offers: dp.offers.map((o) => ({
          slug: o.offer_slug,
          name: o.offer_name,
          edition: o.edition,
          licenseModel: o.license_model,
          kind: o.kind,
          variants: o.variants.map((v) => {
            const sku = makeSku(m.family_slug, o, v);
            return {
              name: v.variant_name,
              metric: v.metric,
              amountUsd: v.amount_usd,
              priceStatus: v.price_status,
              maintenance: v.maintenance,
              sku,
              slug: sku.toLowerCase(),
            };
          }),
        })),
      })),
    };
  });
  return { slug: copy.slug, source: tg.group, name: copy.name, lead: copy.lead, families };
});

const header = `/**
 * Иерархия раздела Zoho ManageEngine: группа → семейство → продукт по
 * способу развёртывания → коммерческое предложение → вариант.
 *
 * АВТОГЕНЕРАЦИЯ из снимков магазина вендора — руками не править.
 * Пересборка: node scripts/build-zoho-hierarchy.mjs
 *
 * Источник: ${taxonomy.source_url}, снято ${taxonomy.collected_at}.
 * Состав групп и распределение продуктов взяты с витрины магазина, цены и
 * редакции — с продуктовых страниц. Ничего не достроено: если вендор не
 * назвал способ поставки, здесь стоит 'unspecified'.
 */

export interface ZohoMetric { quantity: number; unit: string }

export interface ZohoVariant {
  name: string;
  metric: ZohoMetric | null;
  amountUsd: number | null;
  priceStatus: 'listed' | 'on_request';
  maintenance: string | null;
  /** Артикул позиции в каталоге. Совпадает с тем, что заводит импорт. */
  sku: string;
  /** Адрес карточки: /product/<slug>. */
  slug: string;
}

export interface ZohoOffer {
  slug: string;
  name: string;
  edition: string | null;
  licenseModel: 'subscription' | 'perpetual' | null;
  kind: 'base' | 'addon' | 'service';
  variants: ZohoVariant[];
}

export interface ZohoDeployment {
  deployment: 'saas' | 'on_prem' | 'unspecified';
  /** Модель лицензии поставки: подписка или вечная лицензия. */
  licenseModel: 'subscription' | 'perpetual' | null;
  slug: string;
  offers: ZohoOffer[];
}

export interface ZohoFamily {
  slug: string;
  name: string;
  tagline: string;
  subgroup: string | null;
  storeUrl: string;
  priced: boolean;
  sourceUrl: string;
  sourceSnapshotId: string | null;
  sourceCheckedAt: string | null;
  deployments: ZohoDeployment[];
}

export interface ZohoGroup {
  slug: string;
  source: string;
  name: string;
  lead: string;
  families: ZohoFamily[];
}

/** Правило совместимости позиций в спецификации. */
export interface ZohoRule {
  id: string;
  appliesTo: { offerSlug?: string; familySlug?: string; variantPattern?: string };
  requires?: { edition?: string; familySlug?: string; offerSlug?: string };
  excludes?: { offerSlug?: string };
  extends?: { edition?: string; familySlug?: string; offerSlug?: string };
  reason: string;
}

export const ZOHO_SOURCE = ${JSON.stringify({ url: taxonomy.source_url, collectedAt: taxonomy.collected_at, day }, null, 2)};

export const ZOHO_GROUPS: ZohoGroup[] = ${JSON.stringify(groups, null, 2)};

export const ZOHO_RULES: ZohoRule[] = ${JSON.stringify(rules, null, 2)};

export function zohoGroup(slug: string): ZohoGroup | undefined {
  return ZOHO_GROUPS.find((g) => g.slug === slug);
}

export function zohoFamily(groupSlug: string, familySlug: string): ZohoFamily | undefined {
  return zohoGroup(groupSlug)?.families.find((f) => f.slug === familySlug);
}

/** Семейство по слагу в любой группе — для обратных ссылок с карточек. */
export function zohoFamilyAnywhere(familySlug: string): { group: ZohoGroup; family: ZohoFamily } | undefined {
  for (const group of ZOHO_GROUPS) {
    const family = group.families.find((f) => f.slug === familySlug);
    if (family) return { group, family };
  }
  return undefined;
}
`;

writeFileSync(OUT, header);
const fams = groups.reduce((s, g) => s + g.families.length, 0);
console.log(`✓ zoho-hierarchy.ts: ${groups.length} групп, ${fams} семейств`);
console.log(`  с прайсом: ${withPrice}, без прайса (расчёт под запрос): ${withoutPrice}`);
console.log(`  правил совместимости: ${rules.length}`);
console.log(`  артикулов позиций: ${usedSkus.size}`);
