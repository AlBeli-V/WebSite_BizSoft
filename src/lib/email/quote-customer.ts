/**
 * Письмо клиенту с коммерческим предложением.
 *
 * Не техническая нотификация, а первый ход продажи: за минуту читатель
 * должен увидеть, от кого письмо, по какому предложению, на какую сумму, до
 * какого числа оно действует, где сам документ и что он может попросить
 * дальше.
 *
 * Вложение одно — PDF, собранный из листов-картинок (`offer-doc.ts`).
 * Картинку нельзя открыть в редакторе, подменить сумму и выдать за наш
 * документ, а PDF из таких листов сохраняет это свойство и при этом
 * листается одним файлом (решение руководителя 15.09.2026; до него клиенту
 * уходило по файлу на лист).
 *
 * Вёрстка табличная и только с инлайновыми стилями: `<form>`, `<input>`,
 * скрипты, iframe, флексы, гриды и внешние шрифты почтовые клиенты вырезают
 * или рисуют по-своему. Поэтому настоящий выбор действий живёт на странице
 * предложения, а в письме — перечень и кнопки, открывающие либо эту
 * страницу, либо готовое письмо менеджеру.
 */
import { edo, offerDocs, offerManager, seller, site, taxation } from '../../config/site';
import { salutation } from '../salutation';
import { pluralForm } from '../rub-words';
import { PRELIMINARY_NOTE, type QuoteData } from '../quote-layout';
import { OFFER_ACTIONS } from '../offer-actions';
import { actionsMailto, edoAccountingMailto, finalQuoteMailto, invoiceMailto } from '../mailto';
import { fileSizeRu } from '../offer-doc';
import { withEmailUtm, type OfferCategoryLink, type OfferProductLink } from '../offer-content';
import { escapeHtml } from './layout';
import { resolveAsset } from '../pdf-quote';

export interface RenderedEmail {
  subject: string;
  html: string;
  text: string;
}

export interface OfferEmailInput {
  data: QuoteData;
  /** Имя и вес вложенного PDF: получатель ищет файл по имени, а не по счёту. */
  pdfName: string;
  pdfSize: number;
  /** Страница предложения с токеном; пусто — блок выбора действий уходит в письмо. */
  offerUrl?: string;
  products?: OfferProductLink[];
  categories?: OfferCategoryLink[];
}

// ── Палитра и типографика письма ──────────────────────────────────────────
// Своих значений письмо не заводит: те же цвета, что у сайта и документа.
const INK = '#14161A';
const BODY = '#3B3F47';
const MUTED = '#6E7480';
const ORANGE = '#FF763C';
const RULE = '#E5E7EB';
const SOFT = '#F7F8FA';
const PAPER = '#FFFFFF';
/** Системные шрифты: внешние в письме не грузятся, а подмена ломает ритм. */
const FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif";
const WIDTH = 640;

const esc = escapeHtml;

/**
 * Есть ли на диске фотография менеджера.
 *
 * Без проверки письмо ссылалось бы на несуществующий файл, и получатель
 * видел бы битую картинку — хуже, чем аккуратные инициалы. Проверка
 * кэшируется: писем много, файл один.
 */
let photoChecked: boolean | null = null;
function hasManagerPhoto(): boolean {
  if (!offerManager.photo) return false;
  if (photoChecked === null) {
    try {
      resolveAsset(`public/${offerManager.photo}`);
      photoChecked = true;
    } catch {
      photoChecked = false;
    }
  }
  return photoChecked;
}

/** Ячейка текста: размер и цвет письма по умолчанию. */
function textStyle(extra = ''): string {
  return `font-family:${FONT};font-size:15px;line-height:23px;color:${BODY};${extra}`;
}

/** Подпись раздела прописными — единственный декоративный приём письма. */
function sectionLabel(text: string): string {
  return `<div style="font-family:${FONT};font-size:11px;letter-spacing:.1em;`
    + `text-transform:uppercase;color:${MUTED};padding-bottom:8px">${esc(text)}</div>`;
}

/**
 * Кнопка на таблице, а не на `<a>` с паддингами: Word-движок Outlook
 * паддинги ссылки игнорирует, и кнопка превращается в строчку текста.
 */
function button(label: string, href: string, opts: { primary?: boolean } = {}): string {
  const bg = opts.primary ? ORANGE : PAPER;
  const color = opts.primary ? '#FFFFFF' : INK;
  const border = opts.primary ? ORANGE : RULE;
  return `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" `
    + `style="border-collapse:separate"><tr>`
    + `<td align="center" bgcolor="${bg}" style="border-radius:10px;border:1px solid ${border}">`
    + `<a href="${href}" style="display:block;padding:15px 20px;font-family:${FONT};font-size:15px;`
    + `font-weight:700;line-height:20px;color:${color};text-decoration:none;letter-spacing:.02em">`
    + `${esc(label)}</a></td></tr></table>`;
}

/**
 * Ячейка сводки: подпись, значение, пояснение.
 *
 * Длинное значение (номер КП) набирается мельче: в колонке шириной в
 * четверть письма семнадцатый кегль рвёт номер пополам, и читатель видит
 * «BZ-20260915-» и «29343» на разных строках.
 */
function kpiCell(label: string, value: string, hint = ''): string {
  const size = value.length > 12 ? 15 : 17;
  return `<td class="kcell" width="25%" valign="top" style="padding:14px 16px;font-family:${FONT}">`
    + `<div style="font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:${MUTED}">${esc(label)}</div>`
    + `<div style="font-size:${size}px;font-weight:700;color:${INK};padding-top:4px;white-space:nowrap">${esc(value)}</div>`
    + (hint ? `<div style="font-size:12px;color:${MUTED};padding-top:2px">${esc(hint)}</div>` : '')
    + `</td>`;
}

function section(inner: string, topPad = 32): string {
  return `<tr><td style="padding:${topPad}px 32px 0">${inner}</td></tr>`;
}

export function buildCustomerQuoteEmail(input: OfferEmailInput): RenderedEmail {
  const { data, pdfName, pdfSize, offerUrl } = input;
  const products = input.products?.slice(0, 3) ?? [];
  const categories = input.categories?.slice(0, 3) ?? [];
  const total = data.total.toLocaleString('ru-RU');
  const subject = `Коммерческое предложение № ${data.quoteNo} — BIZSoft`;
  const company = data.buyerCompany || 'вашей организации';
  const mailCtx = {
    to: offerManager.email,
    managerName: offerManager.name.split(' ')[0] || offerManager.name,
    quoteNo: data.quoteNo,
    buyerCompany: company,
  };
  const finalHref = finalQuoteMailto(mailCtx);
  const invoiceHref = invoiceMailto(mailCtx);
  const actionsHref = actionsMailto(mailCtx, OFFER_ACTIONS.map((a) => a.label));
  const edoHref = edoAccountingMailto({
    legalName: seller.legalName,
    inn: seller.inn,
    participantId: edo.participantId,
    provider: edo.provider,
    howTo: edo.howTo,
  });
  const docsHref = withEmailUtm(`${site.url}${offerDocs.contract.path}`, 'documents');

  const checklist = OFFER_ACTIONS.map((a) =>
    `<tr><td width="26" valign="top" style="padding:5px 0;font-family:${FONT};font-size:15px;color:${MUTED}">&#9744;</td>`
    + `<td style="padding:5px 0;${textStyle('font-size:14px')}">${esc(a.label)}</td></tr>`).join('');

  const productRows = products.map((p) =>
    `<tr><td style="padding:12px 0;border-bottom:1px solid ${RULE};${textStyle()}">`
    + (p.vendor ? `<div style="font-weight:700;color:${INK};font-size:14px">${esc(p.vendor)}</div>` : '')
    + `<div style="font-size:14px;color:${BODY};padding-top:1px">${esc(p.name)}</div>`
    + `<a href="${esc(p.url)}" style="font-size:13px;color:${ORANGE};text-decoration:none;font-weight:600">`
    + `Подробнее о ${esc(p.name)} &rarr;</a></td></tr>`).join('');

  const categoryLinks = categories.map((c) =>
    `<a href="${esc(c.url)}" style="display:inline-block;margin:0 14px 8px 0;font-family:${FONT};`
    + `font-size:13.5px;color:${INK};text-decoration:none;border-bottom:1px solid ${ORANGE}">`
    + `${esc(c.label)} &rarr;</a>`).join('');

  const html = `<!doctype html><html lang="ru"><head>`
    + `<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">`
    + `<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light">`
    + `<title>${esc(subject)}</title>`
    // Медиазапрос — единственное, что не инлайнится: на телефоне сводка
    // должна встать в два ряда, а кнопки — во всю ширину.
    + `<style>body{margin:0;padding:0;background:${SOFT};-webkit-text-size-adjust:100%}`
    + `img{border:0;display:block;max-width:100%;height:auto}`
    + `@media only screen and (max-width:600px){`
    + `.wrap{width:100%!important}.pad{padding-left:20px!important;padding-right:20px!important}`
    + `.kcell{display:inline-block!important;width:50%!important;box-sizing:border-box!important}`
    + `.half{display:block!important;width:100%!important}.gap{height:10px!important;line-height:10px!important}`
    + `.h1{font-size:26px!important}.hero{display:none!important}}</style></head>`
    + `<body style="margin:0;padding:0;background:${SOFT}">`
    // Превью в списке писем: иначе клиент показывает начало разметки.
    + `<div style="display:none;font-size:1px;color:${SOFT};max-height:0;overflow:hidden">`
    + `КП № ${esc(data.quoteNo)} на ${esc(total)} ₽ — документ во вложении.</div>`
    + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="${SOFT}">`
    + `<tr><td align="center" style="padding:24px 0">`
    + `<table role="presentation" class="wrap" width="${WIDTH}" cellpadding="0" cellspacing="0" border="0" `
    + `bgcolor="${PAPER}" style="width:${WIDTH}px;max-width:100%;background:${PAPER}">`

    // ── Шапка ──
    + `<tr><td class="pad" style="padding:32px 32px 0">`
    + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>`
    + `<td valign="middle" style="font-family:${FONT}">`
    + `<div style="font-size:22px;font-weight:700;color:${INK};letter-spacing:-.01em">BIZ<span style="color:${ORANGE}">Soft</span></div>`
    + `<div style="font-size:11.5px;color:${MUTED};padding-top:3px">${esc(site.tagline)}</div></td>`
    + `<td align="right" valign="middle" class="hero" style="font-family:${FONT};font-size:11px;`
    + `letter-spacing:.08em;text-transform:uppercase;color:${MUTED};border-left:2px solid ${ORANGE};padding-left:14px">`
    + `Надёжные решения<br>для вашего бизнеса</td></tr></table></td></tr>`

    // ── Заголовок и обращение ──
    + section(`<div style="width:38px;height:3px;background:${ORANGE};margin-bottom:16px"></div>`
      + `<div class="h1" style="font-family:${FONT};font-size:34px;line-height:1.16;font-weight:700;color:${INK}">`
      + `Коммерческое<br>предложение</div>`
      + `<div style="font-family:${FONT};font-size:19px;color:${MUTED};padding-top:6px">для ${esc(company)}</div>`, 30)
    + section(`<div style="${textStyle()}"><b style="color:${INK}">${esc(salutation(data.contactName))}</b><br><br>`
      + `Благодарим за интерес к решениям BIZSoft. Во вложении направляем подготовленное `
      + `коммерческое предложение по выбранным вами продуктам. Будем рады ответить на вопросы `
      + `и помочь с дальнейшими шагами.</div>`, 24)

    // ── Сводка ──
    + section(`<table role="presentation" class="kpi" width="100%" cellpadding="0" cellspacing="0" border="0" `
      + `bgcolor="${SOFT}" style="background:${SOFT};border:1px solid ${RULE};border-radius:10px"><tr>`
      + kpiCell('Номер КП', data.quoteNo)
      + kpiCell('Сумма', `${total} ₽`, `в т.ч. НДС ${taxation.vatPercent}%`)
      + kpiCell('Позиций', String(data.items.length), 'наименований')
      + kpiCell('Действует до', data.validUntil, 'включительно')
      + `</tr></table>`, 26)

    // ── Вложение ──
    // Кнопки «скачать» здесь нет намеренно: файл уже в письме, и кнопка
    // обещала бы действие, которого не существует.
    + section(`<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>`
      + `<td width="34" valign="top" style="font-family:${FONT};font-size:20px;line-height:22px;color:${ORANGE}">&#128196;</td>`
      + `<td style="${textStyle('font-size:14px')}">Коммерческое предложение приложено к письму<br>`
      + `<span style="color:${MUTED};font-size:12.5px"><span style="word-break:break-all">${esc(pdfName)}</span>`
      + ` &middot; PDF &middot; ${esc(fileSizeRu(pdfSize)).replace(' ', '&nbsp;')}</span>`
      + `</td></tr></table>`, 18)

    // ── Призывы ──
    + section(button('ЗАПРОСИТЬ ФИНАЛЬНОЕ КП', finalHref, { primary: true })
      + `<div style="font-family:${FONT};font-size:12.5px;color:${MUTED};padding-top:8px;text-align:center">`
      + `Без водяных знаков, после согласования условий</div>`, 26)
    + section(`<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>`
      + `<td class="half" width="49%">${button('ЗАПРОСИТЬ СЧЁТ ПО КП', invoiceHref)}</td>`
      + `<td class="gap" width="2%">&nbsp;</td>`
      + `<td class="half" width="49%">${button('ВЫБРАТЬ НУЖНЫЕ ДЕЙСТВИЯ', offerUrl || actionsHref)}</td>`
      + `</tr></table>`, 12)

    // ── Следующий шаг ──
    + section(sectionLabel('Что мы можем подготовить для вас')
      + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">${checklist}</table>`
      + `<div style="font-family:${FONT};font-size:13px;color:${MUTED};padding-top:12px">`
      + (offerUrl
        ? `Отметить нужное можно <a href="${esc(offerUrl)}" style="color:${ORANGE};font-weight:600">на странице предложения</a> `
          + `или <a href="${actionsHref}" style="color:${INK}">ответить письмом</a>.`
        : `Отметьте нужное <a href="${actionsHref}" style="color:${ORANGE};font-weight:600">ответным письмом</a>.`)
      + `</div>`)

    // ── Документы ──
    + section(sectionLabel('Типовые документы')
      + `<div style="${textStyle('font-size:13.5px')};padding-bottom:8px">`
      + `Если хотите заранее ознакомиться с условиями сотрудничества.</div>`
      + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>`
      + `<td style="padding:11px 0;border-top:1px solid ${RULE};border-bottom:1px solid ${RULE};${textStyle('font-size:14px')}">`
      + `<a href="${esc(docsHref)}" style="color:${INK};text-decoration:none;font-weight:600">${esc(offerDocs.contract.title)}</a>`
      + `<span style="color:${MUTED};font-size:12.5px"> &middot; ${esc(offerDocs.contract.format)}</span>`
      + `</td></tr></table>`)

    // ── ЭДО ──
    // Значения текстом, а не картинкой: их выделяют и копируют, и при
    // отключённых изображениях блок обязан остаться рабочим.
    + section(sectionLabel('Электронный документооборот')
      + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="${SOFT}" `
      + `style="background:${SOFT};border:1px solid ${RULE};border-radius:10px"><tr>`
      + `<td style="padding:14px 16px;${textStyle('font-size:13.5px')}">`
      + `Обмениваемся документами через ${esc(edo.provider)}. Данные для добавления нас в контрагенты:<br><br>`
      + `<span style="color:${MUTED}">Организация:</span> ${esc(seller.legalName)}<br>`
      + `<span style="color:${MUTED}">ИНН:</span> <b style="color:${INK}">${esc(seller.inn)}</b><br>`
      + `<span style="color:${MUTED}">Идентификатор участника ЭДО:</span><br>`
      + `<b style="color:${INK};font-size:12.5px;word-break:break-all">${esc(edo.participantId)}</b><br><br>`
      + `<span style="color:${MUTED};font-size:12.5px">В Диадоке: ${esc(edo.howTo)}. `
      + `Поиск по идентификатору надёжнее поиска по названию.</span><br><br>`
      + `<a href="${edoHref}" style="color:${ORANGE};font-weight:600;text-decoration:none">Передать данные бухгалтерии &rarr;</a>`
      + (offerUrl
        ? `<br><span style="color:${MUTED};font-size:12.5px">Или отметьте «Отправить приглашение в Контур.Диадок» `
          + `<a href="${esc(offerUrl)}" style="color:${MUTED}">на странице предложения</a> — пригласим первыми.</span>`
        : '')
      + `</td></tr></table>`)

    // ── Товары ──
    + (products.length ? section(sectionLabel('Товары из вашего предложения')
      + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">${productRows}</table>`
      + (offerUrl && data.items.length > products.length
        ? `<div style="padding-top:12px"><a href="${esc(offerUrl)}" style="font-family:${FONT};font-size:13.5px;`
          + `color:${ORANGE};font-weight:600;text-decoration:none">Показать все ${data.items.length} `
          + `${pluralForm(data.items.length, ['позицию', 'позиции', 'позиций'])} &rarr;</a></div>`
        : '')
      + (categoryLinks ? `<div style="padding-top:16px">${categoryLinks}</div>` : '')) : '')

    // ── Менеджер ──
    + section(`<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" `
      + `style="border-top:1px solid ${RULE}"><tr><td style="padding-top:20px">`
      + `<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>`
      + `<td width="68" valign="top">`
      + (hasManagerPhoto()
        ? `<img src="${site.url}/${offerManager.photo}" width="56" height="56" alt="${esc(offerManager.name)}" `
          + `style="display:block;width:56px;height:56px;border-radius:28px;background:${SOFT}">`
        : `<div style="width:56px;height:56px;border-radius:28px;background:${SOFT};border:1px solid ${RULE};`
          + `font-family:${FONT};font-size:17px;font-weight:700;color:${MUTED};text-align:center;line-height:56px">`
          + `${esc(offerManager.initials)}</div>`)
      + `</td><td valign="top" style="${textStyle('font-size:14px')}">`
      + `<div style="color:${MUTED};font-size:12.5px">С уважением,</div>`
      + `<div style="font-weight:700;color:${INK};font-size:15px;padding-top:2px">${esc(offerManager.name)}</div>`
      + `<div style="color:${MUTED};font-size:13px">${esc(offerManager.role)}</div>`
      + `<div style="padding-top:8px;font-size:13.5px">`
      + `<a href="tel:${esc(offerManager.phoneHref)}" style="color:${INK};text-decoration:none">${esc(offerManager.phone)}</a><br>`
      + `<a href="mailto:${esc(offerManager.email)}" style="color:${INK};text-decoration:none">${esc(offerManager.email)}</a><br>`
      + `<a href="${esc(offerManager.telegram)}" style="color:${INK};text-decoration:none">Написать в Telegram</a>`
      + `</div></td></tr></table></td></tr></table>`)

    // ── Подвал ──
    + `<tr><td class="pad" style="padding:30px 32px 32px">`
    + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="${SOFT}" `
    + `style="background:${SOFT};border-radius:10px"><tr><td style="padding:18px 18px 16px;font-family:${FONT}">`
    + `<div style="font-size:16px;font-weight:700;color:${INK}">BIZ<span style="color:${ORANGE}">Soft</span></div>`
    + `<div style="font-size:12px;color:${MUTED};padding-top:2px">${esc(site.tagline)} &middot; ${esc(site.domain)}</div>`
    + `<div style="padding-top:12px;font-size:12.5px">`
    + [['Программное обеспечение', '/catalog'], ['AI-сервисы', '/catalog/ai'],
       ['Облачные решения', '/solutions'], ['ИТ-инфраструктура', '/catalog/it']]
      .map(([label, path]) => `<a href="${withEmailUtm(site.url + path, 'footer')}" `
        + `style="color:${BODY};text-decoration:none;margin-right:14px;display:inline-block;padding-bottom:4px">${esc(label)}</a>`)
      .join('')
    + `</div>`
    + `<div style="padding-top:14px;font-size:11.5px;line-height:17px;color:${MUTED}">${esc(PRELIMINARY_NOTE)}</div>`
    + `<div style="padding-top:10px;font-size:11.5px;line-height:17px;color:${MUTED}">`
    + `<b style="color:${BODY}">Конфиденциально.</b> Информация предназначена только для адресата.</div>`
    + `</td></tr></table></td></tr>`

    + `</table></td></tr></table></body></html>`;

  // Текстовая версия — то же содержимое без вёрстки: часть клиентов
  // показывает именно её, и потерять в ней номер или сумму нельзя.
  const text = [
    salutation(data.contactName),
    '',
    `Коммерческое предложение № ${data.quoteNo} для ${company} — во вложении (${pdfName}).`,
    `Сумма: ${total} ₽, в т.ч. НДС ${taxation.vatPercent}%. Позиций: ${data.items.length}. `
      + `Действует до ${data.validUntil}.`,
    '',
    'Что можно попросить подготовить:',
    ...OFFER_ACTIONS.map((a) => `— ${a.label}`),
    offerUrl ? `Отметить нужное: ${offerUrl}` : '',
    '',
    `Типовые документы: ${site.url}${offerDocs.contract.path}`,
    '',
    `ЭДО (${edo.provider}): ${seller.legalName}, ИНН ${seller.inn},`,
    `идентификатор участника ЭДО ${edo.participantId}.`,
    '',
    PRELIMINARY_NOTE,
    '',
    `${offerManager.name}, ${offerManager.role}`,
    `${offerManager.phone} · ${offerManager.email} · ${site.url}`,
  ].filter((l) => l !== '').join('\n');

  return { subject, html, text };
}
