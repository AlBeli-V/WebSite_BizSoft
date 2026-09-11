// Собирает src/data/vendor-content.ts из scripts/content/<slug>.json.
// Каждый json = { summary, comparison, decision, scenarios, faq } для одного slug.
// Запуск: node scripts/build-vendor-content.mjs
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, basename } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const CONTENT_DIR = resolve(__dir, 'content');
const OUT = resolve(__dir, '../src/data/vendor-content.ts');

// zoho-cards/groups/rules — входные данные пайплайна build-zoho-catalog.mjs,
// а не контент лендинга: их структура не совпадает с VendorContent.
const PIPELINE_FILES = new Set(['zoho-cards.json', 'zoho-groups.json', 'zoho-rules.json']);
const files = readdirSync(CONTENT_DIR)
  .filter((f) => f.endsWith('.json') && !PIPELINE_FILES.has(f))
  .sort();
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
/** Блок «Безопасность и данные»: что с данными компании и что спросит ИБ. */
export interface VendorSecurity { text: string; cta?: string }
/**
 * Карточка тарифа: минимальный объём заказа и как называются единицы.
 * Ключ — slug или sku позиции (правило catalog.md). Минимум вендора живёт
 * здесь, а не в тексте FAQ: покупатель считает бюджет по счётчику мест, и
 * «от 2 мест» он должен видеть там же, где считает.
 */
export interface VendorCardMeta { minQty?: number; qtyLabel?: string; check?: string }

export interface VendorContent {
  summary?: string;
  /** Абзац «какой тариф кому» — сразу за блоком «Коротко». */
  intro?: string;
  cards?: Record<string, VendorCardMeta>;
  security?: VendorSecurity;
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
