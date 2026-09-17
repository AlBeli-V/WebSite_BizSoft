export const prerender = false;

/**
 * Фиксация выбора пользователя в cookie-механизме.
 *
 * Согласие на аналитику — такое же согласие, как остальные, и подтверждать
 * его приходится тем же журналом: «почему на сайте грузился Google
 * Analytics» — вопрос с тем же ответом, что и «почему вы писали человеку
 * рекламу» (документ 05, п. 6).
 *
 * Персональных данных здесь нет и быть не должно: субъект технический,
 * выведенный из случайного идентификатора, который браузер хранит у себя.
 * Ни адреса, ни имени страница cookie-выбора не знает.
 *
 * Сбой записи не должен ломать выбор человека: тег включается или не
 * включается по локальному состоянию в браузере, а эта запись — про
 * доказуемость. Поэтому ошибки сюда возвращаются, но интерфейс на них не
 * останавливается.
 */
import type { APIRoute } from 'astro';
import { randomUUID } from 'node:crypto';
import { CONSENT_UI, COOKIE_UI, type ConsentType } from '../../../config/legal';
import { anonymousSubjectId, logConsentEvent } from '../../../lib/consent-log';
import { clientIp } from '../../../lib/client-ip';
import { sharedStore } from '../../../lib/shared-store';

const CATEGORY_TYPE: Record<string, ConsentType> = {
  yandex_analytics: 'yandex_analytics',
  google_analytics: 'google_analytics',
};

/** Пояснение категории из конфигурации — оно же снимок текста в журнале. */
function snapshotFor(type: ConsentType): string {
  const cat = COOKIE_UI.categories.find((c) => c.id === (type as string));
  return cat ? `${cat.title}. ${cat.purpose}` : CONSENT_UI.legend;
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

/** Порог по адресу: интерфейс шлёт одно событие на решение, не больше. */
async function overLimit(ip: string): Promise<boolean> {
  if (!ip) return false;
  const key = `consent-analytics:${ip}:${Math.floor(Date.now() / 3_600_000)}`;
  const n = await sharedStore().incr(key, 3600).catch(() => null);
  return n !== null && n > 60;
}

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'bad json' }, 400);
  }

  const sessionId = String(body.session_id || '').slice(0, 64);
  if (!/^[A-Za-z0-9_-]{8,64}$/.test(sessionId)) return json({ error: 'bad session' }, 422);

  const ip = clientIp(request);
  if (await overLimit(ip)) return json({ error: 'too many' }, 429);

  const choices = body.choices as Record<string, unknown> | undefined;
  if (!choices || typeof choices !== 'object') return json({ error: 'bad choices' }, 422);

  // Как человек выбирал: сразу в баннере или в разделе «Настроить».
  const sourceAction = body.source_action === 'cookie_settings' ? 'cookie_settings' : 'cookie_banner';
  const requestId = randomUUID();
  const subjectId = anonymousSubjectId(sessionId);
  const pageUrl = String(body.page_url || '').slice(0, 2000);

  // Каждая категория — своё событие. Одна запись «принял cookie» не
  // отвечает на вопрос, разрешал ли человек именно иностранный сервис.
  const written: string[] = [];
  for (const [category, value] of Object.entries(choices)) {
    const type = CATEGORY_TYPE[category];
    if (!type) continue;
    try {
      const eventId = await logConsentEvent({
        type,
        // Отказ здесь пишется явным событием `denied`, в отличие от форм:
        // человек нажал «Только необходимые» — это действие, а не
        // отсутствие действия.
        action: value === true ? 'granted' : 'denied',
        sourceAction,
        source: 'cookie-banner',
        formId: 'cookie-consent',
        pageUrl,
        requestId,
        subjectId,
        textSnapshot: snapshotFor(type),
        scope: { category, enabled: value === true },
        ip,
        userAgent: request.headers.get('user-agent') || undefined,
      });
      written.push(eventId);
    } catch (e) {
      console.error('analytics consent log failed', category, e);
    }
  }

  return json({ ok: written.length > 0, events: written.length, request_id: requestId });
};
