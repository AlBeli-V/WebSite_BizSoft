export const prerender = false;

import type { APIRoute } from 'astro';
import { getLeads, patchLead, type Lead } from '../../../lib/directus';
import { checkAdmin, unauthorized } from '../../../lib/admin-auth';

/** Стадии воронки в порядке продвижения. Порядок важен: по нему строится отчёт. */
export const STAGES = ['new', 'in_progress', 'qualified', 'proposal', 'invoiced', 'won', 'lost'] as const;
type Stage = (typeof STAGES)[number];

const LOST_REASONS = ['price', 'timing', 'no_supply', 'competitor', 'no_contact', 'not_our_case'];

/** Поля, которые менеджер может править с телефона. Остальное — только чтение. */
const EDITABLE = ['status', 'owner', 'amount', 'lost_reason', 'next_action_at', 'note'] as const;

function summary(leads: Lead[]) {
  const byStage: Record<string, number> = {};
  for (const s of STAGES) byStage[s] = 0;
  let won = 0;
  let revenue = 0;
  for (const l of leads) {
    const s = (l.status || 'new') as Stage;
    byStage[s] = (byStage[s] || 0) + 1;
    if (s === 'won') {
      won += 1;
      revenue += Number(l.amount) || 0;
    }
  }
  const closed = byStage.won + byStage.lost;
  return {
    total: leads.length,
    by_stage: byStage,
    won,
    revenue,
    // Конверсия считается от закрытых, а не от всех: заявка в работе ещё не
    // проиграна, и включать её в знаменатель значит занижать результат.
    close_rate: closed ? Number((byStage.won / closed).toFixed(3)) : null,
    average_deal: won ? Math.round(revenue / won) : null,
  };
}

export const GET: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();
  try {
    const leads = await getLeads(500);
    return new Response(JSON.stringify({ leads, summary: summary(leads) }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (e) {
    console.error('admin leads read failed', e);
    return new Response(JSON.stringify({ error: 'не удалось получить заявки' }), { status: 502 });
  }
};

export const PATCH: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'bad json' }), { status: 400 });
  }

  const id = body.id;
  if (id === undefined || id === null || id === '') {
    return new Response(JSON.stringify({ error: 'нужен id заявки' }), { status: 422 });
  }

  const patch: Record<string, unknown> = {};
  for (const field of EDITABLE) {
    if (!(field in body)) continue;
    patch[field] = body[field] === '' ? null : body[field];
  }

  if (typeof patch.status === 'string' && !STAGES.includes(patch.status as Stage)) {
    return new Response(JSON.stringify({ error: `неизвестная стадия: ${patch.status}` }), { status: 422 });
  }
  if (typeof patch.lost_reason === 'string' && !LOST_REASONS.includes(patch.lost_reason)) {
    return new Response(JSON.stringify({ error: `неизвестная причина отказа: ${patch.lost_reason}` }), { status: 422 });
  }
  if (patch.amount !== undefined && patch.amount !== null) {
    const n = Number(patch.amount);
    if (!Number.isFinite(n) || n < 0) {
      return new Response(JSON.stringify({ error: 'сумма должна быть неотрицательным числом' }), { status: 422 });
    }
    patch.amount = n;
  }
  if (!Object.keys(patch).length) {
    return new Response(JSON.stringify({ error: 'нечего менять' }), { status: 422 });
  }

  // Даты стадий проставляются системой, а не руками: иначе воронка врёт при
  // первом же пропуске поля, а по ней считается срок сделки в отчёте.
  const now = new Date().toISOString();
  if (patch.status === 'qualified' && !body.qualified_at) patch.qualified_at = now;
  if (patch.status === 'won' || patch.status === 'lost') patch.closed_at = now;
  if (patch.status && patch.status !== 'lost') patch.lost_reason = null;

  try {
    await patchLead(id as string | number, patch);
  } catch (e) {
    console.error('admin leads patch failed', e);
    return new Response(JSON.stringify({ error: 'не удалось сохранить изменения' }), { status: 502 });
  }
  return new Response(JSON.stringify({ ok: true, patch }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
};
