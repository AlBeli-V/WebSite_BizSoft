export const prerender = false;

import type { APIRoute } from 'astro';
import { createLead } from '../../lib/directus';
import { sendMail } from '../../lib/mailer';
import { seller } from '../../config/site';

function isEmail(v: unknown): v is string {
  return typeof v === 'string' && /.+@.+\..+/.test(v);
}

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'bad json' }), { status: 400 });
  }

  if (!isEmail(body.email)) {
    return new Response(JSON.stringify({ error: 'email обязателен' }), { status: 422 });
  }
  if (body.consent !== true) {
    return new Response(JSON.stringify({ error: 'нужно согласие на обработку ПДн' }), { status: 422 });
  }

  const payload = {
    name: String(body.name || '').slice(0, 200),
    company: String(body.company || '').slice(0, 200),
    email: String(body.email).slice(0, 200),
    phone: String(body.phone || '').slice(0, 50),
    message: String(body.message || '').slice(0, 4000),
    product_ref: String(body.product_ref || '').slice(0, 300),
    consent: true,
    source: String(body.source || 'site').slice(0, 60),
  };

  try {
    await createLead(payload);
  } catch (e) {
    console.error('createLead failed', e);
    return new Response(JSON.stringify({ error: 'не удалось сохранить заявку' }), { status: 502 });
  }

  // Уведомление менеджеру (не блокируем ответ при сбое SMTP)
  sendMail({
    to: seller.email,
    subject: `Новая заявка с сайта BizSoft${payload.product_ref ? ': ' + payload.product_ref : ''}`,
    text: [
      `Источник: ${payload.source}`,
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
