/**
 * Защита от подделки межсайтового запроса для действий, которые меняют
 * состояние по нажатию кнопки: отписка, cookie-выбор, операции админ-раздела.
 *
 * Схема — «двойная отправка» с подписью. Страница получает cookie со
 * случайным значением и то же значение скрытым полем формы. Чужой сайт
 * может заставить браузер отправить наш cookie, но прочитать его и
 * подставить в тело запроса не может: политика одного источника этого не
 * позволяет. Поэтому совпадение cookie и поля означает, что запрос
 * отправлен с нашей страницы.
 *
 * Подпись поверх случайного значения нужна, чтобы cookie нельзя было
 * навязать с соседнего поддомена: неподписанное значение туда подставит
 * кто угодно, и сравнение сойдётся.
 *
 * Проверка источника (`Origin`) стоит рядом и не заменяет токен: часть
 * клиентов заголовок не шлёт вовсе, и отказывать им нельзя.
 */
import { createHmac, randomBytes, timingSafeEqual } from 'node:crypto';

export const CSRF_COOKIE = 'bz_csrf';
export const CSRF_FIELD = 'csrf_token';

const SECRET =
  process.env.CSRF_SECRET ||
  import.meta.env.CSRF_SECRET ||
  process.env.UNSUBSCRIBE_SECRET ||
  import.meta.env.UNSUBSCRIBE_SECRET ||
  '';

export function isCsrfConfigured(): boolean {
  return SECRET.length >= 16;
}

function sign(nonce: string): string {
  return createHmac('sha256', SECRET).update(nonce).digest('base64url');
}

/** Новое значение токена: `<nonce>.<подпись>`. */
export function createCsrfToken(): string {
  const nonce = randomBytes(18).toString('base64url');
  return `${nonce}.${sign(nonce)}`;
}

function wellFormed(token: string): boolean {
  const [nonce, sig] = String(token || '').split('.');
  if (!nonce || !sig) return false;
  const a = Buffer.from(sig);
  const b = Buffer.from(sign(nonce));
  return a.length === b.length && timingSafeEqual(a, b);
}

/** Заголовок Set-Cookie для страницы, на которой стоит защищаемая форма. */
export function csrfCookieHeader(token: string): string {
  // SameSite=Lax: cookie не уходит в межсайтовых POST вовсе, и это второй
  // рубеж поверх сравнения значений. HttpOnly нет намеренно — страница
  // читает токен только из своей же разметки, но cookie без HttpOnly
  // позволяет обновить его скриптом без перезагрузки, когда форма живёт в
  // диалоге.
  return `${CSRF_COOKIE}=${token}; Path=/; SameSite=Lax; Max-Age=7200${
    import.meta.env.PROD ? '; Secure' : ''
  }`;
}

function cookieValue(request: Request, name: string): string {
  const raw = request.headers.get('cookie') || '';
  for (const part of raw.split(';')) {
    const [k, ...v] = part.trim().split('=');
    if (k === name) return decodeURIComponent(v.join('='));
  }
  return '';
}

/** Пришёл ли запрос с нашей страницы. Пустой Origin не считается отказом. */
export function sameOrigin(request: Request): boolean {
  const origin = request.headers.get('origin');
  if (!origin) return true;
  try {
    return new URL(origin).host === new URL(request.url).host;
  } catch {
    return false;
  }
}

/**
 * Проверка токена. `token` — значение поля формы или заголовка `x-csrf-token`.
 *
 * Если секрет не настроен, проверка не проходит: молча пропускать запрос без
 * защиты хуже, чем отказать, — незаметно выключенная защита выглядит как
 * работающая.
 */
export function verifyCsrf(request: Request, token: string): boolean {
  if (!isCsrfConfigured()) return false;
  if (!sameOrigin(request)) return false;
  const fromCookie = cookieValue(request, CSRF_COOKIE);
  if (!fromCookie || !token) return false;
  if (!wellFormed(token) || !wellFormed(fromCookie)) return false;
  const a = Buffer.from(token);
  const b = Buffer.from(fromCookie);
  return a.length === b.length && timingSafeEqual(a, b);
}
