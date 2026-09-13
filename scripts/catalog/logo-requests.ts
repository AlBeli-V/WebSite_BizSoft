/**
 * Заявки на знаки продуктов — вход для ops-logo-candidates (правило
 * docs/rules/product-logos.md). Позиции без своего знака и позиции, где
 * вместо знака продукта стоит знак вендора, группируются в семейства
 * (продукт без редакции, объёма и срока): один знак на семейство.
 *
 * Семейство, названное именем вендора (Figma, Cursor, Kling AI), в заявки
 * не попадает: знак вендора и есть знак продукта.
 *
 *   npx tsx scripts/catalog/logo-requests.ts <export.json> <map.json> > data/catalog/logo-requests.json
 */
import { readFileSync, readdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { displayName } from '../../src/lib/card-display';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const [exportPath, mapPath] = process.argv.slice(2);
if (!exportPath || !mapPath) {
  console.error('нужны выгрузка каталога и карта слагов');
  process.exit(2);
}
interface Row { name: string; sku: string; vendor: string }
const rows: Row[] = JSON.parse(readFileSync(exportPath, 'utf8'));
const slugBySku = new Map<string, string>(JSON.parse(readFileSync(mapPath, 'utf8')).map((m: { sku: string; slug: string }) => [m.sku, m.slug]));
const iconMap: Record<string, string> = JSON.parse(readFileSync(resolve(ROOT, 'src/data/product-icon-map.json'), 'utf8'));
const manifest: { icon_id: string; source_kind: string }[] = JSON.parse(readFileSync(resolve(ROOT, 'docs/catalog-product-icons-manifest.json'), 'utf8'));
const kindById = new Map(manifest.map((e) => [e.icon_id, e.source_kind]));
const adobe = new Set(readdirSync(resolve(ROOT, 'src/assets/product-icons/color')).map((f) => f.replace(/\.svg$/, '')));

// Редакции, объёмы и площадки — не часть имени семейства.
const EDITION = /\b(Standard|Professional|Enterprise|Premium|Pro|Plus|Ultimate|Essential|Business|Teams?|Starter|Advanced|Basic|Core|Max|Master|Scale|Creator|Premier|Edit|Post|Suite|Intro|MSP|UEM|Security|Nexus|Distributed|Free|Individual|Organization|Collab seat|Dev seat|Full seat|Standard seat|Premium seat|Custom add-on|Metered|Global Select|Unlimited|Family|Indie|Studio|Artist|Elements|Select|Solo|Corporate|Remote Access|Cloud|Floating|Node-locked|Mac|Windows|Multi Language)\b/g;
function family(name: string): string {
  let n = displayName(name).replace(/\s*\([^)]*\)/g, '');
  n = n.split(' — ')[0].split(', ')[0].split(' | ')[0];
  n = n.replace(/\b\d+(\.\d+)?\b/g, '').replace(EDITION, '');
  return n.replace(/\s{2,}/g, ' ').trim().replace(/[\s\-/+]+$/, '');
}
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9а-я]/g, '');
const slugify = (s: string) => s.toLowerCase().replace(/[^a-z0-9а-я]+/gi, '-').replace(/^-|-$/g, '');

interface Req { id: string; vendor: string; family: string; query: string; reason: 'no-icon' | 'vendor-mark'; skus: string[]; slugs: string[]; marketplace?: string }
const byKey = new Map<string, Req>();
for (const r of rows) {
  const slug = slugBySku.get(r.sku);
  if (!slug || adobe.has(slug)) continue;
  const iconId = iconMap[slug];
  const kind = iconId ? kindById.get(iconId) || '' : '';
  const reason: Req['reason'] | null = !iconId ? 'no-icon' : /fallback|family/i.test(kind) ? 'vendor-mark' : null;
  if (!reason) continue;
  const fam = family(r.name);
  const nv = norm(r.vendor); const nf = norm(fam);
  // знак вендора уже и есть знак продукта
  if (reason === 'vendor-mark' && (nf === nv || (nf.startsWith(nv) && nf.length - nv.length <= 4) || nv.startsWith(nf))) continue;
  const key = `${r.vendor}|${fam}`;
  const req = byKey.get(key) ?? {
    id: slugify(`${r.vendor} ${fam}`), vendor: r.vendor, family: fam,
    query: `${r.vendor} ${fam} logo`.replace(/\s+/g, ' '), reason, skus: [], slugs: [],
    ...(r.sku.startsWith('JB-PLG-') ? { marketplace: fam.replace(/^JetBrains\s+/, '') } : {}),
  };
  req.skus.push(r.sku); req.slugs.push(slug);
  byKey.set(key, req);
}
const out = [...byKey.values()].sort((a, b) => a.vendor.localeCompare(b.vendor) || a.family.localeCompare(b.family));
console.log(JSON.stringify(out, null, 1));
console.error(`заявок: ${out.length}, позиций: ${out.reduce((n, r) => n + r.skus.length, 0)}`);
