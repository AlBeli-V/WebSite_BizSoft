/**
 * Контур предложения после выпуска КП: документ и письмо.
 *
 * Проверяем то, что ломается молча: имя файла, число страниц в PDF, запреты
 * вёрстки письма (форма и скрипт в почте не работают), состав по
 * производителям и отсутствие персональных данных в ссылках аналитики.
 *
 * Страницы `/offer/<токен>` больше нет — снята решением руководителя
 * 15.09.2026 вместе с токенами, списком действий и целями offer_*.
 */
import { describe, expect, it } from 'vitest';
import { latinName, pdfFromJpegPages, quotePdfFileName, fileSizeRu } from '../src/lib/offer-doc';
import { offerProductLinks, offerVendorGroups, withEmailUtm } from '../src/lib/offer-content';
import { buildMailto, contractMailto, finalQuoteMailto, invoiceMailto,
  edoAccountingMailto } from '../src/lib/mailto';
import { buildCustomerQuoteEmail } from '../src/lib/email/quote-customer';
import { generateQuoteJpgPages } from '../src/lib/jpg-quote';
import { edo, offerDocs, offerManager, seller } from '../src/config/site';
import type { Product } from '../src/lib/types';

const data = {
  quoteNo: 'BZ-20260915-29343',
  date: '15.09.2026',
  validUntil: '29.09.2026',
  buyerCompany: 'ООО «ИТ МАТРИЦА»',
  buyerInn: '7702345678',
  contactName: 'Беляев Алексей',
  email: 'client@matrix-it.ru',
  phone: '+79000000000',
  items: [
    { sku: 'ADOBE-LIC-CCTEAMS-TEAM-12M-SEAT', name: 'Adobe Creative Cloud для команд', vendor: 'Adobe', qty: 5, price: 86940, sum: 434700 },
    { sku: 'FIGMA-LIC-ORGANIZATION-TEAM-12M-SEAT', name: 'Figma Organization', vendor: 'Figma', qty: 8, price: 12500, sum: 100000 },
  ],
  total: 534700,
};

const catalog = [
  { sku: 'ADOBE-LIC-CCTEAMS-TEAM-12M-SEAT', slug: 'adobe-cc-teams', name: 'Adobe Creative Cloud для команд', vendor: 'Adobe' },
  { sku: 'FIGMA-LIC-ORGANIZATION-TEAM-12M-SEAT', slug: 'figma-organization', name: 'Figma Organization', vendor: 'Figma' },
] as unknown as Product[];

describe('имя файла КП', () => {
  it('название заказчика — латиницей, без формы собственности и кавычек', () => {
    expect(latinName('ООО «ИТ МАТРИЦА»')).toBe('IT-MATRITSA');
    expect(latinName('АО "Рога и Копыта"')).toBe('ROGA-I-KOPYTA');
    expect(latinName('Acme Ltd')).toBe('ACME-LTD');
  });

  it('пустое или мусорное название не ломает имя файла', () => {
    expect(latinName('')).toBe('CLIENT');
    expect(latinName('«»')).toBe('CLIENT');
    // Сдвоенных и висящих дефисов быть не может: имя файла уезжает в почту.
    expect(latinName('ООО   ---  Тест  ')).not.toMatch(/--|^-|-$/);
  });

  it('полное имя собрано по форме руководителя', () => {
    expect(quotePdfFileName(data.quoteNo, data.buyerCompany, data.date))
      .toBe('КП_BIZSoft_BZ-20260915-29343_IT-MATRITSA_15.09.2026.pdf');
  });

  it('вес файла показывается человеку, а не в байтах', () => {
    expect(fileSizeRu(900)).toBe('900 Б');
    expect(fileSizeRu(12 * 1024)).toBe('12 КБ');
    expect(fileSizeRu(1153434)).toBe('1,1 МБ');
  });
});

describe('единый PDF из листов', () => {
  it('сколько листов — столько страниц', async () => {
    const pages = generateQuoteJpgPages(data);
    expect(pages.length).toBeGreaterThan(0);
    const pdf = await pdfFromJpegPages(pages);
    const marks = pdf.toString('latin1').match(/\/Type\s*\/Page[^s]/g) || [];
    expect(marks.length).toBe(pages.length);
  }, 30000);

  it('листы кладутся без пересжатия: вес PDF не меньше суммы картинок', async () => {
    // Картинка внутри PDF остаётся исходным JPEG: текст в документе той же
    // чёткости, что на листе. Пересжатие выдало бы файл заметно легче.
    const pages = generateQuoteJpgPages(data);
    const pdf = await pdfFromJpegPages(pages);
    const raw = pages.reduce((s, p) => s + p.length, 0);
    expect(pdf.length).toBeGreaterThanOrEqual(raw);
  }, 30000);

  it('без листов документ не собирается', async () => {
    await expect(pdfFromJpegPages([])).rejects.toThrow();
  });
});

describe('заготовки писем', () => {
  const ctx = { to: 'a@b.ru', managerName: 'Алексей', quoteNo: data.quoteNo, buyerCompany: data.buyerCompany };

  it('переносы строк кодируются как CRLF — иначе Outlook склеивает текст', () => {
    const href = buildMailto({ to: 'a@b.ru', subject: 'Тема', body: 'строка\nвторая' });
    expect(href).toContain('%0D%0A');
    expect(href).not.toMatch(/[^%]0A/);
  });

  it('кириллица в теме и теле закодирована', () => {
    const href = finalQuoteMailto(ctx);
    expect(href.startsWith('mailto:a@b.ru?subject=')).toBe(true);
    expect(href).toContain(encodeURIComponent('запрос финального КП'));
    expect(href).toContain(encodeURIComponent(data.quoteNo));
  });

  it('счёт, договор и финальное КП — разные темы, все с номером предложения', () => {
    for (const href of [invoiceMailto(ctx), contractMailto(ctx), finalQuoteMailto(ctx)]) {
      expect(href).toContain(encodeURIComponent(data.quoteNo));
    }
    expect(invoiceMailto(ctx)).toContain(encodeURIComponent('Запрос счёта'));
    expect(contractMailto(ctx)).toContain(encodeURIComponent('Запрос договора'));
    expect(invoiceMailto(ctx)).not.toBe(contractMailto(ctx));
  });

  it('тема запроса называет заказчика, дату и производителей состава', () => {
    // Менеджер узнаёт сделку по одной строке в списке писем, не открывая её.
    const href = invoiceMailto({ ...ctx, date: data.date, buyerInn: data.buyerInn,
      vendors: ['Adobe', 'JetBrains'] });
    expect(href).toContain(encodeURIComponent(`${data.buyerCompany} — Запрос счёта`));
    expect(href).toContain(encodeURIComponent(`от ${data.date}`));
    expect(href).toContain(encodeURIComponent('на Adobe / JetBrains'));
    expect(href).toContain(encodeURIComponent(`(ИНН: ${data.buyerInn})`));
  });

  it('письмо бухгалтерии начинается адресацией прописными', () => {
    // Цвета в теле mailto: не существует — письмо создаёт почтовый клиент
    // получателя. Прописные работают везде.
    const href = edoAccountingMailto({
      legalName: seller.legalName, shortName: seller.shortName, inn: seller.inn,
      ogrnip: seller.ogrnip, participantId: edo.participantId, provider: edo.provider,
      buyerCompany: data.buyerCompany,
    });
    expect(href).toContain(encodeURIComponent('НАПРАВИТЬ В БУХГАЛТЕРИЮ'));
    expect(href).toContain(encodeURIComponent(seller.ogrnip));
  });

  it('письмо бухгалтерии несёт идентификатор ЭДО и без адресата', () => {
    const href = edoAccountingMailto({
      legalName: seller.legalName, shortName: seller.shortName, inn: seller.inn,
      ogrnip: seller.ogrnip, participantId: edo.participantId, provider: edo.provider,
    });
    expect(href.startsWith('mailto:?')).toBe(true);
    expect(href).toContain(encodeURIComponent(edo.participantId));
    expect(href).toContain(encodeURIComponent(seller.inn));
  });
});

describe('ссылки предложения', () => {
  it('позиции ведут на карточки сайта', () => {
    const links = offerProductLinks(data.items, catalog, 'https://biz-soft.pro');
    expect(links).toHaveLength(2);
    expect(links[0].url).toContain('/product/adobe-cc-teams');
    expect(links[0].url).toContain('utm_content=product');
  });

  it('позиция без карточки в каталоге ссылки не получает', () => {
    const links = offerProductLinks(data.items, [catalog[0]], 'https://biz-soft.pro');
    expect(links).toHaveLength(1);
  });

  it('состав группируется по производителям в порядке позиций', () => {
    const groups = offerVendorGroups(
      offerProductLinks(data.items, catalog, 'https://biz-soft.pro'), 'https://biz-soft.pro');
    expect(groups.map((g) => g.vendor)).toEqual(['Adobe', 'Figma']);
    expect(groups[0].url).toContain('/vendors/adobe');
    expect(groups[0].url).toContain('utm_content=vendor');
    expect(groups.flatMap((g) => g.products)).toHaveLength(data.items.length);
  });

  it('метка кампании не затирает существующий параметр', () => {
    expect(withEmailUtm('https://x.ru/a?b=1', 'product')).toContain('?b=1&utm_source=');
  });
});

describe('письмо клиенту', () => {
  const vendors = offerVendorGroups(
    offerProductLinks(data.items, catalog, 'https://biz-soft.pro'), 'https://biz-soft.pro');
  const mail = buildCustomerQuoteEmail({
    data,
    pdfName: quotePdfFileName(data.quoteNo, data.buyerCompany, data.date),
    pdfSize: 1153434,
    vendors,
  });

  it('вёрстка табличная, без того, что почта вырезает', () => {
    expect(mail.html).toContain('<table role="presentation"');
    for (const forbidden of ['<form', '<input', '<script', '<iframe', 'display:flex', 'display:grid']) {
      expect(mail.html).not.toContain(forbidden);
    }
    // Внешние шрифты в письме не грузятся: подмена ломает ритм вёрстки.
    expect(mail.html).not.toContain('fonts.googleapis.com');
  });

  it('шапка — две картинки, телефонная скрыта и от Outlook тоже', () => {
    // Word-движок Outlook `display:none` соблюдает не всегда: без условного
    // комментария получатель увидел бы обе шапки подряд.
    expect(mail.html).toContain('/email/banner-desk.jpg');
    expect(mail.html).toContain('/email/banner-mob.jpg');
    expect(mail.html).toContain('<!--[if !mso]><!-->');
    expect(mail.html).toContain('<!--<![endif]-->');
    // Картинки могут не загрузиться — подпись обязана нести смысл.
    expect(mail.html).toContain('alt="BIZSoft — единая точка доступа');
  });

  it('заголовок прописными и обращение по имени', () => {
    expect(mail.html).toContain('Коммерческое предложение</div>');
    expect(mail.html).toContain('text-transform:uppercase');
    expect(mail.html).toContain('Уважаемый Алексей!');
    expect(mail.html).toContain('в интересах ООО «ИТ МАТРИЦА»');
  });

  it('следующий шаг — четыре строки с маркерами от /01', () => {
    for (const label of ['Запросить счёт', 'Запросить договор',
                         'Скачать образец договора', 'Коннект в ЭДО']) {
      expect(mail.html).toContain(label);
    }
    for (const marker of ['/01', '/02', '/03', '/04']) {
      expect(mail.html).toContain(`>${marker}<`);
    }
    expect(mail.html).not.toContain('>/05<');
    // Стрелка скачивания смотрит вниз: она обещает файл, а не переход.
    expect(mail.html).toContain('&#8595;');
  });

  it('ссылок на страницу предложения в письме нет', () => {
    // Страница снята 15.09.2026: ссылка вела бы в 404 из живого КП.
    expect(mail.html).not.toContain('/offer/');
    expect(mail.text).not.toContain('/offer/');
  });

  it('состав — производитель, под ним его позиции', () => {
    expect(mail.html).toContain('Каталог Adobe');
    expect(mail.html).toContain('Каталог Figma');
    expect(mail.html).toContain('Страница Adobe Creative Cloud для команд');
    expect(mail.html.indexOf('Каталог Adobe')).toBeLessThan(mail.html.indexOf('Каталог Figma'));
  });

  it('сумма и срок в письме не дублируются — они в документе', () => {
    // Решение руководителя 15.09.2026: письмо не должно читаться как второй
    // экземпляр КП. Номер и имя файла остаются в текстовой версии.
    expect(mail.html).not.toContain(data.total.toLocaleString('ru-RU'));
    expect(mail.html).not.toContain(data.validUntil);
    expect(mail.text).toContain(data.quoteNo);
    expect(mail.text).toContain('КП_BIZSoft_BZ-20260915-29343_IT-MATRITSA_15.09.2026.pdf');
  });

  it('данные ЭДО и образец договора уходят заготовкой письма', () => {
    expect(mail.html).toContain(encodeURIComponent(edo.participantId));
    expect(mail.html).toContain(offerDocs.contract.path);
    expect(mail.text).toContain(edo.participantId);
  });

  it('контакты менеджера настоящие и кликабельные, должности нет', () => {
    expect(mail.html).toContain(`mailto:${offerManager.email}`);
    expect(mail.html).toContain(`tel:${offerManager.phoneHref}`);
    expect(mail.html).toContain(offerManager.telegram);
    expect(mail.html).toContain('wa.me/79647161111');
    expect(mail.html).not.toContain(offerManager.role);
  });

  it('ссылки не несут персональных данных клиента', () => {
    const hrefs = [...mail.html.matchAll(/href="([^"]+)"/g)].map((m) => m[1]);
    const utmLinks = hrefs.filter((h) => h.includes('utm_'));
    expect(utmLinks.length).toBeGreaterThan(0);
    for (const href of utmLinks) {
      expect(href).not.toContain(data.email);
      expect(href).not.toContain(data.buyerInn);
      expect(href).not.toContain(encodeURIComponent(data.buyerCompany));
      expect(href).not.toContain(String(data.total));
    }
  });

  it('без состава письмо остаётся рабочим', () => {
    const bare = buildCustomerQuoteEmail({ data, pdfName: 'x.pdf', pdfSize: 100, vendors: [] });
    expect(bare.html).toContain('>/01<');
    expect(bare.html).not.toContain('СОСТАВ ПРЕДЛОЖЕНИЯ');
  });
});


describe('тема письма', () => {
  const vendors = offerVendorGroups(
    offerProductLinks(data.items, catalog, 'https://biz-soft.pro'), 'https://biz-soft.pro');

  it('называет дату и производителей состава, а не номер', () => {
    // Номер КП заказчику ни о чём не говорит: в списке писем он узнаёт
    // предложение по дате и маркам (решение руководителя 16.09.2026).
    const mail = buildCustomerQuoteEmail({ data, pdfName: 'x.pdf', pdfSize: 1, vendors });
    expect(mail.subject).toBe('Предварительное КП BIZSoft от 15.09.2026 на поставку Adobe / Figma');
    expect(mail.subject).not.toContain(data.quoteNo);
  });

  it('без состава тема остаётся осмысленной', () => {
    const mail = buildCustomerQuoteEmail({ data, pdfName: 'x.pdf', pdfSize: 1, vendors: [] });
    expect(mail.subject).toBe('Предварительное КП BIZSoft от 15.09.2026');
  });
});
