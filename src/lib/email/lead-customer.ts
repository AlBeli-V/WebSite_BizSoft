/**
 * Письмо заказчику о том, что его обращение принято.
 *
 * Зачем оно есть. До 21.09.2026 форма заявки отправляла ровно одно письмо —
 * руководителю. Человек, оставивший ФИО, ИНН, телефон и запрос, не получал
 * от нас ничего: подтверждение жило только надписью на экране, которая
 * исчезала с закрытием вкладки. В почте заказчика не оставалось ни следа
 * обращения, ни наших реквизитов, ни адреса, на который можно дослать
 * файл, — а у входящего письма от менеджера через день не оказывалось
 * ветки, к которой оно цепляется.
 *
 * Чем это письмо не является. Это не коммерческое предложение: ни цен, ни
 * сумм, ни сроков поставки в нём нет — их называет КП (`quote-customer.ts`)
 * после расчёта. Здесь только то, что мы уже знаем наверняка: что получено,
 * от кого, когда и что будет дальше. Обещания срока ответа письмо даёт ровно
 * то же, что дала страница в момент отправки, — «ответим в рабочее время»:
 * два разных обещания об одном обращении хуже, чем одно скромное.
 *
 * Адрес получателя не подтверждён — его ввели в публичную форму. Поэтому
 * письмо не несёт ничего, кроме введённых в эту же форму данных, и
 * заканчивается строкой для того, кто обращения не оставлял.
 *
 * Оформление общее с письмом о КП (`client-shell.ts`): два письма подряд на
 * один адрес обязаны читаться как два письма одной компании.
 */
import { offerDocs, offerManager, seller, site } from '../../config/site';
import { salutation } from '../salutation';
import { withEmailUtm } from '../offer-content';
import {
  banner, BODY, closeLetter, confidentialFooter, esc, FONT, INK, letterTitle,
  MUTED, openLetter, RULE, section, sectionHead, signature, stepRow,
  type RenderedEmail,
} from './client-shell';

/** Метка кампании в ссылках письма: переходы отсюда видны отдельно от КП. */
const UTM_CAMPAIGN = 'lead_confirmation';

export interface CustomerLeadEmailInput {
  lead: {
    name: string;
    company: string;
    inn: string;
    email: string;
    phone: string;
    message: string;
    /** Что считаем: тариф, позиция, количество — как выбрал посетитель. */
    product_ref: string;
    /** Дата приёма обращения, дд.мм.гггг. */
    date: string;
  };
}

/** Строка карточки обращения: подпись слева, значение справа. */
function row(key: string, valueHtml: string): string {
  return `<tr>`
    + `<td width="150" valign="top" style="font-family:${FONT};font-size:13px;line-height:20px;`
    + `color:${MUTED};padding:9px 14px 9px 0">${esc(key)}</td>`
    + `<td valign="top" style="font-family:${FONT};font-size:14px;line-height:20px;`
    + `color:${INK};padding:9px 0">${valueHtml}</td>`
    + `</tr>`;
}

/**
 * Сообщение клиента в письме: перенос строки остаётся переносом.
 *
 * Текст пришёл из публичной формы, поэтому экранируется целиком, и только
 * потом в него подставляются `<br>` — иначе разметка из поля «сообщение»
 * доехала бы до почтового клиента получателя как разметка.
 */
function quotedMessage(text: string): string {
  return esc(text).replace(/\r?\n/g, '<br>');
}

export function buildCustomerLeadEmail(input: CustomerLeadEmailInput): RenderedEmail {
  const { lead } = input;
  const company = lead.company.trim() || 'вашей организации';
  // Тема называет предмет и дату: в списке писем обращение узнаётся без
  // открытия, а номера у заявки для клиента нет — он ему ни о чём не говорит.
  const subject = `Обращение принято — BIZSoft, ${lead.date}`;

  const replyHref = `mailto:${offerManager.email}`
    + `?subject=${encodeURIComponent(`Дополнение к обращению от ${lead.date} — ${company}`)}`;
  const docsHref = withEmailUtm(`${site.url}${offerDocs.contract.path}`, 'documents', UTM_CAMPAIGN);
  const howHref = withEmailUtm(`${site.url}/how-we-work`, 'how-we-work', UTM_CAMPAIGN);
  const catalogHref = withEmailUtm(`${site.url}/catalog`, 'catalog', UTM_CAMPAIGN);

  const steps = [
    stepRow('01', 'Дополнить обращение ответным письмом', replyHref),
    stepRow('02', 'Скачать образец договора', docsHref, '&#8595;'),
    stepRow('03', 'Как проходит поставка', howHref),
    stepRow('04', 'Каталог продуктов и AI-сервисов', catalogHref),
  ].join('');

  const details = [
    row('Получено', `${esc(lead.date)}`),
    row('Организация', `<b>${esc(lead.company)}</b>`
      + (lead.inn ? `<br><span style="color:${MUTED};font-size:13px">ИНН ${esc(lead.inn)}</span>` : '')),
    ...(lead.product_ref ? [row('Запрос по позиции', esc(lead.product_ref))] : []),
    ...(lead.message ? [row('Ваше сообщение',
      `<span style="color:${BODY}">${quotedMessage(lead.message)}</span>`)] : []),
    row('Для связи с вами', [esc(lead.phone), esc(lead.email)].filter(Boolean)
      .join(`<br>`)),
  ].join('');

  const html = openLetter(subject,
    `Мы получили ваше обращение от ${lead.date}. Ответим в рабочее время.`)
    + banner()
    + letterTitle('Обращение принято', `в интересах ${company}`)

    // ── Обращение ──
    + section(`<div style="font-family:${FONT};font-size:15px;line-height:24px;color:${BODY}">`
      + `<b style="color:${INK}">${esc(salutation(lead.name))}</b><br><br>`
      + `Благодарим Вас за обращение в BIZSoft. Подтверждаем: Ваш запрос получен и передан `
      + `менеджеру. Мы изучим задачу, подберём продукты и вернёмся с ответом в рабочее время; `
      + `при необходимости уточнить состав или количество — позвоним или напишем. `
      + `Расчёт и предварительное коммерческое предложение придут отдельным письмом.</div>`, 26)
    + `<tr><td class="pad" align="right" style="padding:14px 36px 0;font-family:${FONT};`
    + `font-size:14px;color:${BODY}"><i>Команда BIZSoft.</i></td></tr>`

    // ── Что мы получили ──
    // Состав обращения возвращается заказчику дословно: так он видит, что
    // дошло, и сразу замечает опечатку в телефоне или ИНН — до того, как
    // менеджер потратит день на дозвон по неверному номеру.
    + section(sectionHead('Ваше обращение')
      + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" `
      + `style="border-top:1px solid ${RULE}">`
      + details
      + `</table>`
      + `<div style="font-family:${FONT};font-size:12.5px;line-height:18px;color:${MUTED};`
      + `border-top:1px solid ${RULE};padding-top:12px;margin-top:4px">`
      + `Заметили неточность — ответьте на это письмо, поправим до расчёта.</div>`)

    // ── Что дальше ──
    + section(sectionHead('Что дальше')
      + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">`
      + steps
      + `<tr><td style="border-top:1px solid ${RULE};font-size:0;line-height:0">&nbsp;</td></tr>`
      + `</table>`)

    + signature()
    + confidentialFooter(
      ` <br><br>Письмо отправлено автоматически: адрес указан в форме на `
      + `<a href="${esc(withEmailUtm(site.url, 'footer', UTM_CAMPAIGN))}" `
      + `style="color:${MUTED}">${esc(site.domain)}</a> `
      + `${esc(lead.date)}. Если обращение оставляли не Вы — ответьте на это письмо, `
      + `и мы удалим данные. ${esc(seller.legalName)}, ИНН ${esc(seller.inn)}.`)
    + closeLetter();

  // Текстовая версия — то же содержимое без вёрстки: часть клиентов
  // показывает именно её, и потерять в ней состав обращения нельзя.
  const text = [
    salutation(lead.name),
    '',
    'Благодарим Вас за обращение в BIZSoft. Подтверждаем: Ваш запрос получен и передан '
      + 'менеджеру. Мы изучим задачу, подберём продукты и вернёмся с ответом в рабочее время. '
      + 'Расчёт и предварительное коммерческое предложение придут отдельным письмом.',
    '',
    'ВАШЕ ОБРАЩЕНИЕ',
    `Получено: ${lead.date}`,
    `Организация: ${lead.company}${lead.inn ? ` (ИНН ${lead.inn})` : ''}`,
    ...(lead.product_ref ? [`Запрос по позиции: ${lead.product_ref}`] : []),
    ...(lead.message ? ['Ваше сообщение:', lead.message] : []),
    `Для связи с вами: ${[lead.phone, lead.email].filter(Boolean).join(' · ')}`,
    'Заметили неточность — ответьте на это письмо, поправим до расчёта.',
    '',
    'ЧТО ДАЛЬШЕ',
    '— Дополнить обращение: ответным письмом',
    `— Образец договора: ${site.url}${offerDocs.contract.path}`,
    `— Как проходит поставка: ${site.url}/how-we-work`,
    `— Каталог: ${site.url}/catalog`,
    '',
    'Команда BIZSoft.',
    '',
    offerManager.name,
    `${offerManager.phone} · ${offerManager.email} · ${site.url}`,
    '',
    'Письмо отправлено автоматически: адрес указан в форме на '
      + `${site.domain} ${lead.date}. Если обращение оставляли не Вы — ответьте на это `
      + `письмо, и мы удалим данные. ${seller.legalName}, ИНН ${seller.inn}.`,
  ].join('\n');

  return { subject, html, text };
}
