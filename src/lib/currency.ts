/**
 * Курс доллара ЦБ РФ. Источник: https://www.cbr.ru/scripts/XML_daily.asp
 * XML в кодировке windows-1251. Берём <Valute> с CharCode=USD (id R01235),
 * Value (запятая→точка) ÷ Nominal. При сбое — не перезатирать последний курс.
 *
 * Парсинг XML — чистая функция (тестируется без сети). Загрузка — отдельно.
 */

export const CBR_USD_URL = 'https://www.cbr.ru/scripts/XML_daily.asp';

export interface CbrUsd {
  rate: number; // рублей за 1 USD
  date: string | null; // дата курса (атрибут Date в формате dd.mm.yyyy)
}

/**
 * Извлечь курс USD из XML ЦБ. Работает с уже декодированной в UTF-8 строкой.
 * Возвращает null, если блок USD не найден или значение нечитаемо.
 */
export function parseCbrUsd(xml: string): CbrUsd | null {
  // дата всего документа: <ValCurs Date="27.06.2026" ...>
  const dateMatch = xml.match(/<ValCurs[^>]*Date="([^"]+)"/i);
  const date = dateMatch ? dateMatch[1] : null;

  // находим блок Valute с CharCode USD (или id R01235)
  const valuteRe = /<Valute[^>]*>([\s\S]*?)<\/Valute>/gi;
  let m: RegExpExecArray | null;
  while ((m = valuteRe.exec(xml)) !== null) {
    const block = m[1];
    const isUsd = /<CharCode>\s*USD\s*<\/CharCode>/i.test(block) || /ID="R01235"/i.test(m[0]);
    if (!isUsd) continue;

    const valueMatch = block.match(/<Value>\s*([\d.,\s]+?)\s*<\/Value>/i);
    const nominalMatch = block.match(/<Nominal>\s*(\d+)\s*<\/Nominal>/i);
    if (!valueMatch) return null;

    const value = parseFloat(valueMatch[1].replace(/\s/g, '').replace(',', '.'));
    const nominal = nominalMatch ? parseInt(nominalMatch[1], 10) || 1 : 1;
    if (!isFinite(value) || value <= 0) return null;

    return { rate: value / nominal, date };
  }
  return null;
}

/**
 * Загрузить и декодировать курс USD ЦБ. Декодирование windows-1251 — через
 * встроенный TextDecoder (в Node ≥ полный ICU). Бросает при сетевой ошибке —
 * вызывающий код обязан НЕ перезатирать последний удачный курс.
 */
export async function fetchCbrUsd(fetchImpl: typeof fetch = fetch): Promise<CbrUsd> {
  const res = await fetchImpl(CBR_USD_URL);
  if (!res.ok) throw new Error(`CBR HTTP ${res.status}`);
  const buf = await res.arrayBuffer();
  const xml = new TextDecoder('windows-1251').decode(buf);
  const parsed = parseCbrUsd(xml);
  if (!parsed) throw new Error('CBR: USD не найден в ответе');
  return parsed;
}
