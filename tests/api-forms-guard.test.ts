/**
 * Публичные эндпоинты форм под защитой (SEC-RL-001).
 *
 * Отдельно от tests/form-guard.test.ts: там проверяются решения стража,
 * здесь — что эндпоинт действительно спрашивает его ПЕРВЫМ, до записи в базу
 * и до письма. Проверка не про код, а про счёт: отклонённое обращение не
 * должно стоить ни строки в базе, ни отправленного письма.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { HONEYPOT_FIELD, OPENED_AT_FIELD, HOURLY_LIMIT } from '../src/lib/form-guard';

const createLead = vi.fn(async () => {});
const sendMail = vi.fn(async () => {});

vi.mock('../src/lib/directus', () => ({
  createLead: (...a: unknown[]) => createLead(...(a as [])),
  // Хранилище лимитов в тестах — в памяти (tests/setup.ts), до этих двух
  // дело не доходит; заглушки нужны, чтобы импорт модуля не разъехался.
  kvGet: async () => null,
  kvPut: async () => {},
  DirectusError: class extends Error { status = 0 },
}));

vi.mock('../src/lib/mailer', () => ({
  sendMail: (...a: unknown[]) => sendMail(...(a as [])),
  managerEmail: 'manager@biz-soft.pro',
  salesFrom: 'BizSoft <hello@biz-soft.pro>',
}));

const { POST } = await import('../src/pages/api/lead');

/** Заполненная человеком форма: все поля на месте, форма открыта минуту назад. */
const filled = (extra: Record<string, unknown> = {}) => ({
  name: 'Екатерина Кувшинова',
  company: 'ООО «Ромашка»',
  email: 'k@romashka.ru',
  phone: '+79167898651',
  message: 'Нужен расчёт на 10 мест',
  consent: true,
  [OPENED_AT_FIELD]: Date.now() - 60_000,
  ...extra,
});

const post = (body: Record<string, unknown>, ip = '203.0.113.10') =>
  (POST as (ctx: { request: Request }) => Promise<Response>)({
    request: new Request('https://biz-soft.pro/api/lead', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Real-IP': ip },
      body: JSON.stringify(body),
    }),
  });

beforeEach(() => {
  createLead.mockClear();
  sendMail.mockClear();
});

describe('POST /api/lead', () => {
  it('обычная заявка проходит и доходит до базы', async () => {
    const res = await post(filled());
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ ok: true });
    expect(createLead).toHaveBeenCalledTimes(1);
  });

  it('заполненная приманка отбрасывается молча — без заявки и без письма', async () => {
    const res = await post(filled({ [HONEYPOT_FIELD]: 'https://spam.example' }));
    // Роботу отвечаем как при успехе: отказ подсказал бы, что надо обойти.
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ ok: true });
    expect(createLead).not.toHaveBeenCalled();
    expect(sendMail).not.toHaveBeenCalled();
  });

  it('отправка быстрее трёх секунд после открытия отклоняется', async () => {
    const res = await post(filled({ [OPENED_AT_FIELD]: Date.now() - 500 }));
    expect(res.status).toBe(422);
    expect((await res.json()).error).toMatch(/слишком быстро/);
    expect(createLead).not.toHaveBeenCalled();
  });

  it('превышение порога даёт 429 с понятным текстом, а не отказ без причины', async () => {
    const ip = '198.51.100.200';
    for (let i = 0; i < HOURLY_LIMIT; i++) {
      expect((await post(filled(), ip)).status).toBe(200);
    }
    const res = await post(filled(), ip);
    expect(res.status).toBe(429);
    expect(res.headers.get('Retry-After')).toBe('3600');
    const body = await res.json();
    expect(body.error).toMatch(/подождите|откроется/i);
    expect(body.error).toMatch(/позвоните/i);
    // Главное: сверх порога мы не заводим заявок и не шлём писем.
    expect(createLead).toHaveBeenCalledTimes(HOURLY_LIMIT);
  });

  it('порог одного адреса не закрывает форму соседям', async () => {
    const ip = '198.51.100.201';
    for (let i = 0; i <= HOURLY_LIMIT; i++) await post(filled(), ip);
    expect((await post(filled(), '198.51.100.202')).status).toBe(200);
  });

  it('опечатка в форме не расходует порог живого человека', async () => {
    // Пять промахов мимо обязательных полей не должны закрыть форму до
    // конца часа: порог тратят заявки, а не попытки их отправить.
    const ip = '198.51.100.204';
    for (let i = 0; i < 5; i++) {
      const res = await post(filled({ phone: '' }), ip);
      expect(res.status).toBe(422);
    }
    expect((await post(filled(), ip)).status).toBe(200);
  });

  it('страж стоит до проверки полей — мусорная форма не тратит порог', async () => {
    // Иначе робот выжигал бы окно живых людей за тем же адресом NAT,
    // ничего толком не отправляя.
    const ip = '198.51.100.203';
    for (let i = 0; i < 10; i++) {
      const res = await post({ [HONEYPOT_FIELD]: 'x', ...filled() }, ip);
      expect(res.status).toBe(200);
    }
    expect((await post(filled(), ip)).status).toBe(200);
    expect(createLead).toHaveBeenCalledTimes(1);
  });
});
