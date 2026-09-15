export const prerender = false;

/**
 * Запрос действий по предложению со страницы `/offer/<токен>`.
 *
 * Клиент отмечает, что подготовить — реквизиты, счёт, договор, приглашение в
 * ЭДО, — и запрос уходит менеджеру письмом и в историю сделки. Это середина
 * воронки: до 15.09.2026 после выдачи КП сайт не мог принять от клиента
 * ничего, и следующий шаг зависел от того, вспомнит ли он про почту.
 *
 * Права доступа даёт токен страницы: он подписан серверным секретом, по
 * номеру КП не подбирается, и без него запрос не принимается. Никаких
 * идентификаторов сделки в теле запроса нет — только токен.
 */
import type { APIRoute } from 'astro';
import { createLeadEvent, getLeads } from '../../lib/directus';
import { actionLabels, knownActionIds } from '../../lib/offer-actions';
import { resolveOffer } from '../../lib/offer-lookup';
import { offerUrl } from '../../lib/offer-token';
import { managerEmail, salesFrom, sendMail } from '../../lib/mailer';
import { guardResponse, guardSubmission } from '../../lib/form-guard';
import { clientIp } from '../../lib/client-ip';
import { edo, site } from '../../config/site';

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

/** Обрезка свободного текста: в письмо и в историю сделки, а не в базу целиком. */
function clean(v: unknown, limit: number): string {
  return String(v ?? '').replace(/\s+/g, ' ').trim().slice(0, limit);
}

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'bad json' }, 400);
  }

  // Та же защита, что у публичных форм: за этой строкой отправка письма.
  const verdict = await guardSubmission({ body, ip: clientIp(request) });
  if (!verdict.ok) return guardResponse(verdict);

  const offer = await resolveOffer(String(body.token || ''));
  if (!offer) return json({ error: 'предложение не найдено' }, 404);

  const actions = knownActionIds(body.actions);
  if (actions.length === 0) return json({ error: 'не выбрано ни одного действия' }, 422);

  const labels = actionLabels(actions);
  const comment = clean(body.comment, 2000);
  const contactName = clean(body.contact_name, 200);
  const contactPhone = clean(body.contact_phone, 60);
  const contactEmail = clean(body.contact_email, 200);
  const { data } = offer;

  const lines = [
    `Заказчик: ${data.buyerCompany || '—'} (ИНН ${data.buyerInn || '—'})`,
    `КП № ${data.quoteNo} от ${data.date} на ${data.total.toLocaleString('ru-RU')} ₽, `
      + `позиций: ${data.items.length}`,
    '',
    'Просят подготовить:',
    ...labels.map((l) => `— ${l}`),
    '',
    comment ? `Комментарий: ${comment}` : '',
    '',
    'Контакты из формы:',
    `${contactName || data.contactName || '—'} · ${contactPhone || data.phone || '—'} · `
      + `${contactEmail || data.email || '—'}`,
    '',
    `Страница предложения: ${offerUrl(site.url, data.quoteNo)}`,
    // Приглашение в ЭДО отправляем мы: клиенту достаточно отметить пункт.
    actions.includes('edo_invite')
      ? `Пригласить в ЭДО: ${edo.managerSearchUrl} — искать по ИНН ${data.buyerInn || '—'}`
      : '',
  ].filter((l) => l !== '');

  // История сделки: запрос обязан остаться в карточке, даже если письмо не
  // уйдёт. Отсутствие заявки в воронке — не причина отказать клиенту.
  try {
    const leads = await getLeads(500);
    const email = String(data.email || '').trim().toLowerCase();
    const lead = leads.find((l) => String(l.email || '').trim().toLowerCase() === email);
    if (lead) {
      await createLeadEvent({
        lead: Number(lead.id),
        kind: 'email',
        subject: `Запрос по КП № ${data.quoteNo}: ${labels.join(', ')}`,
        text: lines.join('\n'),
        author: 'сайт',
      });
    }
  } catch (e) {
    console.error('offer actions: lead event failed', e);
  }

  try {
    await sendMail({
      from: salesFrom,
      to: managerEmail,
      replyTo: contactEmail || data.email || undefined,
      subject: `КП № ${data.quoteNo} — запрос действий: ${labels.length} `
        + `${labels.length === 1 ? 'пункт' : 'пунктов'}`,
      text: lines.join('\n'),
    });
  } catch (e) {
    console.error('offer actions: mail failed', e);
    return json({ error: 'запрос сохранён, но письмо менеджеру не ушло' }, 502);
  }

  return json({ ok: true, actions: actions.length });
};
