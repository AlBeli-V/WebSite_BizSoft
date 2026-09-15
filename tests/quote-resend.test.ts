/**
 * Повторная отправка выпущенного КП (`/api/admin/quote-resend`).
 *
 * Проверяется не «письмо ушло», а границы инструмента: он закрыт токеном,
 * ничего не создаёт в базе, берёт цены из сохранённой записи (а не из
 * сегодняшнего каталога) и добирает производителя по артикулу — иначе
 * описание позиции осталось бы без юрлица.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';

// Заголовок HTTP принимает только латиницу — токен настоящего вида.
process.env.ADMIN_TOOLS_TOKEN = 'test-admin-token-0001';

const sendMail = vi.fn(async () => {});
const getQuotes = vi.fn(async () => QUOTES);
const getProductsBySkus = vi.fn(async () => [
  { sku: 'ANTH-LIC-CLAUDETEAM-TEAM-1Y-USER-STD', vendor: 'Anthropic' },
]);

const QUOTES = [
  {
    id: 2,
    created_at: '2026-09-15T08:00:00Z',
    quote_no: 'BZ-20260915-29343',
    buyer_company: 'ООО «ИТ МАТРИЦА»',
    buyer_inn: '7724329635',
    contact_name: 'Беляев',
    email: 'AVBelyaev@matrix-it.ru',
    phone: '+7 (964) 716-11-11',
    // Позиция старого КП: производителя в записи нет, цена есть.
    items: [{ sku: 'ANTH-LIC-CLAUDETEAM-TEAM-1Y-USER-STD', name: 'Claude Team, Standard seat', qty: 2, price: 38421, sum: 76842 }],
    total: 76842,
  },
  {
    id: 1,
    created_at: '2026-09-01T08:00:00Z',
    quote_no: 'BZ-20260901-0001',
    buyer_company: 'Другая компания',
    email: 'other@example.com',
    items: [{ sku: 'X', name: 'Позиция', qty: 1, price: 100, sum: 100 }],
    total: 100,
  },
];

vi.mock('../src/lib/directus', () => ({
  getQuotes: (...a: unknown[]) => getQuotes(...(a as [])),
  getProductsBySkus: (...a: unknown[]) => getProductsBySkus(...(a as [])),
}));

vi.mock('../src/lib/mailer', () => ({
  sendMail: (...a: unknown[]) => sendMail(...(a as [])),
  managerEmail: 'manager@biz-soft.pro',
  salesFrom: 'BizSoft <hello@biz-soft.pro>',
}));

const { POST } = await import('../src/pages/api/admin/quote-resend');

const call = (body: unknown, token = 'test-admin-token-0001') => POST({
  request: new Request('https://biz-soft.pro/api/admin/quote-resend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-admin-token': token },
    body: JSON.stringify(body),
  }),
} as never) as Promise<Response>;

describe('повтор выпущенного КП', () => {
  beforeEach(() => { sendMail.mockClear(); getQuotes.mockClear(); });

  it('без токена администратора инструмент не отвечает', async () => {
    const res = await call({ email: 'AVBelyaev@matrix-it.ru' }, 'wrong-token-0000000001');
    expect(res.status).toBe(401);
    expect(sendMail).not.toHaveBeenCalled();
  });

  it('находит последнее КП по почте клиента и считает листы', async () => {
    const res = await call({ email: 'avbelyaev@matrix-it.ru', dry_run: true });
    const out = await res.json();
    expect(res.status).toBe(200);
    expect(out.quote_no).toBe('BZ-20260915-29343');
    expect(out.sheets).toBeGreaterThan(0);
    // Сухой прогон ничего не отправляет: сначала смотрим состав.
    expect(out.sent).toBe(false);
    expect(sendMail).not.toHaveBeenCalled();
  });

  it('отправляет клиентский PDF, макет и Word одним письмом с пометкой о повторе', async () => {
    const res = await call({ email: 'avbelyaev@matrix-it.ru', to: 'me@biz-soft.pro' });
    const out = await res.json();
    expect(out.sent).toBe(true);
    expect(sendMail).toHaveBeenCalledTimes(1);
    const mail = sendMail.mock.calls[0][0] as unknown as {
      to: string; subject: string; attachments: { filename: string }[] };
    expect(mail.to).toBe('me@biz-soft.pro');
    expect(mail.subject).toContain('(ТЕСТ ПОВТОР)');
    expect(mail.subject).toContain('BZ-20260915-29343');
    const names = mail.attachments.map((a) => a.filename);
    // Клиентский документ — ровно тот файл, что уходит заказчику; рядом
    // рабочие форматы менеджера. Листов картинками больше нет.
    expect(names.some((n) => n.startsWith('КП_BIZSoft_') && n.endsWith('.pdf'))).toBe(true);
    expect(names.some((n) => n.endsWith('.jpg'))).toBe(false);
    expect(names).toContain('KP_BZ-20260915-29343_макет.pdf');
    expect(names).toContain('KP_BZ-20260915-29343.docx');
  });

  it('цены берутся из записи, а не пересчитываются по каталогу', async () => {
    const res = await call({ quote_no: 'BZ-20260915-29343', dry_run: true });
    const out = await res.json();
    // 38 421 × 2 — ровно то, что клиент получил в оригинале.
    expect(out.total).toBe(76842);
  });

  it('несуществующее КП — понятная ошибка, а не пустое письмо', async () => {
    const res = await call({ quote_no: 'BZ-НЕТ-ТАКОГО' });
    expect(res.status).toBe(404);
    expect(sendMail).not.toHaveBeenCalled();
  });
});
