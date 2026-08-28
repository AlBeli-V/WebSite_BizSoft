/**
 * Служебное письмо руководителю о новом КП — карточка sales-возможности.
 *
 * Сверху то, что нужно для решения «звонить сейчас или нет»: сумма,
 * организация, светофор проверок, экономика сделки. Детали — ниже.
 *
 * Вложения собирает обработчик: Word (рабочий исходник без штампов),
 * PDF (слепок клиентского документа со штампами) и Excel экономики —
 * внутренний файл, о чём письмо предупреждает отдельно: Reply-To этого
 * письма — адрес клиента, и «Ответить» с вложениями отправит их наружу.
 */
import { economics as cfg, taxation } from '../../config/site';
import type { QuoteData } from '../quote-layout';
import { usdReference, type QuoteEconomics } from '../quote-economics';
import {
  card, EMAIL_COLOR, emailShell, escapeHtml, heading, kvRow, note, paragraph,
} from './layout';
import type { RenderedEmail } from './quote-customer';

export interface ManagerQuoteEmailInput {
  data: QuoteData;
  innCheck: { valid: boolean; verdict: string; nameMatch?: string };
  /** Строки карточки ЕГРЮЛ (cardLines) — пусто, если справочник молчал. */
  partyCard: string[];
  /** null — организация не проверялась; false — не действует. */
  partyActive: boolean | null;
  /** null — экономику посчитать не удалось (нет курса). */
  eco: QuoteEconomics | null;
}

// Неразрывный пробел перед ₽: обычный позволяет почтовику оторвать знак
// валюты от числа на границе строки.
const rub = (n: number) => `${n.toLocaleString('ru-RU', { maximumFractionDigits: 0 })} ₽`;

function light(ok: boolean | null, okText: string, warnText: string, unknownText = ''): string {
  if (ok === null) return `<span style="color:${EMAIL_COLOR.muted};">◻ ${unknownText}</span>`;
  return ok
    ? `<span style="color:${EMAIL_COLOR.ok};">✓ ${okText}</span>`
    : `<span style="color:${EMAIL_COLOR.warn};">⚠ ${warnText}</span>`;
}

export function buildManagerQuoteEmail(input: ManagerQuoteEmailInput): RenderedEmail {
  const { data, innCheck, partyCard, partyActive, eco } = input;
  const trouble = !(innCheck.valid && innCheck.nameMatch !== 'mismatch' && partyActive !== false);
  const subject = `${trouble ? '⚠ ' : ''}Отправлено КП № ${data.quoteNo} — ${data.buyerCompany}`;

  const ecoRows = eco ? [
    kvRow('Выручка по КП', rub(eco.revenue), true),
    kvRow('Закупка (себестоимость)', eco.purchaseRub > 0
      ? `${rub(eco.purchaseRub)}${usdReference(eco.purchaseRub, eco.fx) != null
          ? ` · $${usdReference(eco.purchaseRub, eco.fx)!.toLocaleString('ru-RU')}` : ''}`
      : 'нет данных'),
    kvRow(`НДС ${taxation.vatPercent}% + ${cfg.taxLabel.toLowerCase()} ${cfg.taxPercent}% + `
      + `${cfg.fxReserveLabel.toLowerCase()} ${cfg.fxReservePercent}%`,
      rub(eco.vat + eco.tax + eco.fxReserve)),
    kvRow('Ожидаемая прибыль', `${rub(eco.profit)} · ${eco.profitPercent.toLocaleString('ru-RU')}%`, true),
  ].join('') : '';

  const html = emailShell(
    heading(`Новое КП — ${rub(data.total)}`)
    + paragraph(`<b>${escapeHtml(data.buyerCompany)}</b> · клиент запросил отправку `
      + `КП № ${escapeHtml(data.quoteNo)} себе на почту.`)
    + paragraph(
      // Вердикт проверки уже начинается со слова «ИНН» — префикс не нужен.
      light(innCheck.valid && innCheck.nameMatch !== 'mismatch',
        escapeHtml(innCheck.verdict), escapeHtml(innCheck.verdict))
      + '<br>'
      + light(partyActive, 'Организация действует (ЕГРЮЛ)',
        'Организация не действует — уточнить до счёта', 'ЕГРЮЛ не проверялся'))
    + card(
      `<table role="presentation" cellpadding="0" cellspacing="0">`
      + kvRow('Контакт', escapeHtml(data.contactName), true)
      + kvRow('E-mail', escapeHtml(data.email))
      + kvRow('Телефон', escapeHtml(data.phone || '—'))
      + kvRow('ИНН', escapeHtml(data.buyerInn))
      + kvRow('Действует до', escapeHtml(data.validUntil))
      + `</table>`)
    + (partyCard.length
      ? paragraph(`По данным ЕГРЮЛ:<br>${partyCard.map(escapeHtml).join('<br>')}`, { small: true, muted: true })
      : '')
    + heading('Состав заказа')
    + card(
      `<table role="presentation" cellpadding="0" cellspacing="0" width="100%">`
      + data.items.map((i) =>
        `<tr><td style="font-family:Arial,Helvetica,sans-serif;font-size:13px;color:${EMAIL_COLOR.body};padding:4px 8px 4px 0;">`
        + `${escapeHtml(i.name)} <span style="color:${EMAIL_COLOR.muted};">(${escapeHtml(i.sku)})</span> × ${i.qty}</td>`
        + `<td align="right" style="font-family:Arial,Helvetica,sans-serif;font-size:13px;color:${EMAIL_COLOR.dark};padding:4px 0;white-space:nowrap;">${rub(i.sum)}</td></tr>`).join('')
      + `</table>`)
    + (eco
      ? heading('Экономика сделки')
        + card(`<table role="presentation" cellpadding="0" cellspacing="0">${ecoRows}</table>`)
        + (eco.complete ? '' : note(
          `Нет закупочных цен по позициям: ${eco.missingPurchase.map(escapeHtml).join(', ')} — `
          + 'прибыль посчитана без них и завышена. Подробности в Excel-вложении.', 'warn'))
        + (eco.suspectMonthly.length ? note(
          `<b>Проверить закупку:</b> у ${eco.suspectMonthly.map(escapeHtml).join(', ')} `
          + 'соотношение продажи к закупке похоже на МЕСЯЧНУЮ закупочную цену при годовой '
          + 'продаже — прибыль завышена, сверить с годовым прайсом вендора.', 'warn') : '')
        + (eco.aboveSale.length ? note(
          `<b>Закупка дороже продажи:</b> ${eco.aboveSale.map(escapeHtml).join(', ')} — `
          + 'проверить период и валюту закупочной цены.', 'warn') : '')
      : note('Экономику посчитать не удалось (нет курса ЦБ) — см. закупочные цены вручную.', 'warn'))
    + note('<b>Вложения.</b> Word — рабочий исходник без штампов (клиенту не пересылать), '
      + 'PDF — точная копия отправленного клиенту документа, '
      + 'Excel — <b>внутренняя экономика сделки: при ответе клиенту удалить из вложений</b>.'),
    `${data.buyerCompany} · ${rub(data.total)}${eco ? ` · прибыль ~${rub(eco.profit)}` : ''}`,
  );

  const text = [
    `Клиент запросил отправку КП № ${data.quoteNo} себе на почту.`,
    '',
    'Данные заказчика из формы:',
    `Организация: ${data.buyerCompany}`,
    `ИНН: ${data.buyerInn} — ${innCheck.verdict}`,
    `Контактное лицо: ${data.contactName}`,
    `E-mail: ${data.email}`,
    `Телефон: ${data.phone}`,
    '',
    ...(partyCard.length ? ['По данным ЕГРЮЛ:', ...partyCard,
      ...(partyActive === false ? ['⚠ Организация не действует — уточнить до счёта.'] : []),
      ''] : []),
    'Состав заказа:',
    ...data.items.map((i) => `— ${i.name} (${i.sku}) × ${i.qty} = ${i.sum.toLocaleString('ru-RU')} ₽`),
    '',
    `Итого: ${data.total.toLocaleString('ru-RU')} ₽. Действует до ${data.validUntil}.`,
    ...(eco ? [
      '',
      'Экономика сделки:',
      `Закупка: ${eco.purchaseRub > 0 ? rub(eco.purchaseRub) : 'нет данных'}`,
      `Ожидаемая прибыль: ${rub(eco.profit)} (${eco.profitPercent.toLocaleString('ru-RU')}%)`,
      ...(eco.complete ? [] : [`⚠ Без закупочных цен: ${eco.missingPurchase.join(', ')} — прибыль завышена.`]),
      ...(eco.suspectMonthly.length
        ? [`⚠ Похоже на месячную закупку при годовой продаже: ${eco.suspectMonthly.join(', ')} — сверить с прайсом вендора.`] : []),
      ...(eco.aboveSale.length
        ? [`⚠ Закупка дороже продажи: ${eco.aboveSale.join(', ')}.`] : []),
    ] : []),
    '',
    'Вложения: Word — рабочий (без штампов), PDF — копия клиентского,',
    'Excel — ВНУТРЕННЯЯ экономика: при ответе клиенту удалить из вложений.',
  ].join('\n');

  return { subject, html, text };
}
