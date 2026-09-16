export const prerender = false;

/**
 * Отписка от рекламной рассылки.
 *
 * Только POST. По GET страница /unsubscribe показывает подтверждение и
 * ничего не меняет: почтовые шлюзы и антивирусы открывают все ссылки письма
 * ботом-сканером ещё до того, как письмо увидел человек, и отписка по GET
 * выкашивала бы аудиторию сама собой (ТЗ 16.09.2026, п. 5).
 *
 * Отписка не удаляет адрес: запись остаётся в реестре со статусом
 * unsubscribed, и следующая выгрузка контактов не подпишет человека заново.
 * Одновременно в журнал уходит событие marketing/withdrawn — доказательство,
 * которым закрывается претензия о рекламе без согласия.
 */
import type { APIRoute } from 'astro';
import { CONSENT_UI } from '../../config/legal';
import { logConsentEvent, normalizeEmail } from '../../lib/consent-log';
import { unsubscribe } from '../../lib/marketing-registry';
import { verifyUnsubscribeToken } from '../../lib/unsubscribe-token';
import { verifyCsrf, CSRF_FIELD } from '../../lib/csrf';
import { clientIp } from '../../lib/client-ip';
import { sharedStore } from '../../lib/shared-store';
import { randomUUID } from 'node:crypto';

/** Порог по адресу: отписка дешёвая, но перебирать её чужими адресами незачем. */
const LIMIT_PER_HOUR = 20;

async function overLimit(ip: string): Promise<boolean> {
  if (!ip) return false;
  const store = sharedStore();
  const key = `unsub:${ip}:${Math.floor(Date.now() / 3_600_000)}`;
  const n = await store.incr(key, 3600).catch(() => null);
  // Хранилище недоступно — порог не применяем: отказать человеку в отписке
  // из-за собственной базы хуже, чем пропустить лишний запрос.
  return n !== null && n > LIMIT_PER_HOUR;
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'bad json' }, 400);
  }

  if (!verifyCsrf(request, String(body[CSRF_FIELD] || request.headers.get('x-csrf-token') || ''))) {
    return json({ error: 'Проверка формы не пройдена. Откройте страницу отписки заново.' }, 403);
  }

  const ip = clientIp(request);
  if (await overLimit(ip)) {
    return json({ error: 'Слишком много запросов. Попробуйте через час или напишите на hello@biz-soft.pro.' }, 429);
  }

  // Адрес берётся из подписанного токена, а не из тела запроса: иначе
  // отписать можно было бы кого угодно, просто подставив чужую почту.
  // Ручной ввод разрешён только там, где токена нет вовсе (протухшая или
  // потерянная ссылка), и тогда подтверждением служит само владение
  // почтовым ящиком — письмо о состоявшейся отписке.
  const token = String(body.token || '');
  const verdict = verifyUnsubscribeToken(token);
  const typed = normalizeEmail(String(body.email || ''));
  const email = verdict.ok && verdict.email ? verdict.email : typed;

  if (!email || !/.+@.+\..+/.test(email)) {
    return json({ error: 'Укажите адрес, на который приходят письма.' }, 422);
  }
  // Токен есть, но подпись не сошлась — это не «истёк», это подделка.
  if (token && !verdict.ok) {
    return json({ error: 'Ссылка повреждена. Введите адрес вручную на странице отписки.' }, 422);
  }

  try {
    await logConsentEvent({
      type: 'marketing',
      action: 'withdrawn',
      sourceAction: 'unsubscribe_link',
      source: 'unsubscribe',
      formId: 'unsubscribe',
      pageUrl: '/unsubscribe',
      requestId: randomUUID(),
      subject: { email },
      textSnapshot: CONSENT_UI.marketing.text,
      scope: { withdrawn: ['email_marketing'], via: verdict.ok ? 'signed_link' : 'manual_entry' },
      ip,
      userAgent: request.headers.get('user-agent') || undefined,
    });
  } catch (e) {
    // Журнал не принял отзыв — реестр менять нельзя: получилось бы, что
    // рассылка прекращена, а доказательства отзыва нет. Для нас это отказ.
    console.error('unsubscribe consent log failed', e);
    return json({ error: 'Не удалось зафиксировать отписку. Напишите на hello@biz-soft.pro — отпишем вручную.' }, 503);
  }

  try {
    await unsubscribe({ email, reason: verdict.ok ? 'link' : 'manual_entry' });
  } catch (e) {
    console.error('unsubscribe registry failed', e);
    return json({ error: 'Отзыв зафиксирован, но реестр не обновился. Напишите на hello@biz-soft.pro.' }, 503);
  }

  return json({ ok: true, email });
};

/**
 * GET оставлен намеренно и только отвечает 405 со ссылкой на страницу.
 *
 * Без него сканер письма получал бы 404 на адрес, который мы сами и
 * выпустили, а часть фильтров считает такую ссылку признаком неисправной
 * рассылки.
 */
export const GET: APIRoute = () =>
  json({ error: 'Отписка выполняется со страницы /unsubscribe' }, 405);
