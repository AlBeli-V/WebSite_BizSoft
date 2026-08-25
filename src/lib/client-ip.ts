/**
 * Адрес обратившегося за обратным прокси.
 *
 * Приложение слушает 127.0.0.1 и видит запрос только от nginx, поэтому
 * `remoteAddress` соединения всегда локальный и для лимитов бесполезен.
 *
 * Порядок источников важен. `X-Real-IP` nginx выставляет сам
 * (`proxy_set_header X-Real-IP $remote_addr`) и затирает любое значение,
 * пришедшее снаружи, — подделать его заголовком в запросе нельзя.
 * `X-Forwarded-For` собирается как «то, что прислал клиент» + адрес
 * соединения, поэтому доверять можно только ПОСЛЕДНЕМУ элементу списка:
 * всё, что левее, пишет сам обратившийся и может выдумать.
 */

/** Похоже ли значение на адрес, а не на мусор из заголовка. */
function looksLikeIp(v: string): boolean {
  if (!v) return false;
  // IPv4 (возможно с портом) либо IPv6 в любом сокращении.
  return /^\d{1,3}(\.\d{1,3}){3}(:\d+)?$/.test(v) || /^[0-9a-f:]+$/i.test(v);
}

/** Отбросить порт у IPv4 и скобки у IPv6 — ключ лимита должен быть стабилен. */
function normalize(v: string): string {
  const t = v.trim().replace(/^\[|\]$/g, '');
  const m = /^(\d{1,3}(?:\.\d{1,3}){3}):\d+$/.exec(t);
  return m ? m[1] : t;
}

/**
 * Адрес клиента или пустая строка, если определить не удалось.
 *
 * Пустая строка — не повод отказать: за ней стоит неверная настройка прокси,
 * а не злоупотребление. Вызывающий код в этом случае лимит не применяет.
 */
export function clientIp(request: Request): string {
  const real = normalize(request.headers.get('x-real-ip') || '');
  if (looksLikeIp(real)) return real;

  const chain = (request.headers.get('x-forwarded-for') || '').split(',');
  const last = normalize(chain[chain.length - 1] || '');
  return looksLikeIp(last) ? last : '';
}
