// Собирает src/data/vendor-content.ts из scripts/content/<slug>.json.
// Каждый json = { summary, comparison, decision, scenarios, faq } для одного slug.
// Запуск: node scripts/build-vendor-content.mjs
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, basename } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const CONTENT_DIR = resolve(__dir, 'content');
const OUT = resolve(__dir, '../src/data/vendor-content.ts');

const files = readdirSync(CONTENT_DIR).filter((f) => f.endsWith('.json')).sort();
const entries = {};
for (const f of files) {
  const slug = basename(f, '.json');
  entries[slug] = JSON.parse(readFileSync(resolve(CONTENT_DIR, f), 'utf8'));
}

const header = `/**
 * Bespoke-контент шаблонных лендингов производителей (/vendors/<slug>).
 * АВТОГЕНЕРАЦИЯ из scripts/content/<slug>.json — руками не править,
 * меняйте JSON и запускайте: node scripts/build-vendor-content.mjs
 * Опциональные секции: если для slug есть запись — VendorLanding.astro рендерит
 * сравнение тарифов, decision-матрицу, сценарии и свой FAQ; иначе — базовый шаблон.
 */

export interface VendorComparison { cols: string[]; rows: { label: string; values: string[] }[] }
export interface VendorDecision { scenario: string; product: string; note: string }
export interface VendorScenario { title: string; text: string }
export interface VendorQA { q: string; a: string }

export interface VendorContent {
  summary?: string;
  comparison?: VendorComparison;
  decision?: VendorDecision[];
  scenarios?: VendorScenario[];
  faq?: VendorQA[];
}

export const VENDOR_CONTENT: Record<string, VendorContent> = ${JSON.stringify(entries, null, 2)};

export function vendorContent(slug: string): VendorContent {
  return VENDOR_CONTENT[slug] || {};
}
`;

writeFileSync(OUT, header);
console.log(`✓ vendor-content.ts: ${Object.keys(entries).length} вендоров (${Object.keys(entries).join(', ')})`);
