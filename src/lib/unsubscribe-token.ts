/**
 * Подписанная ссылка отписки для рекламных писем.
 *
 * Требование ТЗ (п. 5) — один шаг и без входа: человек, который хочет
 * перестать получать письма, не должен ничего вспоминать и никуда
 * логиниться. Отсюда подписанный токен: адрес лежит прямо в ссылке, а
 * подпись HMAC не даёт подставить чужой.
 *
 * Почему GET только показывает страницу, а отписывает POST. Почтовые
 * сервисы и корпоративные шлюзы открывают все ссылки письма ботом-сканером
 * ещё до того, как письмо увидел человек. Если бы отписка происходила по
 * GET, половина получателей отписывалась бы «сама», без единого клика, и
 * рассылка молча вымирала бы. Поэтому GET — страница подтверждения, а
 * действие выполняет POST с той же страницы.
 *
 * Срок жизни у токена длинный (год): ссылка живёт в письме, а письмо
 * читают и через полгода. Протухший токен — не отказ: страница отписки
 * предложит ввести адрес вручную, а не скажет «ссылка недействительна».
 */
import { createHmac, timingSafeEqual } from 'node:crypto';
import { normalizeEmail } from './consent-log';

const SECRET =
  process.env.UNSUBSCRIBE_SECRET ||
  import.meta.env.UNSUBSCRIBE_SECRET ||
  '';

/** Год в секундах: письмо переживает и полгода в архиве почтового ящика. */
export const UNSUBSCRIBE_TTL_SEC = 365 * 24 * 60 * 60;

export function isUnsubscribeConfigured(): boolean {
  return SECRET.length >= 16;
}

const b64u = (buf: Buffer): string => buf.toString('base64url');

function sign(payload: string): string {
  return b64u(createHmac('sha256', SECRET).update(payload).digest());
}

/**
 * Токен для письма. Возвращает пустую строку, если секрет не настроен, —
 * письмо без ссылки отписки выпускать нельзя, и вызывающий код обязан это
 * проверить, а не подставить ссылку без подписи.
 */
export function createUnsubscribeToken(email: string, issuedAt = Date.now()): string {
  if (!isUnsubscribeConfigured()) return '';
  const payload = b64u(Buffer.from(JSON.stringify({ e: normalizeEmail(email), t: Math.floor(issuedAt / 1000) })));
  return `${payload}.${sign(payload)}`;
}

export interface UnsubscribeTokenResult {
  ok: boolean;
  email?: string;
  /** Подпись верна, но срок вышел: адрес известен, подтверждение всё равно нужно. */
  expired?: boolean;
}

export function verifyUnsubscribeToken(token: string, now = Date.now()): UnsubscribeTokenResult {
  if (!isUnsubscribeConfigured()) return { ok: false };
  const [payload, sig] = String(token || '').split('.');
  if (!payload || !sig) return { ok: false };

  const expected = sign(payload);
  // Сравнение постоянного времени: подпись подбирается побайтно, если
  // сравнивать её обычным равенством строк.
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) return { ok: false };

  let data: { e?: string; t?: number };
  try {
    data = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
  } catch {
    return { ok: false };
  }
  if (!data.e || typeof data.t !== 'number') return { ok: false };

  const age = now / 1000 - data.t;
  return { ok: true, email: data.e, expired: age > UNSUBSCRIBE_TTL_SEC };
}

/** Готовый адрес для кнопки «Отписаться» в письме. */
export function unsubscribeUrl(email: string, origin = 'https://biz-soft.pro'): string {
  const token = createUnsubscribeToken(email);
  return token ? `${origin}/unsubscribe?t=${encodeURIComponent(token)}` : `${origin}/unsubscribe`;
}
