export const prerender = false;

/**
 * Служебный API раздела «Комплаенс → Согласия и рассылки».
 *
 * Одна точка входа с полем `op` вместо десятка маршрутов: у всех операций
 * общая проверка доступа, общая запись в журнал действий и общий формат
 * ответа, и разносить их по файлам значило бы размножить эти три вещи.
 *
 * Правила, которые здесь закреплены кодом:
 *  • исходное событие журнала не правится и не удаляется — операции такой
 *    нет вовсе. Исправление оформляется новым событием (`correct`);
 *  • IP и user-agent видит только владелец (`redactForRole`);
 *  • выгрузка и смена маркетингового статуса — только владелец;
 *  • любое обращение к данным пишется в admin_audit_log.
 */
import type { APIRoute } from 'astro';
import { randomUUID } from 'node:crypto';
import {
  queryConsentEvents,
  queryMarketingRegistry,
  queryAdminAudit,
  findMarketingEntry,
  type ConsentEventRow,
} from '../../../lib/directus';
import {
  authorizeCompliance,
  auditAdmin,
  canExport,
  redactForRole,
  type ComplianceSession,
} from '../../../lib/compliance-auth';
import { logConsentEvent, normalizeEmail, subjectIdFor } from '../../../lib/consent-log';
import { allowedAudience, unsubscribe, subscribe } from '../../../lib/marketing-registry';
import { CONSENT_UI, MARKETING_STATUSES, type MarketingStatus } from '../../../config/legal';
import { legalByHash, LEGAL_MANIFEST } from '../../../lib/legal';

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

/** Фильтры вкладки «Аудиторский журнал» → параметры запроса Directus. */
function journalFilter(f: Record<string, unknown>): Record<string, string | number> {
  const out: Record<string, string | number> = {};
  const str = (v: unknown) => String(v || '').trim();
  if (str(f.email)) out['filter[email][_contains]'] = normalizeEmail(str(f.email));
  if (str(f.phone)) out['filter[phone][_contains]'] = str(f.phone);
  if (str(f.company)) out['filter[company][_icontains]'] = str(f.company);
  if (str(f.source)) out['filter[source][_contains]'] = str(f.source);
  if (str(f.consent_type)) out['filter[consent_type][_eq]'] = str(f.consent_type);
  if (str(f.consent_action)) out['filter[consent_action][_eq]'] = str(f.consent_action);
  if (str(f.bitrix_lead_id)) out['filter[bitrix_lead_id][_eq]'] = str(f.bitrix_lead_id);
  if (str(f.event_id)) out['filter[event_id][_eq]'] = str(f.event_id);
  if (str(f.date_from)) out['filter[submitted_at][_gte]'] = str(f.date_from);
  // Верхняя граница включительно: человек, указавший «по 16.09», имеет в виду
  // весь этот день, а не полночь его начала.
  if (str(f.date_to)) out['filter[submitted_at][_lte]'] = `${str(f.date_to)}T23:59:59`;
  return out;
}

/** Одна строка CSV: экранирование по RFC 4180, разделитель — точка с запятой. */
function csvLine(cells: (string | number | null | undefined)[]): string {
  return cells
    .map((c) => {
      const v = c === null || c === undefined ? '' : String(c);
      return /[";\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
    })
    .join(';');
}

const JOURNAL_COLUMNS: (keyof ConsentEventRow)[] = [
  'event_id', 'submitted_at', 'consent_type', 'consent_action', 'source', 'source_action',
  'email', 'phone', 'company', 'last_name', 'first_name',
  'document_version', 'document_sha256', 'consent_text_snapshot',
  'page_url', 'form_id', 'request_id', 'lead_id', 'bitrix_lead_id',
  'ip_address', 'user_agent', 'corrects_event',
];

function journalCsv(rows: ConsentEventRow[]): string {
  // BOM — чтобы Excel открыл кириллицу без «Мастера импорта».
  const head = csvLine(JOURNAL_COLUMNS as string[]);
  const body = rows.map((r) => csvLine(JOURNAL_COLUMNS.map((c) => r[c] as string | number | null)));
  return '﻿' + [head, ...body].join('\r\n') + '\r\n';
}

/** Карточка доказательства по субъекту: всё, чем подтверждается согласие. */
async function evidence(email: string, session: ComplianceSession) {
  const normalized = normalizeEmail(email);
  const events = await queryConsentEvents({ 'filter[email][_eq]': normalized }, 500);
  const registry = await findMarketingEntry(normalized);
  // К каждой записи прикладывается адрес архивной редакции: по SHA-256
  // администратор поднимает ровно тот текст, который человек видел.
  const withDocs = events.map((e) => {
    const found = e.document_sha256 ? legalByHash(e.document_sha256) : null;
    return {
      ...redactForRole(e, session.role),
      document_url: found
        ? found.revision.version === LEGAL_MANIFEST[found.id].version
          ? LEGAL_MANIFEST[found.id].url
          : `${LEGAL_MANIFEST[found.id].url}/${found.revision.version}`
        : null,
      document_title: found ? LEGAL_MANIFEST[found.id].title : null,
    };
  });
  return {
    subject_id: subjectIdFor(normalized),
    email: normalized,
    events: withDocs,
    registry,
  };
}

export const POST: APIRoute = async ({ request }) => {
  const auth = authorizeCompliance(request);
  if (!auth.ok) return json({ error: auth.error }, auth.status);
  const { session } = auth;

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'bad json' }, 400);
  }

  const op = String(body.op || '');
  const filters = (body.filters as Record<string, unknown>) || {};

  try {
    switch (op) {
      // ── Вкладка 1: аудиторский журнал ──────────────────────────────────
      case 'journal': {
        const rows = await queryConsentEvents(journalFilter(filters), 500);
        await auditAdmin(session, 'view_log', undefined, { filters, found: rows.length });
        return json({ rows: rows.map((r) => redactForRole(r, session.role)), role: session.role });
      }

      case 'evidence': {
        const email = String(body.email || '');
        if (!email) return json({ error: 'Укажите адрес субъекта.' }, 422);
        const card = await evidence(email, session);
        await auditAdmin(session, 'view_evidence', email, { events: card.events.length });
        return json(card);
      }

      /**
       * Корректирующее событие. Единственный способ исправить ошибку в
       * журнале: исходная запись остаётся на месте, новая на неё ссылается.
       */
      case 'correct': {
        if (!canExport(session.role)) return json({ error: 'Корректировку оформляет владелец.' }, 403);
        const correctsEvent = String(body.corrects_event || '');
        const email = normalizeEmail(String(body.email || ''));
        const reason = String(body.reason || '').slice(0, 1000);
        if (!correctsEvent || !email || !reason) {
          return json({ error: 'Нужны исходное событие, адрес и причина корректировки.' }, 422);
        }
        const eventId = await logConsentEvent({
          type: (String(body.consent_type || 'personal_data') as 'personal_data'),
          action: 'renewed',
          sourceAction: 'admin_manual',
          source: 'admin-compliance',
          formId: 'admin-correction',
          requestId: randomUUID(),
          subject: { email },
          textSnapshot: `Корректировка события ${correctsEvent}. Основание: ${reason}`,
          scope: { correction: true, reason },
          correctsEvent,
        });
        await auditAdmin(session, 'correct_event', correctsEvent, { email, reason, new_event: eventId });
        return json({ ok: true, event_id: eventId });
      }

      // ── Вкладка 2: рассылочный реестр ──────────────────────────────────
      case 'registry': {
        const status = String(filters.status || '');
        const f: Record<string, string> = {};
        if (status && (MARKETING_STATUSES as readonly string[]).includes(status)) {
          f['filter[status][_eq]'] = status;
        }
        if (String(filters.email || '')) f['filter[email_normalized][_contains]'] = normalizeEmail(String(filters.email));
        const rows = await queryMarketingRegistry(f, 2000);
        await auditAdmin(session, 'view_registry', undefined, { filters, found: rows.length });
        return json({ rows });
      }

      /**
       * Отзыв, пришедший письмом (HELP, п. 5). Ручного удаления записи нет и
       * не будет: отписка — это новое событие, а не стирание старого.
       */
      case 'record_withdrawal': {
        if (!canExport(session.role)) return json({ error: 'Фиксацию отзыва оформляет владелец.' }, 403);
        const email = normalizeEmail(String(body.email || ''));
        const reference = String(body.reference || '').slice(0, 200);
        if (!email) return json({ error: 'Укажите адрес.' }, 422);
        const eventId = await logConsentEvent({
          type: 'marketing',
          action: 'withdrawn',
          sourceAction: 'email_request',
          source: 'admin-compliance',
          formId: 'admin-withdrawal',
          requestId: randomUUID(),
          subject: { email },
          textSnapshot: CONSENT_UI.marketing.text,
          scope: { withdrawn: ['email_marketing'], via: 'email_request', reference },
        });
        await unsubscribe({ email, reason: 'email_request' });
        await auditAdmin(session, 'record_withdrawal', email, { reference, event: eventId });
        return json({ ok: true, event_id: eventId });
      }

      /**
       * Ручная смена статуса: жалоба, недоставляемый адрес, снятие блокировки.
       * Подписать вручную нельзя — для этого нужно событие granted, которое
       * даёт сам человек, а не администратор.
       */
      case 'set_marketing_status': {
        if (!canExport(session.role)) return json({ error: 'Смену статуса оформляет владелец.' }, 403);
        const email = normalizeEmail(String(body.email || ''));
        const status = String(body.status || '') as MarketingStatus;
        if (!email || !(MARKETING_STATUSES as readonly string[]).includes(status)) {
          return json({ error: 'Укажите адрес и корректный статус.' }, 422);
        }
        if (status === 'subscribed') {
          return json({
            error: 'Подписать вручную нельзя: подписка возможна только новым согласием самого человека.',
          }, 422);
        }
        const eventId = await logConsentEvent({
          type: 'marketing',
          action: 'withdrawn',
          sourceAction: 'admin_manual',
          source: 'admin-compliance',
          formId: 'admin-status',
          requestId: randomUUID(),
          subject: { email },
          textSnapshot: CONSENT_UI.marketing.text,
          scope: { status, reason: String(body.reason || '').slice(0, 500) },
        });
        await unsubscribe({ email, reason: String(body.reason || 'admin').slice(0, 120), status });
        await auditAdmin(session, 'set_marketing_status', email, { status, event: eventId });
        return json({ ok: true, event_id: eventId });
      }

      // ── Вкладка 3: экспорты и запросы ──────────────────────────────────
      /**
       * Разрешённая аудитория рассылки. Только status=subscribed с
       * действующим consent_event_id: контакты Bitrix24 сюда не попадают
       * никогда — в портале доказательства согласия нет.
       */
      case 'audience': {
        if (!canExport(session.role)) return json({ error: 'Выгрузку формирует владелец.' }, 403);
        const rows = await allowedAudience(20000);
        await auditAdmin(session, 'build_audience', 'marketing_registry', { count: rows.length });
        const csv = '﻿' + [
          csvLine(['email', 'subject_id', 'consent_event_id', 'subscribed_at', 'source']),
          ...rows.map((r) => csvLine([r.email_normalized, r.subject_id, r.consent_event_id, r.subscribed_at, r.source])),
        ].join('\r\n') + '\r\n';
        return new Response(csv, {
          headers: {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': `attachment; filename="audience-${new Date().toISOString().slice(0, 10)}.csv"`,
          },
        });
      }

      case 'export_journal': {
        if (!canExport(session.role)) return json({ error: 'Выгрузку формирует владелец.' }, 403);
        const rows = await queryConsentEvents(journalFilter(filters), 20000);
        await auditAdmin(session, 'export', 'consent_audit_log', { filters, count: rows.length });
        return new Response(journalCsv(rows), {
          headers: {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': `attachment; filename="consent-log-${new Date().toISOString().slice(0, 10)}.csv"`,
          },
        });
      }

      case 'admin_log': {
        if (!canExport(session.role)) return json({ error: 'Журнал действий открывает владелец.' }, 403);
        const rows = await queryAdminAudit(500);
        return json({ rows });
      }

      /** Ручная подписка допустима ровно в одном случае — снятие блокировки. */
      case 'resubscribe_after_block': {
        if (!canExport(session.role)) return json({ error: 'Операцию выполняет владелец.' }, 403);
        const email = normalizeEmail(String(body.email || ''));
        const consentEventId = String(body.consent_event_id || '');
        if (!email || !consentEventId) {
          return json({ error: 'Нужны адрес и событие MARKETING granted, на котором держится подписка.' }, 422);
        }
        // Проверяем, что событие действительно существует и относится к
        // этому адресу: подписка по выдуманному идентификатору — это ровно
        // та рассылка без согласия, от которой защищает реестр.
        const [event] = await queryConsentEvents(
          { 'filter[event_id][_eq]': consentEventId, 'filter[email][_eq]': email }, 1,
        );
        if (!event || event.consent_type !== 'marketing' || event.consent_action !== 'granted') {
          return json({ error: 'Событие не найдено или не является согласием на рассылку этого адреса.' }, 422);
        }
        await subscribe({ email, consentEventId, source: 'admin-unblock', allowBlocked: true });
        await auditAdmin(session, 'resubscribe_after_block', email, { consent_event_id: consentEventId });
        return json({ ok: true });
      }

      default:
        return json({ error: 'Неизвестная операция.' }, 400);
    }
  } catch (e) {
    console.error('compliance api failed', op, e);
    return json({ error: 'Источник данных недоступен. Повторите позже.' }, 502);
  }
};
