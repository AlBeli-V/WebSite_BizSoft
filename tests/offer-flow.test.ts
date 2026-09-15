/**
 * Контур предложения после выпуска КП: документ, письмо, страница, действия.
 *
 * Проверяем то, что ломается молча: имя файла, число страниц в PDF, подпись
 * ссылки на страницу, запреты вёрстки письма (форма и скрипт в почте не
 * работают) и отсутствие персональных данных в ссылках аналитики.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { latinName, pdfFromJpegPages, quotePdfFileName, fileSizeRu } from '../src/lib/offer-doc';
import { offerExpired, offerToken, offerTokenMatches, offerUrl } from '../src/lib/offer-token';
import { OFFER_ACTIONS, actionLabels, knownActionIds } from '../src/lib/offer-actions';
import { offerCategoryLinks, offerProductLinks, withEmailUtm } from '../src/lib/offer-content';
import { buildMailto, finalQuoteMailto, invoiceMailto, edoAccountingMailto } from '../src/lib/mailto';
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

describe('ссылка на страницу предложения', () => {
  it('токен подписывает номер КП и сверяется с ним', () => {
    const t = offerToken(data.quoteNo);
    expect(t).toHaveLength(32);
    expect(offerTokenMatches(data.quoteNo, t)).toBe(true);
    expect(offerTokenMatches('BZ-20260915-00000', t)).toBe(false);
  });

  it('в адресе нет ни номера КП, ни данных клиента', () => {
    const url = offerUrl('https://biz-soft.pro', data.quoteNo, 'actions');
    expect(url).not.toContain(data.quoteNo);
    expect(url).not.toContain(data.buyerInn);
    expect(url).not.toContain(data.email);
    expect(url).toContain('utm_source=bizsoft_email');
  });

  it('страница живёт дольше предложения, но не вечно', () => {
    const issued = new Date('2026-09-15T09:00:00Z');
    expect(offerExpired(issued, 7, new Date('2026-09-30T09:00:00Z'))).toBe(false);
    expect(offerExpired(issued, 7, new Date('2026-11-30T09:00:00Z'))).toBe(true);
  });
});

describe('список действий', () => {
  it('идентификаторы уникальны и пригодны для параметров аналитики', () => {
    const ids = OFFER_ACTIONS.map((a) => a.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of ids) expect(id).toMatch(/^[a-z_]+$/);
  });

  it('чужие значения с формы отбрасываются', () => {
    expect(knownActionIds(['invoice', 'drop table', 'invoice'])).toEqual(['invoice']);
    expect(knownActionIds('invoice')).toEqual([]);
  });

  it('приглашение в ЭДО отправляем мы, а не ждём клиента', () => {
    expect(OFFER_ACTIONS.some((a) => a.id === 'edo_invite')).toBe(true);
    expect(actionLabels(['edo_invite'])[0]).toContain('Диадок');
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

  it('счёт и финальное КП — разные темы, обе с номером предложения', () => {
    expect(invoiceMailto(ctx)).toContain(encodeURIComponent('запрос счёта'));
    expect(invoiceMailto(ctx)).not.toBe(finalQuoteMailto(ctx));
  });

  it('письмо бухгалтерии несёт идентификатор ЭДО и без адресата', () => {
    const href = edoAccountingMailto({
      legalName: seller.legalName, inn: seller.inn,
      participantId: edo.participantId, provider: edo.provider, howTo: edo.howTo,
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

  it('разделов не больше трёх и они не повторяются', () => {
    const cats = offerCategoryLinks(data.items, catalog, 'https://biz-soft.pro');
    expect(cats.length).toBeLessThanOrEqual(3);
    expect(new Set(cats.map((c) => c.url)).size).toBe(cats.length);
  });

  it('метка кампании не затирает существующий параметр', () => {
    expect(withEmailUtm('https://x.ru/a?b=1', 'product')).toContain('?b=1&utm_source=');
  });
});

describe('письмо клиенту', () => {
  const mail = buildCustomerQuoteEmail({
    data,
    pdfName: quotePdfFileName(data.quoteNo, data.buyerCompany, data.date),
    pdfSize: 1153434,
    offerUrl: offerUrl('https://biz-soft.pro', data.quoteNo, 'actions'),
    products: offerProductLinks(data.items, catalog, 'https://biz-soft.pro'),
    categories: offerCategoryLinks(data.items, catalog, 'https://biz-soft.pro'),
  });

  it('вёрстка табличная, без того, что почта вырезает', () => {
    expect(mail.html).toContain('<table role="presentation"');
    for (const forbidden of ['<form', '<input', '<script', '<iframe', 'display:flex', 'display:grid']) {
      expect(mail.html).not.toContain(forbidden);
    }
    // Внешние шрифты в письме не грузятся: подмена ломает ритм вёрстки.
    expect(mail.html).not.toContain('fonts.googleapis.com');
  });

  it('называет документ во вложении и не обещает кнопку «скачать»', () => {
    expect(mail.html).toContain('КП_BIZSoft_BZ-20260915-29343_IT-MATRITSA_15.09.2026.pdf');
    expect(mail.html).toContain('приложено к письму');
    expect(mail.html).not.toContain('Скачать коммерческое предложение');
  });

  it('номер, сумма, срок и позиции есть текстом, а не картинкой', () => {
    // Сумма сверяется тем же форматированием, каким собрана: в ru-RU
    // разряды разделяет неразрывный пробел, и обычный здесь не совпадёт.
    const total = data.total.toLocaleString('ru-RU');
    for (const must of [data.quoteNo, total, data.validUntil, String(data.items.length)]) {
      expect(mail.html).toContain(must);
      expect(mail.text).toContain(must);
    }
  });

  it('главный призыв — запрос финального КП, счёт и действия — вторые', () => {
    expect(mail.html).toContain('ЗАПРОСИТЬ ФИНАЛЬНОЕ КП');
    expect(mail.html).toContain('ЗАПРОСИТЬ СЧЁТ ПО КП');
    expect(mail.html).toContain('ВЫБРАТЬ НУЖНЫЕ ДЕЙСТВИЯ');
    // Автоматической выдачи документа без знаков быть не должно: кнопка
    // создаёт разговор с менеджером, а не отдаёт файл.
    expect(mail.html).toContain('после согласования условий');
  });

  it('перечень действий показан, но формы в письме нет', () => {
    for (const a of OFFER_ACTIONS) expect(mail.html).toContain(a.label);
    expect(mail.html).toContain('&#9744;');
  });

  it('данные ЭДО и типовые документы на месте', () => {
    expect(mail.html).toContain(edo.participantId);
    expect(mail.html).toContain(seller.inn);
    expect(mail.html).toContain(offerDocs.contract.path);
    expect(mail.text).toContain(edo.participantId);
  });

  it('контакты менеджера настоящие и кликабельные', () => {
    expect(mail.html).toContain(`mailto:${offerManager.email}`);
    expect(mail.html).toContain(`tel:${offerManager.phoneHref}`);
    expect(mail.html).toContain(offerManager.telegram);
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

  it('без настроенной страницы предложения письмо остаётся рабочим', () => {
    const fallback = buildCustomerQuoteEmail({
      data, pdfName: 'x.pdf', pdfSize: 100, products: [], categories: [],
    });
    expect(fallback.html).toContain('ответным письмом');
    expect(fallback.html).not.toContain('/offer/');
  });
});

describe('страница предложения', () => {
  const page = readFileSync('src/pages/offer/[token].astro', 'utf8');

  it('в индекс не попадает', () => {
    expect(page).toContain('noindex={true}');
  });

  it('поля с персональными данными закрыты от Вебвизора', () => {
    // Правило docs/rules/webvisor-masking.md: любое поле ПДн на публичной
    // странице несёт класс ym-disable-keys.
    const inputs = page.match(/<(input|textarea)[^>]*>/g) || [];
    const personal = inputs.filter((t) => /name="(comment|contact_)/.test(t));
    expect(personal.length).toBeGreaterThan(0);
    for (const tag of personal) expect(tag).toContain('ym-disable-keys');
  });

  it('чекбоксы настоящие — это и есть смысл страницы', () => {
    expect(page).toContain('type="checkbox"');
    expect(page).toContain('/api/offer-actions');
  });
});
