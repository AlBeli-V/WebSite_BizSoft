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
import {
  banner, BODY, closeLetter, confidentialFooter, esc, FONT, INK, letterTitle, MUTED,
  openLetter, ORANGE, RULE, section, sectionHead, signature, stepRow,
  type RenderedEmail,
} from './client-shell';

export type { RenderedEmail };

export interface OfferEmailInput {
  data: QuoteData;
  /** Имя вложенного PDF: получатель ищет файл по имени, а не по счёту. */
  pdfName: string;
  pdfSize: number;
  /** Состав по производителям: марка, её раздел, её позиции. */
  vendors?: OfferVendorGroup[];
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

export function buildCustomerQuoteEmail(input: OfferEmailInput): RenderedEmail {
  const { data, pdfName } = input;
  const vendors = input.vendors ?? [];
  const company = data.buyerCompany || 'вашей организации';
  // Тема называет предмет, а не номер: в списке писем заказчик узнаёт
  // предложение по дате и производителям, а номер ему ни о чём не говорит
  // (формулировка руководителя 16.09.2026).
  const vendorList = vendors.map((v) => v.vendor).filter(Boolean).join(' / ');
  const subject = `Предварительное КП BIZSoft от ${data.date}`
    + (vendorList ? ` на поставку ${vendorList}` : '');
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

  const html = openLetter(subject,
    `Коммерческое предложение № ${data.quoteNo} для ${company} — документ во вложении.`)
    + banner()
    + letterTitle('Коммерческое предложение', `в интересах ${company}`)

    // ── Обращение ──
    + section(`<div style="font-family:${FONT};font-size:15px;line-height:24px;color:${BODY}">`
      + `<b style="color:${INK}">${esc(salutation(data.contactName))}</b><br><br>`
      + `Благодарим Вас за интерес к нашей компании и обращение. В ответ на Ваш запрос `
      + `направляем предварительное коммерческое предложение в интересах ${esc(company)} `
      + `на выбранные Вами продукты и AI-сервисы. Будем рады помочь с уточнением выбора и `
      + `ответить на возникшие вопросы.</div>`, 26)
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

    + signature()
    + confidentialFooter()
    + closeLetter();

  // Текстовая версия — то же содержимое без вёрстки: часть клиентов
  // показывает именно её, и потерять в ней номер или вложение нельзя.
  const text = [
    salutation(data.contactName),
    '',
    `Благодарим Вас за интерес к нашей компании и обращение. В ответ на Ваш запрос `
      + `направляем предварительное коммерческое предложение № ${data.quoteNo} в интересах `
      + `${company} на выбранные Вами продукты и AI-сервисы — документ во вложении (${pdfName}).`,
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
    `${offerManager.phone} · ${offerManager.signatureEmail} · ${site.url}`,
    '',
    'Конфиденциально. Настоящее сообщение и приложения к нему содержат сведения '
      + 'конфиденциального характера и предназначены исключительно указанному адресату.',
  ].filter((l) => l !== '').join('\n');

  return { subject, html, text };
}
