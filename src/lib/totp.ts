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

/** Проверить код с окном ±1 шаг. Сравнение постоянного времени. */
export function verifyTotp(secretBase32: string, code: string, now = Date.now()): boolean {
  const typed = String(code || '').replace(/\s/g, '');
  if (!/^\d{6}$/.test(typed) || !secretBase32) return false;
  const counter = Math.floor(now / 1000 / STEP_SEC);
  for (const shift of [-1, 0, 1]) {
    const expected = totpAt(secretBase32, counter + shift);
    const a = Buffer.from(expected);
    const b = Buffer.from(typed);
    if (a.length === b.length && timingSafeEqual(a, b)) return true;
  }
  return false;
}
