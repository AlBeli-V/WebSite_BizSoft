/**
 * Общий слой писем заказчику.
 *
 * Писем клиенту два — подтверждение обращения и КП, — и приходят они на один
 * адрес, часто подряд. Пока шапка, подпись и оговорка жили копиями в каждом
 * шаблоне, любая правка одного письма молча расходилась с другим. Этот тест
 * сторожит, что оба письма собираются одним слоем и выглядят как письма
 * одной компании.
 */
import { describe, expect, it } from 'vitest';
import { buildCustomerLeadEmail } from '../src/lib/email/lead-customer';
import { buildCustomerQuoteEmail } from '../src/lib/email/quote-customer';

const quote = buildCustomerQuoteEmail({
  data: {
    quoteNo: 'BZ-20260921-0001', date: '21.09.2026', validUntil: '28.09.2026',
    buyerCompany: 'ООО «Ромашка»', buyerInn: '7701234567',
    contactName: 'Иванов Иван Иванович', email: 'ivanov@example.ru',
    phone: '+7 916 000-00-00',
    items: [{ sku: 'A', name: 'Товар А', qty: 1, price: 1000, sum: 1000 }],
    total: 1000,
  },
  pdfName: 'КП.pdf',
  pdfSize: 1024,
}).html;

const lead = buildCustomerLeadEmail({
  lead: {
    name: 'Иванов Иван Иванович', company: 'ООО «Ромашка»', inn: '7701234567',
    email: 'ivanov@example.ru', phone: '+7 916 000-00-00',
    message: 'Нужен расчёт.', product_ref: 'количество: 3', date: '21.09.2026',
  },
}).html;

describe('письма заказчику собраны одним слоем', () => {
  const common = [
    // Шапка-баннер: десктопная и телефонная картинки.
    'email/banner-desk.jpg',
    'email/banner-mob.jpg',
    // Условный комментарий Outlook вокруг телефонной шапки.
    '<!--[if !mso]><!-->',
    // Лист письма одной ширины.
    'width:640px;max-width:100%',
    // Подпись менеджера с теми же контактами.
    'Алексей Беляев',
    'email/g-mail.png',
    // Оговорка о конфиденциальности.
    '<b style="color:#3B3F47">Конфиденциально.</b>',
  ];

  it.each(common)('оба письма несут «%s»', (part) => {
    expect(quote).toContain(part);
    expect(lead).toContain(part);
  });

  it('заголовок раздела рисуется одинаково — оранжевый слэш и прописные', () => {
    const head = /<span style="color:#FF763C">\/<\/span> /g;
    expect(quote.match(head)?.length).toBeGreaterThan(0);
    expect(lead.match(head)?.length).toBeGreaterThan(0);
  });

  it('письмо с КП осталось письмом с КП: состав и следующий шаг на месте', () => {
    expect(quote).toContain('Коммерческое предложение');
    expect(quote).toContain('Следующий шаг');
    // Оговорка про адрес из формы — только у подтверждения: у КП адрес уже
    // подтверждён перепиской, и лишняя строка в КП читалась бы как рассылка.
    expect(quote).not.toContain('Письмо отправлено автоматически');
    expect(lead).toContain('Письмо отправлено автоматически');
  });
});
