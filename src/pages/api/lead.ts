export const prerender = false;

import type { APIRoute } from 'astro';
import { defaultLeadOwner } from '../../config/site';
import { createLeadTolerant } from '../../lib/lead-write';
import { sendMail, managerEmail, salesFrom } from '../../lib/mailer';
import { attributionFields, cartItems } from '../../lib/quote-lead';
import { mirrorLeadAndLink } from '../../lib/bitrix24';
import { verifyCompany } from '../../lib/inn';
import { findParty } from '../../lib/dadata';
import { buildManagerLeadEmail } from '../../lib/email/lead-manager';
import { buildCustomerLeadEmail } from '../../lib/email/lead-customer';
import { identifyRequest, leadLinks, type LeadRequestReview } from '../../lib/lead-request';
import { getProducts } from '../../lib/directus';
import { site } from '../../config/site';
import { guardSubmission, guardResponse, countSubmission } from '../../lib/form-guard';
import { clientIp } from '../../lib/client-ip';
import { intakeFormConsents } from '../../lib/consent-intake';

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

  // Защита публичных форм (SEC-RL-001): приманка, отсечка по времени и
  // пороги по адресу. Стоит до валидации — отклонённое обращение не должно
  // стоить нам ни запроса в базу, ни письма.
  const ip = clientIp(request);
  const verdict = await guardSubmission({ body, ip });
  if (!verdict.ok) return guardResponse(verdict);

  // Все поля формы обязательны
  if (!filled(body.name)) return new Response(JSON.stringify({ error: 'Укажите ФИО' }), { status: 422 });
  if (!filled(body.company)) return new Response(JSON.stringify({ error: 'Укажите компанию' }), { status: 422 });
  // Состав реквизитов формы заявки идентичен форме КП — решение
  // руководителя 28.08.2026. Контрольная сумма ИНН не блокирует заявку:
  // вердикт сверки уходит менеджеру в письмо, решает человек.
  if (!filled(body.inn)) return new Response(JSON.stringify({ error: 'Укажите ИНН' }), { status: 422 });
  if (!isEmail(body.email)) return new Response(JSON.stringify({ error: 'Укажите корректный e-mail' }), { status: 422 });
  if (!filled(body.phone)) return new Response(JSON.stringify({ error: 'Укажите телефон' }), { status: 422 });
  if (!filled(body.message)) return new Response(JSON.stringify({ error: 'Заполните сообщение' }), { status: 422 });
  if (body.consent !== true) {
    return new Response(JSON.stringify({ error: 'Нужно согласие на обработку персональных данных' }), { status: 422 });
  }

  // Поля разобраны — это заявка, а не опечатка. Только теперь она тратит
  // порог адреса: иначе три промаха мимо формата телефона закрыли бы форму
  // человеку до конца часа.
  await countSubmission(ip);

  // Согласия фиксируются ДО заявки и до зеркала в портале (ТЗ 16.09.2026,
  // п. 3). Если журнал недоступен, обращение не принимается вовсе: контакт
  // в работе без доказательства согласия — это и есть нарушение, ради
  // предотвращения которого журнал заводился. Человеку при этом
  // предлагается живой канал, а не «попробуйте позже в никуда».
  let consent: Awaited<ReturnType<typeof intakeFormConsents>>;
  try {
    consent = await intakeFormConsents({
      body,
      subject: {
        name: String(body.name || ''),
        email: String(body.email || ''),
        phone: String(body.phone || ''),
        company: String(body.company || ''),
      },
      fallbackFormId: String(body.source || 'lead-form'),
      purpose: 'Обработка обращения, подготовка ответа и КП',
      ip,
      userAgent: request.headers.get('user-agent') || undefined,
    });
  } catch (e) {
    console.error('consent log failed', e);
    return new Response(
      JSON.stringify({ error: 'Не удалось зафиксировать согласие. Напишите нам на hello@biz-soft.pro или позвоните.' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } },
    );
  }

  const cart = cartItems(body.cart);

  const payload = {
    name: String(body.name || '').slice(0, 200),
    company: String(body.company || '').slice(0, 200),
    inn: String(body.inn || '').replace(/[\s-]/g, '').slice(0, 20),
    email: String(body.email).slice(0, 200),
    phone: String(body.phone || '').slice(0, 50),
    message: String(body.message || '').slice(0, 4000),
    product_ref: String(body.product_ref || '').slice(0, 300),
    // Состав подборки на момент обращения: точные артикулы вместо разбора
    // свободного текста. Поле необязательное (lead-write.ts): пока на проде
    // не выполнен ops-directus-schema, заявка запишется и без него.
    cart_items: cart.length ? JSON.stringify(cart) : '',
    consent: true,
    // Ссылка на доказательство: по event_id карточка заявки поднимается в
    // журнале согласий одним запросом. Сам журнал при этом остаётся
    // источником истины — в заявке лежит только ссылка.
    consent_event_id: consent.personalDataEventId,
    marketing_consent: consent.marketingStatus === 'subscribed',
    marketing_consent_event_id: consent.marketingEventId,
    // Идентификатор формы, а не канал трафика. Прежде поле называлось просто
    // `source`, и в письме менеджеру строка «Источник: pricing» читалась как
    // источник перехода. Канал теперь лежит отдельно, в last_touch_source.
    form_source: String(body.source || 'site').slice(0, 60),
    source: String(body.source || 'site').slice(0, 60),
    ...attributionFields(body),
    // Стадия воронки с первой секунды: заявка без статуса не попадает ни в один
    // фильтр воронки и теряется из виду, хотя формально сохранена.
    status: 'new',
    // Ответственный по умолчанию — распоряжение руководителя 21.08.2026.
    // Заявка без владельца ничья, и о ней забывают.
    owner: defaultLeadOwner,
  };

  let leadId: string | number | null = null;
  try {
    leadId = await createLeadTolerant(payload);
  } catch (e) {
    console.error('createLead failed', e);
    return new Response(JSON.stringify({ error: 'не удалось сохранить заявку' }), { status: 502 });
  }

  // Зеркало в Bitrix24: копия обращения в окно, в котором работает менеджер.
  // Источник воронки остаётся здесь, в Directus (docs/rules/crm-mirror.md).
  // Отдельным фоном от письма: отказ одного канала не должен гасить другой,
  // а ошибка портала — доходить до заказчика, у которого заявка уже принята.
  const attr = attributionFields(body);
  mirrorLeadAndLink(leadId, {
    title: `Заявка с сайта — ${payload.company}`,
    name: payload.name,
    company: payload.company,
    inn: payload.inn,
    email: payload.email,
    phone: payload.phone,
    comments: payload.message,
    formSource: payload.form_source,
    channel: attr.last_touch_source,
    productRef: payload.product_ref,
    consentEventId: consent.personalDataEventId,
    marketingStatus: consent.marketingStatus === 'subscribed' ? 'subscribed' : 'not_subscribed',
    utm: {
      utm_source: attr.utm_source,
      utm_medium: attr.utm_medium,
      utm_campaign: attr.utm_campaign,
      utm_content: attr.utm_content,
      utm_term: attr.utm_term,
    },
  }).catch((e) => console.error('b24 mirror failed', e));

  // Разбор обращения по каталогу — один на оба письма. Каталог читается с
  // кэшем, но это всё равно внешний вызов: его отказ не должен отменять ни
  // письмо заказчику, ни письмо менеджеру, поэтому пустой разбор здесь
  // штатный исход (docs/rules/lead-confirmation-email.md).
  const reviewPromise: Promise<LeadRequestReview | null> = getProducts()
    .then((products) => identifyRequest(products, {
      productRef: payload.product_ref,
      message: payload.message,
      cart,
    }))
    .catch((e) => {
      console.error('lead request review failed', e);
      return null;
    });

  // Подтверждение заказчику: обращение принято, вот что мы получили и что
  // будет дальше. До 21.09.2026 письма не было вовсе — человек оставлял
  // реквизиты и не получал в почту ни строки, а надпись на экране жила до
  // закрытия вкладки (docs/rules/lead-confirmation-email.md).
  //
  // Фоном и с проглоченной ошибкой: заявка уже сохранена, и сбой SMTP не
  // должен превращаться в отказ на экране у человека, чьё обращение принято.
  // Письмо себе (ниже) отправляется отдельно — падение одного канала не
  // гасит другой.
  (async () => {
    const review = await reviewPromise;
    const mail = buildCustomerLeadEmail({
      lead: {
        name: payload.name,
        company: payload.company,
        inn: payload.inn,
        email: payload.email,
        phone: payload.phone,
        message: payload.message,
        product_ref: payload.product_ref,
        date: new Date().toLocaleDateString('ru-RU'),
      },
      hasQuestion: review?.hasQuestion,
      request: review ? { ...review.request, links: leadLinks(review, site.url) } : undefined,
    });
    await sendMail({
      from: salesFrom,
      to: payload.email,
      replyTo: managerEmail,
      subject: mail.subject,
      text: mail.text,
      html: mail.html,
    });
  })().catch((e) => console.error('lead customer mail failed', e));

  // Уведомление менеджеру: фирменное HTML-письмо с источником перехода,
  // сверкой ИНН с ЕГРЮЛ и карточкой организации. Собирается в фоне и не
  // блокирует ответ клиенту: сверка ходит во внешний справочник.
  (async () => {
    const innCheck = await verifyCompany(payload.inn, payload.company);
    const party = innCheck.valid ? await findParty(payload.inn).catch(() => null) : null;
    const review = await reviewPromise;
    const mail = buildManagerLeadEmail({
      review: review ? {
        vendor: review.request.vendor,
        product: review.request.product,
        matched: Boolean(review.request.matched),
        qty: review.request.qty,
        term: review.term?.label,
        notes: review.notes,
        candidates: review.candidates.map((p) => p.name),
      } : null,
      lead: {
        name: payload.name,
        company: payload.company,
        inn: payload.inn,
        email: payload.email,
        phone: payload.phone,
        message: payload.message,
        product_ref: payload.product_ref,
        form_source: payload.form_source,
        date: new Date().toLocaleDateString('ru-RU'),
      },
      attribution: attributionFields(body),
      innCheck,
      party,
    });
    await sendMail({
      to: managerEmail,
      replyTo: payload.email,
      subject: mail.subject,
      text: mail.text,
      html: mail.html,
    });
  })().catch((e) => console.error('lead mail failed', e));

  return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'Content-Type': 'application/json' } });
};
