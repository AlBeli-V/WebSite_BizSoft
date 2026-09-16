/**
 * Письмо клиенту с коммерческим предложением.
 *
 * Не техническая нотификация, а первый ход продажи: за минуту читатель
 * должен увидеть, от кого письмо, по какому поводу, что он может попросить
 * дальше и куда вернуться на сайт.
 *
 * Вложение одно — PDF, собранный из листов-картинок (`offer-doc.ts`).
 * Картинку нельзя открыть в редакторе, подменить сумму и выдать за наш
 * документ, а PDF из таких листов сохраняет это свойство и при этом
 * листается одним файлом.
 *
 * Композиция утверждена руководителем 15.09.2026 (редакция 9, девять кругов
 * правок по референсам). Смысл правок: письмо перестало быть витриной с
 * плитками, сводкой и кнопками и стало письмом — шапка-баннер, обращение,
 * два списка со стрелками, подпись. Сумма, срок и перечень позиций живут в
 * документе; дублировать их в письме руководитель запретил, чтобы письмо не
 * читалось как второй экземпляр КП.
 *
 * Вёрстка табличная и только с инлайновыми стилями: `<form>`, `<input>`,
 * скрипты, iframe, флексы, гриды и внешние шрифты почтовые клиенты вырезают
 * или рисуют по-своему. Поэтому действие — это четыре строки, каждая
 * открывает готовое письмо с набранными темой и текстом либо отдаёт файл.
 * Страницы предложения с чекбоксами больше нет (решение руководителя
 * 15.09.2026): один путь ответа вместо двух, и клиенту не нужно уходить с
 * почты, чтобы сказать, чего он хочет.
 */
import { edo, offerDocs, offerManager, seller, site } from '../../config/site';
import { salutation } from '../salutation';
import { type QuoteData } from '../quote-layout';
import { contractMailto, edoAccountingMailto, invoiceMailto } from '../mailto';
import { withEmailUtm, type OfferVendorGroup } from '../offer-content';
import { escapeHtml } from './layout';
import { resolveAsset } from '../pdf-quote';

export interface RenderedEmail {
  subject: string;
  html: string;
  text: string;
}

export interface OfferEmailInput {
  data: QuoteData;
  /** Имя вложенного PDF: получатель ищет файл по имени, а не по счёту. */
  pdfName: string;
  pdfSize: number;
  /** Состав по производителям: марка, её раздел, её позиции. */
  vendors?: OfferVendorGroup[];
}

// ── Палитра и типографика письма ──────────────────────────────────────────
// Своих значений письмо не заводит: те же цвета, что у сайта и документа.
const INK = '#14161A';
const BODY = '#3B3F47';
const MUTED = '#6E7480';
const ORANGE = '#FF763C';
const RULE = '#E5E7EB';
const SOFT = '#F5F6F8';
const PAPER = '#FFFFFF';
/** Системные шрифты: внешние в письме не грузятся, а подмена ломает ритм. */
const FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif";
const WIDTH = 640;

/** Шапка-баннер: своя картинка под ширину экрана (scripts/brand/build-email-banner.mjs). */
const BANNER_DESK = 'email/banner-desk.jpg';
const BANNER_MOB = 'email/banner-mob.jpg';
const BANNER_ALT = 'BIZSoft — единая точка доступа к ПО и AI-сервисам';

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

/** Заголовок раздела: оранжевый слэш, прописные, жирный. */
function sectionHead(text: string): string {
  return `<div style="font-family:${FONT};font-size:12px;line-height:18px;letter-spacing:.14em;`
    + `text-transform:uppercase;font-weight:700;color:${INK};padding-bottom:16px">`
    + `<span style="color:${ORANGE}">/</span> ${esc(text)}</div>`;
}

/** Строка «Следующего шага»: маркер со сдвигом, подпись, жирная стрелка. */
function stepRow(marker: string, label: string, href: string, glyph = '&#8594;'): string {
  return `<tr><td style="border-top:1px solid ${RULE};padding:16px 0">`
    + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>`
    + `<td width="62" valign="middle" style="font-family:${FONT};font-size:13px;line-height:1.4;`
    + `color:${ORANGE};padding-left:14px">/${esc(marker)}</td>`
    + `<td valign="middle" style="font-family:${FONT};font-size:16px;line-height:1.4;color:${INK}">`
    + `<a href="${esc(href)}" style="color:${INK};text-decoration:none">${esc(label)}</a></td>`
    + `<td align="right" width="26" valign="middle" style="font-family:${FONT};font-size:16px">`
    + `<a href="${esc(href)}" style="color:${ORANGE};text-decoration:none;font-weight:700">${glyph}</a>`
    + `</td></tr></table></td></tr>`;
}

/** Ссылка состава: «Каталог Adobe →» или «Страница Acrobat Pro →». */
function compositionLink(text: string, url: string, strong: boolean): string {
  const size = strong ? 17 : 15;
  const color = strong ? INK : MUTED;
  const body = url
    ? `<a href="${esc(url)}" style="color:${color};text-decoration:none">${esc(text)}</a>`
      + ` <span style="color:${ORANGE};font-weight:700">&#8594;</span>`
    : `<span style="color:${color}">${esc(text)}</span>`;
  return `<div style="${strong ? '' : `padding-top:8px;`}font-size:${size}px;line-height:1.4;`
    + `font-weight:${strong ? 600 : 400}">${body}</div>`;
}

/**
 * Контакт подписи: тонкий значок картинкой и текст-ссылка.
 *
 * Значок именно картинкой: svg почта вырезает, а юникодные ✉ и ☎ каждый
 * клиент рисует своим шрифтом — от чёрного глифа до цветного эмодзи.
 * Не загрузился — остаётся подпись, и строка читается.
 */
function contactRow(icon: string, text: string, href: string): string {
  return `<tr><td style="padding:0"><table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>`
    + `<td width="24" valign="middle">`
    + `<img src="${site.url}/email/${icon}.png" width="17" height="17" alt="" `
    + `style="display:block;width:17px;height:17px"></td>`
    + `<td valign="middle" style="font-family:${FONT};font-size:14px;line-height:18px">`
    + `<a href="${esc(href)}" style="color:${INK};text-decoration:none">${esc(text)}</a>`
    + `</td></tr></table></td></tr>`;
}

function section(inner: string, topPad = 42): string {
  return `<tr><td class="pad" style="padding:${topPad}px 36px 0">${inner}</td></tr>`;
}

export function buildCustomerQuoteEmail(input: OfferEmailInput): RenderedEmail {
  const { data, pdfName } = input;
  const vendors = input.vendors ?? [];
  const subject = `Коммерческое предложение № ${data.quoteNo} — BIZSoft`;
  const company = data.buyerCompany || 'вашей организации';
  const mailCtx = {
    to: offerManager.email,
    managerName: offerManager.name.split(' ')[0] || offerManager.name,
    quoteNo: data.quoteNo,
    buyerCompany: company,
    date: data.date,
    buyerInn: data.buyerInn,
    vendors: vendors.map((v) => v.vendor).filter(Boolean),
  };
  const edoHref = edoAccountingMailto({
    legalName: seller.legalName,
    shortName: seller.shortName,
    inn: seller.inn,
    ogrnip: seller.ogrnip,
    participantId: edo.participantId,
    provider: edo.provider,
    buyerCompany: company,
  });
  const docsHref = withEmailUtm(`${site.url}${offerDocs.contract.path}`, 'documents');

  const steps: string[] = [];
  const next = () => String(steps.length + 1).padStart(2, '0');
  steps.push(stepRow(next(), 'Запросить счёт', invoiceMailto(mailCtx)));
  steps.push(stepRow(next(), 'Запросить договор', contractMailto(mailCtx)));
  steps.push(stepRow(next(), 'Скачать образец договора', docsHref, '&#8595;'));
  steps.push(stepRow(next(), 'Коннект в ЭДО', edoHref));

  const composition = vendors.map((v) =>
    `<tr><td style="border-top:1px solid ${RULE};padding:18px 0;font-family:${FONT}">`
    + (v.vendor ? compositionLink(`Каталог ${v.vendor}`, v.url, true) : '')
    + v.products.map((p) => compositionLink(`Страница ${p.name}`, p.url, false)).join('')
    + `</td></tr>`).join('');

  const html = `<!doctype html><html lang="ru"><head>`
    + `<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">`
    + `<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light">`
    + `<title>${esc(subject)}</title>`
    // Медиазапрос — единственное, что не инлайнится: на телефоне письмо
    // отдаёт свою шапку, поля уже, а кегль заголовка меньше.
    + `<style>body{margin:0;padding:0;background:${SOFT};-webkit-text-size-adjust:100%}`
    + `img{border:0;display:block;max-width:100%;height:auto}`
    + `@media only screen and (max-width:600px){`
    + `.wrap{width:100%!important}.pad{padding-left:22px!important;padding-right:22px!important}`
    + `.b-desk{display:none!important;max-height:0!important;overflow:hidden!important}`
    + `.b-mob{display:block!important;max-height:none!important;overflow:visible!important}`
    + `}</style></head>`
    + `<body style="margin:0;padding:0;background:${SOFT}">`
    // Превью в списке писем: иначе клиент показывает начало разметки.
    + `<div style="display:none;font-size:1px;color:${SOFT};max-height:0;overflow:hidden">`
    + `Коммерческое предложение № ${esc(data.quoteNo)} для ${esc(company)} — документ во вложении.</div>`
    + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="${SOFT}">`
    + `<tr><td align="center" style="padding:24px 0">`
    + `<table role="presentation" class="wrap" width="${WIDTH}" cellpadding="0" cellspacing="0" border="0" `
    + `bgcolor="${PAPER}" style="width:${WIDTH}px;max-width:100%;background:${PAPER}">`

    // ── Шапка-баннер ──
    // Две картинки вместо одной: общая на телефоне ужимается вдвое, и слоган
    // лок-апа падает до 5 px. Телефонная спрятана условным комментарием, а не
    // только классом: Word-движок Outlook `display:none` соблюдает не всегда,
    // и получатель увидел бы обе.
    + `<tr><td class="b-desk" style="padding:0">`
    + `<img src="${site.url}/${BANNER_DESK}" width="${WIDTH}" alt="${esc(BANNER_ALT)}" `
    + `style="display:block;width:100%"></td></tr>`
    + `<!--[if !mso]><!-->`
    + `<tr><td class="b-mob" style="padding:0;display:none;max-height:0;overflow:hidden">`
    + `<img src="${site.url}/${BANNER_MOB}" width="${WIDTH}" alt="${esc(BANNER_ALT)}" `
    + `style="display:block;width:100%"></td></tr>`
    + `<!--<![endif]-->`

    // ── Заголовок ──
    + section(`<div style="width:32px;height:2px;background:${ORANGE};font-size:0;line-height:0">&nbsp;</div>`
      + `<div style="font-family:${FONT};font-size:15px;font-weight:700;letter-spacing:.06em;`
      + `text-transform:uppercase;color:${INK};padding-top:12px">Коммерческое предложение</div>`
      + `<div style="font-family:${FONT};font-size:14px;color:${MUTED};padding-top:3px">`
      + `в интересах ${esc(company)}</div>`, 30)

    // ── Обращение ──
    + section(`<div style="font-family:${FONT};font-size:15px;line-height:24px;color:${BODY}">`
      + `<b style="color:${INK}">${esc(salutation(data.contactName))}</b><br><br>`
      + `Благодарим Вас за обращение. Направляем предварительное коммерческое предложение по `
      + `выбранным вами продуктам. Будем рады помочь с подбором и ответить на возникшие вопросы.`
      + `</div>`, 26)
    + `<tr><td class="pad" align="right" style="padding:14px 36px 0;font-family:${FONT};`
    + `font-size:14px;color:${BODY}"><i>Команда BIZSoft.</i></td></tr>`

    // ── Следующий шаг ──
    + section(sectionHead('Следующий шаг')
      + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">`
      + steps.join('')
      + `<tr><td style="border-top:1px solid ${RULE};font-size:0;line-height:0">&nbsp;</td></tr>`
      + `</table>`)

    // ── Состав предложения ──
    + (composition ? section(sectionHead('Состав предложения')
      + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">`
      + composition
      + `<tr><td style="border-top:1px solid ${RULE};font-size:0;line-height:0">&nbsp;</td></tr>`
      + `</table>`) : '')

    // ── Подпись ──
    + section(`<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>`
      + `<td width="122" valign="top">`
      + (hasManagerPhoto()
        ? `<img src="${site.url}/${offerManager.photo}" width="104" height="104" alt="${esc(offerManager.name)}" `
          + `style="display:block;width:104px;height:104px;border-radius:52px;background:${SOFT}">`
        : `<div style="width:104px;height:104px;border-radius:52px;background:${SOFT};border:1px solid ${RULE};`
          + `font-family:${FONT};font-size:30px;font-weight:700;color:${MUTED};text-align:center;line-height:104px">`
          + `${esc(offerManager.initials)}</div>`)
      + `</td><td valign="top" style="font-family:${FONT}">`
      // Должности в подписи нет (решение руководителя 15.09.2026): клиенту
      // нужно имя и способ связаться, а «менеджер» ничего не добавляет.
      + `<div style="font-weight:700;color:${INK};font-size:16px;line-height:22px;`
      + `padding-bottom:10px">${esc(offerManager.name)}</div>`
      + `<table role="presentation" cellpadding="0" cellspacing="0" border="0">`
      + contactRow('g-mail', offerManager.email, `mailto:${offerManager.email}`)
      + contactRow('g-phone', offerManager.phone, `tel:${offerManager.phoneHref}`)
      + contactRow('g-tg', 'Telegram', offerManager.telegram)
      + contactRow('g-wa', 'WhatsApp', `https://wa.me/${offerManager.phoneHref.replace('+', '')}`)
      + `</table></td></tr></table>`)

    // ── Подвал ──
    + `<tr><td class="pad" style="padding:36px 36px 36px">`
    + `<div style="border-top:1px solid ${RULE};padding-top:14px;font-family:${FONT};`
    + `font-size:11.5px;line-height:17px;color:${MUTED}">`
    + `<b style="color:${BODY}">Конфиденциально.</b> Настоящее сообщение и приложения к нему содержат `
    + `сведения конфиденциального характера и предназначены исключительно указанному адресату. Если вы `
    + `получили письмо по ошибке, просим уведомить отправителя и удалить сообщение: ознакомление, `
    + `использование, копирование и распространение содержащихся в нём сведений третьими лицами `
    + `не допускается.</div></td></tr>`

    + `</table></td></tr></table></body></html>`;

  // Текстовая версия — то же содержимое без вёрстки: часть клиентов
  // показывает именно её, и потерять в ней номер или вложение нельзя.
  const text = [
    salutation(data.contactName),
    '',
    `Благодарим Вас за обращение. Направляем предварительное коммерческое предложение `
      + `№ ${data.quoteNo} в интересах ${company} — документ во вложении (${pdfName}).`,
    '',
    'СЛЕДУЮЩИЙ ШАГ',
    '— Запросить счёт или договор: ответным письмом',
    `— Образец договора: ${site.url}${offerDocs.contract.path}`,
    `— Коннект в ЭДО (${edo.provider}): ${seller.legalName}, ИНН ${seller.inn},`,
    `  идентификатор участника ЭДО ${edo.participantId}`,
    ...(vendors.length ? ['', 'СОСТАВ ПРЕДЛОЖЕНИЯ'] : []),
    ...vendors.flatMap((v) => [
      v.url ? `— Каталог ${v.vendor}: ${v.url}` : `— ${v.vendor}`,
      ...v.products.map((p) => `  · ${p.name}: ${p.url}`),
    ]),
    '',
    'Команда BIZSoft.',
    '',
    offerManager.name,
    `${offerManager.phone} · ${offerManager.email} · ${site.url}`,
    '',
    'Конфиденциально. Настоящее сообщение и приложения к нему содержат сведения '
      + 'конфиденциального характера и предназначены исключительно указанному адресату.',
  ].filter((l) => l !== '').join('\n');

  return { subject, html, text };
}
