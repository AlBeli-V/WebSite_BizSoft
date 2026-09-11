export const prerender = false;

import type { APIRoute } from 'astro';
import { getProductsBySkus, getZohoPositionsBySkus, createQuote, getLeads, createLeadEvent } from '../../lib/directus';
import { leadFromQuote, describeQuote, attributionFields } from '../../lib/quote-lead';
import { createLeadTolerant } from '../../lib/lead-write';
import { effectivePrice } from '../../lib/pricing';
import { sendMail, managerEmail, salesFrom } from '../../lib/mailer';
import { generateQuotePdf, buildQuoteNo, formatDateRu, addDays, type QuoteData } from '../../lib/pdf-quote';
import { generateQuoteJpg } from '../../lib/jpg-quote';
import { generateQuoteDocx } from '../../lib/docx-quote';
import { site } from '../../config/site';
import { verifyCompany } from '../../lib/inn';
import { findParty } from '../../lib/dadata';
import { buildCustomerQuoteEmail } from '../../lib/email/quote-customer';
import { buildManagerQuoteEmail } from '../../lib/email/quote-manager';
import { buildQuoteEconomics, type QuoteEconomics } from '../../lib/quote-economics';
import { generateQuoteEconomicsXlsx, economicsFileName } from '../../lib/xlsx-quote';
import { fetchCbrRates } from '../../lib/currency';
import type { QuoteItem } from '../../lib/types';
import { guardSubmission, guardResponse, countSubmission } from '../../lib/form-guard';
import { clientIp } from '../../lib/client-ip';

interface CartLine { sku: string; qty: number }

function isEmail(v: unknown): v is string {
  return typeof v === 'string' && /.+@.+\..+/.test(v);
}

/** Непустая строка после trim. */
function filled(v: unknown): v is string {
  return typeof v === 'string' && v.trim().length > 0;
}

/**
 * Записать скачивание КП в воронку.
 *
 * Если клиент уже есть в работе, второй карточки не заводим: повторное
 * скачивание — событие существующей сделки, а не новая заявка. Иначе один
 * человек, качнувший КП трижды, превращается в три сделки и ломает конверсию.
 */
async function recordQuoteLead(q: Parameters<typeof leadFromQuote>[0]): Promise<void> {
  const email = q.email.trim().toLowerCase();
  let open: { id: string | number } | undefined;
  try {
    const leads = await getLeads(500);
    open = leads.find((l) =>
      String(l.email || '').trim().toLowerCase() === email &&
      !['won', 'lost', 'spam'].includes(String(l.status || 'new')));
  } catch (e) {
    // Не смогли проверить — заводим новую: потерять контакт хуже, чем задвоить.
    console.error('quote lead lookup failed', e);
  }

  if (open) {
    await createLeadEvent({
      lead: Number(open.id),
      kind: 'email',
      subject: `Клиент скачал КП № ${q.quoteNo} на ${q.total.toLocaleString('ru-RU')} ₽`,
      text: describeQuote(q),
      author: 'сайт',
    });
    return;
  }
  // Откат при отставании схемы прода — общий для обеих форм (lead-write.ts).
  await createLeadTolerant(leadFromQuote(q));
}

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'bad json' }), { status: 400 });
  }

  // Защита публичных форм (SEC-RL-001). Здесь она дороже всего окупается:
  // за этой строкой — справочник организаций, три документа и письмо с
  // вложением на указанный в форме адрес от имени hello@biz-soft.pro.
  const ip = clientIp(request);
  const verdict = await guardSubmission({ body, ip });
  if (!verdict.ok) return guardResponse(verdict);

  // Все поля формы КП обязательны
  const company = body.buyer_company ?? body.company;
  const inn = body.buyer_inn ?? body.inn;
  const contact = body.contact_name ?? body.name;
  if (!filled(company)) return new Response(JSON.stringify({ error: 'Укажите организацию' }), { status: 422 });
  if (!filled(inn)) return new Response(JSON.stringify({ error: 'Укажите ИНН' }), { status: 422 });
  if (!filled(contact)) return new Response(JSON.stringify({ error: 'Укажите контактное лицо' }), { status: 422 });
  if (!isEmail(body.email)) return new Response(JSON.stringify({ error: 'Укажите корректный e-mail' }), { status: 422 });
  if (!filled(body.phone)) return new Response(JSON.stringify({ error: 'Укажите телефон' }), { status: 422 });
  if (body.consent !== true) return new Response(JSON.stringify({ error: 'Нужно согласие на обработку персональных данных' }), { status: 422 });

  const rawItems = Array.isArray(body.items) ? (body.items as CartLine[]) : [];
  const lines = rawItems
    .filter((i) => i && typeof i.sku === 'string' && Number(i.qty) > 0)
    .map((i) => ({ sku: i.sku, qty: Math.min(9999, Math.max(1, Math.floor(Number(i.qty)))) }));

  if (lines.length === 0) return new Response(JSON.stringify({ error: 'список избранного пуст' }), { status: 422 });

  // Форма разобрана, дальше начинается дорогая часть: справочник, документы,
  // письмо. Порог тратит эта заявка, а не отвергнутая валидацией попытка.
  await countSubmission(ip);

  // Пересчёт по авторитетным ценам из БД (с учётом акции на момент запроса)
  let products;
  try {
    const skus = lines.map((l) => l.sku);
    // Позиции конфигуратора ManageEngine страниц не имеют и лежат в базе
    // черновиками. В КП они нужны: спецификацию, собранную конфигуратором,
    // иначе нечем оценить.
    const [published, hidden] = await Promise.all([
      getProductsBySkus(skus),
      getZohoPositionsBySkus(skus),
    ]);
    const seen = new Set(published.map((p) => p.sku));
    products = [...published, ...hidden.filter((p) => !seen.has(p.sku))];
  } catch (e) {
    console.error('quote: getProductsBySkus failed', e);
    return new Response(JSON.stringify({ error: 'не удалось получить цены' }), { status: 502 });
  }
  const bySku = new Map(products.map((p) => [p.sku, p]));

  const items: QuoteItem[] = [];
  for (const line of lines) {
    const p = bySku.get(line.sku);
    if (!p) continue;
    const price = effectivePrice(p).price;
    items.push({ sku: p.sku, name: p.name, qty: line.qty, price,
                 sum: price * line.qty, vat_percent: p.vat_percent });
  }
  if (items.length === 0) return new Response(JSON.stringify({ error: 'позиции не найдены' }), { status: 422 });

  const total = items.reduce((s, i) => s + i.sum, 0);

  const now = new Date();
  const suffix = String(now.getTime()).slice(-4) + String(Math.floor(Math.random() * 10));
  const quoteNo = buildQuoteNo(now, suffix);

  const data: QuoteData = {
    quoteNo,
    date: formatDateRu(now),
    validUntil: formatDateRu(addDays(now, site.quoteValidDays)),
    buyerCompany: String(body.buyer_company || body.company || '').slice(0, 300),
    buyerInn: String(body.buyer_inn || body.inn || '').slice(0, 20),
    contactName: String(body.contact_name || body.name || '').slice(0, 200),
    email: String(body.email).slice(0, 200),
    phone: String(body.phone || '').slice(0, 50),
    items,
    total,
  };

  // Три формата одного документа, каждый своему получателю:
  //   JPG  — клиенту (скачивание со страницы и вложение в его письмо);
  //   PDF  — руководителю, чтобы отправить клиенту лично;
  //   DOCX — руководителю, чтобы поправить перед отправкой.
  // Редактируемый PDF с реквизитами, гуляющий по почте клиента, — риск:
  // сумму в нём меняют в любом просмотрщике и предъявляют как наш документ.
  let pdf: Buffer;
  let jpg: Buffer;
  try {
    pdf = await generateQuotePdf(data);
    jpg = generateQuoteJpg(data);
  } catch (e) {
    console.error('quote: gen failed', e);
    return new Response(JSON.stringify({ error: 'не удалось сформировать документ' }), { status: 500 });
  }

  // Сохранение в Directus (не блокируем выдачу документа при сбое)
  createQuote({
    quote_no: quoteNo,
    buyer_company: data.buyerCompany,
    buyer_inn: data.buyerInn,
    contact_name: data.contactName,
    email: data.email,
    phone: data.phone,
    items,
    total,
    consent: true,
  }).catch((e) => console.error('createQuote failed', e));

  // Достоверность заявки: сходятся ли название и ИНН. Менеджеру это нужно
  // до звонка, а не после выставленного счёта. Проверка не блокирует выдачу
  // КП — она информирует: ошибка в цифре и умысел выглядят одинаково, и
  // решать, что это было, человеку, а не форме.
  const innCheck = await verifyCompany(data.buyerInn, data.buyerCompany);
  // Карточка организации из ЕГРЮЛ — менеджеру до звонка. Заявка от
  // ликвидированной компании и от действующей выглядят в форме одинаково,
  // а разговор с ними разный. Справочник молчит — заявка уходит как есть:
  // это дополнение к обращению, а не условие его приёма.
  const party = innCheck.valid ? await findParty(data.buyerInn).catch(() => null) : null;

  // Экономика сделки: считается один раз и уходит и в заявку CRM, и в
  // письмо руководителю. Обещание, а не ожидание: курс ЦБ — внешний сервис,
  // его сбой или медленный ответ не должны задерживать письмо клиенту.
  const ecoPromise: Promise<QuoteEconomics | null> = fetchCbrRates()
    .then((rates) => buildQuoteEconomics(items, products, rates))
    .catch((e) => { console.error('quote economics failed', e); return null; });

  // Заявка в воронку. Скачивание КП — самый тёплый контакт на сайте: назвали
  // организацию, ИНН, телефон и собрали корзину. Раньше это оседало в quotes и
  // в почте менеджера, а в воронке канал не существовал.
  ecoPromise.then((eco) => recordQuoteLead({
    innCheck: innCheck.verdict,
    quoteNo,
    buyerCompany: data.buyerCompany,
    buyerInn: data.buyerInn,
    contactName: data.contactName,
    email: data.email,
    phone: data.phone,
    items,
    total,
    validUntil: data.validUntil,
    attribution: attributionFields(body),
    economics: eco ? {
      costRub: eco.purchaseRub > 0 ? eco.purchaseRub : null,
      marginRub: eco.profit,
      marginPct: eco.profitPercent,
      fxRate: eco.fx.usd,
      incomplete: !eco.complete,
    } : undefined,
  })).catch((e) => console.error('quote lead failed', e));

  // ── Письма ──
  const clientFile = `KP_${quoteNo}.jpg`;
  const clientAttachment = { filename: clientFile, content: jpg, contentType: 'image/jpeg' };

  // 1. Клиенту — КП во вложении, отправитель hello@biz-soft.pro.
  // HTML с text-fallback собирает шаблон (src/lib/email): фирменная шапка,
  // карточка предложения, оговорка о предварительном характере, приглашение
  // ответить на письмо — Reply-To ведёт к менеджеру.
  const clientMail = buildCustomerQuoteEmail(data);

  // Письмо клиенту отправляем до ответа и ждём результата: экран говорит
  // «отправлено», и это должно быть правдой. Сбой SMTP при отправке в фоне
  // оставлял человека с подтверждением и без письма.
  try {
    await sendMail({
      from: salesFrom,
      to: data.email,
      replyTo: managerEmail,
      subject: clientMail.subject,
      text: clientMail.text,
      html: clientMail.html,
      attachments: [clientAttachment],
    });
  } catch (e) {
    console.error('quote client mail failed', e);
    return new Response(JSON.stringify({
      error: 'Предложение сформировано, но письмо не ушло. '
        + 'Позвоните нам — отправим вручную.',
      quote_no: quoteNo,
    }), { status: 502, headers: { 'Content-Type': 'application/json' } });
  }

  // 2. Менеджеру — карточка сделки и рабочий комплект: Word — поправить
  // (без штампов, клиенту не пересылается), PDF — слепок клиентского
  // документа, Excel — внутренняя экономика сделки (закупка, налоги,
  // прибыль). Всё собирается уже после ответа клиенту, поэтому сбой любого
  // шага не мешает выдать КП: письмо себе важно, но не важнее скачивания.
  //
  // Экономика уже считается с момента приёма заявки (ecoPromise); здесь
  // только дожидаемся результата — письмо клиенту к этому моменту ушло.
  const eco = await ecoPromise;

  const managerMail = buildManagerQuoteEmail({
    data,
    innCheck,
    party,
    eco,
    attribution: attributionFields(body),
  });

  generateQuoteDocx(data)
    .then((docx) => sendMail({
      from: salesFrom,
      to: managerEmail,
      replyTo: data.email,
      subject: managerMail.subject,
      text: managerMail.text,
      html: managerMail.html,
      attachments: [
        { filename: `KP_${quoteNo}.docx`, content: docx,
          contentType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
        { filename: `KP_${quoteNo}.pdf`, content: pdf, contentType: 'application/pdf' },
        // Внутренний файл: письмо предупреждает удалить его из вложений
        // при ответе клиенту (Reply-To этого письма — адрес клиента).
        ...(eco ? [{
          filename: economicsFileName(quoteNo),
          content: generateQuoteEconomicsXlsx(quoteNo, data.date, eco),
          contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }] : []),
      ],
    }))
    .catch((e) => console.error('quote manager mail failed', e));

  // Ответ — подтверждение, а не файл. Документ уходит письмом; отдавать его
  // же в ответ значило показать человеку страницу «сохранить и напечатать»
  // вместо ответа на вопрос «отправили или нет».
  return new Response(JSON.stringify({
    ok: true,
    quote_no: quoteNo,
    sent_to: data.email,
  }), {
    status: 200,
    headers: { 'Content-Type': 'application/json', 'X-Quote-No': quoteNo },
  });
};
