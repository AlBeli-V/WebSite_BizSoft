export const prerender = false;

import type { APIRoute } from 'astro';
import { getLeads, type Lead } from '../../../../lib/directus';
import { checkAdmin, unauthorized } from '../../../../lib/admin-auth';
import { managerEmail, sendMail } from '../../../../lib/mailer';
import { verifyCompany } from '../../../../lib/inn';
import { findParty } from '../../../../lib/dadata';
import { buildManagerLeadEmail } from '../../../../lib/email/lead-manager';
import { buildLeadSourceFollowup } from '../../../../lib/email/lead-source-followup';
import { explainSource, type SourceEnrichment } from '../../../../lib/traffic-source';
import type { AttributionFields } from '../../../../lib/quote-lead';

/**
 * Разбор источника заявок письмами: утреннее уточнение и повторная отправка.
 *
 * Почему это делает сайт, а не прогон на раннере. В письме о заявке есть
 * персональные данные — имя, телефон, почта и текст обращения. По правилу
 * доступа к проду они не покидают сервер: в журнал прогона GitHub Actions им
 * попасть нельзя. Поэтому обогащение (Метрика, Директ) считает раннер, где
 * лежат токены, и присылает сюда безличный слепок по идентификатору заявки, а
 * письмо собирается и уходит здесь, теми же шаблонами, что и живое письмо.
 *
 * GET  — безличный список последних заявок для обогащения на раннере.
 * POST — собрать и отправить письма (mode=followup | resend), dry_run=true
 *        показывает, что ушло бы, ничего не отправляя.
 */

const json = (d: unknown, s = 200) =>
  new Response(JSON.stringify(d), { status: s, headers: { 'Content-Type': 'application/json' } });

/** Поля источника из записи воронки. */
function attributionOf(lead: Lead): AttributionFields {
  const s = (v: unknown): string => (typeof v === 'string' ? v : '');
  return {
    utm_source: s(lead.utm_source),
    utm_medium: s(lead.utm_medium),
    utm_campaign: s(lead.utm_campaign),
    utm_content: s(lead.utm_content),
    utm_term: s(lead.utm_term),
    yclid: s(lead.yclid),
    gclid: s(lead.gclid),
    first_touch_source: s(lead.first_touch_source),
    first_touch_ts: s(lead.first_touch_ts),
    last_touch_source: s(lead.last_touch_source),
    landing_path: s(lead.landing_path),
    ym_client_id: s(lead.ym_client_id),
    ga_client_id: s(lead.ga_client_id),
    first_touch_referrer: s(lead.first_touch_referrer),
    last_touch_referrer: s(lead.last_touch_referrer),
    visit_path: s(lead.visit_path),
  };
}

/** дд.мм.гггг по московскому времени — как в живом письме. */
function ruDate(iso: string | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('ru-RU', { timeZone: 'Europe/Moscow' });
}

/** Заявки, отобранные по запросу: последние N либо за N суток. */
function pick(leads: Lead[], opts: { limit?: number; days?: number; ids?: string[] }): Lead[] {
  if (opts.ids && opts.ids.length) {
    const want = new Set(opts.ids.map(String));
    return leads.filter((l) => want.has(String(l.id)));
  }
  if (opts.days) {
    const since = Date.now() - opts.days * 864e5;
    return leads.filter((l) => {
      const ts = Date.parse(l.created_at || '');
      return Number.isFinite(ts) && ts >= since;
    });
  }
  return leads.slice(0, opts.limit || 10);
}

export const GET: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();
  const url = new URL(request.url);
  const limit = Math.min(Number(url.searchParams.get('limit') || 10) || 10, 50);
  const days = Number(url.searchParams.get('days') || 0) || 0;

  let leads: Lead[];
  try {
    leads = await getLeads(200);
  } catch (e) {
    console.error('source-mail: чтение воронки не удалось', e);
    return json({ error: 'не удалось прочитать воронку' }, 502);
  }

  // Наружу уходит только то, что нужно для запроса в Метрику и Директ.
  // Имя, телефон, почта и текст обращения остаются на сервере.
  const rows = pick(leads, { limit, days }).map((l) => ({
    id: l.id,
    created_at: l.created_at || '',
    form_source: l.form_source || l.source || '',
    quote_no: l.quote_no || '',
    ym_client_id: l.ym_client_id || '',
    yclid: l.yclid || '',
    gclid: l.gclid || '',
    utm_source: l.utm_source || '',
    utm_medium: l.utm_medium || '',
    utm_campaign: l.utm_campaign || '',
    utm_content: l.utm_content || '',
    utm_term: l.utm_term || '',
    last_touch_source: l.last_touch_source || '',
    landing_path: l.landing_path || '',
  }));
  return json({ leads: rows });
};

export const POST: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();

  let body: Record<string, unknown> = {};
  try {
    body = await request.json();
  } catch {
    return json({ error: 'bad json' }, 400);
  }

  const mode = body.mode === 'resend' ? 'resend' : 'followup';
  const dryRun = body.dry_run === true;
  const to = typeof body.to === 'string' && body.to ? body.to : managerEmail;
  const prefix = typeof body.subject_prefix === 'string' ? body.subject_prefix : '';
  const enrichment = (body.enrichment || {}) as Record<string, SourceEnrichment>;
  const ids = Array.isArray(body.ids) ? body.ids.map(String) : undefined;
  const limit = Math.min(Number(body.limit || 10) || 10, 50);
  const days = Number(body.days || 0) || 0;

  let leads: Lead[];
  try {
    leads = await getLeads(200);
  } catch (e) {
    console.error('source-mail: чтение воронки не удалось', e);
    return json({ error: 'не удалось прочитать воронку' }, 502);
  }

  const chosen = pick(leads, { limit, days, ids });
  const report: { id: string | number; kind: string; system: string; sent: boolean; error?: string }[] = [];

  // Письма уходят последовательно: десяток служебных писем подряд по одному
  // SMTP-соединению надёжнее, чем параллельная пачка, которую почтовый узел
  // может придержать как всплеск.
  for (const lead of chosen) {
    const attribution = attributionOf(lead);
    const facts = enrichment[String(lead.id)] || null;
    const verdict = explainSource(attribution, facts);
    const date = ruDate(lead.created_at);
    let sent = false;
    let error: string | undefined;

    try {
      let mail;
      if (mode === 'resend') {
        // Повтор письма о заявке: собирается тем же шаблоном, что и живое, —
        // руководитель сравнивает его с исходным письмом строка в строку.
        const innCheck = await verifyCompany(String(lead.inn || ''), String(lead.company || ''))
          .catch(() => null);
        const party = innCheck?.valid
          ? await findParty(String(lead.inn || '')).catch(() => null)
          : null;
        const isQuote = Boolean(lead.quote_no);
        mail = buildManagerLeadEmail({
          lead: {
            name: String(lead.name || ''),
            company: String(lead.company || ''),
            inn: String(lead.inn || ''),
            email: String(lead.email || ''),
            phone: String(lead.phone || ''),
            message: String(lead.message || ''),
            product_ref: String(lead.product_ref || ''),
            form_source: String(lead.form_source || lead.source || ''),
            date,
          },
          attribution,
          innCheck,
          party,
          enrichment: facts,
          subjectPrefix: prefix,
          subjectOverride: isQuote
            ? `Отправлено КП № ${lead.quote_no} — ${lead.company || ''}`
            : undefined,
          notice: `Повтор письма от ${date} с разбором источника обращения. `
            + 'Вложения исходного письма не дублируются, отвечать на него не нужно.',
        });
      } else {
        mail = buildLeadSourceFollowup({
          lead: {
            id: lead.id,
            company: String(lead.company || ''),
            product_ref: String(lead.product_ref || ''),
            form_source: String(lead.form_source || lead.source || ''),
            quote_no: String(lead.quote_no || ''),
            amount: Number(lead.amount || 0),
            date,
          },
          attribution,
          enrichment: facts,
          subjectPrefix: prefix,
        });
      }

      if (!dryRun) {
        // Reply-To не ставится намеренно: письмо служебное, и «Ответить»
        // не должно уводить переписку клиенту.
        sent = await sendMail({ to, subject: mail.subject, text: mail.text, html: mail.html });
        if (!sent) error = 'SMTP не настроен — письмо не отправлено';
      }
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
      console.error('source-mail: письмо не собрано', lead.id, e);
    }

    report.push({
      id: lead.id,
      kind: verdict.kindLabel,
      system: verdict.system,
      sent,
      ...(error ? { error } : {}),
    });
  }

  return json({
    mode,
    dry_run: dryRun,
    to,
    picked: chosen.length,
    sent: report.filter((r) => r.sent).length,
    leads: report,
  });
};
