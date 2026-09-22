/**
 * Путь «подборка → заявка → письмо».
 *
 * Разбор 21.09.2026: посетитель прошёл / → /cart → /contacts, в корзине
 * лежали точные артикулы, а в заявку ушла одна строка «количество: 3» —
 * и ни письмо заказчику, ни менеджер предмета обращения не видели. Здесь
 * проверяется, что состав подборки доезжает до заявки и до письма, а при
 * недоступном каталоге заявка всё равно принимается.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { OPENED_AT_FIELD } from '../src/lib/form-guard';
import type { Product } from '../src/lib/types';

const createLead = vi.fn(async () => 'lead-1');
const sendMail = vi.fn(async () => true);
const getProducts = vi.fn(async (): Promise<Product[]> => CATALOG);

const CATALOG = [{
  id: 1, name: 'Adobe Creative Cloud Pro для команд (все приложения)',
  sku: 'ADBE-LIC-CCPRO-TEAM-1Y-USER', slug: 'adobe-cc-pro-team',
  vendor: 'Adobe', category: null,
}, {
  id: 2, name: 'Adobe Creative Cloud Pro (все приложения)',
  sku: 'ADBE-LIC-CCPRO-IND-1Y-USER', slug: 'adobe-cc-pro',
  vendor: 'Adobe', category: null,
}, {
  id: 3, name: 'Perplexity Enterprise Pro', sku: 'PPLX-LIC-ENTPRO-TEAM-1Y-USER',
  slug: 'perplexity-enterprise-pro', vendor: 'Perplexity', category: null,
}] as unknown as Product[];

vi.mock('../src/lib/directus', () => ({
  createLead: (...a: unknown[]) => createLead(...(a as [])),
  getProducts: () => getProducts(),
  kvGet: async () => null,
  kvPut: async () => {},
  createConsentEvent: async () => {},
  findMarketingEntry: async () => null,
  createMarketingEntry: async () => {},
  patchMarketingEntry: async () => {},
  DirectusError: class extends Error { status = 0 },
}));

vi.mock('../src/lib/mailer', () => ({
  sendMail: (...a: unknown[]) => sendMail(...(a as [])),
  managerEmail: 'manager@biz-soft.pro',
  salesFrom: 'BizSoft <hello@biz-soft.pro>',
}));

const { POST } = await import('../src/pages/api/lead');

const post = (extra: Record<string, unknown>) =>
  (POST as (ctx: { request: Request }) => Promise<Response>)({
    request: new Request('https://biz-soft.pro/api/lead', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Real-IP': '203.0.113.77' },
      body: JSON.stringify({
        name: 'Иванов Иван Иванович',
        company: 'АО «ЭКСАР»',
        inn: '7704792651',
        email: 'ivanov@example.ru',
        phone: '+79160000000',
        message: 'Нужен расчёт.',
        consent: true,
        [OPENED_AT_FIELD]: Date.now() - 60_000,
        ...extra,
      }),
    }),
  });

/** Письмо заказчику: оно единственное уходит на адрес из формы. */
const customerMail = () => sendMail.mock.calls
  .map((c) => c[0] as { to: string; html: string })
  .find((m) => m.to === 'ivanov@example.ru');

const managerMail = () => sendMail.mock.calls
  .map((c) => c[0] as { to: string; html: string })
  .find((m) => m.to === 'manager@biz-soft.pro');

/** Письма уходят фоном: ждём, пока обработчик их допишет. */
const settle = () => new Promise((r) => setTimeout(r, 30));

beforeEach(() => {
  createLead.mockClear();
  sendMail.mockClear();
  getProducts.mockClear();
  getProducts.mockImplementation(async () => CATALOG);
});

describe('подборка доезжает до заявки и до письма', () => {
  it('состав пишется в заявку', async () => {
    const res = await post({
      product_ref: 'количество: 3',
      cart: [{ sku: 'ADBE-LIC-CCPRO-TEAM-1Y-USER', name: 'Adobe Creative Cloud Pro для команд', qty: 3 }],
    });
    expect(res.status).toBe(200);
    const record = createLead.mock.calls[0][0] as Record<string, string>;
    expect(JSON.parse(record.cart_items)).toEqual([
      { sku: 'ADBE-LIC-CCPRO-TEAM-1Y-USER', name: 'Adobe Creative Cloud Pro для команд', qty: 3 },
    ]);
  });

  it('письмо заказчику называет позицию из подборки, а не гадает по тексту', async () => {
    await post({
      product_ref: 'количество: 3',
      cart: [{ sku: 'ADBE-LIC-CCPRO-TEAM-1Y-USER', name: 'Adobe Creative Cloud Pro для команд', qty: 3 }],
    });
    await settle();
    const mail = customerMail();
    expect(mail?.html).toContain('Adobe Creative Cloud Pro для команд (все приложения)');
    expect(mail?.html).toContain('Командная');
    // Ссылки собраны по слагу каталога, включая другой план того же продукта.
    expect(mail?.html).toContain('https://biz-soft.pro/product/adobe-cc-pro-team');
    expect(mail?.html).toContain('https://biz-soft.pro/product/adobe-cc-pro');
    expect(mail?.html).toContain('https://biz-soft.pro/vendors/adobe');
  });

  it('разбор доходит до письма менеджеру', async () => {
    await post({ message: 'Нужен Perplexity Personal PRO, 3 лицензии на 6 месяцев.' });
    await settle();
    const mail = managerMail();
    expect(mail?.html).toContain('Разбор обращения');
    // Название клиента показано, но помечено как неподтверждённое: по нему
    // нельзя выставить счёт.
    expect(mail?.html).toContain('Personal PRO');
    expect(mail?.html).toContain('в каталоге не найдена');
    expect(mail?.html).toContain('Perplexity Enterprise Pro');
  });

  it('несколько позиций подборки названы перечислением', async () => {
    await post({
      cart: [
        { sku: 'ADBE-LIC-CCPRO-TEAM-1Y-USER', name: 'Adobe CC Pro для команд', qty: 3 },
        { sku: 'PPLX-LIC-ENTPRO-TEAM-1Y-USER', name: 'Perplexity Enterprise Pro', qty: 5 },
      ],
    });
    await settle();
    const mail = customerMail();
    // Обе позиции, у каждой свой тип лицензии и количество.
    expect(mail?.html).toContain('Adobe Creative Cloud Pro для команд (все приложения)');
    expect(mail?.html).toContain('Perplexity Enterprise Pro');
    expect(mail?.html).toContain('Командная · 3 шт.');
    expect(mail?.html).toContain('Командная · 5 шт.');
    // Ссылки — на каждую позицию.
    expect(mail?.html).toContain('/product/adobe-cc-pro-team');
    expect(mail?.html).toContain('/product/perplexity-enterprise-pro');
    // Другой план к подборке из нескольких строк не предлагается: замена
    // относилась бы к одной из позиций, а к какой — письмо не знает.
    expect(mail?.html).not.toContain('/product/adobe-cc-pro?');
  });

  it('позиция подборки, снятая из каталога, в письмо не попадает', async () => {
    await post({
      cart: [
        { sku: 'НЕТ-ТАКОГО-АРТИКУЛА', name: 'Снятая позиция', qty: 1 },
        { sku: 'PPLX-LIC-ENTPRO-TEAM-1Y-USER', name: 'Perplexity Enterprise Pro', qty: 2 },
      ],
    });
    await settle();
    const mail = customerMail();
    expect(mail?.html).toContain('Perplexity Enterprise Pro');
    expect(mail?.html).not.toContain('Снятая позиция');
  });

  it('подпись письма называет личную почту менеджера, а не общий ящик', async () => {
    await post({});
    await settle();
    const mail = customerMail();
    expect(mail?.html).toContain('mailto:avbelyaev@biz-soft.pro');
    expect(mail?.text).toContain('avbelyaev@biz-soft.pro');
  });

  it('вопрос в обращении отмечен в письме заказчику', async () => {
    await post({ message: 'Возможна ли оплата по счёту-оферте?' });
    await settle();
    expect(customerMail()?.html).toContain('ответит менеджер');
  });

  it('каталог недоступен — заявка принята, письмо ушло без разбора', async () => {
    getProducts.mockImplementation(async () => { throw new Error('directus down'); });
    const res = await post({ product_ref: 'количество: 3' });
    await settle();
    expect(res.status).toBe(200);
    expect(createLead).toHaveBeenCalledTimes(1);
    const mail = customerMail();
    expect(mail?.html).toContain('Обращение принято');
    expect(mail?.html).not.toContain('Производитель');
  });

  it('мусор в составе подборки заявку не роняет', async () => {
    const res = await post({ cart: [{ sku: 42 }, null, { name: 'x'.repeat(500), qty: -5 }] });
    expect(res.status).toBe(200);
    const record = createLead.mock.calls[0][0] as Record<string, string>;
    const saved = JSON.parse(record.cart_items);
    expect(saved).toHaveLength(1);
    expect(saved[0].name).toHaveLength(200);
    expect(saved[0].qty).toBe(1);
  });
});
