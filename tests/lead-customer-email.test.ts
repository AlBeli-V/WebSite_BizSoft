/**
 * Письмо заказчику о принятом обращении.
 *
 * Проверяется то, ради чего письмо заводилось (состав обращения возвращается
 * человеку дословно, есть текстовый двойник, есть строка для того, кто
 * обращения не оставлял) и то, чем письмо не должно стать: вторым КП с
 * ценами и обещаниями срока.
 */
import { describe, expect, it } from 'vitest';
import { buildCustomerLeadEmail } from '../src/lib/email/lead-customer';

const lead = {
  name: 'Иванов Иван Иванович',
  company: 'ООО «Ромашка» <script>alert(1)</script>',
  inn: '7701234567',
  email: 'ivanov@example.ru',
  phone: '+7 916 000-00-00',
  message: 'Нужен расчёт на 3 рабочих места.\nСчёт на юрлицо.',
  product_ref: 'количество: 3',
  date: '21.09.2026',
};

describe('письмо заказчику о заявке', () => {
  const mail = buildCustomerLeadEmail({ lead });

  it('есть и HTML, и текстовый двойник', () => {
    expect(mail.html).toContain('<!doctype html>');
    expect(mail.text).toContain('ВАШЕ ОБРАЩЕНИЕ');
    expect(mail.subject).toBe('Обращение принято — BIZSoft, 21.09.2026');
  });

  it('обращение по имени, а не по всему полю ФИО', () => {
    expect(mail.text).toContain('Уважаемый Иван Иванович!');
  });

  it('возвращает человеку состав обращения — есть что сверить', () => {
    for (const part of ['21.09.2026', '7701234567', 'количество: 3',
      '+7 916 000-00-00', 'ivanov@example.ru']) {
      expect(mail.html).toContain(part);
      expect(mail.text).toContain(part);
    }
    // Перенос строки в сообщении остаётся переносом, а не склейкой слов.
    expect(mail.html).toContain('места.<br>Счёт');
  });

  it('поля формы экранируются: чужой разметки в почте клиента не будет', () => {
    // Название организации и сообщение приходят из публичной формы.
    expect(mail.html).not.toContain('<script>');
    expect(mail.html).toContain('&lt;script&gt;');
  });

  it('это не второе КП: ни цен, ни сумм, ни срока ответа в часах', () => {
    expect(mail.html).not.toMatch(/₽|руб\./);
    expect(mail.html).not.toMatch(/в течение \d+/i);
    // Обещание ровно то же, что дала страница в момент отправки.
    expect(mail.text).toContain('в рабочее время');
  });

  it('адрес не подтверждён — письмо объясняет, как от него отказаться', () => {
    expect(mail.html).toContain('Если обращение оставляли не Вы');
    expect(mail.text).toContain('Если обращение оставляли не Вы');
  });

  it('вёрстка почты: без скриптов, форм и внешних стилей', () => {
    expect(mail.html).not.toMatch(/<link|<form|<iframe/);
    expect(mail.html).not.toMatch(/<script[\s>]/);
    // Картинки — только со своего домена (баннер, значки, фото менеджера).
    const srcs = [...mail.html.matchAll(/src="([^"]+)"/g)].map((m) => m[1]);
    expect(srcs.length).toBeGreaterThan(0);
    for (const src of srcs) expect(src.startsWith('https://biz-soft.pro/')).toBe(true);
  });

  it('пустые поля не оставляют в письме пустых строк', () => {
    const bare = buildCustomerLeadEmail({
      lead: { ...lead, product_ref: '', message: '' },
    });
    expect(bare.html).not.toContain('Запрос по позиции');
    expect(bare.html).not.toContain('Ваше сообщение');
    expect(bare.text).not.toContain('Ваше сообщение');
  });

  it('организация не указана — письмо не обещает «в интересах »', () => {
    const bare = buildCustomerLeadEmail({ lead: { ...lead, company: '  ' } });
    expect(bare.html).toContain('в интересах вашей организации');
  });
});
