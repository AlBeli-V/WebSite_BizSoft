export const prerender = false;

import type { APIRoute } from 'astro';
import { defaultLeadOwner } from '../../config/site';
import { createLead } from '../../lib/directus';
import { sendMail, managerEmail } from '../../lib/mailer';
import { attributionFields } from '../../lib/quote-lead';
import { guardSubmission, guardResponse, countSubmission } from '../../lib/form-guard';
import { clientIp } from '../../lib/client-ip';

function isEmail(v: unknown): v is string {
  return typeof v === 'string' && /.+@.+\..+/.test(v);
}

/** Непустая строка после trim. */
function filled(v: unknown): v is string {
  return typeof v === 'string' && v.trim().length > 0;
}

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'bad json' }), { status: 400 });
  }

  // Защита публичных форм (SEC-RL-001): приманка, отсечка по времени и
  // пороги по адресу. Стоит до валидации — отклонённое обращение не должно
  // стоить нам ни запроса в базу, ни письма.
  const ip = clientIp(request);
  const verdict = await guardSubmission({ body, ip });
  if (!verdict.ok) return guardResponse(verdict);

  // Все поля формы обязательны
  if (!filled(body.name)) return new Response(JSON.stringify({ error: 'Укажите ФИО' }), { status: 422 });
  if (!filled(body.company)) return new Response(JSON.stringify({ error: 'Укажите компанию' }), { status: 422 });
  if (!isEmail(body.email)) return new Response(JSON.stringify({ error: 'Укажите корректный e-mail' }), { status: 422 });
  if (!filled(body.phone)) return new Response(JSON.stringify({ error: 'Укажите телефон' }), { status: 422 });
  if (!filled(body.message)) return new Response(JSON.stringify({ error: 'Заполните сообщение' }), { status: 422 });
  if (body.consent !== true) {
    return new Response(JSON.stringify({ error: 'Нужно согласие на обработку персональных данных' }), { status: 422 });
  }

  // Поля разобраны — это заявка, а не опечатка. Только теперь она тратит
  // порог адреса: иначе три промаха мимо формата телефона закрыли бы форму
  // человеку до конца часа.
  await countSubmission(ip);

  const payload = {
    name: String(body.name || '').slice(0, 200),
    company: String(body.company || '').slice(0, 200),
    email: String(body.email).slice(0, 200),
    phone: String(body.phone || '').slice(0, 50),
    message: String(body.message || '').slice(0, 4000),
    product_ref: String(body.product_ref || '').slice(0, 300),
    consent: true,
    // Идентификатор формы, а не канал трафика. Прежде поле называлось просто
    // `source`, и в письме менеджеру строка «Источник: pricing» читалась как
    // источник перехода. Канал теперь лежит отдельно, в last_touch_source.
    form_source: String(body.source || 'site').slice(0, 60),
    source: String(body.source || 'site').slice(0, 60),
    ...attributionFields(body),
    // Стадия воронки с первой секунды: заявка без статуса не попадает ни в один
    // фильтр воронки и теряется из виду, хотя формально сохранена.
    status: 'new',
    // Ответственный по умолчанию — распоряжение руководителя 21.08.2026.
    // Заявка без владельца ничья, и о ней забывают.
    owner: defaultLeadOwner,
  };

  try {
    await createLead(payload);
  } catch (e) {
    console.error('createLead failed', e);
    return new Response(JSON.stringify({ error: 'не удалось сохранить заявку' }), { status: 502 });
  }

  // Уведомление менеджеру на avbelyaev@biz-soft.pro (не блокируем ответ при сбое SMTP)
  sendMail({
    to: managerEmail,
    replyTo: payload.email,
    subject: `Новая заявка с сайта BIZSoft${payload.product_ref ? ': ' + payload.product_ref : ''}`,
    text: [
      `Форма: ${payload.form_source}`,
      `Канал: ${payload.last_touch_source || 'не определён'}`,
      payload.first_touch_source && payload.first_touch_source !== payload.last_touch_source
        && `Первое касание: ${payload.first_touch_source}`,
      payload.utm_campaign && `Кампания: ${payload.utm_campaign}`,
      payload.product_ref && `Товар: ${payload.product_ref}`,
      `Имя: ${payload.name || '—'}`,
      `Компания: ${payload.company || '—'}`,
      `E-mail: ${payload.email}`,
      `Телефон: ${payload.phone || '—'}`,
      `Сообщение: ${payload.message || '—'}`,
    ].filter(Boolean).join('\n'),
  }).catch((e) => console.error('lead mail failed', e));

  return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'Content-Type': 'application/json' } });
};
