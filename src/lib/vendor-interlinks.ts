/**
 * Перелинковка «лендинг вендора → экспертный слой».
 *
 * Задача IDX-001 (`reports/seo/tasks/IDX-001-google-crawl-demand.md`):
 * из 222 запросов, где Яндекс держит нас в топ-10, а Google не показывает,
 * у 167 ранжирующая страница отсутствует в индексе Google. Причина
 * структурная: экспертный слой не получает внутреннего веса. Разделы
 * `/blog`, `/compare` и `/alternatives` индексируются на 9%, 0% и 0%,
 * а `/alternatives` вообще не имел ни одной входящей ссылки во всём сайте —
 * только запись в sitemap. При этом `/vendors/*` — лучший раздел по
 * покрытию (48%), то есть именно оттуда вес и должен идти.
 *
 * Связь не размечается руками: страница считается относящейся к вендору,
 * если среди её исходящих ссылок есть лендинг этого вендора или карточка
 * любого его товара. Так новый вендор и новая статья связываются сами, без
 * второго реестра, который неизбежно разошёлся бы с первым.
 */

/** Минимальная форма страницы-источника: нам нужны только ссылки и заголовок. */
export interface LinkableDoc {
  /** URL страницы на сайте, например `/blog/kak-oplatit-framer-dlya-yurlica`. */
  href: string;
  /** Подпись ссылки. */
  label: string;
  /** Все исходящие внутренние ссылки страницы. */
  outbound: string[];
}

export interface InterlinkGroup {
  title: string;
  /** Пояснение, зачем читателю эти ссылки. Пустое не выводится. */
  note?: string;
  links: { label: string; href: string }[];
}

/** Нормализация пути: без хвостового слеша, без query и hash. */
export function normalizePath(href: string): string {
  const path = (href || '').split('?')[0].split('#')[0];
  if (path === '/' || path === '') return '/';
  return path.replace(/\/+$/, '');
}

/**
 * Относится ли документ к вендору. Признак один: документ ссылается либо на
 * лендинг вендора, либо на карточку его товара.
 */
export function belongsToVendor(
  doc: LinkableDoc,
  vendorSlug: string,
  productSlugs: readonly string[],
): boolean {
  const vendorPath = `/vendors/${vendorSlug}`;
  const products = new Set(productSlugs.map((s) => `/product/${s}`));
  return doc.outbound.some((raw) => {
    const path = normalizePath(raw);
    return path === vendorPath || products.has(path);
  });
}

/**
 * Группы ссылок для блока «Ещё по теме» на лендинге вендора.
 *
 * Порядок групп — по ценности для покупателя-юрлица: сначала разбор «как это
 * покупается», потом чем заменить, потом с чем сравнить. Пустые группы
 * отбрасываются; сам лендинг из выдачи исключается, чтобы страница не
 * ссылалась на себя.
 */
export function vendorInterlinks(input: {
  vendorSlug: string;
  productSlugs: readonly string[];
  articles: readonly LinkableDoc[];
  alternatives: readonly LinkableDoc[];
  comparisons: readonly LinkableDoc[];
  /** Ограничение на группу: длинный список ссылок читается как простыня. */
  limit?: number;
}): InterlinkGroup[] {
  const { vendorSlug, productSlugs, limit = 6 } = input;
  const selfPath = `/vendors/${vendorSlug}`;

  const pick = (docs: readonly LinkableDoc[]) =>
    docs
      .filter((d) => normalizePath(d.href) !== selfPath)
      .filter((d) => belongsToVendor(d, vendorSlug, productSlugs))
      .slice(0, limit)
      .map((d) => ({ label: d.label, href: d.href }));

  const groups: InterlinkGroup[] = [
    {
      title: 'Разборы и инструкции',
      note: 'Как это оформляется на юрлицо: порядок, документы, тарифы.',
      links: pick(input.articles),
    },
    {
      title: 'Чем заменить',
      links: pick(input.alternatives),
    },
    {
      title: 'Сравнения',
      links: pick(input.comparisons),
    },
  ];
  return groups.filter((g) => g.links.length > 0);
}

// ─────────────────────────── адаптеры источников ───────────────────────────
// Данные экспертного слоя лежат в трёх разных формах. Приводим их к одной
// здесь, а не в шаблоне: шаблон не должен знать про устройство реестров.

import { comparisons } from '../data/comparisons';
import { alternativesPages } from '../data/alternatives';

/** Страницы «Аналоги X» как источники ссылок. */
export function alternativesDocs(): LinkableDoc[] {
  return alternativesPages.map((a) => ({
    href: `/alternatives/${a.slug}`,
    label: a.h1,
    outbound: [
      ...a.alternatives.map((x) => x.href),
      ...a.related.map((r) => r.href),
    ],
  }));
}

/** Страницы сравнений как источники ссылок. */
export function comparisonDocs(): LinkableDoc[] {
  return comparisons.map((c) => ({
    href: `/compare/${c.slug}`,
    label: c.h1,
    outbound: [c.a.href, c.b.href, ...c.relatedCompare.map((r) => r.href)],
  }));
}

/**
 * Статьи блога как источники ссылок. Принимает записи коллекции: обращение
 * к `getCollection` живёт в шаблоне, здесь — только преобразование, чтобы
 * функцию можно было проверить тестом без окружения Astro.
 */
export function articleDocs(
  posts: readonly {
    id: string;
    data: {
      title: string;
      draft?: boolean;
      noindex?: boolean;
      relatedProducts?: string[];
      relatedSolutions?: string[];
      related?: { label: string; href: string }[];
    };
  }[],
): LinkableDoc[] {
  return posts
    .filter((p) => !p.data.draft && !p.data.noindex)
    .map((p) => ({
      href: `/blog/${p.id}`,
      label: p.data.title,
      outbound: [
        ...(p.data.relatedProducts || []).map((s) => `/product/${s}`),
        ...(p.data.related || []).map((r) => r.href),
      ],
    }));
}
