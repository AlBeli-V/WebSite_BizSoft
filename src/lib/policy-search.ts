/**
 * Поиск по базе условий работы (src/data/policies.ts) для инструмента
 * `search_policies`.
 *
 * Отличие от product-search.ts — сопоставление по основе слова, а не по
 * подстроке. Каталог ищут латиницей и артикулами, условия спрашивают
 * по-русски и в разных падежах: «какие сроки поставки» не находило ответ
 * со словами «срок» и «поставка», хотя это ровно он. Полноценный
 * стеммер ради тринадцати записей не нужен — хватает совпадения по общему
 * началу слова (`stemMatch`).
 *
 * Отбор как у товаров: сначала записи, где нашлись все слова запроса, при
 * пустом результате — где нашлась часть. Пустой ответ лучше выдуманного, но
 * близкий — лучше пустого: не найдя ничего, агент начнёт сочинять условия сам.
 *
 * Ранжирование иное: слово, попавшее в вопрос или в ключевые слова, весит
 * вдвое против слова из ответа. Запись «о чём она» задаётся вопросом, а в
 * ответе слово может стоять мимоходом — «дадите закрывающие документы»
 * иначе выигрывала общая запись про порядок покупки, у которой ЭДО упомянут
 * последней строкой ответа, а не запись про закрывающие документы.
 */
import type { PolicyItem } from '../data/policies';

/** Служебные слова русского вопроса: смысла не несут, шум в поиске дают. */
const STOP = new Set([
  'как', 'что', 'где', 'когда', 'какой', 'какая', 'какие', 'каких', 'чем', 'кто',
  'это', 'вы', 'мы', 'вас', 'нас', 'ваш', 'ваши', 'мне', 'меня', 'нам',
  'ли', 'же', 'бы', 'не', 'ни', 'да', 'но', 'или', 'и', 'а',
  'для', 'при', 'по', 'на', 'в', 'во', 'с', 'со', 'от', 'до', 'из', 'за', 'у', 'о', 'об',
  'можно', 'могу', 'нужно', 'надо', 'есть', 'быть', 'буду',
]);

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/ё/g, 'е')
    .split(/[^\p{L}\p{N}%]+/u)
    .filter((t) => t.length >= 2);
}

function commonPrefix(a: string, b: string): number {
  const n = Math.min(a.length, b.length);
  let i = 0;
  while (i < n && a[i] === b[i]) i += 1;
  return i;
}

/**
 * Одно ли это слово в разных формах. Пять общих букв — надёжный признак
 * («поставки»/«поставка», «бухгалтерии»/«бухгалтерия»); четырёх хватает,
 * только если короткое слово целиком является началом длинного
 * («срок»/«сроки», «счет»/«счета»).
 */
function stemMatch(a: string, b: string): boolean {
  if (a === b) return true;
  const n = commonPrefix(a, b);
  return n >= 5 || (n >= 4 && n === Math.min(a.length, b.length));
}

/** Вес совпадения: в теме записи (вопрос + ключевые слова) — 2, в ответе — 1. */
const TOPIC_WEIGHT = 2;

export function searchPolicies(policies: PolicyItem[], query: string): PolicyItem[] {
  const toks = tokenize(query).filter((t) => !STOP.has(t));
  // Запрос из одних служебных слов («а что если») — искать нечего.
  if (toks.length === 0) return [];
  const scored = policies.map((p) => {
    const topic = tokenize(`${p.question} ${p.keywords}`);
    const body = tokenize(p.answer);
    let hit = 0;
    let score = 0;
    for (const t of toks) {
      const inTopic = topic.some((w) => stemMatch(t, w));
      const inBody = body.some((w) => stemMatch(t, w));
      if (!inTopic && !inBody) continue;
      hit += 1;
      score += (inTopic ? TOPIC_WEIGHT : 0) + (inBody ? 1 : 0);
    }
    return { p, hit, score };
  });
  // Сначала полнота покрытия запроса, и только внутри неё — вес совпадений:
  // запись, ответившая на все слова, важнее удачно совпавшей по одному.
  let found = scored.filter((s) => s.hit === toks.length);
  if (found.length === 0) found = scored.filter((s) => s.hit > 0);
  return found.sort((a, b) => b.hit - a.hit || b.score - a.score).map((s) => s.p);
}
