/**
 * Почтовые шаблоны КП: HTML + обязательный text-fallback.
 *
 * Проверяется содержимое, безопасность (экранирование пользовательских
 * полей) и договорённости 28.08.2026: оговорка «не оферта» в письме
 * клиенту, предупреждение о внутреннем Excel в письме руководителю,
 * ⚠ в теме проблемной заявки.
 */
import { describe, expect, it } from 'vitest';
import { buildCustomerQuoteEmail } from '../src/lib/email/quote-customer';
import { buildManagerQuoteEmail } from '../src/lib/email/quote-manager';
import { buildQuoteEconomics } from '../src/lib/quote-economics';
import type { Product } from '../src/lib/types';

const data = {
  quoteNo: 'BZ-20260828-0042',
  date: '28.08.2026',
  validUntil: '04.09.2026',
  buyerCompany: 'ООО «Ромашка» <script>',
  buyerInn: '7701234567',
  contactName: 'Иванов Иван Иванович',
  email: 'ivanov@example.ru',
  phone: '+7 916 000-00-00',
  items: [
    { sku: 'A', name: 'Товар А', qty: 10, price: 105000, sum: 1050000 },
  ],
  total: 1050000,
};

describe('письмо клиенту', () => {
  const mail = buildCustomerQuoteEmail(data);

  it('есть и HTML, и text-fallback с одним содержимым', () => {
    expect(mail.html).toContain('<!DOCTYPE html>');
    for (const part of ['BZ-20260828-0042', 'не является публичной офертой',
                        '100% аванс', '04.09.2026']) {
      expect(mail.html).toContain(part);
      expect(mail.text).toContain(part);
    }
  });

  it('обращение по имени, а не по всему полю ФИО', () => {
    expect(mail.text).toContain('Уважаемый Иван Иванович!');
  });

  it('пользовательские поля экранируются в HTML', () => {
    expect(mail.html).not.toContain('<script>');
    expect(mail.html).toContain('&lt;script&gt;');
  });

  it('приглашает ответить на письмо — путь к менеджеру', () => {
    expect(mail.html).toContain('ответьте на это письмо');
    expect(mail.text).toContain('Ответьте на это письмо');
  });

  it('вёрстка без внешних ресурсов', () => {
    expect(mail.html).not.toMatch(/src="http|<link|<script/);
  });
});

describe('письмо руководителю', () => {
  const product = (sku: string, extra: Partial<Product> = {}): Product => ({
    id: 1, name: sku, sku, vendor: 'v', origin: '', slug: sku.toLowerCase(),
    price: 0, currency: 'RUB', status: 'published', ...extra,
  } as unknown as Product);
  const fx = { usd: 85, eur: 92, date: '28.08.2026' };
  const eco = buildQuoteEconomics(data.items, [product('A', { base_price_usd: 700 })], fx);

  const ok = buildManagerQuoteEmail({
    data, innCheck: { valid: true, verdict: 'ИНН корректен', nameMatch: 'match' },
    partyCard: ['ООО «Ромашка»'], partyActive: true, eco,
  });

  it('чистая заявка — без ⚠ в теме', () => {
    expect(ok.subject.startsWith('⚠')).toBe(false);
    expect(ok.subject).toContain('BZ-20260828-0042');
  });

  it('проблемная заявка помечается ⚠ в теме', () => {
    for (const bad of [
      { valid: false, verdict: 'не сошлась', nameMatch: 'not_checked' },
      { valid: true, verdict: 'ок', nameMatch: 'mismatch' },
    ]) {
      const m = buildManagerQuoteEmail({ data, innCheck: bad, partyCard: [], partyActive: null, eco });
      expect(m.subject.startsWith('⚠ ')).toBe(true);
    }
    const dead = buildManagerQuoteEmail({
      data, innCheck: { valid: true, verdict: 'ок', nameMatch: 'match' },
      partyCard: [], partyActive: false, eco,
    });
    expect(dead.subject.startsWith('⚠ ')).toBe(true);
  });

  it('экономика в карточке: закупка и прибыль', () => {
    expect(ok.html).toContain('Экономика сделки');
    expect(ok.html).toContain('Ожидаемая прибыль');
    expect(ok.text).toContain('Ожидаемая прибыль');
  });

  it('предупреждение про внутренний Excel — и в HTML, и в тексте', () => {
    expect(ok.html).toContain('удалить из вложений');
    expect(ok.text).toContain('ВНУТРЕННЯЯ');
  });

  it('без курса ЦБ письмо честно говорит, что экономики нет', () => {
    const m = buildManagerQuoteEmail({
      data, innCheck: { valid: true, verdict: 'ок', nameMatch: 'match' },
      partyCard: [], partyActive: null, eco: null,
    });
    expect(m.html).toContain('Экономику посчитать не удалось');
  });

  it('неполная закупка — предупреждение о завышенной прибыли', () => {
    const partial = buildQuoteEconomics(
      [...data.items, { sku: 'B', name: 'Б', qty: 1, price: 100, sum: 100 }],
      [product('A', { base_price_usd: 700 }), product('B')], fx);
    const m = buildManagerQuoteEmail({
      data, innCheck: { valid: true, verdict: 'ок', nameMatch: 'match' },
      partyCard: [], partyActive: null, eco: partial,
    });
    expect(m.html).toContain('прибыль посчитана без них');
    expect(m.text).toContain('прибыль завышена');
  });
});
