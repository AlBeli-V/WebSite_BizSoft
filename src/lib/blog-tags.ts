/**
 * Теги Базы знаний: слаг для URL и правила индексации страниц-подборок.
 *
 * Теги статей пишутся по-русски («оформление», «гайд»), а адрес подборки
 * `/blog/tag/<slug>` — латиницей, по той же транслитерации, что и слаги самих
 * статей (я → ya, й → j, ц → c). Таблица держится здесь, а не в шаблоне, чтобы
 * её проверял тест: два разных тега не должны склеиваться в один слаг.
 *
 * Индексируются только подборки, в которых статей не меньше порога: подборка
 * из одной-двух статей — тонкая страница-дубль, её Яндекс считает мусором.
 * Такие подборки существуют для навигации, но отдают noindex и в sitemap не
 * попадают.
 */

const MAP: Record<string, string> = {
  а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ё: 'e', ж: 'zh', з: 'z', и: 'i',
  й: 'j', к: 'k', л: 'l', м: 'm', н: 'n', о: 'o', п: 'p', р: 'r', с: 's', т: 't',
  у: 'u', ф: 'f', х: 'h', ц: 'c', ч: 'ch', ш: 'sh', щ: 'shch', ъ: '', ы: 'y', ь: '',
  э: 'e', ю: 'yu', я: 'ya',
};

/** Слаг подборки по тегу: латиница, цифры и дефисы, без пустого результата. */
export function tagSlug(tag: string): string {
  const out = tag
    .toLowerCase()
    .split('')
    .map((ch) => (ch in MAP ? MAP[ch] : ch))
    .join('')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return out || 'tag';
}

/** Минимум статей, при котором подборка индексируется и попадает в sitemap. */
export const MIN_INDEXED_TAG_POSTS = 3;

/**
 * Минимум статей, при котором тема показывается в панели тем на /blog и на
 * страницах подборок. Темы с одной статьёй панель только замусоривают
 * (на 03.09.2026 их половина из 37); до них можно дойти со страницы статьи.
 */
export const MIN_BAR_TAG_POSTS = 2;

export interface TagEntry {
  tag: string;
  slug: string;
  count: number;
  indexed: boolean;
}

/**
 * Сводка тегов по списку статей: сколько статей у каждого, слаг и признак
 * индексации. Порядок — по убыванию числа статей, при равенстве по алфавиту,
 * чтобы панель тегов была стабильной от сборки к сборке.
 */
export function collectTags(posts: { tags: string[] }[]): TagEntry[] {
  const counts = new Map<string, number>();
  for (const p of posts) for (const t of p.tags) counts.set(t, (counts.get(t) || 0) + 1);
  return [...counts.entries()]
    .map(([tag, count]) => ({ tag, slug: tagSlug(tag), count, indexed: count >= MIN_INDEXED_TAG_POSTS }))
    .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag, 'ru'));
}

/** Тег по слагу из URL, либо undefined, если такого тега нет. */
export function findTagBySlug(entries: TagEntry[], slug: string): TagEntry | undefined {
  return entries.find((e) => e.slug === slug);
}
