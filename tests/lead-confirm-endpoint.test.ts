/**
 * Повтор подтверждения по уже принятой заявке (`/api/admin/lead-confirm`).
 *
 * Разбор 21.09.2026: первый живой прогон `ops-lead-confirm` упал с «нужен
 * email или lead_id». Адрес заказчика лежит в базе, у оператора прогона его
 * нет — требование сообщить то, чего он не знает, закрывало операцию совсем.
 * Теперь пустые параметры означают самую свежую заявку, а сухой прогон
 * показывает, кого выбрали, до любой отправки.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';
import type { Product } from '../src/lib/types';

const sendMail = vi.fn(async () => true);
const LEADS = [
  {
    id: 42, email: 'fresh@example.ru', name: 'Иванов Иван Иванович',
    company: 'АО «ЭКСАР»', inn: '7704792651', phone: '+7 495 000-00-00',
    message: 'Требуется закупка 3-х лицензий Perplexity Personal PRO на 6 месяцев.',
    product_ref: 'количество: 3', created_at: '2026-09-21T15:12:00Z',
  },
  {
    id: 41, email: 'older@example.ru', name: 'Петров Пётр',
    company: 'ООО «Ромашка»', message: 'Нужен счёт.', product_ref: '',
    created_at: '2026-09-20T10:00:00Z',
  },
];

vi.mock('../src/lib/directus', () => ({
  getLeads: async () => LEADS,
  getProducts: async (): Promise<Product[]> => [],
}));

vi.mock('../src/lib/mailer', () => ({
  sendMail: (...a: unknown[]) => sendMail(...(a as [])),
  managerEmail: 'avbelyaev@biz-soft.pro',
  salesFrom: 'BizSoft <hello@biz-soft.pro>',
}));

vi.mock('../src/lib/admin-auth', () => ({
  isAdminConfigured: () => true,
  checkAdmin: () => true,
  unauthorized: () => new Response('no', { status: 401 }),
}));

const { POST } = await import('../src/pages/api/admin/lead-confirm');

const call = (body: Record<string, unknown>) =>
  (POST as (ctx: { request: Request }) => Promise<Response>)({
    request: new Request('https://biz-soft.pro/api/admin/lead-confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  }).then((r) => r.json() as Promise<Record<string, unknown>>);

beforeEach(() => sendMail.mockClear());

describe('выбор заявки', () => {
  it('без параметров берётся самая свежая', async () => {
    const d = await call({});
    expect(d.picked).toBe('самая свежая');
    expect(d.lead_id).toBe(42);
    expect(d.client_email).toBe('fresh@example.ru');
  });

  it('адрес и идентификатор выбирают конкретную заявку', async () => {
    expect((await call({ email: 'older@example.ru' })).lead_id).toBe(41);
    expect((await call({ lead_id: 41 })).lead_id).toBe(41);
  });

  it('заявки нет — отказ, а не отправка наугад', async () => {
    const d = await call({ email: 'нет-такого@example.ru' });
    expect(d.error).toBe('заявка не найдена');
    expect(sendMail).not.toHaveBeenCalled();
  });
});

describe('режимы отправки', () => {
  it('сухой прогон ничего не отправляет', async () => {
    const d = await call({});
    expect(d.sent).toBe(false);
    expect(sendMail).not.toHaveBeenCalled();
  });

  it('test шлёт копию менеджеру с пометкой о задержке', async () => {
    const d = await call({ dry_run: false });
    expect(d.to).toBe('avbelyaev@biz-soft.pro');
    expect(String(d.subject)).toContain('(отправлено с задержкой)');
    expect(d.sent).toBe(true);
    const mail = sendMail.mock.calls[0][0] as { to: string; html: string };
    // Письмо то же, что получит заказчик: тот же разбор и та же вёрстка.
    expect(mail.html).toContain('Обращение принято');
    expect(mail.html).toContain('Уважаемый Иван Иванович!');
  });

  it('явный адрес перекрывает MANAGER_EMAIL сервера', async () => {
    // На проде MANAGER_EMAIL — общий ящик, а письма руководителю положено
    // слать на личный адрес (docs/rules/mail-recipient.md).
    const d = await call({ to: 'avbelyaev@biz-soft.pro', dry_run: false });
    expect(d.to).toBe('avbelyaev@biz-soft.pro');
    expect((sendMail.mock.calls[0][0] as { to: string }).to).toBe('avbelyaev@biz-soft.pro');
  });

  it('в режиме client явный адрес игнорируется — письмо идёт заказчику', async () => {
    const d = await call({ mode: 'client', to: 'avbelyaev@biz-soft.pro', dry_run: false });
    expect(d.to).toBe('fresh@example.ru');
  });

  it('client шлёт заказчику и не приписывает ничего к теме', async () => {
    const d = await call({ mode: 'client', dry_run: false });
    expect(d.to).toBe('fresh@example.ru');
    expect(String(d.subject)).not.toContain('задержкой');
    expect((sendMail.mock.calls[0][0] as { to: string }).to).toBe('fresh@example.ru');
  });
});
