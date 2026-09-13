/**
 * Пакетное добавление/обновление товаров (upsert по sku) из строк Excel/CSV.
 * Чистая логика построения плана; применение — в эндпоинте.
 */
import type { Product } from './types';
import { computePegRub, defaultMarkupCoeff, type Rates } from './pricing';
import { buildSku, validateSkuParts, type SkuKind, type SkuPlan, type SkuUnit } from './sku';
import SKU_VENDORS from '../../data/catalog/sku-vendors.json';
import { legacySku } from './sku-map';

export interface RawRow { [key: string]: string | number | null | undefined }

export const IMPORT_COLUMNS = [
  'sku', 'name', 'vendor', 'origin', 'category', 'license_type',
  'short_description', 'description', 'keywords',
  'base_price_usd', 'base_price_eur', 'peg_currency', 'markup_coeff', 'price_locked',
  'price', 'price_note', 'vat_percent', 'currency',
  'promo_price', 'promo_label', 'promo_start', 'promo_end',
  'features', 'status', 'sort',
  // Тип товара и варианты (подарочные карты, docs/gift-cards.md).
  'product_type', 'parent_sku', 'region_code', 'region_name', 'denomination', 'denomination_currency', 'availability',
  'variant_label', 'price_from',
  // Сегменты артикула новой системы (docs/rules/sku-system.md): при пустом
  // sku импорт собирает артикул сам — <вендор>-<вид>-<продукт>-<план>-<срок>-<единица>[-<вариант>].
  'sku_kind', 'sku_product', 'sku_plan', 'sku_term', 'sku_unit', 'sku_variant',
] as const;

const VENDOR_CODES = (SKU_VENDORS as { vendors: Record<string, string> }).vendors;

/**
 * Автоприсваивание артикула по сегментам строки. Код вендора — из реестра
 * data/catalog/sku-vendors.json по точному значению vendor; вендора без
 * кода импорт не принимает — код заводится в реестре через PR, потому что
 * он входит во все артикулы вендора и потом не меняется. Пустые план,
 * срок и единица получают умолчания правила: UNI, 1Y (BAL у CRD/GFT),
 * USER (NOM у CRD/GFT). Ошибка — строка пропускается с пояснением.
 */
export function autoSku(row: Record<string, string>): { sku: string } | { errors: string[] } {
  const vendor = row.vendor || '';
  const vcode = VENDOR_CODES[vendor];
  if (!vcode) return { errors: [`артикул: нет кода вендора «${vendor}» в data/catalog/sku-vendors.json`] };
  const kind = (row.sku_kind || 'LIC').toUpperCase() as SkuKind;
  const balance = kind === 'CRD' || kind === 'GFT';
  const parts = {
    vendor: vcode,
    kind,
    product: (row.sku_product || '').toUpperCase(),
    plan: (row.sku_plan || 'UNI').toUpperCase() as SkuPlan,
    term: (row.sku_term || (balance ? 'BAL' : '1Y')).toUpperCase(),
    unit: (row.sku_unit || (balance ? 'NOM' : 'USER')).toUpperCase() as SkuUnit,
    variant: (row.sku_variant || '').toUpperCase() || null,
  };
  const errs = validateSkuParts(parts);
  if (errs.length) return { errors: errs.map((e) => `артикул: ${e}`) };
  return { sku: buildSku(parts) };
}

const NUM = new Set(['price', 'vat_percent', 'base_price_usd', 'base_price_eur', 'markup_coeff', 'promo_price', 'sort', 'denomination']);

export function normPegCurrency(v: string): 'USD' | 'EUR' | '' {
  const s = v.trim().toUpperCase();
  if (['USD', 'ДОЛЛАР', 'ДОЛЛАРЫ', '$'].includes(s)) return 'USD';
  if (['EUR', 'ЕВРО', '€'].includes(s)) return 'EUR';
  return '';
}

function str(v: unknown): string { return v == null ? '' : String(v).trim(); }

export function normOrigin(v: string): 'domestic' | 'foreign' | '' {
  const s = v.toLowerCase();
  if (['domestic', 'отечественное', 'отечественное по', 'рф', 'россия', 'ru'].includes(s)) return 'domestic';
  if (['foreign', 'иностранное', 'иностранное по', 'зарубежное', 'int'].includes(s)) return 'foreign';
  return '';
}
export function normLicense(v: string): 'org' | 'individual' | 'student' | '' {
  const s = v.toLowerCase();
  if (['org', 'для организаций', 'организация', 'организации'].includes(s)) return 'org';
  if (['individual', 'индивидуальное', 'индивидуальное использование', 'личное'].includes(s)) return 'individual';
  if (['student', 'студенческая', 'студенческая версия', 'учебная'].includes(s)) return 'student';
  return '';
}
export function normBool(v: string): boolean { return ['1', 'true', 'да', 'yes', 'y'].includes(v.toLowerCase()); }
export function normNum(v: string): number | null {
  if (v === '') return null;
  const n = parseFloat(v.replace(/\s/g, '').replace(',', '.'));
  return isFinite(n) ? n : null;
}
export function normList(v: string): string[] {
  return v.split(/[|\n]/).map((s) => s.trim()).filter(Boolean);
}

/** Привести ключи строки к канону (нижний регистр, поддержка пробелов). */
export function canonRow(row: RawRow): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(row)) {
    const key = String(k).trim().toLowerCase().replace(/\s+/g, '_');
    out[key] = str(v);
  }
  return out;
}

export interface PlanItem {
  sku: string;
  name: string;
  mode: 'create' | 'update' | 'skip';
  payload: Record<string, unknown>;
  changes: { field: string; before: string; after: string }[];
  errors: string[];
}

export interface BulkPlan {
  items: PlanItem[];
  summary: { create: number; update: number; errors: number; rows: number };
}

/**
 * Построить план upsert.
 * @param rows строки (уже с каноничными значениями — см. canonRow)
 * @param existing текущие товары (для определения create/update и diff)
 * @param categoryResolver slug|name → id (вернуть null если не найдено)
 */
export interface BuildOpts {
  /** курсы ЦБ для авто-расчёта рублёвой цены из валютной себестоимости */
  rates?: Rates;
  /** базовый коэффициент наценки (если в строке не задан) */
  defaultCoeff?: number;
}

export function buildPlan(
  rows: Record<string, string>[],
  existing: Product[],
  categoryResolver: (key: string) => (string | number | null),
  opts: BuildOpts = {},
): BulkPlan {
  // Существующие позиции — и по текущему артикулу, и по старому: строка с
  // новым артикулом обновляет карточку, которая в базе ещё под старым
  // (переходная карта lib/sku-map), а не заводит дубль.
  const bySku = new Map(existing.map((p) => [p.sku, p]));
  for (const p of existing) {
    const legacy = legacySku(p.sku);
    if (legacy && !bySku.has(legacy)) bySku.set(legacy, p);
  }
  const items: PlanItem[] = [];
  let create = 0, update = 0, errors = 0;

  for (const row of rows) {
    let sku = row.sku || '';
    const errs: string[] = [];
    // Пустой sku при заполненном sku_product — автоприсваивание по сегментам.
    if (!sku && row.sku_product) {
      const auto = autoSku(row);
      if ('errors' in auto) { items.push({ sku: '', name: row.name || '', mode: 'skip', payload: {}, changes: [], errors: auto.errors }); errors++; continue; }
      sku = auto.sku;
    }
    if (!sku) { items.push({ sku: '', name: row.name || '', mode: 'skip', payload: {}, changes: [], errors: ['пустой sku'] }); errors++; continue; }

    const cur = bySku.get(sku) ?? bySku.get(legacySku(sku) ?? '');
    const mode: 'create' | 'update' = cur ? 'update' : 'create';
    const payload: Record<string, unknown> = {};
    const changes: { field: string; before: string; after: string }[] = [];

    const setField = (field: string, value: unknown) => {
      payload[field] = value;
      let before = cur ? (cur as unknown as Record<string, unknown>)[field] : undefined;
      // category в существующем товаре приходит объектом {id,...} — сравниваем по id
      if (field === 'category' && before && typeof before === 'object') before = (before as { id?: unknown }).id;
      const beforeStr = before == null ? '' : (typeof before === 'object' ? JSON.stringify(before) : String(before));
      const afterStr = value == null ? '' : (typeof value === 'object' ? JSON.stringify(value) : String(value));
      if (mode === 'create' || beforeStr !== afterStr) changes.push({ field, before: beforeStr || '—', after: afterStr });
    };

    // Карточка найдена по старому артикулу — строка переводит её на новый.
    if (cur && cur.sku !== sku) { payload.sku = sku; changes.push({ field: 'sku', before: cur.sku, after: sku }); }
    // простые строковые поля
    for (const f of ['name', 'vendor', 'short_description', 'description', 'keywords', 'price_note', 'promo_label', 'currency',
      'parent_sku', 'region_code', 'region_name', 'denomination_currency', 'variant_label']) {
      if (row[f] !== undefined && row[f] !== '') setField(f, row[f]);
    }
    // Тип товара: пусто — обычный товар; gift_card — подарочная карта.
    if (row.product_type) {
      const t = row.product_type.toLowerCase().replace(/[\s-]/g, '_');
      if (t !== 'gift_card') errs.push(`product_type: неизвестно «${row.product_type}»`); else setField('product_type', 'gift_card');
    }
    if (row.availability) {
      const a = row.availability.toLowerCase().replace(/[\s-]/g, '_');
      if (!['in_stock', 'limited', 'out_of_stock'].includes(a)) errs.push(`availability: неизвестно «${row.availability}»`); else setField('availability', a);
    }
    // даты
    for (const f of ['promo_start', 'promo_end']) {
      if (row[f]) setField(f, row[f]);
    }
    // числа
    for (const f of ['price', 'vat_percent', 'base_price_usd', 'base_price_eur', 'markup_coeff', 'promo_price', 'sort', 'denomination']) {
      if (row[f] !== undefined && row[f] !== '') {
        const n = normNum(row[f]);
        if (n == null) errs.push(`поле ${f}: не число «${row[f]}»`); else setField(f, n);
      }
    }
    // origin
    if (row.origin) { const o = normOrigin(row.origin); if (!o) errs.push(`origin: неизвестно «${row.origin}»`); else setField('origin', o); }
    // license_type
    if (row.license_type) { const l = normLicense(row.license_type); if (!l) errs.push(`license_type: неизвестно «${row.license_type}»`); else setField('license_type', l); }
    // peg_currency
    if (row.peg_currency) { const c = normPegCurrency(row.peg_currency); if (!c) errs.push(`peg_currency: неизвестно «${row.peg_currency}»`); else setField('peg_currency', c); }
    // peg_to_usd / price_locked (булевы)
    if (row.peg_to_usd !== undefined && row.peg_to_usd !== '') setField('peg_to_usd', normBool(row.peg_to_usd));
    if (row.price_locked !== undefined && row.price_locked !== '') setField('price_locked', normBool(row.price_locked));
    // Цена «от» — у родителя вариантов (минимальный номинал) и у конфигурируемых позиций.
    if (row.price_from !== undefined && row.price_from !== '') setField('price_from', normBool(row.price_from));
    // category
    if (row.category) {
      const id = categoryResolver(row.category);
      if (id == null) errs.push(`category: не найдена «${row.category}»`); else setField('category', id);
    }
    // features
    if (row.features) setField('features', normList(row.features));
    // status
    if (row.status) {
      const s = row.status.toLowerCase();
      const st = ['published', 'опубликовано', 'pub'].includes(s) ? 'published' : ['draft', 'черновик'].includes(s) ? 'draft' : ['archived', 'архив'].includes(s) ? 'archived' : '';
      if (!st) errs.push(`status: неизвестно «${row.status}»`); else setField('status', st);
    }

    // Авто-расчёт рублёвой цены из валютной себестоимости по курсу ЦБ × коэффициент.
    // Срабатывает, если в строке задана закупочная цена в USD/EUR и НЕ задана рублёвая price.
    const rowBaseUsd = row.base_price_usd !== undefined && row.base_price_usd !== '';
    const rowBaseEur = row.base_price_eur !== undefined && row.base_price_eur !== '';
    const priceProvided = row.price !== undefined && row.price !== '';
    if (!errs.length && !priceProvided && (rowBaseUsd || rowBaseEur) && opts.rates) {
      let pc = (payload.peg_currency as 'USD' | 'EUR' | undefined) ?? cur?.peg_currency ?? undefined;
      if (!pc) pc = rowBaseEur && !rowBaseUsd ? 'EUR' : 'USD';
      setField('peg_currency', pc);
      if (payload.peg_to_usd === undefined && !cur?.peg_to_usd) setField('peg_to_usd', true);
      const eff = {
        peg_to_usd: true,
        peg_currency: pc,
        base_price_usd: ((payload.base_price_usd ?? cur?.base_price_usd) ?? null) as number | null,
        base_price_eur: ((payload.base_price_eur ?? cur?.base_price_eur) ?? null) as number | null,
        markup_coeff: (payload.markup_coeff as number | undefined) ?? cur?.markup_coeff ?? null,
      };
      // Коэффициент по умолчанию зависит от типа товара: подарочные карты ×3,0.
      const productType = (payload.product_type as Product['product_type'] | undefined) ?? cur?.product_type ?? null;
      const rub = computePegRub(eff, opts.rates, opts.defaultCoeff ?? defaultMarkupCoeff({ product_type: productType }));
      if (rub != null) setField('price', rub);
    }

    // обязательное для создания
    if (mode === 'create') {
      if (!payload.name) errs.push('для нового товара нужен name');
      if (payload.slug === undefined) payload.slug = sku.toLowerCase();
      if (payload.status === undefined) payload.status = 'published';
      if (payload.currency === undefined) payload.currency = 'RUB';
      payload.sku = sku;
    }

    if (errs.length) { errors++; items.push({ sku, name: row.name || cur?.name || '', mode: 'skip', payload, changes, errors: errs }); continue; }
    if (mode === 'update' && changes.length === 0) { items.push({ sku, name: cur?.name || '', mode: 'skip', payload: {}, changes: [], errors: [] }); continue; }
    if (mode === 'create') create++; else update++;
    items.push({ sku, name: String(payload.name || cur?.name || ''), mode, payload, changes, errors: [] });
  }

  return { items, summary: { create, update, errors, rows: rows.length } };
}
