/**
 * Служебное письмо руководителю о новом КП — карточка sales-возможности.
 *
 * Состав и порядок блоков — решение руководителя 28.08.2026 (разбор
 * тестового прогона): шапка «Запрос КП на продукты …», предупреждения
 * только при реальной проблеме (бордовым), карточка реквизитов с названием
 * по ЕГРЮЛ против названия из формы, юрадресом, сайтом по домену почты,
 * наценкой и прибылью; состав заказа — таблицей как в КП; развёрнутая
 * карточка ЕГРЮЛ — серой сноской.
 *
 * Вложения собирает обработчик: Word (рабочий исходник без штампов),
 * PDF (слепок клиентского документа со штампами) и Excel экономики —
 * внутренний файл, о чём письмо предупреждает отдельно: Reply-To этого
 * письма — адрес клиента, и «Ответить» с вложениями отправит их наружу.
 */
import { economics as cfg, taxation } from '../../config/site';
import type { QuoteData } from '../quote-layout';
import type { PartyCard } from '../dadata';
import { usdReference, type QuoteEconomics } from '../quote-economics';
import type { AttributionFields } from '../quote-lead';
import type { SourceEnrichment } from '../traffic-source';
import {
  attributionLines, attributionRows, card, EMAIL_COLOR, emailShell, escapeHtml,
  heading, kvRow, note, paragraph,
} from './layout';
import type { RenderedEmail } from './quote-customer';

export interface ManagerQuoteEmailInput {
  data: QuoteData;
  innCheck: { valid: boolean; verdict: string; nameMatch?: string };
  /** Карточка организации по ИНН (ЕГРЮЛ/ДаДата); null — справочник молчал. */
  party: PartyCard | null;
  /** null — экономику посчитать не удалось (нет курса). */
  eco: QuoteEconomics | null;
  /** Источник перехода (канал → кампания → фраза); опционален для старых вызовов. */
  attribution?: AttributionFields;
  /**
   * Данные Метрики и Директа: в живом письме их нет (визит появляется в
   * Метрике с задержкой, расход Директа закрывается за сутки), заполняются
   * при повторной отправке и в утреннем уточнении.
   */
  enrichment?: SourceEnrichment | null;
  /** Приписка к теме — «(ТЕСТ ПОВТОР)» у повторной отправки. */
  subjectPrefix?: string;
  /** Плашка в начале письма: зачем оно пришло второй раз. */
  notice?: string;
}

// Неразрывный пробел перед ₽: обычный позволяет почтовику оторвать знак
// валюты от числа на границе строки.
const rub = (n: number) => `${n.toLocaleString('ru-RU', { maximumFractionDigits: 0 })} ₽`;
const pct = (n: number) => `${n.toLocaleString('ru-RU', { maximumFractionDigits: 1 })}%`;

/**
 * Почтовые домены, по которым сайт компании не угадать: ящик личный.
 * Для корпоративного домена сайт почти всегда живёт на нём же.
 */
const FREE_MAIL = new Set([
  'mail.ru', 'bk.ru', 'list.ru', 'inbox.ru', 'internet.ru', 'xmail.ru',
  'yandex.ru', 'ya.ru', 'yandex.com', 'gmail.com', 'googlemail.com',
  'icloud.com', 'me.com', 'outlook.com', 'hotmail.com', 'live.com',
  'rambler.ru', 'vk.com', 'proton.me', 'protonmail.com', 'yahoo.com',
]);

/** Догадка о сайте клиента по домену корпоративной почты. */
export function siteFromEmail(email: string): { url: string | null; label: string } {
  const domain = email.split('@')[1]?.trim().toLowerCase() || '';
  if (!domain) return { url: null, label: '—' };
  if (FREE_MAIL.has(domain)) return { url: null, label: `— (почта на публичном домене ${domain})` };
  return { url: `https://${domain}`, label: domain };
}

const F = "font-family:'Raleway','Segoe UI',Roboto,Helvetica,Arial,sans-serif;";
const th = (text: string, right = false): string =>
  `<td ${right ? 'align="right" ' : ''}style="${F}font-size:11px;text-transform:uppercase;`
  + `letter-spacing:.04em;color:${EMAIL_COLOR.muted};padding:0 8px 6px 0;`
  + `border-bottom:1px solid ${EMAIL_COLOR.rule};">${text}</td>`;
const td = (text: string, right = false, bold = false): string =>
  `<td ${right ? 'align="right" ' : ''}style="${F}font-size:13px;color:${EMAIL_COLOR.dark};`
  + `padding:6px 8px 6px 0;${bold ? 'font-weight:bold;' : ''}white-space:${right ? 'nowrap' : 'normal'};">${text}</td>`;

export function buildManagerQuoteEmail(input: ManagerQuoteEmailInput): RenderedEmail {
  const { data, innCheck, party, eco, attribution, enrichment } = input;
  const mismatch = innCheck.nameMatch === 'mismatch';
  const trouble = !(innCheck.valid && !mismatch && (party === null || party.active));
  const built = `${trouble ? '⚠ ' : ''}Отправлено КП № ${data.quoteNo} — ${data.buyerCompany}`;
  const subject = input.subjectPrefix ? `${input.subjectPrefix} ${built}` : built;

  // ── Предупреждения: только при реальной проблеме, одно на строку, бордовым.
  const warnings: string[] = [];
  if (!innCheck.valid) warnings.push('ВНИМАНИЕ: ИНН не проходит проверку контрольной суммы — сверить реквизиты до счёта');
  else if (mismatch) warnings.push('ВНИМАНИЕ: ИНН не соответствует декларируемому названию компании');
  if (party && !party.active) warnings.push('ВНИМАНИЕ: организация не действует по ЕГРЮЛ — уточнить до счёта');
  const warnHtml = warnings.map((w) =>
    paragraph(`<b style="color:${EMAIL_COLOR.maroon};">⚠ ${escapeHtml(w)}</b>`)).join('');

  // ── Компания: краткое имя по ИНН против введённого клиентом.
  // Совпали — одно название жирным чёрным; разошлись — реестровое
  // тёмно-зелёным, клиентское красным, оба подписаны.
  const companyHtml = mismatch && party?.name
    ? `<b style="color:${EMAIL_COLOR.ok};">${escapeHtml(party.name)}</b>`
      + ` <span style="color:${EMAIL_COLOR.muted};">(по ИНН)</span><br>`
      + `<b style="color:${EMAIL_COLOR.warn};">${escapeHtml(data.buyerCompany)}</b>`
      + ` <span style="color:${EMAIL_COLOR.muted};">(указано клиентом)</span>`
    : `<b>${escapeHtml(party?.name || data.buyerCompany)}</b>`;

  const siteGuess = siteFromEmail(data.email);
  const siteHtml = siteGuess.url
    ? `<a href="${siteGuess.url}" style="color:${EMAIL_COLOR.accent};text-decoration:none;">${escapeHtml(siteGuess.label)}</a>`
      + ` <span style="color:${EMAIL_COLOR.muted};">(по домену почты)</span>`
    : escapeHtml(siteGuess.label);

  const markup = eco && eco.purchaseRub > 0
    ? { rubV: eco.grossMargin, pctV: (eco.grossMargin / eco.purchaseRub) * 100 }
    : null;

  const names = data.items.map((i) => i.name);
  const shownNames = names.slice(0, 3).join(', ') + (names.length > 3 ? ` и ещё ${names.length - 3}` : '');

  // ── Состав заказа: таблица как в КП — цена за единицу, количество, сумма.
  const itemsTable =
    `<table role="presentation" cellpadding="0" cellspacing="0" width="100%">`
    + `<tr>${th('Наименование')}${th('Цена', true)}${th('Кол-во', true)}${th('Сумма', true)}</tr>`
    + data.items.map((i) =>
      `<tr>${td(`${escapeHtml(i.name)} <span style="color:${EMAIL_COLOR.muted};">(${escapeHtml(i.sku)})</span>`)}`
      + `${td(rub(i.price), true)}${td(String(i.qty), true)}${td(rub(i.sum), true)}</tr>`).join('')
    + `<tr><td colspan="3" style="${F}font-size:13px;color:${EMAIL_COLOR.dark};font-weight:bold;`
    + `padding:8px 8px 2px 0;border-top:1px solid ${EMAIL_COLOR.rule};">Итого</td>`
    + `<td align="right" style="${F}font-size:13px;color:${EMAIL_COLOR.dark};font-weight:bold;`
    + `padding:8px 0 2px;border-top:1px solid ${EMAIL_COLOR.rule};white-space:nowrap;">${rub(data.total)}</td></tr>`
    + `</table>`;

  // ── Развёрнутый ЕГРЮЛ — серой сноской одной строкой.
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

  const ecoRows = eco ? [
    kvRow('Выручка по КП', rub(eco.revenue), true),
    kvRow('Закупка (себестоимость)', eco.purchaseRub > 0
      ? `${rub(eco.purchaseRub)}${usdReference(eco.purchaseRub, eco.fx) != null
          ? ` · $${usdReference(eco.purchaseRub, eco.fx)!.toLocaleString('ru-RU')}` : ''}`
      : 'нет данных'),
    kvRow(`НДС ${taxation.vatPercent}% + ${cfg.taxLabel.toLowerCase()} ${cfg.taxPercent}% + `
      + `${cfg.fxReserveLabel.toLowerCase()} ${cfg.fxReservePercent}%`,
      rub(eco.vat + eco.tax + eco.fxReserve)),
    kvRow('Ожидаемая прибыль', `${rub(eco.profit)} · ${pct(eco.profitPercent)}`, true),
  ].join('') : '';

  const html = emailShell(
    heading(`Запрос КП — ${rub(data.total)}`)
    + paragraph(`Запрос КП на продукты: <b>${escapeHtml(shownNames)}</b>. `
      + `Сумма — <b>${rub(data.total)}</b>. КП № ${escapeHtml(data.quoteNo)} отправлено клиенту на почту.`)
    + (input.notice ? note(escapeHtml(input.notice)) : '')
    + warnHtml
    + (attribution
      ? heading('Источник обращения')
        + card(`<table role="presentation" cellpadding="0" cellspacing="0">${
          attributionRows(attribution, enrichment)}</table>`)
      : '')
    + card(
      `<table role="presentation" cellpadding="0" cellspacing="0">`
      + kvRow('Компания', companyHtml)
      + kvRow('Адрес (юрид.)', escapeHtml(party?.address || '—'))
      + kvRow('Сайт', siteHtml)
      + kvRow('Контакт', escapeHtml(data.contactName), true)
      + kvRow('Телефон', escapeHtml(data.phone || '—'))
      + kvRow('Почта', escapeHtml(data.email))
      + kvRow('Дата', `получено ${escapeHtml(data.date)} · действует до ${escapeHtml(data.validUntil)}`)
      + kvRow('Сумма до торга', rub(data.total), true)
      + kvRow('Наценка', markup ? `${rub(markup.rubV)} · ${pct(markup.pctV)}` : '—')
      + kvRow('Прибыль', eco ? `${rub(eco.profit)} · ${pct(eco.profitPercent)}` : '—')
      + `</table>`)
    + heading('Состав заказа')
    + card(itemsTable)
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
    + egrulNote
    + note('<b>Вложения.</b> Word — рабочий исходник без штампов (клиенту не пересылать), '
      + 'PDF — точная копия отправленного клиенту документа, '
      + 'Excel — <b>внутренняя экономика сделки: при ответе клиенту удалить из вложений</b>.'),
    `${data.buyerCompany} · ${rub(data.total)}${eco ? ` · прибыль ~${rub(eco.profit)}` : ''}`,
  );

  const text = [
    `Запрос КП на продукты: ${shownNames}. Сумма — ${data.total.toLocaleString('ru-RU')} ₽.`,
    `КП № ${data.quoteNo} отправлено клиенту на почту.`,
    ...(input.notice ? ['', input.notice] : []),
    ...warnings.map((w) => `⚠ ${w}`),
    ...(attribution ? ['', 'Источник обращения:', ...attributionLines(attribution, enrichment)] : []),
    '',
    'Реквизиты:',
    ...(mismatch && party?.name
      ? [`Компания (по ИНН): ${party.name}`, `Компания (указано клиентом): ${data.buyerCompany}`]
      : [`Компания: ${party?.name || data.buyerCompany}`]),
    `ИНН: ${data.buyerInn} — ${innCheck.verdict}`,
    `Адрес (юрид.): ${party?.address || '—'}`,
    `Сайт: ${siteGuess.url || siteGuess.label}`,
    `Контакт: ${data.contactName}`,
    `Телефон: ${data.phone}`,
    `Почта: ${data.email}`,
    `Дата: получено ${data.date}, действует до ${data.validUntil}`,
    `Сумма до торга: ${data.total.toLocaleString('ru-RU')} ₽`,
    `Наценка: ${markup ? `${markup.rubV.toLocaleString('ru-RU')} ₽ (${pct(markup.pctV)})` : '—'}`,
    `Прибыль: ${eco ? `${eco.profit.toLocaleString('ru-RU')} ₽ (${pct(eco.profitPercent)})` : '—'}`,
    '',
    'Состав заказа:',
    ...data.items.map((i) =>
      `— ${i.name} (${i.sku}): ${i.price.toLocaleString('ru-RU')} ₽ × ${i.qty} = ${i.sum.toLocaleString('ru-RU')} ₽`),
    `Итого: ${data.total.toLocaleString('ru-RU')} ₽.`,
    ...(eco ? [
      '',
      'Экономика сделки:',
      `Закупка: ${eco.purchaseRub > 0 ? rub(eco.purchaseRub) : 'нет данных'}`,
      `Ожидаемая прибыль: ${rub(eco.profit)} (${pct(eco.profitPercent)})`,
      ...(eco.complete ? [] : [`⚠ Без закупочных цен: ${eco.missingPurchase.join(', ')} — прибыль завышена.`]),
      ...(eco.suspectMonthly.length
        ? [`⚠ Похоже на месячную закупку при годовой продаже: ${eco.suspectMonthly.join(', ')} — сверить с прайсом вендора.`] : []),
      ...(eco.aboveSale.length
        ? [`⚠ Закупка дороже продажи: ${eco.aboveSale.join(', ')}.`] : []),
    ] : ['', 'Экономику посчитать не удалось (нет курса ЦБ) — см. закупочные цены вручную.']),
    ...(party ? ['', 'ЕГРЮЛ: ' + [
      party.fullName,
      `ИНН/КПП ${party.inn}${party.kpp ? ` / ${party.kpp}` : ''}`,
      party.ogrn ? `ОГРН ${party.ogrn}` : '',
      party.address,
      `статус: ${party.status}`,
    ].filter(Boolean).join(' · ')] : []),
    '',
    'Вложения: Word — рабочий (без штампов), PDF — копия клиентского,',
    'Excel — ВНУТРЕННЯЯ экономика: при ответе клиенту удалить из вложений.',
  ].join('\n');

  return { subject, html, text };
}
