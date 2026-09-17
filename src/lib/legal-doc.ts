/**
 * Правовые документы сайта: канонический текст, редакции, контрольный хэш.
 *
 * Каждая редакция — отдельный файл `src/legal/<документ>/<версия>.md`, который
 * после выпуска не правится: старая редакция обязана остаться доказуемой и
 * через год, когда действующей будет уже другая. Новая редакция — новый файл,
 * а не правка существующего (docs/rules/legal-documents.md).
 *
 * Хэш считается не от файла как он лежит на диске, а от канонического текста:
 * иначе смена переводов строки при выгрузке из Windows или случайный пробел в
 * конце строки меняли бы SHA-256 документа, в котором не изменилось ни одного
 * слова, и журнал согласий ссылался бы на «другую» редакцию.
 */
import { createHash } from 'node:crypto';

export type LegalDocId =
  | 'privacy'
  | 'personal-data-consent'
  | 'marketing-consent'
  | 'cookies'
  | 'terms';

export const LEGAL_DOC_IDS: readonly LegalDocId[] = [
  'privacy',
  'personal-data-consent',
  'marketing-consent',
  'cookies',
  'terms',
] as const;

/** Публичный адрес документа. Постоянный: на него ссылаются формы и письма. */
export function legalUrl(id: LegalDocId): string {
  return `/legal/${id}`;
}

/**
 * Канонический текст редакции: то, от чего считается SHA-256 и что
 * предъявляется как доказательство.
 *
 * Приведение минимальное и обратимое по смыслу — переводы строк к `\n`,
 * снятие хвостовых пробелов, ровно один завершающий перевод строки. Ни одно
 * слово документа при этом не меняется.
 */
export function canonicalText(raw: string): string {
  return (
    raw
      .replace(/\r\n?/g, '\n')
      .split('\n')
      .map((line) => line.replace(/[ \t]+$/, ''))
      .join('\n')
      .replace(/\n+$/, '') + '\n'
  );
}

/** SHA-256 канонического текста, 64 символа в нижнем регистре. */
export function sha256(raw: string): string {
  return createHash('sha256').update(canonicalText(raw), 'utf8').digest('hex');
}

// ── Разбор документа ────────────────────────────────────────────────────────
//
// Формат намеренно узкий: заголовок `#`, подзаголовок `>`, разделы `##`,
// списки `- `, таблицы строками с `|`, всё остальное — абзац. Полноценный
// markdown сюда не тянется: документ, который предъявляют регулятору, не
// должен зависеть от поведения стороннего парсера, а состав блоков за пять
// лет менялся только в пределах этого списка.

export type LegalBlock =
  | { kind: 'heading'; text: string }
  | { kind: 'paragraph'; text: string }
  | { kind: 'list'; items: string[] }
  | { kind: 'table'; head: string[]; rows: string[][] };

export interface LegalDocContent {
  /** Название документа (строка `#`). */
  title: string;
  /** Пояснение под названием (строка `>`), может отсутствовать. */
  subtitle: string;
  blocks: LegalBlock[];
}

function splitRow(line: string): string[] {
  return line
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((c) => c.trim());
}

export function parseLegalDoc(raw: string): LegalDocContent {
  const lines = canonicalText(raw).split('\n');
  let title = '';
  let subtitle = '';
  const blocks: LegalBlock[] = [];

  let list: string[] | null = null;
  let table: { head: string[]; rows: string[][] } | null = null;
  let para: string[] = [];

  const flush = () => {
    if (para.length) {
      blocks.push({ kind: 'paragraph', text: para.join(' ') });
      para = [];
    }
    if (list) {
      blocks.push({ kind: 'list', items: list });
      list = null;
    }
    if (table) {
      blocks.push({ kind: 'table', head: table.head, rows: table.rows });
      table = null;
    }
  };

  for (const line of lines) {
    const t = line.trim();
    if (!t) {
      flush();
      continue;
    }
    if (t.startsWith('# ')) {
      flush();
      title = t.slice(2).trim();
      continue;
    }
    if (t.startsWith('> ')) {
      flush();
      subtitle = t.slice(2).trim();
      continue;
    }
    if (t.startsWith('## ')) {
      flush();
      blocks.push({ kind: 'heading', text: t.slice(3).trim() });
      continue;
    }
    if (t.startsWith('- ')) {
      if (para.length || table) flush();
      (list ??= []).push(t.slice(2).trim());
      continue;
    }
    if (t.startsWith('|')) {
      if (para.length || list) flush();
      const cells = splitRow(t);
      // Первая строка таблицы — шапка: отдельной строки-разделителя в нашем
      // формате нет, её пришлось бы синхронно править в каждом документе.
      if (!table) table = { head: cells, rows: [] };
      else table.rows.push(cells);
      continue;
    }
    if (list || table) flush();
    para.push(t);
  }
  flush();

  return { title, subtitle, blocks };
}

// ── Дата редакции для людей ─────────────────────────────────────────────────
//
// Версия редакции — это ISO-дата её вступления в силу (`effective_from` в
// терминах ТЗ 16.09.2026, п. 6). На странице она показывается словами и
// только так: контрольный хэш, номер версии и прочие служебные
// идентификаторы посетителю ничего не объясняют, а документ, предъявляемый
// как обязательство, от них выглядит технической выгрузкой.
//
// Внутренний слой при этом не трогаем: журнал согласий по-прежнему хранит
// версию и SHA-256, а архив редакций открывается по адресу с версией.

const MONTHS_GENITIVE = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
] as const;

/** Дата вступления редакции в силу: первые три сегмента версии. */
export function effectiveFrom(version: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(version || ''));
  return m ? `${m[1]}-${m[2]}-${m[3]}` : '';
}

/**
 * «16 сентября 2026 года» — то, что видит посетитель.
 *
 * Разбор строкой, а не `Intl.DateTimeFormat`: у сервера и у сборки может не
 * оказаться нужных данных локали, и вместо даты вышло бы «2026-09-16».
 */
export function legalDateRu(version: string): string {
  const iso = effectiveFrom(version);
  if (!iso) return '';
  const [y, m, d] = iso.split('-');
  const month = MONTHS_GENITIVE[Number(m) - 1];
  return month ? `${Number(d)} ${month} ${y} года` : iso;
}
