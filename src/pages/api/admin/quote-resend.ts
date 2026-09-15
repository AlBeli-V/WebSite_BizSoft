export const prerender = false;

/**
 * Повторная отправка уже выпущенного КП — тем же номером и теми же ценами.
 *
 * Нужна ровно для одного случая: документ переделан, а посмотреть, как
 * теперь выглядит уже отправленное предложение, можно только на живых
 * данных. Поэтому эндпоинт ничего не создаёт — ни заявки, ни записи в
 * quotes, ни зеркала в Bitrix24: он берёт сохранённое КП, пересобирает
 * документ текущим кодом и отправляет письмо с пометкой о повторе.
 *
 * Доступ — по токену админ-инструментов (`x-admin-token`), как у остальных
 * инструментов в `/api/admin/*`. Вызывается прогоном `ops-quote-resend`
 * изнутри сервера; наружу эндпоинт не публикуется и в sitemap не попадает.
 *
 * Производитель у позиций старых КП не сохранён — в записи есть только
 * артикул, название и деньги. Он добирается из каталога по артикулу: без
 * него описание позиции осталось бы без юрлица и без формы поставки
 * (`docs/rules/spec-line.md`).
 */
import type { APIRoute } from 'astro';
import { checkAdmin, isAdminConfigured, unauthorized } from '../../../lib/admin-auth';
import { getProductsBySkus, getQuotes } from '../../../lib/directus';
import { generateQuoteDocx } from '../../../lib/docx-quote';
import { generateQuoteJpgPages, jpgFileNames } from '../../../lib/jpg-quote';
import { buildCustomerQuoteEmail } from '../../../lib/email/quote-customer';
import { managerEmail, salesFrom, sendMail } from '../../../lib/mailer';
import { generateQuotePdf } from '../../../lib/pdf-quote';
import { addDays, formatDateRu, type QuoteData } from '../../../lib/quote-layout';
import { site } from '../../../config/site';
import type { QuoteItem } from '../../../lib/types';

/** Приписка в теме: получатель должен сразу видеть, что это повтор, а не новое КП. */
const TEST_PREFIX = '(ТЕСТ ПОВТОР)';

interface Body {
  /** Почта клиента, чьё последнее КП переотправляем. */
  email?: string;
  /** Точный номер КП; если задан — ищем по нему, а не по почте. */
  quote_no?: string;
  /** Куда отправить. По умолчанию — менеджеру, а не клиенту. */
  to?: string;
  /**
   * `manager` (по умолчанию) — служебное письмо со всеми форматами сразу.
   * `client` — ровно то письмо, которое получает заказчик: та же вёрстка,
   *   те же вложения (листы картинками), тот же отправитель. Нужен, чтобы
   *   смотреть и править клиентское письмо на живых данных.
   */
  mode?: 'manager' | 'client';
  /** true — показать состав и ничего не отправлять. */
  dry_run?: boolean;
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

export const POST: APIRoute = async ({ request }) => {
  if (!isAdminConfigured() || !checkAdmin(request)) return unauthorized();

  let body: Body;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'bad json' }, 400);
  }

  const wantedNo = String(body.quote_no || '').trim();
  const wantedEmail = String(body.email || '').trim().toLowerCase();
  if (!wantedNo && !wantedEmail) return json({ error: 'нужен quote_no или email' }, 422);

  let quotes;
  try {
    quotes = await getQuotes(500);
  } catch (e) {
    console.error('quote-resend: getQuotes failed', e);
    return json({ error: 'не удалось прочитать список КП' }, 502);
  }

  // Список приходит отсортированным по убыванию даты, поэтому первое
  // совпадение — самое свежее.
  const found = quotes.find((q) => (wantedNo
    ? String(q.quote_no || '') === wantedNo
    : String(q.email || '').trim().toLowerCase() === wantedEmail));
  if (!found) {
    return json({ error: wantedNo ? `КП № ${wantedNo} не найдено` : `КП на адрес ${wantedEmail} не найдено` }, 404);
  }

  const stored = Array.isArray(found.items) ? found.items : [];
  if (stored.length === 0) return json({ error: 'в сохранённом КП нет позиций' }, 422);

  // Производитель — из каталога по артикулу. Сбой выборки не отменяет
  // отправку: описание тогда обойдётся без юрлица, но документ уйдёт.
  let vendorBySku = new Map<string, string>();
  try {
    const products = await getProductsBySkus(stored.map((i) => i.sku));
    vendorBySku = new Map(products.map((p) => [p.sku, p.vendor || '']));
  } catch (e) {
    console.error('quote-resend: getProductsBySkus failed', e);
  }

  const items: QuoteItem[] = stored.map((i) => ({
    sku: i.sku,
    name: i.name,
    qty: i.qty,
    // Цены берутся из записи, а не пересчитываются: это повтор выпущенного
    // документа, и суммы в нём обязаны совпасть с тем, что клиент получил.
    price: (i as QuoteItem).price ?? (i.qty > 0 ? i.sum / i.qty : i.sum),
    sum: i.sum,
    vat_percent: (i as QuoteItem).vat_percent,
    vendor: (i as QuoteItem).vendor || vendorBySku.get(i.sku) || '',
    email_rent: Boolean((i as QuoteItem).email_rent),
  }));

  const issued = found.created_at ? new Date(found.created_at) : new Date();
  const data: QuoteData = {
    quoteNo: String(found.quote_no || ''),
    date: formatDateRu(issued),
    validUntil: formatDateRu(addDays(issued, site.quoteValidDays)),
    buyerCompany: String(found.buyer_company || ''),
    buyerInn: String(found.buyer_inn || ''),
    contactName: String(found.contact_name || ''),
    email: String(found.email || ''),
    phone: String(found.phone || ''),
    items,
    total: Number(found.total) || items.reduce((s, i) => s + i.sum, 0),
  };

  const to = String(body.to || '').trim() || managerEmail;

  let jpgPages: Buffer[];
  let pdf: Buffer;
  let docx: Buffer;
  try {
    jpgPages = generateQuoteJpgPages(data);
    pdf = await generateQuotePdf(data);
    docx = await generateQuoteDocx(data);
  } catch (e) {
    console.error('quote-resend: gen failed', e);
    return json({ error: 'не удалось собрать документ' }, 500);
  }

  const asClient = body.mode === 'client';
  const files = jpgFileNames(data.quoteNo, jpgPages.length);
  const summary = {
    ok: true,
    quote_no: data.quoteNo,
    issued: data.date,
    buyer: data.buyerCompany,
    client_email: data.email,
    to,
    mode: asClient ? 'client' : 'manager',
    positions: items.length,
    total: data.total,
    sheets: jpgPages.length,
    files: asClient ? files : [...files, `KP_${data.quoteNo}.pdf`, `KP_${data.quoteNo}.docx`],
  };
  if (body.dry_run) return json({ ...summary, ok: true, sent: false, dry_run: true });

  // Режим `client` — точная копия письма заказчика: та же вёрстка, те же
  // вложения, тот же отправитель и Reply-To. Пометка о повторе остаётся в
  // теме: письмо уходит на внутренний адрес, и спутать его с настоящим
  // предложением нельзя.
  if (asClient) {
    const mail = buildCustomerQuoteEmail(data, jpgPages.length);
    try {
      await sendMail({
        from: salesFrom,
        to,
        replyTo: managerEmail,
        subject: `${TEST_PREFIX} ${mail.subject}`,
        text: mail.text,
        html: mail.html,
        attachments: files.map((filename, i) => ({
          filename, content: jpgPages[i], contentType: 'image/jpeg',
        })),
      });
    } catch (e) {
      console.error('quote-resend: client mail failed', e);
      return json({ error: 'документ собран, но письмо не ушло', ...summary, sent: false }, 502);
    }
    return json({ ...summary, sent: true });
  }

  // Служебное письмо: все форматы сразу — получатель смотрит и то, что
  // видит клиент (картинка по листам), и рабочие PDF с Word.
  try {
    await sendMail({
      from: salesFrom,
      to,
      subject: `${TEST_PREFIX} Коммерческое предложение № ${data.quoteNo} — BIZSoft`,
      text: [
        `Повторная отправка ранее выпущенного КП № ${data.quoteNo} от ${data.date}.`,
        `Заказчик: ${data.buyerCompany || '—'}, адрес клиента: ${data.email || '—'}.`,
        `Позиций: ${items.length}. Сумма: ${data.total.toLocaleString('ru-RU')} ₽.`,
        `Листов в документе: ${jpgPages.length} — картинка идёт по файлу на лист.`,
        '',
        'Письмо служебное: заявка не заводилась, запись в CRM не создавалась,'
        + ' клиенту ничего не отправлялось.',
      ].join('\n'),
      attachments: [
        ...files.map((filename, i) => ({ filename, content: jpgPages[i], contentType: 'image/jpeg' })),
        { filename: `KP_${data.quoteNo}.pdf`, content: pdf, contentType: 'application/pdf' },
        { filename: `KP_${data.quoteNo}.docx`, content: docx,
          contentType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
      ],
    });
  } catch (e) {
    console.error('quote-resend: mail failed', e);
    return json({ error: 'документ собран, но письмо не ушло', ...summary, sent: false }, 502);
  }

  return json({ ...summary, sent: true });
};
