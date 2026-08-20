export const prerender = false;

import type { APIRoute } from 'astro';
import {
  getLeads, patchLead, deleteLead, getLeadEvents, createLeadEvent,
  type Lead, type LeadEvent,
} from '../../../lib/directus';
import { checkAdmin, unauthorized } from '../../../lib/admin-auth';
import { sendMail, salesFrom, managerEmail } from '../../../lib/mailer';

/** Стадии воронки в порядке продвижения. spam — корзина, в воронке не участвует. */
export const STAGES = ['new', 'in_progress', 'qualified', 'proposal', 'invoiced', 'won', 'lost'] as const;
export const ALL_STATUSES = [...STAGES, 'spam'] as const;
type Status = (typeof ALL_STATUSES)[number];

const LOST_REASONS = ['price', 'timing', 'no_supply', 'competitor', 'no_contact', 'not_our_case'];
const EDITABLE = ['status', 'owner', 'amount', 'lost_reason', 'next_action_at', 'note'] as const;

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });

/** Сводка воронки. Мусор исключён отовсюду: он не заявка, а шум. */
export function summarize(leads: Lead[]) {
  const real = leads.filter((l) => (l.status || 'new') !== 'spam');
  const byStage: Record<string, number> = {};
  for (const s of STAGES) byStage[s] = 0;
  let revenue = 0;
  for (const l of real) {
    const s = (l.status || 'new') as string;
    byStage[s] = (byStage[s] || 0) + 1;
    if (s === 'won') revenue += Number(l.amount) || 0;
  }
  const won = byStage.won;
  const closed = won + byStage.lost;
  return {
    total: real.length,
    spam: leads.length - real.length,
    in_work: real.length - closed,
    by_stage: byStage,
    won,
    revenue,
    // Знаменатель — закрытые сделки, а не все заявки: та, что в работе, ещё не
    // проиграна, и включать её значит занижать результат.
    close_rate: closed ? Number((won / closed).toFixed(3)) : null,
    average_deal: won ? Math.round(revenue / won) : null,
  };
}

async function logEvent(lead: string | number, kind: string, text: string, subject?: string, author?: string) {
  try {
    await createLeadEvent({ lead: Number(lead), kind, text, subject: subject || null, author: author || null });
  } catch (e) {
    // История — вспомогательная вещь: её сбой не должен ронять основную операцию.
    console.error('lead event log failed', e);
  }
}

export const GET: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();
  try {
    const [leads, events] = await Promise.all([
      getLeads(500),
      getLeadEvents(1000).catch(() => [] as LeadEvent[]),
    ]);
    const byLead: Record<string, LeadEvent[]> = {};
    for (const e of events) {
      const k = String(e.lead ?? '');
      if (!k) continue;
      (byLead[k] ||= []).push(e);
    }
    return json({ leads, events: byLead, summary: summarize(leads) });
  } catch (e) {
    console.error('admin leads read failed', e);
    return json({ error: 'не удалось получить заявки' }, 502);
  }
};

export const PATCH: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'bad json' }, 400);
  }

  const id = body.id;
  if (id === undefined || id === null || id === '') return json({ error: 'нужен id заявки' }, 422);

  const patch: Record<string, unknown> = {};
  for (const field of EDITABLE) {
    if (!(field in body)) continue;
    patch[field] = body[field] === '' ? null : body[field];
  }

  if (typeof patch.status === 'string' && !ALL_STATUSES.includes(patch.status as Status)) {
    return json({ error: `неизвестная стадия: ${patch.status}` }, 422);
  }
  if (typeof patch.lost_reason === 'string' && !LOST_REASONS.includes(patch.lost_reason)) {
    return json({ error: `неизвестная причина отказа: ${patch.lost_reason}` }, 422);
  }
  if (patch.amount !== undefined && patch.amount !== null) {
    const n = Number(patch.amount);
    if (!Number.isFinite(n) || n < 0) return json({ error: 'сумма должна быть неотрицательным числом' }, 422);
    patch.amount = n;
  }
  if (!Object.keys(patch).length) return json({ error: 'нечего менять' }, 422);

  // Даты стадий проставляет система: если бы их вводили руками, воронка врала бы
  // при первом пропуске, а по ней считается срок сделки.
  const now = new Date().toISOString();
  if (patch.status === 'qualified' && !body.qualified_at) patch.qualified_at = now;
  if (patch.status === 'won' || patch.status === 'lost') patch.closed_at = now;
  if (patch.status && patch.status !== 'lost') patch.lost_reason = null;

  try {
    await patchLead(id as string | number, patch);
  } catch (e) {
    console.error('admin leads patch failed', e);
    return json({ error: 'не удалось сохранить изменения' }, 502);
  }

  if (typeof patch.status === 'string' && body.prev_status && body.prev_status !== patch.status) {
    await logEvent(id as string | number, 'stage',
      `Стадия: ${body.prev_status} → ${patch.status}`, undefined, String(patch.owner || body.owner || ''));
  }
  return json({ ok: true, patch });
};

export const DELETE: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'bad json' }, 400);
  }
  const id = body.id;
  if (id === undefined || id === null || id === '') return json({ error: 'нужен id заявки' }, 422);
  try {
    await deleteLead(id as string | number);
  } catch (e) {
    console.error('admin leads delete failed', e);
    return json({ error: 'не удалось удалить заявку' }, 502);
  }
  return json({ ok: true, deleted: id });
};

/** Событие истории: заметка, звонок или письмо клиенту. */
export const POST: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'bad json' }, 400);
  }

  const id = body.id;
  const kind = String(body.kind || 'note');
  if (id === undefined || id === null || id === '') return json({ error: 'нужен id заявки' }, 422);
  if (!['note', 'call', 'email'].includes(kind)) return json({ error: `неизвестный тип: ${kind}` }, 422);

  const text = String(body.text || '').trim();
  if (!text) return json({ error: 'пустое сообщение' }, 422);
  const author = String(body.author || '').slice(0, 120);

  if (kind === 'email') {
    const to = String(body.to || '').trim();
    const subject = String(body.subject || '').trim() || 'BIZSoft — по вашей заявке';
    if (!/.+@.+\..+/.test(to)) return json({ error: 'некорректный адрес получателя' }, 422);
    let sent = false;
    try {
      sent = await sendMail({ to, from: salesFrom, replyTo: managerEmail, subject, text });
    } catch (e) {
      console.error('lead email failed', e);
      return json({ error: 'письмо не отправлено: сбой SMTP' }, 502);
    }
    if (!sent) return json({ error: 'письмо не отправлено: SMTP не настроен' }, 502);
    await logEvent(id as string | number, 'email', text, `${subject} → ${to}`, author);
    return json({ ok: true, sent: true });
  }

  await logEvent(id as string | number, kind, text, undefined, author);
  return json({ ok: true });
};
