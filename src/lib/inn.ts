/**
 * Проверка ИНН в заявке.
 *
 * Заявка приходит с двух полей, которые человек заполняет сам: название
 * организации и ИНН. Совпадают они или нет — вопрос доверия к обращению.
 * Заказчик, указавший чужой или выдуманный ИНН, либо ошибся, либо не хочет
 * называть себя; и то и другое менеджеру нужно знать до звонка, а не после
 * выставленного счёта.
 *
 * Проверка двухуровневая. Контрольная сумма считается всегда и локально —
 * она ловит выдуманные номера вроде 1234567890 мгновенно и без интернета.
 * Сверка названия с ЕГРЮЛ требует внешнего справочника и включается, когда
 * задан ключ; без ключа мы честно говорим «не сверяли», а не молчим так,
 * будто проверили.
 */

const WEIGHTS_10 = [2, 4, 10, 3, 5, 9, 4, 6, 8];
const WEIGHTS_11 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8];
const WEIGHTS_12 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8];

const digit = (weights: number[], digits: number[]): number =>
  (weights.reduce((sum, w, i) => sum + w * digits[i], 0) % 11) % 10;

export type InnKind = 'legal' | 'individual' | 'unknown';

export interface InnCheck {
  /** Введённое значение, очищенное от пробелов и дефисов. */
  value: string;
  /** Контрольная сумма сошлась. */
  valid: boolean;
  kind: InnKind;
  /** Человеческая формулировка для письма и карточки заявки. */
  note: string;
}

export function checkInn(raw: string): InnCheck {
  const value = String(raw || '').replace(/[\s-]/g, '');
  const fail = (note: string, kind: InnKind = 'unknown'): InnCheck =>
    ({ value, valid: false, kind, note });

  if (!value) return fail('ИНН не указан');
  if (!/^\d+$/.test(value)) return fail('ИНН содержит не только цифры');
  if (value.length !== 10 && value.length !== 12) {
    return fail(`ИНН из ${value.length} цифр: у организаций 10, у ИП 12`);
  }
  // Номер из одинаковых цифр проходит контрольную сумму арифметически:
  // 0000000000 и 1111111111 дают верный остаток. Так поле заполняют, чтобы
  // форма пропустила, поэтому отсекаем отдельно.
  if (/^(\d)\1+$/.test(value)) {
    return fail('ИНН из одинаковых цифр — поле заполнено формально');
  }

  const d = value.split('').map(Number);
  if (value.length === 10) {
    const ok = digit(WEIGHTS_10, d) === d[9];
    return ok
      ? { value, valid: true, kind: 'legal', note: 'ИНН организации, контрольная сумма верна' }
      : fail('контрольная сумма ИНН не сходится — номер недействителен', 'legal');
  }

  const ok = digit(WEIGHTS_11, d) === d[10] && digit(WEIGHTS_12, d) === d[11];
  return ok
    ? { value, valid: true, kind: 'individual', note: 'ИНН физлица или ИП, контрольная сумма верна' }
    : fail('контрольная сумма ИНН не сходится — номер недействителен', 'individual');
}

/** Нормализация названия для сравнения: «ООО "Ромашка"» и «ООО Ромашка» — одно. */
const LEGAL_FORMS = new Set([
  'ооо', 'оао', 'зао', 'пао', 'ао', 'ип', 'нко', 'фгуп', 'гбу', 'мбу',
  'общество', 'с', 'ограниченной', 'ответственностью', 'акционерное',
  'индивидуальный', 'предприниматель', 'публичное', 'непубличное',
]);

export function normalizeCompany(name: string): string {
  // Слова отбрасываем списком, а не границей слова: в JavaScript \b
  // определена для латиницы, и на кириллице такая замена молча
  // не срабатывает — «ООО Ромашка» так и осталось бы с «ооо».
  return String(name || '')
    .toLowerCase()
    .replace(/[^a-zа-яё0-9]+/gi, ' ')
    .split(' ')
    .filter((w) => w && !LEGAL_FORMS.has(w))
    .join(' ')
    .trim();
}

export type NameMatch = 'match' | 'mismatch' | 'not_checked';

export interface CompanyCheck extends InnCheck {
  /** Название из ЕГРЮЛ, если справочник отвечал. */
  registryName?: string;
  nameMatch: NameMatch;
  /** Итоговая строка для менеджера. */
  verdict: string;
}

/**
 * Сверка названия с ЕГРЮЛ через DaData.
 *
 * Ключа может не быть — тогда возвращаем «не сверяли». Отсутствие проверки
 * и пройденная проверка не должны выглядеть одинаково: менеджер, увидевший
 * пустое место, решит, что всё в порядке.
 */
export async function verifyCompany(
  inn: string,
  company: string,
  token = process.env.DADATA_TOKEN || '',
): Promise<CompanyCheck> {
  const base = checkInn(inn);
  const stated = normalizeCompany(company);

  if (!base.valid) {
    return { ...base, nameMatch: 'not_checked', verdict: `⚠ ${base.note}` };
  }
  if (!token) {
    return {
      ...base, nameMatch: 'not_checked',
      verdict: `${base.note}; название с ЕГРЮЛ не сверялось (нет ключа справочника)`,
    };
  }

  try {
    const res = await fetch(
      'https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          Authorization: `Token ${token}`,
        },
        body: JSON.stringify({ query: base.value, count: 1 }),
        signal: AbortSignal.timeout(5000),
      },
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json() as { suggestions?: { value?: string }[] };
    const found = data.suggestions?.[0]?.value;
    if (!found) {
      return {
        ...base, nameMatch: 'mismatch',
        verdict: `⚠ ИНН ${base.value} в ЕГРЮЛ не найден`,
      };
    }
    const registry = normalizeCompany(found);
    // Совпадением считаем вхождение: «Ромашка» и «Ромашка-Строй» — разные,
    // а «Ромашка» и «Торговый дом Ромашка» стоит показать менеджеру как
    // совпадение с оговоркой, а не как обман.
    const match = Boolean(stated) && (registry.includes(stated) || stated.includes(registry));
    return {
      ...base,
      registryName: found,
      nameMatch: match ? 'match' : 'mismatch',
      verdict: match
        ? `ИНН и название сходятся: ${found}`
        : `⚠ Название не сходится с ЕГРЮЛ. Указано «${company}», по ИНН — «${found}»`,
    };
  } catch (e) {
    return {
      ...base, nameMatch: 'not_checked',
      verdict: `${base.note}; справочник ЕГРЮЛ не ответил (${(e as Error).message})`,
    };
  }
}
