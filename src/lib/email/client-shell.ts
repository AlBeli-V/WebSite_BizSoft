/**
 * Общий фирменный слой писем, которые получает заказчик.
 *
 * Писем клиенту у нас два: подтверждение обращения (`lead-customer.ts`) и
 * коммерческое предложение (`quote-customer.ts`). Оба приходят на один
 * адрес, часто подряд, и обязаны читаться как два письма одной компании, а
 * не как две разные рассылки. Поэтому шапка-баннер, заголовок раздела,
 * строка шага, подпись менеджера и оговорка о конфиденциальности живут
 * здесь одним экземпляром, а не копией в каждом шаблоне.
 *
 * Композиция и все значения перенесены из письма с КП без единой правки
 * (редакция 9, одобрена руководителем 15.09.2026): вынос не меняет ни байта
 * в выпускаемом письме — это сторожит `tests/client-shell.test.ts`.
 *
 * Правила вёрстки те же, что у КП: только таблицы и инлайновые стили,
 * без `<form>`, скриптов, iframe, флексов, гридов и внешних шрифтов —
 * почтовые клиенты вырезают их или рисуют по-своему.
 */
import { offerManager, site } from '../../config/site';
import { escapeHtml } from './layout';
import { resolveAsset } from '../pdf-quote';

/** Письмо: HTML и обязательный текстовый двойник. */
export interface RenderedEmail {
  subject: string;
  html: string;
  text: string;
}

// ── Палитра и типографика ─────────────────────────────────────────────────
// Своих значений письма не заводят: те же цвета, что у сайта и документа.
export const INK = '#14161A';
export const BODY = '#3B3F47';
export const MUTED = '#6E7480';
export const ORANGE = '#FF763C';
export const RULE = '#E5E7EB';
export const SOFT = '#F5F6F8';
export const PAPER = '#FFFFFF';
/** Системные шрифты: внешние в письме не грузятся, а подмена ломает ритм. */
export const FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif";
export const WIDTH = 640;

/** Шапка-баннер: своя картинка под ширину экрана (scripts/brand/build-email-banner.mjs). */
const BANNER_DESK = 'email/banner-desk.jpg';
const BANNER_MOB = 'email/banner-mob.jpg';
const BANNER_ALT = 'BIZSoft — единая точка доступа к ПО и AI-сервисам';

export const esc = escapeHtml;

/**
 * Есть ли на диске фотография менеджера.
 *
 * Без проверки письмо ссылалось бы на несуществующий файл, и получатель
 * видел бы битую картинку — хуже, чем аккуратные инициалы. Проверка
 * кэшируется: писем много, файл один.
 */
let photoChecked: boolean | null = null;
export function hasManagerPhoto(): boolean {
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
export function sectionHead(text: string): string {
  return `<div style="font-family:${FONT};font-size:12px;line-height:18px;letter-spacing:.14em;`
    + `text-transform:uppercase;font-weight:700;color:${INK};padding-bottom:16px">`
    + `<span style="color:${ORANGE}">/</span> ${esc(text)}</div>`;
}

/** Строка «Следующего шага»: маркер со сдвигом, подпись, жирная стрелка. */
export function stepRow(marker: string, label: string, href: string, glyph = '&#8594;'): string {
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

/**
 * Контакт подписи: тонкий значок картинкой и текст-ссылка.
 *
 * Значок именно картинкой: svg почта вырезает, а юникодные ✉ и ☎ каждый
 * клиент рисует своим шрифтом — от чёрного глифа до цветного эмодзи.
 * Не загрузился — остаётся подпись, и строка читается.
 */
export function contactRow(icon: string, text: string, href: string): string {
  return `<tr><td style="padding:0"><table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>`
    + `<td width="24" valign="middle">`
    + `<img src="${site.url}/email/${icon}.png" width="17" height="17" alt="" `
    + `style="display:block;width:17px;height:17px"></td>`
    + `<td valign="middle" style="font-family:${FONT};font-size:14px;line-height:18px">`
    + `<a href="${esc(href)}" style="color:${INK};text-decoration:none">${esc(text)}</a>`
    + `</td></tr></table></td></tr>`;
}

/** Полоса письма: единственный способ отбить блок друг от друга. */
export function section(inner: string, topPad = 42): string {
  return `<tr><td class="pad" style="padding:${topPad}px 36px 0">${inner}</td></tr>`;
}

/**
 * Голова документа и открытая таблица-лист.
 *
 * Медиазапрос — единственное, что не инлайнится: на телефоне письмо
 * отдаёт свою шапку, поля уже, а кегль заголовка меньше.
 */
export function openLetter(subject: string, preheader: string): string {
  return `<!doctype html><html lang="ru"><head>`
    + `<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">`
    + `<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light">`
    + `<title>${esc(subject)}</title>`
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
    + `${esc(preheader)}</div>`
    + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="${SOFT}">`
    + `<tr><td align="center" style="padding:24px 0">`
    + `<table role="presentation" class="wrap" width="${WIDTH}" cellpadding="0" cellspacing="0" border="0" `
    + `bgcolor="${PAPER}" style="width:${WIDTH}px;max-width:100%;background:${PAPER}">`;
}

export function closeLetter(): string {
  return `</table></td></tr></table></body></html>`;
}

/**
 * Шапка-баннер.
 *
 * Две картинки вместо одной: общая на телефоне ужимается вдвое, и слоган
 * лок-апа падает до 5 px. Телефонная спрятана условным комментарием, а не
 * только классом: Word-движок Outlook `display:none` соблюдает не всегда,
 * и получатель увидел бы обе.
 */
export function banner(): string {
  return `<tr><td class="b-desk" style="padding:0">`
    + `<img src="${site.url}/${BANNER_DESK}" width="${WIDTH}" alt="${esc(BANNER_ALT)}" `
    + `style="display:block;width:100%"></td></tr>`
    + `<!--[if !mso]><!-->`
    + `<tr><td class="b-mob" style="padding:0;display:none;max-height:0;overflow:hidden">`
    + `<img src="${site.url}/${BANNER_MOB}" width="${WIDTH}" alt="${esc(BANNER_ALT)}" `
    + `style="display:block;width:100%"></td></tr>`
    + `<!--<![endif]-->`;
}

/**
 * Заголовок письма: оранжевая черта, назначение прописными, адресат.
 *
 * Адресат необязателен: в подтверждении заявки заказчик и так знает, о чьём
 * обращении речь, и строка «в интересах <организация>» там лишняя (решение
 * руководителя 21.09.2026). В КП она остаётся — документ выпускается в
 * интересах юрлица, и это часть его адресации.
 */
export function letterTitle(kind: string, forWhom = ''): string {
  return section(`<div style="width:32px;height:2px;background:${ORANGE};font-size:0;line-height:0">&nbsp;</div>`
    + `<div style="font-family:${FONT};font-size:15px;font-weight:700;letter-spacing:.06em;`
    + `text-transform:uppercase;color:${INK};padding-top:12px">${esc(kind)}</div>`
    + (forWhom
      ? `<div style="font-family:${FONT};font-size:14px;color:${MUTED};padding-top:3px">`
        + `${esc(forWhom)}</div>`
      : ''), 30);
}

/**
 * Подпись менеджера. Должности в ней нет (решение руководителя 15.09.2026):
 * клиенту нужно имя и способ связаться, а «менеджер» ничего не добавляет.
 */
export function signature(): string {
  return section(`<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>`
    + `<td width="122" valign="top">`
    + (hasManagerPhoto()
      ? `<img src="${site.url}/${offerManager.photo}" width="104" height="104" alt="${esc(offerManager.name)}" `
        + `style="display:block;width:104px;height:104px;border-radius:52px;background:${SOFT}">`
      : `<div style="width:104px;height:104px;border-radius:52px;background:${SOFT};border:1px solid ${RULE};`
        + `font-family:${FONT};font-size:30px;font-weight:700;color:${MUTED};text-align:center;line-height:104px">`
        + `${esc(offerManager.initials)}</div>`)
    + `</td><td valign="top" style="font-family:${FONT}">`
    + `<div style="font-weight:700;color:${INK};font-size:16px;line-height:22px;`
    + `padding-bottom:10px">${esc(offerManager.name)}</div>`
    + `<table role="presentation" cellpadding="0" cellspacing="0" border="0">`
    + contactRow('g-mail', offerManager.signatureEmail, `mailto:${offerManager.signatureEmail}`)
    + contactRow('g-phone', offerManager.phone, `tel:${offerManager.phoneHref}`)
    + contactRow('g-tg', 'Telegram', offerManager.telegram)
    + contactRow('g-wa', 'WhatsApp', `https://wa.me/${offerManager.phoneHref.replace('+', '')}`)
    + `</table></td></tr></table>`);
}

/** Оговорка о конфиденциальности в подвале письма. */
export function confidentialFooter(extraHtml = ''): string {
  return `<tr><td class="pad" style="padding:36px 36px 36px">`
    + `<div style="border-top:1px solid ${RULE};padding-top:14px;font-family:${FONT};`
    + `font-size:11.5px;line-height:17px;color:${MUTED}">`
    + `<b style="color:${BODY}">Конфиденциально.</b> Настоящее сообщение и приложения к нему содержат `
    + `сведения конфиденциального характера и предназначены исключительно указанному адресату. Если вы `
    + `получили письмо по ошибке, просим уведомить отправителя и удалить сообщение: ознакомление, `
    + `использование, копирование и распространение содержащихся в нём сведений третьими лицами `
    + `не допускается.${extraHtml}</div></td></tr>`;
}
