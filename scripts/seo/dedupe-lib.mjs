/**
 * Разведение одинаковых описаний внутри линейки товаров.
 *
 * У линеек (ManageEngine и подобных) short_description пишется один на все
 * редакции и объёмы, а различие живёт в названии: «Endpoint Central
 * Professional» против «Endpoint Central Security», «ADManager Plus MSP,
 * один домен клиента, 500 доменных пользователей» против «…, AD Backup на
 * 250 объектов». Общий текст даёт одинаковый лид карточки, одинаковый
 * Product.description в разметке и одинаковое описание в фидах — Яндекс
 * считает такие страницы дублями.
 *
 * Различитель не выдумывается: он берётся из названия товара. Метка —
 * это заголовочный сегмент названия (без имени вендора) плюс те сегменты,
 * которые внутри группы не общие.
 */

/** Название по сегментам: «ManageEngine X Professional, 10 серверов» → 2 части. */
export function segments(name) {
  return String(name || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

/**
 * Марка линейки в начале названия («ManageEngine») в лиде карточки лишняя:
 * она уже стоит в заголовке страницы прямо над текстом. Снимаем её только
 * когда она общая для всей группы и после этого остаётся название продукта
 * хотя бы из двух слов.
 */
export function stripBrand(head, group) {
  const first = head.split(/\s+/)[0] || '';
  const heads = group.map((g) => segments(g.name)[0] || '');
  if (!heads.every((h) => h.split(/\s+/)[0] === first)) return head;
  const rest = head.slice(first.length).trim();
  return rest.split(/\s+/).length >= 2 ? rest : head;
}

/**
 * Метка карточки внутри группы: заголовочный сегмент + сегменты, которые
 * есть не у всех. Для «SupportCenter Plus Enterprise, многоязычная версия,
 * 2 сотрудника поддержки» в группе с одноязычной версией это
 * «SupportCenter Plus Enterprise, многоязычная версия».
 */
export function labelFor(item, group, { brand = true } = {}) {
  const parts = segments(item.name);
  if (!parts.length) return '';
  const head = brand ? parts[0] : stripBrand(parts[0], group);
  const others = group.filter((g) => g !== item).map((g) => segments(g.name).slice(1));
  const common = new Set(
    parts.slice(1).filter((seg) => others.length > 0 && others.every((o) => o.includes(seg))),
  );
  const rest = parts.slice(1).filter((seg) => !common.has(seg));
  return [head, ...rest].join(', ');
}

/** Первая буква строчной, если слово русское и не аббревиатура. */
export function lowerFirst(text) {
  const s = String(text || '');
  const first = s.split(/\s+/)[0] || '';
  if (!/^[А-ЯЁ][а-яё-]+$/.test(first)) return s;
  return s[0].toLowerCase() + s.slice(1);
}

/** Одно предложение, без хвостовой точки. */
export function firstSentence(text) {
  const s = String(text || '').trim();
  const dot = s.indexOf('. ');
  return (dot > 0 ? s.slice(0, dot) : s).replace(/\.$/, '');
}

/**
 * Видимое описание карточки: метка + общий текст линейки.
 * Двоеточие в общем тексте меняем на тире, чтобы не было двух подряд.
 */
export function buildShort(base, label) {
  const body = lowerFirst(String(base || '').trim());
  if (!label) return body;
  return `${label} — ${body}`;
}

const TAIL = ' Оплата по счёту, ЭДО.';

/**
 * Тип лицензии из общего текста линейки. Без него карточки «годовая
 * подписка» и «вечная лицензия» получили бы одинаковое описание: различие
 * между ними живёт именно во второй фразе.
 */
export function licenseKind(base) {
  const m = String(base || '').match(/(Годовая подписка|Вечная лицензия|Годовое сопровождение)/i);
  return m ? m[1].toLowerCase() : '';
}

/** meta_description: метка, тип лицензии и суть линейки — в 160 символов. */
export function buildMeta(base, labels, limit = 160) {
  const { full = '', short = '' } = typeof labels === 'string' ? { full: labels } : labels;
  const lead = firstSentence(base).replace(/:/g, ' —');
  const kind = licenseKind(base);
  const heads = [full, short].filter(Boolean).map((l) => {
    const mark = kind ? `${l}, ${kind}` : l;
    return `${mark}: ${lowerFirst(lead)}`.replace(/\s+/g, ' ').trim();
  });
  for (const tail of [TAIL, '']) {
    for (const head of heads) {
      if (head.length + 1 <= limit - tail.length) return `${head}.${tail}`;
    }
  }
  // Даже короткий вариант не влез — усекаем по границе слова.
  const cut = (heads[heads.length - 1] || lead).slice(0, limit - 1);
  const sp = cut.lastIndexOf(' ');
  return `${(sp > limit * 0.6 ? cut.slice(0, sp) : cut).replace(/[ ,;:—-]+$/, '')}.`;
}

/**
 * Разводит группу карточек с одинаковым описанием.
 * Возвращает { slug: { short_description, meta_description } }.
 * Если метки внутри группы совпали, различителя в названиях нет — такую
 * группу автоматика не трогает: её разбирают руками (или разводят названия).
 */
export function dedupeGroup(group) {
  const full = group.map((item) => labelFor(item, group));
  const short = group.map((item) => labelFor(item, group, { brand: false }));
  if (new Set(full).size !== group.length) return null;
  const out = {};
  group.forEach((item, i) => {
    out[item.slug] = {
      short_description: buildShort(item.short_description, short[i]),
      meta_description: buildMeta(item.short_description, { full: full[i], short: short[i] }),
    };
  });
  return out;
}
