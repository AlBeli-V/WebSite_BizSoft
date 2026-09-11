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
/** Строка «что выбрать». slug делает рекомендацию ссылкой на карточку. */
export interface VendorDecision { scenario: string; product: string; note: string; slug?: string }
export interface VendorScenario { title: string; text: string; note?: string }
export interface VendorQA { q: string; a: string; group?: string }
/** Блок «Безопасность и данные»: что с данными компании и что спросит ИБ. */
export interface VendorSecurity { text: string; cta?: string }
/**
 * Карточка тарифа: минимальный объём заказа и как называются единицы.
 * Ключ — slug или sku позиции (правило catalog.md). Минимум вендора живёт
 * здесь, а не в тексте FAQ: покупатель считает бюджет по счётчику мест, и
 * «от 2 мест» он должен видеть там же, где считает.
 */
export interface VendorCardMeta {
  minQty?: number;
  qtyLabel?: string;
  check?: string;
  /** Случай, к которому относится позиция (см. VendorSegment). */
  seg?: string;
  /** Плашка над названием: план, редакция, тип места. */
  badge?: string;
  /** Кому адресована позиция — вместо короткого описания из каталога. */
  forWhom?: string;
  /** Состав позиции — вместо списка возможностей из каталога. */
  features?: string[];
}
/** Разбор, который нужен до цен: типы мест, виды лицензий, редакции. */
export interface VendorExplainer { title: string; items: VendorScenario[] }

/**
 * Выбор ситуации перед сеткой тарифов. Покупатель выбирает не между
 * тарифами, а между случаями: «сотруднику», «команде», «в свой продукт».
 * Отмеченный случай сужает сетку до карточек со своим полем seg.
 */
export interface VendorSegment {
  id: string; title: string; text: string;
  /** Короткая приписка на плитке: что это даёт. */
  hint?: string;
  /** Почему именно этот случай — показывается после выбора. */
  why?: string;
  /**
   * Позиции случая: slug или sku. Состав случая перечисляется в одном
   * месте — иначе он расползается по карточкам и расходится с текстом.
   */
  keys?: string[];
}

/** Раздел линейки: своя подсетка карточек (например, личные и командные планы). */
export interface VendorGroup { id: string; title: string; note?: string; items: string[] }

/**
 * Полоса номиналов: варианты одной родительской позиции (пополнение
 * баланса, пакеты кредитов). Плитками, а не карточками: одиннадцать
 * одинаковых карточек заменили бы собой страницу.
 */
export interface VendorDenominations {
  title: string; note?: string;
  /** Родительская позиция — slug или sku; её варианты и составляют ряд. */
  parent: string;
  /** Что показывает плитка: «$», «кредитов». */
  unit?: string;
}

/**
 * Быстрый подбор: ярлык задачи или стека → продукт. Не опросник: один клик
 * подставляет выбор в форму и ведёт к карточке.
 */
export interface VendorPick { label: string; product: string; target?: string; query: string }

/**
 * Свободный блок страницы. Виды: текст, ячейки, плитки-ссылки на товары и
 * раскрывающийся список. Больше видов не заводить: следующий вид — повод
 * спросить, не пора ли этой странице снова стать своей.
 */
export interface VendorSection {
  id?: string;
  title: string;
  kind?: 'prose' | 'cells' | 'links' | 'accordion';
  text?: string;
  note?: string;
  cells?: VendorScenario[];
  links?: { label: string; slug?: string; href?: string; text?: string }[];
  items?: VendorQA[];
  /** Подпись кнопки, ведущей к форме страницы. */
  cta?: string;
  /** Ссылка «дальше по теме» под блоком: каталог раздела, документация. */
  more?: { label: string; href: string };
  /** Куда ставить блок: до тарифов или после сравнения (по умолчанию). */
  place?: 'before-products' | 'after-compare' | 'before-buy';
}

export interface VendorContent {
  summary?: string;
  /** Абзац «какой тариф кому» — сразу за блоком «Коротко». */
  intro?: string;
  explainer?: VendorExplainer;
  segments?: VendorSegment[];
  groups?: VendorGroup[];
  denominations?: VendorDenominations;
  picks?: { title: string; note?: string; items: VendorPick[] };
  sections?: VendorSection[];
  /** Темы блока вопросов: вопрос попадает в тему по полю group. */
  faqGroups?: { id: string; title: string }[];
  cards?: Record<string, VendorCardMeta>;
  /**
   * Порядок карточек: slug или sku. Не перечисленные уходят в конец.
   * Нужен там, где линейка читается только в своём порядке — планы от
   * младшего к старшему, а не как отдала база.
   */
  order?: string[];
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
