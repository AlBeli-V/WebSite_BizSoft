export const prerender = false;

import type { APIRoute } from 'astro';
import { getQuotes, getLeads, createLead, createLeadEvent } from '../../../../lib/directus';
import { checkAdmin, unauthorized } from '../../../../lib/admin-auth';
import { leadFromQuote, describeQuote } from '../../../../lib/quote-lead';

const json = (d: unknown, s = 200) =>
  new Response(JSON.stringify(d), { status: s, headers: { 'Content-Type': 'application/json' } });

/**
 * Перенос ранее скачанных КП в воронку.
 *
 * До сегодняшнего дня скачивания оседали в коллекции quotes и в почте, а в
 * заявках их не было. Метрика заднего числа этот разрыв не закроет — а здесь
 * есть и дата, и состав корзины, и контакты, поэтому история восстанавливается
 * целиком.
 *
 * Идемпотентно: КП, уже отражённое заявкой или событием, второй раз не заводится.
 * Без dry-run такой перенос запускать нельзя — сначала показываем, что будет.
 */
export const POST: APIRoute = async ({ request }) => {
  if (!checkAdmin(request)) return unauthorized();

  let body: Record<string, unknown> = {};
  try {
    body = await request.json();
  } catch { /* тело необязательно: по умолчанию сухой прогон */ }
  const apply = body.apply === true;

  let quotes; let leads;
  try {
    [quotes, leads] = await Promise.all([getQuotes(500), getLeads(500)]);
  } catch (e) {
    console.error('import-quotes read failed', e);
    return json({ error: 'не удалось прочитать данные' }, 502);
  }

  const knownQuoteNo = new Set(
    leads.map((l) => String(l.quote_no || '').trim()).filter(Boolean));
  const openByEmail = new Map<string, string | number>();
  for (const l of leads) {
    const mail = String(l.email || '').trim().toLowerCase();
    if (!mail) continue;
    if (['won', 'lost', 'spam'].includes(String(l.status || 'new'))) continue;
    if (!openByEmail.has(mail)) openByEmail.set(mail, l.id);
  }

  const planned: { quote_no: string; company: string; total: number; action: string }[] = [];
  let created = 0; let attached = 0; let skipped = 0; let noNumber = 0;

  for (const q of quotes) {
    const quoteNo = String(q.quote_no || '').trim();
    // «Уже в воронке» и «без номера» — разные причины пропуска. Слитый счётчик
    // читается как «всё на месте» и в случае, когда КП просто нечем сопоставить.
    if (!quoteNo) { noNumber += 1; continue; }
    if (knownQuoteNo.has(quoteNo)) { skipped += 1; continue; }

    const payload = {
      quoteNo,
      buyerCompany: String(q.buyer_company || ''),
      buyerInn: String(q.buyer_inn || ''),
      contactName: String(q.contact_name || ''),
      email: String(q.email || ''),
      phone: String(q.phone || ''),
      items: (q.items || []).map((i) => ({ sku: i.sku, name: i.name, qty: i.qty, sum: i.sum })),
      total: Number(q.total) || 0,
    };
    const mail = payload.email.trim().toLowerCase();
    const openId = mail ? openByEmail.get(mail) : undefined;

    if (openId) {
      planned.push({ quote_no: quoteNo, company: payload.buyerCompany, total: payload.total, action: 'событие к открытой заявке' });
      if (apply) {
        await createLeadEvent({
          lead: Number(openId), kind: 'email',
          subject: `Скачано КП № ${quoteNo} на ${payload.total.toLocaleString('ru-RU')} ₽`,
          text: describeQuote(payload), author: 'перенос истории',
        });
        attached += 1;
      }
      continue;
    }

    planned.push({ quote_no: quoteNo, company: payload.buyerCompany, total: payload.total, action: 'новая заявка' });
    if (apply) {
      // Дата исходного скачивания уходит в текст заявки: created_at проставляет
      // база, и подменить его нельзя — а знать, когда клиент приходил, важно.
      const row = leadFromQuote(payload);
      const when = String(q.created_at || '').slice(0, 10);
      if (when) row.message = `Скачано ${when.split('-').reverse().join('.')}.\n\n${row.message}`;
      await createLead(row);
      knownQuoteNo.add(quoteNo);
      if (mail) openByEmail.set(mail, 'new');
      created += 1;
    }
  }

  return json({
    dry_run: !apply,
    quotes_total: quotes.length,
    planned: planned.slice(0, 100),
    summary: { planned: planned.length, skipped, skipped_no_number: noNumber,
               created, attached },
  });
};
