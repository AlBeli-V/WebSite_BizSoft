export const prerender = false;

import type { APIRoute } from 'astro';
import { getLeads } from '../../../../lib/directus';
import { checkAdmin, unauthorized } from '../../../../lib/admin-auth';
import { TEMPLATES, buildLetter } from '../../../../crm/templates';

/** Готовый текст письма по шаблону: подстановка идёт на сервере, из живой заявки. */
export const POST: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'bad json' }), { status: 400 });
  }

  const id = body.id;
  const template = String(body.template || '');
  if (!id) return new Response(JSON.stringify({ error: 'нужен id заявки' }), { status: 422 });

  const leads = await getLeads(500);
  const lead = leads.find((l) => String(l.id) === String(id));
  if (!lead) return new Response(JSON.stringify({ error: 'заявка не найдена' }), { status: 404 });

  const letter = buildLetter(template, {
    lead,
    manager: String(body.manager || '') || undefined,
    managerPhone: String(body.managerPhone || '') || undefined,
  });
  if (!letter) return new Response(JSON.stringify({ error: `неизвестный шаблон: ${template}` }), { status: 422 });

  return new Response(JSON.stringify({
    ...letter,
    templates: TEMPLATES.map((t) => ({ id: t.id, label: t.label, hint: t.hint })),
  }), { status: 200, headers: { 'Content-Type': 'application/json' } });
};
