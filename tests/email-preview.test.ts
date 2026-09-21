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
const demoLead = {
  name: 'Иванов Иван Иванович',
  company: 'ООО «Ромашка»',
  inn: '7701234567',
  email: 'ivanov@example.ru',
  phone: '+7 916 000-00-00',
  message: 'Добрый день! Нужен расчёт на три рабочих места и счёт на юрлицо.\n'
    + 'Продление действующих лицензий, оплата по безналу.',
  product_ref: 'количество: 3',
  date: '21.09.2026',
};

/**
 * Поля заявки можно подменить своим файлом:
 *
 *   EMAIL_PREVIEW=1 EMAIL_PREVIEW_LEAD=my-lead.json npx vitest run …
 *
 * Так смотрят письмо на составе настоящего обращения, не заводя его в код.
 * Файл с персональными данными в репозиторий не кладётся.
 */
function previewLead(): typeof demoLead {
  const file = process.env.EMAIL_PREVIEW_LEAD;
  if (!file) return demoLead;
  return { ...demoLead, ...JSON.parse(readFileSync(file, 'utf8')) };
}

describe.runIf(process.env.EMAIL_PREVIEW === '1')('предпросмотр писем', () => {
  it('собирает HTML писем заказчику в out/email-preview', () => {
    mkdirSync(OUT, { recursive: true });
    const letters: Record<string, string> = {
      'lead-customer.html': buildCustomerLeadEmail({ lead: previewLead() }).html,
      'quote-customer.html': buildCustomerQuoteEmail({
        data: {
          quoteNo: 'BZ-20260921-0001', date: '21.09.2026', validUntil: '28.09.2026',
          buyerCompany: demoLead.company, buyerInn: demoLead.inn,
          contactName: demoLead.name, email: demoLead.email, phone: demoLead.phone,
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
