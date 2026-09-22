export const prerender = false;

/**
 * Отправка подтверждения по уже принятой заявке — задним числом.
 *
 * Нужна ровно для одного случая: контур подтверждения заведён 21.09.2026, а
 * заявки до него остались без письма. Человек оставил реквизиты и не получил
 * ни строки; лучше написать ему с задержкой, чем не написать вовсе
 * (решение руководителя 21.09.2026).
 *
 * Эндпоинт ничего не создаёт и ничего не меняет: берёт заявку из Directus,
 * собирает то же письмо, что уходит из `/api/lead`, и отправляет. Ни заявки,
 * ни событий, ни зеркала в Bitrix24.
 *
 * Два режима: `test` (по умолчанию) шлёт письмо менеджеру — точную копию
 * того, что получит заказчик, для проверки в боевой почте; `client` шлёт
 * заказчику на адрес из заявки. Сухой прогон показывает состав и адрес и не
 * отправляет ничего.
 *
 * Доступ — по токену админ-инструментов (`x-admin-token`), как у остальных
 * инструментов в `/api/admin/*`. Вызывается прогоном `ops-lead-confirm`
 * изнутри сервера; наружу эндпоинт не публикуется и в sitemap не попадает.
 */
import type { APIRoute } from 'astro';
import { checkAdmin, isAdminConfigured, unauthorized } from '../../../lib/admin-auth';
import { getLeads, getProducts } from '../../../lib/directus';
import { buildCustomerLeadEmail } from '../../../lib/email/lead-customer';
import { identifyRequest, leadLinks } from '../../../lib/lead-request';
import { cartItems } from '../../../lib/quote-lead';
import { managerEmail, salesFrom, sendMail } from '../../../lib/mailer';
import { site } from '../../../config/site';

/** Приписка в теме: получатель должен видеть, что письмо пришло с задержкой. */
const LATE_PREFIX = '(отправлено с задержкой)';

interface Body {
  /**
   * Почта заказчика, чью заявку подтверждаем. Пусто и без `lead_id` —
   * берётся самая свежая заявка: адрес заказчика лежит в базе и в руках у
   * оператора прогона его нет, а требовать то, чего он не знает, значит
   * закрыть операцию совсем. Сухой прогон по умолчанию показывает, кого
   * нашли, — ошибиться адресатом молча нельзя.
   */
  email?: string;
  /** Идентификатор заявки; задан — ищем по нему, а не по почте. */
  lead_id?: string | number;
  /**
   * `test` (по умолчанию) — копия письма менеджеру для проверки в боевой
   * почте. `client` — письмо заказчику на адрес из заявки.
   */
  mode?: 'test' | 'client';
  /**
   * Куда слать проверочную копию. Пусто — `MANAGER_EMAIL` сервера; на проде
   * это общий ящик, а письма руководителю положено слать на его личный
   * адрес (docs/rules/mail-recipient.md), поэтому адрес задаётся явно.
   * В режиме `client` вход игнорируется: там адресат — заказчик из заявки.
   */
  to?: string;
  /** true — показать состав и ничего не отправлять. */
  dry_run?: boolean;
  /** Приписка в теме для режима `client`; пусто — без приписки. */
  subject_note?: string;
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

/** Дата заявки в виде дд.мм.гггг — та же, что стоит в письме дня отправки. */
function leadDate(raw: unknown): string {
  const d = raw ? new Date(String(raw)) : new Date();
  return Number.isNaN(d.getTime())
    ? new Date().toLocaleDateString('ru-RU')
    : d.toLocaleDateString('ru-RU');
}

export const POST: APIRoute = async ({ request }) => {
  if (!isAdminConfigured() || !checkAdmin(request)) return unauthorized();

  let body: Body;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'bad json' }, 400);
  }

  const wantedEmail = String(body.email || '').trim().toLowerCase();
  const wantedId = String(body.lead_id ?? '').trim();
  const mode = body.mode === 'client' ? 'client' : 'test';
  const dryRun = body.dry_run !== false;

  // Заявки читаются пачкой и фильтруются здесь: отдельного чтения по полю в
  // слое Directus нет, а заводить его ради одноразовой операции незачем.
  // Заявки приходят свежими сверху (`sort: -created_at`), поэтому «без
  // параметров» — это первая в списке.
  const leads = await getLeads(500) as unknown as Record<string, unknown>[];
  const lead = wantedId
    ? leads.find((l) => String(l.id ?? '') === wantedId)
    : wantedEmail
      ? leads.find((l) => String(l.email || '').toLowerCase() === wantedEmail)
      : leads[0];
  if (!lead) return json({ error: 'заявка не найдена' }, 404);

  const customerEmail = String(lead.email || '').trim();
  if (!customerEmail) return json({ error: 'в заявке нет адреса' }, 422);

  const message = String(lead.message || '');
  const productRef = String(lead.product_ref || '');
  const cart = cartItems((() => {
    try {
      return lead.cart_items ? JSON.parse(String(lead.cart_items)) : [];
    } catch {
      return [];
    }
  })());

  // Разбор — тот же, что при живой отправке. Его отказ письмо не отменяет:
  // подтверждение без блоков лучше молчания, ради которого всё и затевалось.
  const review = await getProducts()
    .then((products) => identifyRequest(products, { productRef, message, cart }))
    .catch(() => null);

  const mail = buildCustomerLeadEmail({
    lead: {
      name: String(lead.name || ''),
      company: String(lead.company || ''),
      inn: String(lead.inn || ''),
      email: customerEmail,
      phone: String(lead.phone || ''),
      message,
      product_ref: productRef,
      date: leadDate(lead.created_at ?? lead.date_created),
    },
    hasQuestion: review?.hasQuestion,
    request: review ? {
      ...review.request,
      items: review.request.items?.map((i) => ({
        name: i.product.name, plan: i.plan, qty: i.qty,
      })),
      links: leadLinks(review, site.url),
    } : undefined,
  });

  const wantedTo = String(body.to || '').trim();
  const to = mode === 'client' ? customerEmail : (wantedTo || managerEmail);
  // Приписка в теме: в проверочной копии — всегда, заказчику — только если
  // её задали явно. Врать о дате письмо не должно, а объяснять задержку —
  // работа человека, не темы письма.
  const note = mode === 'client' ? String(body.subject_note || '').trim() : LATE_PREFIX;
  const subject = note ? `${note} ${mail.subject}` : mail.subject;

  const result = {
    ok: true,
    /** Как выбрали заявку: по запросу или «самая свежая». */
    picked: wantedId ? 'по id' : wantedEmail ? 'по адресу' : 'самая свежая',
    lead_id: lead.id ?? null,
    company: lead.company || '',
    client_email: customerEmail,
    date: leadDate(lead.created_at ?? lead.date_created),
    mode,
    to,
    subject,
    vendor: review?.request.vendor || '',
    product: review?.request.product || '',
    positions: review?.request.items?.length ?? 0,
    notes: review?.notes ?? [],
    sent: false,
  };
  if (dryRun) return json(result);

  await sendMail({
    from: salesFrom,
    to,
    replyTo: managerEmail,
    subject,
    text: mail.text,
    html: mail.html,
  });
  return json({ ...result, sent: true });
};
