export const prerender = false;

import type { APIRoute } from 'astro';
import { getLeads } from '../../../../lib/directus';
import { checkAdmin, unauthorized } from '../../../../lib/admin-auth';
import { buildIcs } from '../../../../crm/ics';
import { specOf } from '../../../../crm/stages';

/**
 * Файл напоминания для календаря телефона.
 *
 * Токен передаётся параметром, а не заголовком: ссылку открывает системный
 * загрузчик iOS, свои заголовки к ней не приделать. Ответ отдаётся с
 * Content-Disposition, поэтому телефон сразу предлагает добавить событие.
 */
export const GET: APIRoute = async ({ request, url }) => {
  const token = url.searchParams.get('token') || '';
  const probe = new Request(request.url, { headers: { 'x-admin-token': token } });
  if (!checkAdmin(probe)) return unauthorized();

  const id = url.searchParams.get('id');
  if (!id) return new Response('нужен id заявки', { status: 422 });

  const leads = await getLeads(500);
  const lead = leads.find((l) => String(l.id) === String(id));
  if (!lead) return new Response('заявка не найдена', { status: 404 });

  const date = (lead.next_action_at || '').slice(0, 10);
  if (!date) return new Response('у заявки не задана дата следующего касания', { status: 422 });

  const who = lead.name || lead.company || `заявка №${lead.id}`;
  const spec = specOf(lead.status || 'new');
  const ics = buildIcs({
    uid: `bizsoft-lead-${lead.id}@biz-soft.pro`,
    date,
    title: `BIZSoft: ${who}`,
    description: [
      spec ? `Что сделать: ${spec.action}` : '',
      lead.company ? `Компания: ${lead.company}` : '',
      lead.phone ? `Телефон: ${lead.phone}` : '',
      lead.email ? `Почта: ${lead.email}` : '',
      lead.product_ref ? `Запрос: ${lead.product_ref}` : '',
      `Карточка: https://biz-soft.pro/admin`,
    ].filter(Boolean).join('\n'),
  });

  return new Response(ics, {
    status: 200,
    headers: {
      'Content-Type': 'text/calendar; charset=utf-8',
      'Content-Disposition': `attachment; filename="bizsoft-lead-${lead.id}.ics"`,
      'Cache-Control': 'no-store',
    },
  });
};
