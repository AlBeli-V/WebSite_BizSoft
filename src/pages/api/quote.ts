export const prerender = false;

import type { APIRoute } from 'astro';
import { getProductsBySkus, createQuote } from '../../lib/directus';
import { effectivePrice } from '../../lib/pricing';
import { sendMail, managerEmail, salesFrom } from '../../lib/mailer';
import { generateQuotePdf, buildQuoteNo, formatDateRu, addDays, type QuoteData } from '../../lib/pdf-quote';
import { site, seller } from '../../config/site';
import type { QuoteItem } from '../../lib/types';

interface CartLine { sku: string; qty: number }

function isEmail(v: unknown): v is string {
  return typeof v === 'string' && /.+@.+\..+/.test(v);
}

/** Непустая строка после trim. */
function filled(v: unknown): v is string {
  return typeof v === 'string' && v.trim().length > 0;
}

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'bad json' }), { status: 400 });
  }

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

  // Пересчёт по авторитетным ценам из БД (с учётом акции на момент запроса)
  let products;
  try {
    products = await getProductsBySkus(lines.map((l) => l.sku));
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
    items.push({ sku: p.sku, name: p.name, qty: line.qty, price, sum: price * line.qty });
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

  let pdf: Buffer;
  try {
    pdf = await generateQuotePdf(data);
  } catch (e) {
    console.error('quote: pdf gen failed', e);
    return new Response(JSON.stringify({ error: 'не удалось сформировать PDF' }), { status: 500 });
  }

  // Сохранение в Directus (не блокируем выдачу PDF при сбое)
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

  // ── Письма ──
  const filename = `KP_${quoteNo}.pdf`;
  const attachment = { filename, content: pdf, contentType: 'application/pdf' };

  // 1. Клиенту — КП во вложении, отправитель hello@biz-soft.pro
  const clientText = [
    `Здравствуйте${data.contactName ? ', ' + data.contactName : ''}!`,
    '',
    `Коммерческое предложение № ${quoteNo} во вложении.`,
    `Сумма: ${total.toLocaleString('ru-RU')} ₽. Действует до ${data.validUntil}.`,
    '',
    'Оплата по счёту, договор и закрывающие документы через ЭДО.',
    `${seller.shortName} · ${seller.phone} · ${site.url}`,
  ].join('\n');

  sendMail({
    from: salesFrom,
    to: data.email,
    replyTo: managerEmail,
    subject: `Коммерческое предложение № ${quoteNo} — BIZSoft`,
    text: clientText,
    attachments: [attachment],
  }).catch((e) => console.error('quote client mail failed', e));

  // 2. Менеджеру — копия КП с данными заказчика из формы
  const managerText = [
    `Клиент запросил отправку КП № ${quoteNo} себе на почту.`,
    '',
    'Данные заказчика из формы:',
    `Организация: ${data.buyerCompany}`,
    `ИНН: ${data.buyerInn}`,
    `Контактное лицо: ${data.contactName}`,
    `E-mail: ${data.email}`,
    `Телефон: ${data.phone}`,
    '',
    'Состав заказа:',
    ...items.map((i) => `— ${i.name} (${i.sku}) × ${i.qty} = ${i.sum.toLocaleString('ru-RU')} ₽`),
    '',
    `Итого: ${total.toLocaleString('ru-RU')} ₽. Действует до ${data.validUntil}.`,
  ].join('\n');

  sendMail({
    from: salesFrom,
    to: managerEmail,
    replyTo: data.email,
    subject: `Отправлено КП № ${quoteNo} — ${data.buyerCompany}`,
    text: managerText,
    attachments: [attachment],
  }).catch((e) => console.error('quote manager mail failed', e));

  return new Response(new Uint8Array(pdf), {
    status: 200,
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="${filename}"`,
      'X-Quote-No': quoteNo,
    },
  });
};
