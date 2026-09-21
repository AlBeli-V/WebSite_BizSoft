/**
 * Служебное HTML-письмо руководителю о новой заявке с сайта.
 *
 * Решение руководителя 28.08.2026: заявка приходит в том же фирменном
 * оформлении, что и письмо о КП, — с блоком источника (канал → кампания →
 * фраза), карточкой реквизитов (название по ЕГРЮЛ против указанного
 * клиентом, юрадрес, сайт по домену почты) и сообщением клиента.
 */
import type { PartyCard } from '../dadata';
import type { AttributionFields } from '../quote-lead';
import type { SourceEnrichment } from '../traffic-source';
import {
  attributionLines, attributionRows, card, EMAIL_COLOR, emailShell, escapeHtml,
  heading, kvRow, note, paragraph,
} from './layout';
import type { RenderedEmail } from './quote-customer';
import { siteFromEmail } from './quote-manager';

export interface ManagerLeadEmailInput {
  lead: {
    name: string;
    company: string;
    inn: string;
    email: string;
    phone: string;
    message: string;
    product_ref: string;
    form_source: string;
    /** Дата получения заявки, дд.мм.гггг. */
    date: string;
  };
  attribution: AttributionFields;
  /** null — ИНН не проверялся (ключа ДаДаты нет). */
  innCheck: { valid: boolean; verdict: string; nameMatch?: string } | null;
  party: PartyCard | null;
  /**
   * Данные Метрики и Директа по этой заявке. В живом письме их нет: визит в
   * Метрике появляется с задержкой, расход Директа закрывается за сутки.
   * Заполняются при повторной отправке и в утреннем уточнении.
   */
  enrichment?: SourceEnrichment | null;
  /** Приписка к теме — «(ТЕСТ ПОВТОР)» у повторной отправки. */
  subjectPrefix?: string;
  /** Тема целиком вместо собранной: повтор письма о КП сохраняет свою. */
  subjectOverride?: string;
  /** Плашка в начале письма: зачем оно пришло второй раз. */
  notice?: string;
  /**
   * Разбор обращения по каталогу (`src/lib/lead-request.ts`): что удалось
   * опознать и что требует человека. Заказчику из этого блока не
   * показывается ничего — письмо-подтверждение молчит обо всём, в чём
   * разбор не уверен, а решать расхождения человеку.
   */
  review?: {
    vendor?: string;
    product?: string;
    /** Позиция найдена в каталоге. Иначе название — только слова клиента. */
    matched?: boolean;
    qty?: string;
    term?: string;
    notes: string[];
    candidates: string[];
  } | null;
}

export function buildManagerLeadEmail(input: ManagerLeadEmailInput): RenderedEmail {
  const { lead, attribution, innCheck, party, enrichment } = input;
  const mismatch = innCheck?.nameMatch === 'mismatch';
  const trouble = Boolean(innCheck && (!innCheck.valid || mismatch)) || (party ? !party.active : false);
  const built = input.subjectOverride
    || `${trouble ? '⚠ ' : ''}Новая заявка с сайта BIZSoft`
      + (lead.product_ref ? `: ${lead.product_ref}` : '');
  const subject = input.subjectPrefix ? `${input.subjectPrefix} ${built}` : built;

  const warnings: string[] = [];
  if (innCheck && !innCheck.valid) warnings.push('ВНИМАНИЕ: ИНН не проходит проверку контрольной суммы — сверить реквизиты');
  else if (mismatch) warnings.push('ВНИМАНИЕ: ИНН не соответствует декларируемому названию компании');
  if (party && !party.active) warnings.push('ВНИМАНИЕ: организация не действует по ЕГРЮЛ — уточнить до счёта');
  const warnHtml = warnings.map((w) =>
    paragraph(`<b style="color:${EMAIL_COLOR.maroon};">⚠ ${escapeHtml(w)}</b>`)).join('');

  const companyHtml = mismatch && party?.name
    ? `<b style="color:${EMAIL_COLOR.ok};">${escapeHtml(party.name)}</b>`
      + ` <span style="color:${EMAIL_COLOR.muted};">(по ИНН)</span><br>`
      + `<b style="color:${EMAIL_COLOR.warn};">${escapeHtml(lead.company)}</b>`
      + ` <span style="color:${EMAIL_COLOR.muted};">(указано клиентом)</span>`
    : `<b>${escapeHtml(party?.name || lead.company)}</b>`;

  // Разбор обращения: опознанное и то, что требует человека. Блок
  // появляется, только когда есть что сказать, — пустая рамка «разбор:
  // ничего» занимала бы место в письме, которое читают с телефона.
  const review = input.review;
  const reviewRows = review ? [
    ...(review.vendor ? [kvRow('Производитель', `<b>${escapeHtml(review.vendor)}</b>`)] : []),
    // Названное клиентом и найденное в каталоге — разные вещи, и менеджер
    // обязан видеть разницу: по первому нельзя выставить счёт.
    ...(review.product
      ? [kvRow('Позиция', `<b>${escapeHtml(review.product)}</b>`
        + (review.matched
          ? ''
          : ` <span style="color:${EMAIL_COLOR.warn};">· названа клиентом, в каталоге не найдена</span>`))]
      : [kvRow('Позиция', `<span style="color:${EMAIL_COLOR.warn};">не опознана</span>`)]),
    ...(review.qty ? [kvRow('Количество', escapeHtml(review.qty))] : []),
    ...(review.term ? [kvRow('Запрошенный срок', escapeHtml(review.term))] : []),
    ...(review.candidates.length
      ? [kvRow('Есть в каталоге', escapeHtml(review.candidates.join(', ')))] : []),
  ].join('') : '';
  const reviewHtml = review && (reviewRows || review.notes.length)
    ? heading('Разбор обращения')
      + card(`<table role="presentation" cellpadding="0" cellspacing="0">${reviewRows}</table>`)
      + review.notes.map((n) => note(escapeHtml(n))).join('')
    : '';

  const siteGuess = siteFromEmail(lead.email);
  const siteHtml = siteGuess.url
    ? `<a href="${siteGuess.url}" style="color:${EMAIL_COLOR.accent};text-decoration:none;">${escapeHtml(siteGuess.label)}</a>`
      + ` <span style="color:${EMAIL_COLOR.muted};">(по домену почты)</span>`
    : escapeHtml(siteGuess.label);

  const egrulNote = party
    ? paragraph('ЕГРЮЛ: ' + [
        party.fullName,
        `ИНН/КПП ${party.inn}${party.kpp ? ` / ${party.kpp}` : ''}`,
        party.ogrn ? `ОГРН ${party.ogrn}` : '',
        party.address,
        `статус: ${party.status}${party.registeredOn ? `, в реестре с ${party.registeredOn}` : ''}`,
        party.okved ? `ОКВЭД ${party.okved}` : '',
      ].filter(Boolean).map(escapeHtml).join(' · '), { small: true, muted: true })
    : '';

  const html = emailShell(
    heading('Новая заявка с сайта')
    + paragraph(`Форма: <b>${escapeHtml(lead.form_source)}</b>`
      + (lead.product_ref ? ` · товар: <b>${escapeHtml(lead.product_ref)}</b>` : '')
      + ` · получена ${escapeHtml(lead.date)}.`)
    + (input.notice ? note(escapeHtml(input.notice)) : '')
    + warnHtml
    + reviewHtml
    + heading('Источник обращения')
    + card(`<table role="presentation" cellpadding="0" cellspacing="0">${
      attributionRows(attribution, enrichment)}</table>`)
    + card(
      `<table role="presentation" cellpadding="0" cellspacing="0">`
      + kvRow('Компания', companyHtml)
      + kvRow('ИНН', escapeHtml(lead.inn || '—')
        + (innCheck ? ` <span style="color:${EMAIL_COLOR.muted};">· ${escapeHtml(innCheck.verdict)}</span>` : ''))
      + kvRow('Адрес (юрид.)', escapeHtml(party?.address || '—'))
      + kvRow('Сайт', siteHtml)
      + kvRow('Контакт', escapeHtml(lead.name), true)
      + kvRow('Телефон', escapeHtml(lead.phone || '—'))
      + kvRow('Почта', escapeHtml(lead.email))
      + `</table>`)
    + heading('Сообщение клиента')
    + card(paragraph(escapeHtml(lead.message).replace(/\n/g, '<br>')))
    + egrulNote,
    `${lead.company} · ${lead.name}${attribution.last_touch_source ? ` · ${attribution.last_touch_source}` : ''}`,
  );

  const text = [
    `Новая заявка с сайта. Форма: ${lead.form_source}`
      + (lead.product_ref ? ` · товар: ${lead.product_ref}` : '') + ` · получена ${lead.date}.`,
    ...(input.notice ? ['', input.notice] : []),
    ...warnings.map((w) => `⚠ ${w}`),
    '',
    ...(review && (reviewRows || review.notes.length) ? [
      'Разбор обращения:',
      `Производитель: ${review.vendor || '—'}`,
      `Позиция: ${review.product
        ? `${review.product}${review.matched ? '' : ' (названа клиентом, в каталоге не найдена)'}`
        : 'не опознана'}`,
      ...(review.qty ? [`Количество: ${review.qty}`] : []),
      ...(review.term ? [`Запрошенный срок: ${review.term}`] : []),
      ...(review.candidates.length ? [`Есть в каталоге: ${review.candidates.join(', ')}`] : []),
      ...review.notes.map((n) => `! ${n}`),
      '',
    ] : []),
    'Источник обращения:',
    ...attributionLines(attribution, enrichment),
    '',
    'Реквизиты:',
    ...(mismatch && party?.name
      ? [`Компания (по ИНН): ${party.name}`, `Компания (указано клиентом): ${lead.company}`]
      : [`Компания: ${party?.name || lead.company}`]),
    `ИНН: ${lead.inn || '—'}${innCheck ? ` — ${innCheck.verdict}` : ''}`,
    `Адрес (юрид.): ${party?.address || '—'}`,
    `Сайт: ${siteGuess.url || siteGuess.label}`,
    `Контакт: ${lead.name}`,
    `Телефон: ${lead.phone || '—'}`,
    `Почта: ${lead.email}`,
    '',
    'Сообщение клиента:',
    lead.message,
    ...(party ? ['', 'ЕГРЮЛ: ' + [
      party.fullName,
      `ИНН/КПП ${party.inn}${party.kpp ? ` / ${party.kpp}` : ''}`,
      party.ogrn ? `ОГРН ${party.ogrn}` : '',
      party.address,
      `статус: ${party.status}`,
    ].filter(Boolean).join(' · ')] : []),
  ].join('\n');

  return { subject, html, text };
}
