/**
 * Назначение производителя: вторая ось навигации на /vendors.
 *
 * До 11.09.2026 ось была одна — первая буква имени. Она помогает только тому,
 * кто уже знает имя вендора, и ничем не помогает запросу «нужен AI» или
 * «нужен дизайн-софт», хотя разделы назначения на сайте есть и наполнены.
 *
 * Источник — живой каталог: пары «вендор → раздел товара» отдаёт
 * `getCatalogFacets()`. Ни имён вендоров, ни их раскладки здесь нет и быть
 * не должно: новый вендор получает назначение в тот же день, когда его
 * товары появляются в разделе.
 *
 * Здесь только укрупнение: разделов каталога больше двух десятков, и ряд из
 * двадцати фильтров бесполезен так же, как алфавит из двадцати семи букв.
 * Раздел, не попавший в укрупнение, становится собственной группой с именем
 * из Directus — новая категория не исчезает из фильтра молча.
 */

/** Укрупнённые назначения в порядке показа. */
export const VENDOR_GROUPS: { key: string; label: string; categories: string[] }[] = [
  { key: 'ai', label: 'AI и нейросети', categories: [
    'ai', 'ai-text', 'ai-code', 'ai-image', 'ai-video', 'ai-audio', 'ai-office',
    'ai-marketing', 'ai-enterprise'] },
  { key: 'design', label: 'Дизайн и графика', categories: ['design'] },
  { key: 'development', label: 'Разработка и сайты', categories: ['development', 'database', 'web'] },
  { key: 'media', label: 'Видео и медиа', categories: ['media'] },
  { key: 'engineering', label: 'Инженерия и BIM', categories: ['engineering', 'architecture'] },
  { key: 'it', label: 'ИТ и безопасность', categories: [
    'system', 'security', 'monitoring', 'iam', 'helpdesk', 'endpoint'] },
  { key: 'work', label: 'Офис и совместная работа', categories: ['office', 'collaboration', 'pm', 'vcs'] },
  { key: 'gift', label: 'Подарочные карты', categories: ['gift-cards'] },
];

const GROUP_BY_CATEGORY = new Map<string, string>();
for (const g of VENDOR_GROUPS) for (const c of g.categories) GROUP_BY_CATEGORY.set(c, g.key);

export interface VendorGroup {
  key: string;
  label: string;
  /** Сколько вендоров относится к назначению. */
  vendors: number;
}

export interface VendorGrouping {
  /** Имя вендора (как в Directus) → ключ основного назначения. */
  groupByVendor: Map<string, string>;
  /** Непустые назначения в порядке показа. */
  groups: VendorGroup[];
  /** Ключ назначения → подпись. */
  labelOf: (key: string) => string;
}

/**
 * Разложить вендоров по назначениям.
 *
 * У вендора бывает несколько разделов сразу (Microsoft — офис, AI и рабочие
 * места). Основным считается тот, где у него больше всего позиций; при
 * равенстве — тот, что выше в порядке показа. Одно назначение на вендора —
 * сознательное упрощение: вендор, попадающий в три фильтра, ломает счётчик
 * «сколько всего» и заставляет посетителя видеть одно имя трижды.
 */
export function groupVendors(
  facets: { vendor: string | null; category: { slug: string } | null }[],
  categoryNames: Record<string, string> = {},
): VendorGrouping {
  const order = new Map(VENDOR_GROUPS.map((g, i) => [g.key, i]));
  const labels = new Map(VENDOR_GROUPS.map((g) => [g.key, g.label]));

  // вендор → ключ группы → сколько позиций
  const perVendor = new Map<string, Map<string, number>>();
  for (const row of facets) {
    const vendor = row.vendor;
    const slug = row.category?.slug;
    if (!vendor || !slug) continue;
    const key = GROUP_BY_CATEGORY.get(slug) ?? slug;
    if (!labels.has(key)) {
      // Раздел вне укрупнения: своя группа с именем из каталога.
      labels.set(key, categoryNames[slug] || slug);
      if (!order.has(key)) order.set(key, VENDOR_GROUPS.length + order.size);
    }
    const counts = perVendor.get(vendor) ?? new Map<string, number>();
    counts.set(key, (counts.get(key) ?? 0) + 1);
    perVendor.set(vendor, counts);
  }

  const groupByVendor = new Map<string, string>();
  const vendorsInGroup = new Map<string, number>();
  for (const [vendor, counts] of perVendor) {
    let best = '';
    let bestCount = -1;
    for (const [key, count] of counts) {
      const better = count > bestCount
        || (count === bestCount && (order.get(key) ?? 0) < (order.get(best) ?? 0));
      if (better) { best = key; bestCount = count; }
    }
    if (!best) continue;
    groupByVendor.set(vendor, best);
    vendorsInGroup.set(best, (vendorsInGroup.get(best) ?? 0) + 1);
  }

  const groups = [...vendorsInGroup.entries()]
    .map(([key, vendors]) => ({ key, label: labels.get(key) ?? key, vendors }))
    .sort((a, b) => (order.get(a.key) ?? 0) - (order.get(b.key) ?? 0));

  return { groupByVendor, groups, labelOf: (key: string) => labels.get(key) ?? key };
}

/**
 * Ступень веса вендора по числу позиций: сотни, десятки, единицы.
 *
 * Плитка вендора с девятьюстами позициями и вендора с одной отличались
 * только мелкой серой строкой — сетка уравнивала их в правах. Ступень
 * назначает число из каталога, а не редактор.
 */
export type VendorTier = 'major' | 'mid' | 'niche';

export function vendorTier(count: number): VendorTier {
  if (count >= 100) return 'major';
  if (count >= 10) return 'mid';
  return 'niche';
}
