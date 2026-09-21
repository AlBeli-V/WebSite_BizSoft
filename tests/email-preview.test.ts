/**
 * Предпросмотр писем заказчику: HTML на диск, чтобы посмотреть глазами.
 *
 * Письмо нельзя принять по коду — его принимают по тому, как оно выглядит в
 * почте (письмо с КП прошло девять кругов правок именно так). Отдельного
 * запускаемого инструмента в проекте нет: исходники писем на TypeScript, а
 * компилятора у `node scripts/*.mjs` нет, — поэтому предпросмотр живёт
 * прогоном vitest, у которого компилятор есть.
 *
 *   EMAIL_PREVIEW=1 npx vitest run tests/email-preview.test.ts
 *
 * Файлы ложатся в `out/email-preview/` (каталог в .gitignore): открыть
 * браузером, снять скриншот, показать. Без переменной прогон пропускается —
 * в общем `pnpm test` этот тест ничего не пишет и ничего не стоит.
 */
import { describe, expect, it } from 'vitest';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { buildCustomerLeadEmail } from '../src/lib/email/lead-customer';
import { buildCustomerQuoteEmail } from '../src/lib/email/quote-customer';

const OUT = process.env.EMAIL_PREVIEW_DIR || 'out/email-preview';

/** Данные показа — вымышленные: настоящая заявка в предпросмотр не берётся. */
const demo = {
  lead: {
    name: 'Иванов Иван Иванович',
    company: 'ООО «Ромашка»',
    inn: '7701234567',
    email: 'ivanov@example.ru',
    phone: '+7 916 000-00-00',
    message: 'Добрый день! Нужен расчёт на три рабочих места и счёт на юрлицо.\n'
      + 'Продление действующих лицензий, оплата по безналу.',
    product_ref: 'количество: 3',
    date: '21.09.2026',
  },
  request: {
    vendor: 'Adobe',
    product: 'Creative Cloud Pro',
    plan: 'team' as const,
    qty: 3,
    links: {
      product: { name: 'Adobe Creative Cloud Pro', url: 'https://biz-soft.pro/product/adobe-cc-pro' },
      alternative: { name: 'Adobe Creative Cloud Standard', url: 'https://biz-soft.pro/product/adobe-cc-std' },
      catalog: { name: 'Каталог Adobe', url: 'https://biz-soft.pro/vendors/adobe' },
    },
  },
};

/**
 * Состав обращения можно подменить своим файлом:
 *
 *   EMAIL_PREVIEW=1 EMAIL_PREVIEW_LEAD=my-lead.json npx vitest run …
 *
 * Файл повторяет вход шаблона: `lead` и необязательный `request`. Так
 * смотрят письмо на составе настоящего обращения, не заводя его в код;
 * файл с персональными данными в репозиторий не кладётся.
 */
function previewInput(): typeof demo {
  const file = process.env.EMAIL_PREVIEW_LEAD;
  if (!file) return demo;
  const own = JSON.parse(readFileSync(file, 'utf8'));
  // `request` заменяется целиком, а не подмешивается к демонстрационному:
  // иначе в предпросмотр настоящей заявки протекли бы чужие продукт, план и
  // ссылки — и письмо показало бы то, чего в обращении не было.
  return {
    lead: { ...demo.lead, ...(own.lead ?? own) },
    request: own.request ?? demo.request,
  };
}

describe.runIf(process.env.EMAIL_PREVIEW === '1')('предпросмотр писем', () => {
  it('собирает HTML писем заказчику в out/email-preview', () => {
    mkdirSync(OUT, { recursive: true });
    const letters: Record<string, string> = {
      'lead-customer.html': buildCustomerLeadEmail(previewInput()).html,
      'quote-customer.html': buildCustomerQuoteEmail({
        data: {
          quoteNo: 'BZ-20260921-0001', date: '21.09.2026', validUntil: '28.09.2026',
          buyerCompany: demo.lead.company, buyerInn: demo.lead.inn,
          contactName: demo.lead.name, email: demo.lead.email, phone: demo.lead.phone,
          items: [{ sku: 'ADBE-LIC-CCALL-TEAM-12M-SEAT', name: 'Creative Cloud для команд', qty: 3, price: 95000, sum: 285000 }],
          total: 285000,
        },
        pdfName: 'КП_BIZSoft_BZ-20260921-0001_ROMASHKA_21.09.2026.pdf',
        pdfSize: 512000,
      }).html,
    };
    for (const [file, html] of Object.entries(letters)) {
      writeFileSync(`${OUT}/${file}`, html);
      expect(html.length).toBeGreaterThan(1000);
    }
    console.log(`письма собраны: ${Object.keys(letters).map((f) => `${OUT}/${f}`).join(', ')}`);
  });
});
