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
 * после расчёта.
 *
 * Композиция утверждена руководителем 21.09.2026 (редакция 2). Смысл
 * правок: письмо перестало пересказывать заказчику наши намерения («мы
 * изучим задачу, подберём продукты, вернёмся с ответом») и стало отвечать
 * на единственный вопрос человека — что именно у нас лежит по его запросу.
 * Отсюда состав: подтверждение одним абзацем, предмет обращения от общего к
 * частному (производитель → продукт → тип лицензии → количество → дословная
 * цитата сообщения), два действия и подборка позиций по теме запроса.
 *
 * Адрес получателя не подтверждён — его ввели в публичную форму. Поэтому
 * письмо не несёт ничего, кроме введённых в эту же форму данных и позиций
 * нашего же каталога, и заканчивается строкой для того, кто обращения не
 * оставлял.
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

/** Позиция каталога, названная в письме: подпись и адрес страницы. */
export interface LeadLink {
  name: string;
  url: string;
}

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
  /**
   * Предмет обращения, когда позиция опознана: заявка с карточки товара
   * знает производителя, продукт и тип плана, заявка из общей формы — нет.
   * Поля необязательные: строки, которых нет в данных, в письме не
   * рисуются, а не показываются пустыми.
   */
  request?: {
    /** Производитель: «Adobe», «JetBrains». */
    vendor?: string;
    /** Название подписки или сервиса: «Creative Cloud Pro». */
    product?: string;
    /**
     * Тип лицензии — из сегмента `ПЛАН` артикула (`src/lib/plan-type.ts`),
     * то есть данные, а не догадка по названию: TEAM → командная, IND →
     * индивидуальная, UNI → деления нет.
     */
    plan?: LeadPlan;
    qty?: number | string;
    /** Страницы каталога, названные в письме. */
    links?: {
      /** Страница запрошенной позиции. */
      product?: LeadLink;
      /** Другой план того же продукта — командный против личного и наоборот. */
      alternative?: LeadLink;
      /** Раздел каталога, куда входит позиция. */
      catalog?: LeadLink;
    };
  };
}

export type LeadPlan = 'team' | 'individual' | 'universal';

/**
 * Тип лицензии словами. Свой словарь, а не `PLAN_SHORT` карточки: там
 * значения согласованы со словом «план» («Командный»), а в письме строка
 * называется «Тип лицензии» — и «Командный лицензия» не читается.
 */
const PLAN_WORD: Record<LeadPlan, string> = {
  team: 'Командная',
  individual: 'Индивидуальная',
  universal: 'Универсальная',
};

/** Строка блока обращения: подпись слева, значение справа. */
function row(key: string, valueHtml: string): string {
  return `<tr>`
    + `<td width="150" valign="top" style="font-family:${FONT};font-size:13px;line-height:20px;`
    + `color:${MUTED};padding:9px 14px 9px 0">${esc(key)}</td>`
    + `<td valign="top" style="font-family:${FONT};font-size:14px;line-height:20px;`
    + `color:${INK};padding:9px 0">${valueHtml}</td>`
    + `</tr>`;
}

/**
 * Сообщение клиента — цитатой, дословно и с сохранением переносов.
 *
 * Текст пришёл из публичной формы, поэтому экранируется целиком, и только
 * потом в него подставляются `<br>` — иначе разметка из поля «сообщение»
 * доехала бы до почтового клиента получателя как разметка. Цитата
 * набирается полосой слева, а не кавычками: в почте кавычки теряются среди
 * кавычек самого текста.
 */
function quote(text: string): string {
  return `<div style="font-family:${FONT};font-size:14px;line-height:21px;color:${BODY};`
    + `border-left:2px solid ${RULE};padding:2px 0 2px 12px">`
    + esc(text).replace(/\r?\n/g, '<br>') + `</div>`;
}

/**
 * Количество из свободной строки формы.
 *
 * Поле `product_ref` посетитель не заполняет — его собирает страница, и на
 * карточке товара оно приходит как «количество: 3». Разбирать эту строку
 * приходится здесь: пока в заявке нет отдельного поля, число мест иначе
 * потеряется в письме, хотя человек его указал.
 */
export function refParts(ref: string): { qty?: string; rest?: string } {
  const m = ref.match(/кол(?:ичество|-во)\s*:?\s*(\d+)/i);
  const rest = (m ? ref.replace(m[0], '') : ref).replace(/^[\s,;·—-]+|[\s,;·—-]+$/g, '');
  return { qty: m?.[1], rest: rest || undefined };
}

export function buildCustomerLeadEmail(input: CustomerLeadEmailInput): RenderedEmail {
  const { lead } = input;
  const req = input.request ?? {};
  const company = lead.company.trim();
  // Тема называет предмет и дату: в списке писем обращение узнаётся без
  // открытия, а номера у заявки для клиента нет — он ему ни о чём не говорит.
  const subject = `Обращение принято — BIZSoft, ${lead.date}`;

  const parts = refParts(lead.product_ref || '');
  const qty = req.qty !== undefined && req.qty !== '' ? String(req.qty) : parts.qty;
  const product = req.product || parts.rest;
  const links = req.links ?? {};

  const replyHref = `mailto:${offerManager.email}`
    + `?subject=${encodeURIComponent(`Дополнение к обращению от ${lead.date}`
      + (company ? ` — ${company}` : ''))}`;
  const docsHref = withEmailUtm(`${site.url}${offerDocs.contract.path}`, 'documents', UTM_CAMPAIGN);
  const link = (l: LeadLink, tag: string) => withEmailUtm(l.url, tag, UTM_CAMPAIGN);

  // Первая строка абзаца собирается из того, что известно наверняка: дата
  // приёма и организация из формы. Организации в заявке может не быть —
  // тогда предложение просто кончается на «в BIZSoft».
  const intro = `Благодарим Вас за обращение от ${lead.date} в BIZSoft`
    + (company ? ` от компании ${company}` : '')
    + `. Подтверждаем, что Ваш запрос получен и передан менеджеру.`;

  // Порядок строк — от общего к частному: чей продукт, какой продукт, какая
  // лицензия, сколько и что человек написал своими словами.
  const details = [
    ...(req.vendor ? [row('Производитель', `<b>${esc(req.vendor)}</b>`)] : []),
    ...(product ? [row('Продукт', esc(product))] : []),
    ...(req.plan ? [row('Тип лицензии', esc(PLAN_WORD[req.plan]))] : []),
    ...(qty ? [row('Количество', esc(qty))] : []),
    ...(lead.message ? [row('Текст сообщения', quote(lead.message))] : []),
  ].join('');

  // Подборка по теме запроса. Показывается только тем, чью позицию мы
  // опознали: три строки-заглушки «посмотрите каталог» у человека, который
  // уже назвал продукт, — это шум, а не помощь.
  const interest = [
    ...(links.product ? [stepRow('01', links.product.name, link(links.product, 'product'))] : []),
    ...(links.alternative
      ? [stepRow('02', links.alternative.name, link(links.alternative, 'alternative'))] : []),
    ...(links.catalog ? [stepRow(links.product || links.alternative ? '03' : '01',
      links.catalog.name, link(links.catalog, 'catalog'))] : []),
  ].join('');

  const html = openLetter(subject,
    `Мы получили ваше обращение от ${lead.date}. Ответим в рабочее время.`)
    + banner()
    + letterTitle('Обращение принято')

    // ── Обращение ──
    + section(`<div style="font-family:${FONT};font-size:15px;line-height:24px;color:${BODY}">`
      + `<b style="color:${INK}">${esc(salutation(lead.name))}</b><br><br>`
      + `${esc(intro)}</div>`, 26)

    // ── Предмет обращения ──
    // Состав возвращается заказчику дословно: так он видит, что дошло, и
    // сразу замечает расхождение — до того, как менеджер посчитает не то.
    + (details ? section(sectionHead('Ваше обращение')
      + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" `
      + `style="border-top:1px solid ${RULE}">`
      + details
      + `</table>`
      + `<div style="font-family:${FONT};font-size:12.5px;line-height:18px;color:${MUTED};`
      + `border-top:1px solid ${RULE};padding-top:12px;margin-top:4px">`
      + `Заметили неточность — ответьте на это письмо, поправим до расчёта.</div>`) : '')

    // ── Что дальше ──
    + section(sectionHead('Что дальше')
      + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">`
      + stepRow('01', 'Дополнить обращение ответным письмом', replyHref)
      + stepRow('02', 'Скачать образец договора', docsHref, '&#8595;')
      + `<tr><td style="border-top:1px solid ${RULE};font-size:0;line-height:0">&nbsp;</td></tr>`
      + `</table>`)

    // ── Вас может заинтересовать ──
    + (interest ? section(sectionHead('Вас может заинтересовать')
      + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">`
      + interest
      + `<tr><td style="border-top:1px solid ${RULE};font-size:0;line-height:0">&nbsp;</td></tr>`
      + `</table>`) : '')

    + signature()
    + confidentialFooter(
      ` <br><br>Письмо отправлено автоматически: адрес указан в форме на `
      + `<a href="${esc(withEmailUtm(site.url, 'footer', UTM_CAMPAIGN))}" `
      + `style="color:${MUTED}">${esc(site.domain)}</a> `
      + `${esc(lead.date)}. Если обращение оставляли не Вы — ответьте на это письмо, `
      + `и мы удалим данные. ${esc(seller.legalName)}, ИНН ${esc(seller.inn)}.`)
    + closeLetter();

  // Текстовая версия — то же содержимое без вёрстки: часть клиентов
  // показывает именно её, и потерять в ней предмет обращения нельзя.
  const text = [
    salutation(lead.name),
    '',
    intro,
    ...(details ? [
      '',
      'ВАШЕ ОБРАЩЕНИЕ',
      ...(req.vendor ? [`Производитель: ${req.vendor}`] : []),
      ...(product ? [`Продукт: ${product}`] : []),
      ...(req.plan ? [`Тип лицензии: ${PLAN_WORD[req.plan]}`] : []),
      ...(qty ? [`Количество: ${qty}`] : []),
      ...(lead.message ? ['Текст сообщения:', lead.message] : []),
      'Заметили неточность — ответьте на это письмо, поправим до расчёта.',
    ] : []),
    '',
    'ЧТО ДАЛЬШЕ',
    '— Дополнить обращение: ответным письмом',
    `— Образец договора: ${site.url}${offerDocs.contract.path}`,
    ...(interest ? [
      '',
      'ВАС МОЖЕТ ЗАИНТЕРЕСОВАТЬ',
      ...(links.product ? [`— ${links.product.name}: ${links.product.url}`] : []),
      ...(links.alternative ? [`— ${links.alternative.name}: ${links.alternative.url}`] : []),
      ...(links.catalog ? [`— ${links.catalog.name}: ${links.catalog.url}`] : []),
    ] : []),
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
