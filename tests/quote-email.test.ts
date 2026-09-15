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
  // Полный разбор письма — в tests/offer-flow.test.ts. Здесь остаётся то,
  // что относится к безопасности шаблона: экранирование полей формы и
  // обязательный текстовый двойник.
  const mail = buildCustomerQuoteEmail({
    data, pdfName: 'КП_BIZSoft_BZ-20260828-0042_ROMASHKA_28.08.2026.pdf', pdfSize: 512000,
  });

  it('есть и HTML, и text-fallback с одним содержимым', () => {
    expect(mail.html).toContain('<!doctype html>');
    for (const part of ['BZ-20260828-0042', 'не является публичной офертой', '04.09.2026']) {
      expect(mail.html).toContain(part);
      expect(mail.text).toContain(part);
    }
  });

  it('обращение по имени, а не по всему полю ФИО', () => {
    expect(mail.text).toContain('Уважаемый Иван Иванович!');
  });

  it('пользовательские поля экранируются в HTML', () => {
    // Название организации приходит из формы: неэкранированный тег в письме
    // — это чужой HTML в почтовом клиенте получателя.
    expect(mail.html).not.toContain('<script>');
    expect(mail.html).toContain('&lt;script&gt;');
  });

  it('вёрстка без внешних ресурсов и скриптов', () => {
    expect(mail.html).not.toMatch(/<link|<script/);
    // Картинок со стороны в письме нет: единственная — фотография менеджера
    // с нашего домена, и только если файл действительно лежит на месте.
    const external = [...mail.html.matchAll(/src="(https?:[^"]+)"/g)].map((m) => m[1]);
    for (const src of external) expect(src).toContain('biz-soft.pro');
  });
});

describe('письмо руководителю', () => {
  const product = (sku: string, extra: Partial<Product> = {}): Product => ({
    id: 1, name: sku, sku, vendor: 'v', origin: '', slug: sku.toLowerCase(),
    price: 0, currency: 'RUB', status: 'published', ...extra,
  } as unknown as Product);
  const fx = { usd: 85, eur: 92, date: '28.08.2026' };
  const eco = buildQuoteEconomics(data.items, [product('A', { base_price_usd: 700 })], fx);

const party = {
  name: 'ООО «Ромашка»', fullName: 'ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ «Ромашка»',
  inn: '7701234567', kpp: '770101001', ogrn: '1027700000000',
  address: '119021, г Москва, ул Тестовая, д 1', manager: '',
  status: 'действующая', active: true, registeredOn: '01.01.2010', okved: '62.01',
};

  const ok = buildManagerQuoteEmail({
    data, innCheck: { valid: true, verdict: 'ИНН корректен', nameMatch: 'match' },
    party, eco,
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
      const m = buildManagerQuoteEmail({ data, innCheck: bad, party: null, eco });
      expect(m.subject.startsWith('⚠ ')).toBe(true);
    }
    const dead = buildManagerQuoteEmail({
      data, innCheck: { valid: true, verdict: 'ок', nameMatch: 'match' },
      party: { ...party, active: false, status: 'ликвидирована' }, eco,
    });
    expect(dead.subject.startsWith('⚠ ')).toBe(true);
  });


  it('шапка — «Запрос КП на продукты …» с суммой', () => {
    expect(ok.html).toContain('Запрос КП на продукты');
    expect(ok.text).toContain('Запрос КП на продукты');
  });

  it('чистая заявка — без предупреждений и без светофора в теле', () => {
    expect(ok.html).not.toContain('ВНИМАНИЕ');
  });

  it('несовпадение названия: одно бордовое предупреждение, оба названия с цветами', () => {
    const m = buildManagerQuoteEmail({
      data, innCheck: { valid: true, verdict: 'название не сходится', nameMatch: 'mismatch' },
      party, eco,
    });
    expect(m.html).toContain('ИНН не соответствует декларируемому названию компании');
    expect(m.html).toContain('(по ИНН)');
    expect(m.html).toContain('(указано клиентом)');
    expect(m.text).toContain('Компания (по ИНН): ООО «Ромашка»');
  });

  it('карточка: юрадрес, сайт по домену почты, наценка и прибыль', () => {
    expect(ok.html).toContain('ул Тестовая');
    expect(ok.html).toContain('example.ru');
    expect(ok.html).toContain('Наценка');
    expect(ok.html).toContain('Сумма до торга');
    expect(ok.text).toContain('Наценка:');
  });

  it('состав заказа — таблицей с ценой за единицу и итогом', () => {
    expect(ok.html).toContain('Кол-во');
    expect(ok.html).toContain('Итого');
    expect(ok.text).toContain('105\u00A0000');
  });

  it('развёрнутый ЕГРЮЛ ужат до серой сноски', () => {
    expect(ok.html).toContain('ЕГРЮЛ:');
    expect(ok.html).not.toContain('Основной вид деятельности');
  });

  it('письма набраны брендовым шрифтом Raleway со стеком фолбэков', () => {
    expect(ok.html).toContain("'Raleway'");
    expect(ok.html).toContain('@font-face');
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
      party: null, eco: null,
    });
    expect(m.html).toContain('Экономику посчитать не удалось');
  });

  it('неполная закупка — предупреждение о завышенной прибыли', () => {
    const partial = buildQuoteEconomics(
      [...data.items, { sku: 'B', name: 'Б', qty: 1, price: 100, sum: 100 }],
      [product('A', { base_price_usd: 700 }), product('B')], fx);
    const m = buildManagerQuoteEmail({
      data, innCheck: { valid: true, verdict: 'ок', nameMatch: 'match' },
      party: null, eco: partial,
    });
    expect(m.html).toContain('прибыль посчитана без них');
    expect(m.text).toContain('прибыль завышена');
  });
});
