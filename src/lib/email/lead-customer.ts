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
  MUTED, openLetter, ORANGE, RULE, section, sectionHead, signature, stepRow,
  type RenderedEmail,
} from './client-shell';

/** Метка кампании в ссылках письма: переходы отсюда видны отдельно от КП. */
const UTM_CAMPAIGN = 'lead_confirmation';

/** Подложка прямой речи: тёплый тон фирменной пары, а не серый по умолчанию. */
const QUOTE_BG = '#FFF7F3';

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
  /**
   * В обращении есть прямой вопрос. Письмо тогда говорит, что ответит
   * человек: фирменное подтверждение приходит через секунды после отправки
   * и без этой строки читается как ответ, которым оно не является.
   */
  hasQuestion?: boolean;
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
    /**
     * Подтверждённые позиции подборки. Одна — строки «Продукт» и
     * «Количество» идут раздельно; несколько — письмо называет их
     * перечислением, и сводить заявку к первой нельзя.
     */
    items?: { name: string; plan?: LeadPlan; qty?: string }[];
    /** Страницы каталога, названные в письме. */
    links?: {
      /** Страницы подтверждённых позиций. */
      products?: LeadLink[];
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

/**
 * Строка предмета обращения: подпись мелким капсом слева, значение крупно
 * справа. Капс и разрядка — тот же приём, что у заголовков разделов: строки
 * читаются как позиции спецификации, а не как переписка.
 */
function row(key: string, valueHtml: string): string {
  return `<tr>`
    + `<td width="150" valign="top" style="font-family:${FONT};font-size:11px;line-height:20px;`
    + `letter-spacing:.08em;text-transform:uppercase;color:${MUTED};padding:11px 14px 11px 0">`
    + `${esc(key)}</td>`
    + `<td valign="top" style="font-family:${FONT};font-size:15px;line-height:20px;`
    + `color:${INK};padding:10px 0">${valueHtml}</td>`
    + `</tr>`;
}

/**
 * Сообщение клиента — прямой речью.
 *
 * Не строка таблицы, а отдельный блок: это единственное место письма, где
 * говорит сам заказчик, и оно должно читаться его голосом. Кавычка-ёлочка
 * набрана текстом крупно и акцентом, текст — курсивом на светлой подложке с
 * акцентной полосой. Картинок здесь нет намеренно: кавычка обязана
 * нарисоваться и при выключенной загрузке изображений.
 *
 * Текст пришёл из публичной формы, поэтому экранируется целиком, и только
 * потом в него подставляются `<br>` — иначе разметка из поля «сообщение»
 * доехала бы до почтового клиента получателя как разметка.
 */
function speech(text: string): string {
  return `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" `
    + `style="background:${QUOTE_BG};border-left:3px solid ${ORANGE}">`
    + `<tr>`
    + `<td width="34" valign="top" style="font-family:Georgia,'Times New Roman',serif;`
    + `font-size:34px;line-height:34px;color:${ORANGE};padding:14px 0 0 14px">&#171;</td>`
    + `<td valign="top" style="font-family:${FONT};font-size:14.5px;line-height:23px;`
    + `color:${BODY};font-style:italic;padding:16px 18px 16px 4px">`
    + esc(clampMessage(text)).replace(/\r?\n/g, '<br>')
    + `<span style="font-family:Georgia,'Times New Roman',serif;font-style:normal;`
    + `color:${ORANGE}">&#187;</span></td>`
    + `</tr></table>`;
}

/**
 * Предел цитаты. Поле сообщения принимает до 4 000 знаков, и такое письмо
 * растянулось бы на несколько экранов: цитата нужна для сверки, а полный
 * текст у человека и так есть — он его писал. Обрыв делается по границе
 * слова, чтобы цитата не заканчивалась половиной слова.
 */
export const MESSAGE_LIMIT = 1200;

export function clampMessage(text: string): string {
  if (text.length <= MESSAGE_LIMIT) return text;
  const cut = text.slice(0, MESSAGE_LIMIT);
  const stop = Math.max(cut.lastIndexOf(' '), cut.lastIndexOf('\n'));
  return `${cut.slice(0, stop > MESSAGE_LIMIT - 120 ? stop : MESSAGE_LIMIT).trimEnd()}…`;
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
  // Подборка из нескольких строк называется перечислением: каждая позиция
  // своей строкой, под ней — тип лицензии и количество. Сводить такую заявку
  // к одной позиции значило бы потерять остальные.
  const many = (req.items?.length ?? 0) > 1;
  const listHtml = many ? req.items!.map((i) =>
    `<div style="padding:2px 0 8px">`
    + `<b>${esc(i.name)}</b>`
    + (i.plan || i.qty
      ? `<br><span style="color:${MUTED};font-size:13px">`
        + [i.plan ? PLAN_WORD[i.plan] : '', i.qty ? `${i.qty} шт.` : '']
          .filter(Boolean).map(esc).join(' · ')
        + `</span>`
      : '')
    + `</div>`).join('') : '';

  const details = [
    ...(req.vendor && !many ? [row('Производитель', `<b>${esc(req.vendor)}</b>`)] : []),
    ...(many
      ? [row('Позиции', listHtml)]
      : [
        ...(product ? [row('Продукт', `<b>${esc(product)}</b>`)] : []),
        ...(req.plan ? [row('Тип лицензии', esc(PLAN_WORD[req.plan]))] : []),
        ...(qty ? [row('Количество', esc(qty))] : []),
      ]),
  ].join('');

  // Подборка по теме запроса. Показывается только тем, чью позицию мы
  // опознали: три строки-заглушки «посмотрите каталог» у человека, который
  // уже назвал продукт, — это шум, а не помощь.
  const marker = (n: number) => String(n).padStart(2, '0');
  const interest = [
    ...(links.products || []).map((l, i) => stepRow(marker(i + 1), l.name, link(l, 'product'))),
    ...(links.alternative
      ? [stepRow(marker((links.products?.length || 0) + 1), links.alternative.name,
        link(links.alternative, 'alternative'))] : []),
    ...(links.catalog
      ? [stepRow(marker((links.products?.length || 0) + (links.alternative ? 1 : 0) + 1),
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
    + (details || lead.message ? section(sectionHead('Ваше обращение')
      + (details
        ? `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" `
          + `style="border-top:1px solid ${RULE};border-bottom:1px solid ${RULE}">`
          + details
          + `</table>`
        : '')
      + (lead.message
        ? `<div style="font-family:${FONT};font-size:11px;line-height:18px;letter-spacing:.08em;`
          + `text-transform:uppercase;color:${MUTED};padding:18px 0 8px">Дословно из обращения</div>`
          + speech(lead.message)
        : '')
      + `<div style="font-family:${FONT};font-size:12.5px;line-height:18px;color:${MUTED};`
      + `padding-top:14px">`
      + `Заметили неточность — ответьте на это письмо, поправим до расчёта.</div>`) : '')

    // ── Вопрос в обращении ──
    + (input.hasQuestion ? section(
      `<div style="font-family:${FONT};font-size:14px;line-height:21px;color:${BODY};`
      + `border-left:3px solid ${ORANGE};padding:10px 0 10px 14px">`
      + `<b style="color:${INK}">На вопрос из обращения ответит менеджер</b> — отдельным `
      + `письмом. Это подтверждение отправлено автоматически и ответом не является.</div>`, 26) : '')

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
    ...(input.hasQuestion ? ['',
      'На вопрос из обращения ответит менеджер — отдельным письмом. '
        + 'Это подтверждение отправлено автоматически и ответом не является.'] : []),
    ...(details || lead.message ? [
      '',
      'ВАШЕ ОБРАЩЕНИЕ',
      ...(req.vendor && !many ? [`Производитель: ${req.vendor}`] : []),
      ...(many
        ? ['Позиции:', ...req.items!.map((i) => `  ${i.name}`
          + (i.plan || i.qty
            ? ` (${[i.plan ? PLAN_WORD[i.plan] : '', i.qty ? `${i.qty} шт.` : '']
              .filter(Boolean).join(', ')})`
            : ''))]
        : [
          ...(product ? [`Продукт: ${product}`] : []),
          ...(req.plan ? [`Тип лицензии: ${PLAN_WORD[req.plan]}`] : []),
          ...(qty ? [`Количество: ${qty}`] : []),
        ]),
      ...(lead.message ? ['Дословно из обращения:', `«${clampMessage(lead.message)}»`] : []),
      'Заметили неточность — ответьте на это письмо, поправим до расчёта.',
    ] : []),
    '',
    'ЧТО ДАЛЬШЕ',
    '— Дополнить обращение: ответным письмом',
    `— Образец договора: ${site.url}${offerDocs.contract.path}`,
    ...(interest ? [
      '',
      'ВАС МОЖЕТ ЗАИНТЕРЕСОВАТЬ',
      ...(links.products || []).map((l) => `— ${l.name}: ${l.url}`),
      ...(links.alternative ? [`— ${links.alternative.name}: ${links.alternative.url}`] : []),
      ...(links.catalog ? [`— ${links.catalog.name}: ${links.catalog.url}`] : []),
    ] : []),
    '',
    offerManager.name,
    `${offerManager.phone} · ${offerManager.signatureEmail} · ${site.url}`,
    '',
    'Письмо отправлено автоматически: адрес указан в форме на '
      + `${site.domain} ${lead.date}. Если обращение оставляли не Вы — ответьте на это `
      + `письмо, и мы удалим данные. ${seller.legalName}, ИНН ${seller.inn}.`,
  ].join('\n');

  return { subject, html, text };
}
