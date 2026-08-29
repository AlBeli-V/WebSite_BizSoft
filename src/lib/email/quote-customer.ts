/**
 * Письмо клиенту с коммерческим предложением.
 *
 * Не техническая нотификация, а первая часть продажи: карточка предложения,
 * честная оговорка о предварительном характере цены и приглашение к
 * переговорам. Reply-To настроен на менеджера — «ответьте на это письмо»
 * действительно приводит к живому человеку.
 *
 * Вложение — только JPG (решение руководителя 21.08.2026): картинку нельзя
 * отредактировать и выдать за наш документ.
 */
import { seller, site, taxation } from '../../config/site';
import { salutation } from '../salutation';
import { PRELIMINARY_NOTE, type QuoteData } from '../quote-layout';
import { card, emailShell, escapeHtml, heading, kvRow, note, paragraph } from './layout';

export interface RenderedEmail {
  subject: string;
  html: string;
  text: string;
}

export function buildCustomerQuoteEmail(data: QuoteData): RenderedEmail {
  const total = data.total.toLocaleString('ru-RU');
  const subject = `Коммерческое предложение № ${data.quoteNo} — BIZSoft`;

  const html = emailShell(
    heading('Коммерческое предложение готово')
    + paragraph(escapeHtml(salutation(data.contactName)))
    + paragraph('Благодарим за интерес к программным продуктам BIZSoft. '
      + `Для ${escapeHtml(data.buyerCompany || 'вашей организации')} подготовлено `
      + 'предварительное коммерческое предложение — документ во вложении.')
    + card(
      `<table role="presentation" cellpadding="0" cellspacing="0">`
      + kvRow('КП №', escapeHtml(data.quoteNo), true)
      + kvRow('Сумма', `${total} ₽ — в т.ч. НДС ${taxation.vatPercent}%`, true)
      + kvRow('Позиций', String(data.items.length))
      + kvRow('Действует до', escapeHtml(data.validUntil))
      + `</table>`)
    + note(escapeHtml(PRELIMINARY_NOTE))
    + paragraph('Форма поставки — в электронном виде. Оплата: 100% аванс по счёту. '
      + escapeHtml(taxation.docsLine))
    + paragraph('<b>Хотите обсудить условия или получить индивидуальную цену?</b><br>'
      + 'Просто ответьте на это письмо — оно сразу поступит ответственному менеджеру. '
      + `Телефон: ${escapeHtml(seller.phone)}.`),
    `КП № ${data.quoteNo} на ${total} ₽ — во вложении`,
  );

  // Text-fallback — то же содержимое без вёрстки.
  const text = [
    salutation(data.contactName),
    '',
    `Коммерческое предложение № ${data.quoteNo} во вложении.`,
    `Сумма: ${total} ₽, в т.ч. НДС ${taxation.vatPercent}%. `
      + `Действует до ${data.validUntil}.`,
    '',
    PRELIMINARY_NOTE,
    '',
    'Форма поставки — в электронном виде. Оплата: 100% аванс по счёту.',
    taxation.docsLine,
    '',
    'Хотите обсудить условия или получить индивидуальную цену?',
    'Ответьте на это письмо — оно сразу поступит ответственному менеджеру.',
    `${seller.shortName} · ${seller.phone} · ${site.url}`,
  ].join('\n');

  return { subject, html, text };
}
