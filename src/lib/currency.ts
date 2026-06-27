/**
 * Курс доллара ЦБ РФ. Источник: https://www.cbr.ru/scripts/XML_daily.asp
 * XML в кодировке windows-1251. Берём <Valute> с CharCode=USD (id R01235),
 * Value (запятая→точка) ÷ Nominal. При сбое — не перезатирать последний курс.
 *
 * Парсинг XML — чистая функция (тестируется без сети). Загрузка — отдельно.
 */

export const CBR_USD_URL = 'https://www.cbr.ru/scripts/XML_daily.asp';

export interface CbrRate {
  rate: number; // рублей за 1 единицу валюты
  date: string | null; // дата курса (атрибут Date в формате dd.mm.yyyy)
}
export type CbrUsd = CbrRate; // обратная совместимость

/** Дата документа ЦБ (атрибут Date у <ValCurs>). */
function cbrDate(xml: string): string | null {
  const m = xml.match(/<ValCurs[^>]*Date="([^"]+)"/i);
  return m ? m[1] : null;
}

/**
 * Извлечь курс валюты по CharCode (USD/EUR) из XML ЦБ (UTF-8).
 * Value (запятая→точка) ÷ Nominal. null — если не найдено/нечитаемо.
 */
export function parseCbrValute(xml: string, charCode: 'USD' | 'EUR'): CbrRate | null {
  const date = cbrDate(xml);
  const valuteRe = /<Valute[^>]*>([\s\S]*?)<\/Valute>/gi;
  let m: RegExpExecArray | null;
  while ((m = valuteRe.exec(xml)) !== null) {
    const block = m[1];
    const re = new RegExp(`<CharCode>\\s*${charCode}\\s*</CharCode>`, 'i');
    if (!re.test(block)) continue;
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

/** Совместимость: курс USD. */
export function parseCbrUsd(xml: string): CbrRate | null {
  return parseCbrValute(xml, 'USD');
}

export interface CbrRates {
  usd: number | null;
  eur: number | null;
  date: string | null;
}

/**
 * Загрузить и декодировать курсы USD и EUR ЦБ (windows-1251 → UTF-8).
 * Бросает при сетевой ошибке — вызывающий код обязан НЕ перезатирать последние удачные курсы.
 */
export async function fetchCbrRates(fetchImpl: typeof fetch = fetch): Promise<CbrRates> {
  const res = await fetchImpl(CBR_USD_URL);
  if (!res.ok) throw new Error(`CBR HTTP ${res.status}`);
  const buf = await res.arrayBuffer();
  const xml = new TextDecoder('windows-1251').decode(buf);
  const usd = parseCbrValute(xml, 'USD');
  const eur = parseCbrValute(xml, 'EUR');
  if (!usd && !eur) throw new Error('CBR: курсы не найдены в ответе');
  return { usd: usd?.rate ?? null, eur: eur?.rate ?? null, date: (usd || eur)?.date ?? null };
}

/** Совместимость: только USD. */
export async function fetchCbrUsd(fetchImpl: typeof fetch = fetch): Promise<CbrRate> {
  const r = await fetchCbrRates(fetchImpl);
  if (r.usd == null) throw new Error('CBR: USD не найден');
  return { rate: r.usd, date: r.date };
}
