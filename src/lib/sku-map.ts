/**
 * Переходная карта артикулов: старый → новый (docs/rules/sku-system.md,
 * раздел «Переход каталога»). Пока в Directus у части позиций остаётся
 * старый артикул, слой чтения приводит его к новому, а выборки по артикулу
 * запрашивают обе формы. После переименования в базе (ops-sku-migrate) карта
 * ничего не находит и слой становится тождественным; тогда её можно снять.
 */
import SKU_MAP from '../../data/catalog/sku-map.json';

const LEGACY_TO_NEW: ReadonlyMap<string, string> = new Map(Object.entries((SKU_MAP as { map: Record<string, string> }).map));
const NEW_TO_LEGACY: ReadonlyMap<string, string> = new Map([...LEGACY_TO_NEW].map(([o, n]) => [n, o]));

/** Артикул в новой системе: старый переводится по карте, остальное — как есть. */
export function canonSku<T extends string | null | undefined>(sku: T): T {
  if (!sku) return sku;
  return (LEGACY_TO_NEW.get(sku) ?? sku) as T;
}

/** Обе формы артикула для запроса в базу, в которой мог остаться старый. */
export function skuAliases(sku: string): string[] {
  const out = new Set<string>([sku]);
  const n = LEGACY_TO_NEW.get(sku);
  if (n) out.add(n);
  const o = NEW_TO_LEGACY.get(sku);
  if (o) out.add(o);
  return [...out];
}

/** Старый артикул, который стоял у позиции до перехода; null — не было. */
export function legacySku(sku: string): string | null {
  return NEW_TO_LEGACY.get(sku) ?? null;
}

/** Привести sku и parent_sku прочитанной позиции к новой системе. */
export function canonProduct<T extends { sku: string; parent_sku?: string | null }>(p: T): T {
  const sku = canonSku(p.sku);
  const parent = canonSku(p.parent_sku ?? null);
  if (sku === p.sku && parent === (p.parent_sku ?? null)) return p;
  return { ...p, sku, parent_sku: parent };
}
