/**
 * Письмо заказчику о принятом обращении (редакция 2, 21.09.2026).
 *
 * Проверяется то, ради чего письмо заводилось (предмет обращения
 * возвращается человеку дословно, есть текстовый двойник, есть строка для
 * того, кто обращения не оставлял) и то, чем письмо не должно стать: вторым
 * КП с ценами и обещаниями срока.
 */
import { describe, expect, it } from 'vitest';
import { buildCustomerLeadEmail, refParts } from '../src/lib/email/lead-customer';

const lead = {
  name: 'Иванов Иван Иванович',
  company: 'АО «ЭКСАР» <script>alert(1)</script>',
  inn: '7704792651',
  email: 'ivanov@example.ru',
  phone: '+7 916 000-00-00',
  message: 'Нужен расчёт на 3 рабочих места.\nСчёт на юрлицо.',
  product_ref: 'количество: 3',
  date: '21.09.2026',
};

const request = {
  vendor: 'Adobe',
  product: 'Creative Cloud Pro',
  plan: 'team' as const,
  qty: 3,
  links: {
    product: { name: 'Adobe Creative Cloud Pro', url: 'https://biz-soft.pro/product/adobe-cc-pro' },
    alternative: { name: 'Adobe Creative Cloud Standard', url: 'https://biz-soft.pro/product/adobe-cc-std' },
    catalog: { name: 'Каталог Adobe', url: 'https://biz-soft.pro/vendors/adobe' },
  },
};

describe('письмо заказчику о заявке', () => {
  const mail = buildCustomerLeadEmail({ lead, request });

  it('есть и HTML, и текстовый двойник', () => {
    expect(mail.html).toContain('<!doctype html>');
    expect(mail.text).toContain('ВАШЕ ОБРАЩЕНИЕ');
    expect(mail.subject).toBe('Обращение принято — BIZSoft, 21.09.2026');
  });

  it('обращение по имени, а не по всему полю ФИО', () => {
    expect(mail.text).toContain('Уважаемый Иван Иванович!');
  });

  it('первый абзац называет дату приёма и организацию', () => {
    expect(mail.text).toContain(
      'Благодарим Вас за обращение от 21.09.2026 в BIZSoft от компании АО «ЭКСАР»');
    expect(mail.text).toContain('Подтверждаем, что Ваш запрос получен и передан менеджеру.');
  });

  it('заголовок не повторяет заказчика строкой «в интересах»', () => {
    expect(mail.html).not.toContain('в интересах');
  });

  it('предмет обращения: производитель, продукт, тип лицензии, количество, цитата', () => {
    expect(mail.html).toContain('<b>Adobe</b>');
    expect(mail.html).toContain('Creative Cloud Pro');
    expect(mail.html).toContain('Командная');
    // Порядок строк — от общего к частному, он же согласован руководителем.
    const order = ['Производитель', 'Продукт', 'Тип лицензии', 'Количество', 'Текст сообщения']
      .map((k) => mail.html.indexOf(k));
    expect(order).toEqual([...order].sort((a, b) => a - b));
    expect(order.every((i) => i > 0)).toBe(true);
    // Сообщение — дословно и с сохранением переноса строки.
    expect(mail.html).toContain('места.<br>Счёт');
    expect(mail.text).toContain('Нужен расчёт на 3 рабочих места.');
  });

  it('подборка по теме запроса: сам план, альтернатива, каталог', () => {
    const { product, alternative, catalog } = request.links;
    for (const url of [product.url, alternative.url, catalog.url]) {
      expect(mail.html).toContain(url);
      expect(mail.text).toContain(url);
    }
    expect(mail.html).toContain('Вас может заинтересовать');
  });

  it('«Что дальше» — только два действия', () => {
    expect(mail.html).toContain('Дополнить обращение ответным письмом');
    expect(mail.html).toContain('Скачать образец договора');
    expect(mail.html).not.toContain('Как проходит поставка');
  });

  it('поля формы экранируются: чужой разметки в почте клиента не будет', () => {
    expect(mail.html).not.toContain('<script>');
    expect(mail.html).toContain('&lt;script&gt;');
  });

  it('это не второе КП: ни цен, ни сумм, ни срока ответа в часах', () => {
    expect(mail.html).not.toMatch(/₽|руб\./);
    expect(mail.html).not.toMatch(/в течение \d+/i);
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
});

describe('заявка без опознанной позиции', () => {
  // Общая форма не знает ни производителя, ни лицензии: письмо в этом
  // случае не рисует пустых строк и не обещает подборку, которой нет.
  const bare = buildCustomerLeadEmail({
    lead: { ...lead, product_ref: '', message: '' },
  });

  it('пустые поля строк не создают', () => {
    expect(bare.html).not.toContain('Производитель');
    expect(bare.html).not.toContain('Тип лицензии');
    expect(bare.html).not.toContain('Количество');
    expect(bare.html).not.toContain('Текст сообщения');
    expect(bare.html).not.toContain('Ваше обращение');
  });

  it('подборки нет, а два действия остаются', () => {
    expect(bare.html).not.toContain('Вас может заинтересовать');
    expect(bare.html).toContain('Скачать образец договора');
  });

  it('организации нет — предложение кончается на «в BIZSoft»', () => {
    const noCompany = buildCustomerLeadEmail({ lead: { ...lead, company: '  ' } });
    expect(noCompany.text).toContain('обращение от 21.09.2026 в BIZSoft. Подтверждаем');
  });
});

describe('количество из строки формы', () => {
  // Отдельного поля под количество в заявке нет: страница кладёт его в
  // product_ref, и без разбора число мест терялось бы в письме.
  it.each([
    ['количество: 3', '3', undefined],
    ['Количество 12', '12', undefined],
    ['Creative Cloud Pro, количество: 5', '5', 'Creative Cloud Pro'],
    ['Creative Cloud Pro', undefined, 'Creative Cloud Pro'],
  ])('«%s» → количество %s, остаток %s', (ref, qty, rest) => {
    expect(refParts(ref)).toEqual({ qty, rest });
  });

  it('без явного request количество берётся из строки формы', () => {
    const mail = buildCustomerLeadEmail({ lead });
    expect(mail.text).toContain('Количество: 3');
  });
});
