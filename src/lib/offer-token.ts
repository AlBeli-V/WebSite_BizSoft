/**
 * Ссылка на страницу предложения: `/offer/<токен>`.
 *
 * Токен считается от номера КП подписью на серверном секрете, а не хранится
 * в базе: схему Directus правит человек в проде, и выпуск страницы не должен
 * этого ждать. Свойства при этом те же, что у случайного токена в таблице —
 * по номеру его не подобрать, перебором соседних предложений не открыть, а
 * смена секрета отзывает разом все ссылки.
 *
 * В адресе нет ни номера сделки, ни идентификатора клиента: страница
 * показывает суммы и состав предложения, и такие данные в ссылке, которая
 * уедет в переписку и в отчёты аналитики, оставлять нельзя.
 */
import { createHmac, timingSafeEqual } from 'node:crypto';

/**
 * Секрет подписи. Отдельная переменная окружения, но при её отсутствии
 * берётся серверный токен Directus: он есть на проде всегда, наружу не
 * ходит, и без него сайт всё равно не работает. Так страница КП не окажется
 * выключенной из-за незаполненной переменной.
 */
function secret(): string {
  return process.env.OFFER_TOKEN_SECRET
    || import.meta.env.OFFER_TOKEN_SECRET
    || process.env.DIRECTUS_TOKEN
    || import.meta.env.DIRECTUS_TOKEN
    || '';
}

/** Секрет не задан — страница предложения не выпускается вовсе. */
export function offerTokensReady(): boolean {
  return secret().length >= 8;
}

/** Токен предложения: 32 символа base64url от HMAC-SHA256 номера КП. */
export function offerToken(quoteNo: string): string {
  return createHmac('sha256', secret())
    .update(`offer:${String(quoteNo).trim()}`)
    .digest('base64url')
    .slice(0, 32);
}

/** Сверка токена с номером КП — за постоянное время, без утечки по таймингу. */
export function offerTokenMatches(quoteNo: string, token: string): boolean {
  const expected = Buffer.from(offerToken(quoteNo));
  const given = Buffer.from(String(token || ''));
  if (expected.length !== given.length) return false;
  return timingSafeEqual(expected, given);
}

/** Полный адрес страницы предложения. */
export function offerUrl(siteUrl: string, quoteNo: string, utmContent?: string): string {
  const base = `${siteUrl.replace(/\/$/, '')}/offer/${offerToken(quoteNo)}`;
  if (!utmContent) return base;
  // Метки ставятся только на переходе «письмо → сайт»: внутренние переходы
  // сайта их не несут, иначе источник в GA4 и Метрике переписывался бы сам
  // на себя и первичный канал терялся.
  return `${base}?utm_source=bizsoft_email&utm_medium=email`
    + `&utm_campaign=commercial_offer&utm_content=${encodeURIComponent(utmContent)}`;
}

/**
 * Срок жизни страницы: до окончания предложения плюс запас.
 *
 * Запас нужен, потому что переговоры продолжаются и после формальной даты:
 * клиент открывает ссылку из старого письма, и упереться в «страница
 * недоступна» он должен не раньше, чем предложение действительно устарело.
 */
export const OFFER_GRACE_DAYS = 30;

export function offerExpired(issued: Date, validDays: number, now = new Date()): boolean {
  const deadline = new Date(issued.getTime());
  deadline.setDate(deadline.getDate() + validDays + OFFER_GRACE_DAYS);
  return now > deadline;
}
