/**
 * Утреннее уточнение источника заявки (решение руководителя 10.09.2026).
 *
 * Зачем отдельное письмо. Часть ответа на вопрос «откуда пришла заявка» в
 * секунду заявки не существует: поисковую фразу и путь визитов Метрика
 * отдаёт с задержкой, а расход и цену клика Директ закрывает только за
 * прошедшие сутки. Задерживать письмо о самой заявке ради этих строк нельзя
 * — срок реакции на новую заявку два часа. Поэтому живое письмо уходит
 * сразу с тем, что знает браузер, а утром по той же заявке приходит короткое
 * второе письмо с разбором по Метрике и Директу.
 *
 * Письмо намеренно короткое: реквизиты, сообщение клиента и экономику
 * руководитель уже видел в первом письме, здесь — только источник.
 */
import type { AttributionFields } from '../quote-lead';
import { explainSource, type SourceEnrichment } from '../traffic-source';
import {
  attributionLines, attributionRows, card, EMAIL_COLOR, emailShell, escapeHtml,
  heading, kvRow, paragraph,
} from './layout';
import type { RenderedEmail } from './quote-customer';

export interface LeadSourceFollowupInput {
  lead: {
    id: string | number;
    company: string;
    product_ref: string;
    form_source: string;
    quote_no: string;
    /** Сумма заявки, ₽; 0 — суммы нет. */
    amount: number;
    /** Дата получения заявки, дд.мм.гггг. */
    date: string;
  };
  attribution: AttributionFields;
  enrichment: SourceEnrichment | null;
  /** Приписка к теме — «(ТЕСТ ПОВТОР)» у разового прогона. */
  subjectPrefix?: string;
  /** Плашка в начале письма, если оно пришло не по расписанию. */
  notice?: string;
}

const rub = (n: number) => `${n.toLocaleString('ru-RU', { maximumFractionDigits: 0 })} ₽`;

export function buildLeadSourceFollowup(input: LeadSourceFollowupInput): RenderedEmail {
  const { lead, attribution, enrichment } = input;
  const v = explainSource(attribution, enrichment);
  const built = `Источник заявки от ${lead.date} — ${lead.company}: ${v.kindLabel}`
    + (v.system ? `, ${v.system}` : '');
  const subject = input.subjectPrefix ? `${input.subjectPrefix} ${built}` : built;

  const leadRows = [
    kvRow('Компания', `<b>${escapeHtml(lead.company)}</b>`),
    lead.product_ref ? kvRow('Запрос', escapeHtml(lead.product_ref)) : '',
    lead.quote_no ? kvRow('КП', escapeHtml(lead.quote_no)) : '',
    lead.amount ? kvRow('Сумма', rub(lead.amount)) : '',
    kvRow('Форма', escapeHtml(lead.form_source)),
    kvRow('Получена', escapeHtml(lead.date)),
  ].filter(Boolean).join('');

  const html = emailShell(
    heading('Источник заявки')
    + paragraph('Уточнение к письму о заявке: данных Метрики и Директа в момент '
      + 'обращения ещё не существует — визит появляется в Метрике с задержкой, '
      + 'а расход Директ закрывает за прошедшие сутки.')
    + (input.notice
      ? paragraph(`<b style="color:${EMAIL_COLOR.maroon};">${escapeHtml(input.notice)}</b>`)
      : '')
    + card(`<table role="presentation" cellpadding="0" cellspacing="0">${leadRows}</table>`)
    + heading('Разбор источника')
    + card(`<table role="presentation" cellpadding="0" cellspacing="0">${
      attributionRows(attribution, enrichment)}</table>`),
    `${lead.company} · ${v.kindLabel}${v.system ? ` · ${v.system}` : ''}`,
  );

  const text = [
    `Источник заявки от ${lead.date} — ${lead.company}.`,
    ...(input.notice ? ['', input.notice] : []),
    '',
    `Компания: ${lead.company}`,
    ...(lead.product_ref ? [`Запрос: ${lead.product_ref}`] : []),
    ...(lead.quote_no ? [`КП: ${lead.quote_no}`] : []),
    ...(lead.amount ? [`Сумма: ${rub(lead.amount)}`] : []),
    `Форма: ${lead.form_source}`,
    '',
    'Разбор источника:',
    ...attributionLines(attribution, enrichment),
  ].join('\n');

  return { subject, html, text };
}
