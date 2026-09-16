/**
 * Одноразовый код второго фактора (TOTP, RFC 6238).
 *
 * Сорок строк на node:crypto вместо зависимости: алгоритм не менялся с
 * 2011 года, а библиотека ради него тянула бы в образ чужой код, который
 * придётся обновлять и проверять. Совместим с любым приложением-
 * аутентификатором — секрет задаётся в base32 через окружение.
 *
 * Окно допуска — один шаг в каждую сторону (±30 с): часы телефона и часы
 * сервера расходятся, и отказывать человеку из-за пары секунд нельзя.
 * Шире не делаем: каждый лишний шаг — лишний код, действующий одновременно.
 */
import { createHmac, timingSafeEqual } from 'node:crypto';

const STEP_SEC = 30;
const DIGITS = 6;

const B32 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';

/** base32 (RFC 4648, без паддинга) → байты. Регистр и пробелы не важны. */
export function base32Decode(input: string): Buffer {
  const clean = String(input || '').toUpperCase().replace(/[\s=-]/g, '');
  let bits = 0;
  let value = 0;
  const out: number[] = [];
  for (const ch of clean) {
    const idx = B32.indexOf(ch);
    if (idx < 0) throw new Error('секрет TOTP не в base32');
    value = (value << 5) | idx;
    bits += 5;
    if (bits >= 8) {
      out.push((value >>> (bits - 8)) & 0xff);
      bits -= 8;
    }
  }
  return Buffer.from(out);
}

/** Код для конкретного шага времени. */
export function totpAt(secretBase32: string, counter: number): string {
  const key = base32Decode(secretBase32);
  const buf = Buffer.alloc(8);
  buf.writeUInt32BE(Math.floor(counter / 0x1_0000_0000), 0);
  buf.writeUInt32BE(counter >>> 0, 4);
  const hmac = createHmac('sha1', key).update(buf).digest();
  const offset = hmac[hmac.length - 1] & 0x0f;
  const code =
    ((hmac[offset] & 0x7f) << 24) |
    ((hmac[offset + 1] & 0xff) << 16) |
    ((hmac[offset + 2] & 0xff) << 8) |
    (hmac[offset + 3] & 0xff);
  return String(code % 10 ** DIGITS).padStart(DIGITS, '0');
}

/**
 * Похож ли секрет на base32.
 *
 * Отдельная проверка нужна там, где решается «настроен контур или нет»:
 * секрет с посторонним символом — это не «неверный код», а неработающая
 * настройка, и сказать об этом надо прямо. В base32 нет цифр 0, 1, 8 и 9 —
 * именно на них чаще всего и спотыкаются, перенося ключ руками.
 */
export function isValidBase32(secret: string): boolean {
  const clean = String(secret || '').toUpperCase().replace(/[\s=-]/g, '');
  return clean.length > 0 && /^[A-Z2-7]+$/.test(clean);
}

/**
 * Проверить код с окном ±1 шаг. Сравнение постоянного времени.
 *
 * Испорченный секрет возвращает false, а не исключение. Раньше `base32Decode`
 * бросал наружу, вызов шёл до блока try обработчика, и вместо понятного
 * «неверный код» раздел отвечал 500. Формат секрета проверяет
 * `ops-consent-setup` на шаге check, но полагаться на то, что в окружении
 * лежит только проверенное значение, нельзя: сюда приходит и то, что
 * записали руками.
 */
export function verifyTotp(secretBase32: string, code: string, now = Date.now()): boolean {
  const typed = String(code || '').replace(/\s/g, '');
  if (!/^\d{6}$/.test(typed) || !isValidBase32(secretBase32)) return false;
  const counter = Math.floor(now / 1000 / STEP_SEC);
  try {
    for (const shift of [-1, 0, 1]) {
      const expected = totpAt(secretBase32, counter + shift);
      const a = Buffer.from(expected);
      const b = Buffer.from(typed);
      if (a.length === b.length && timingSafeEqual(a, b)) return true;
    }
  } catch (e) {
    // Сюда попадаем только при секрете, который не разобрать. Молчать нельзя:
    // снаружи это выглядит как «код не подходит», и человек будет вводить его
    // заново, пока кто-нибудь не заглянет в журнал приложения.
    console.error('totp: секрет не разобран — проверьте COMPLIANCE_TOTP_SECRET', e);
    return false;
  }
  return false;
}
