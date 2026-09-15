/**
 * Паритет Word-версии КП с клиентским документом.
 *
 * Word верстается отдельной библиотекой, и это единственное место, где
 * форматы могут молча разойтись: правка макета без правки Word уедет
 * клиенту в одном виде, а руководителю в другом. Поэтому содержимое
 * DOCX сверяется с раскладкой построчно: позиции, суммы, тексты, условия.
 *
 * Решение руководителя 28.08.2026: Word — внутренний рабочий исходник,
 * водяных знаков в нём нет, наружу уходит только PDF/JPG со штампами.
 */
import { describe, expect, it } from 'vitest';
import { createRequire } from 'node:module';
import { generateQuoteDocx } from '../src/lib/docx-quote';
import { buildQuoteLayout, STAMP_LINE_1 } from '../src/lib/quote-layout';
import { pdfMeasure } from '../src/lib/pdf-quote';

const require = createRequire(import.meta.url);
// jszip — транзитивная зависимость пакета docx; берём её через его резолвер,
// чтобы не тащить отдельную зависимость ради чтения архива в тесте.
const docxRequire = createRequire(require.resolve('docx'));
const JSZip = docxRequire('jszip');

const data = {
  quoteNo: 'BZ-20260828-0042',
  date: '28.08.2026',
  validUntil: '04.09.2026',
  buyerCompany: 'ООО «Энкор Менеджмент»',
  buyerInn: '7701234567',
  contactName: 'Екатерина Кувшинова',
  email: 'k@encoreresort.ru',
  phone: '+79167898651',
  items: [
    // vendor приходит от API вместе с позицией: из него документ берёт
    // юридическое название производителя и форму поставки для фразы.
    { sku: 'ADOBE-CC-TEAMS', name: 'Adobe Creative Cloud для команд', vendor: 'Adobe', qty: 5, price: 100000, sum: 500000 },
    { sku: 'FIGMA-PRO', name: 'Figma Professional', vendor: 'Figma', qty: 3, price: 30000, sum: 90000 },
  ],
  total: 590000,
};

/** Весь видимый текст документа: тело и колонтитулы. */
async function docxText(): Promise<string> {
  const buf = await generateQuoteDocx(data);
  const zip = await JSZip.loadAsync(buf);
  const parts: string[] = [];
  for (const name of Object.keys(zip.files)) {
    if (!/^word\/(document|footer\d*|header\d*)\.xml$/.test(name)) continue;
    parts.push(await zip.files[name].async('string'));
  }
  // Текст живёт в <w:t>; теги убираем, пробелы (включая неразрывные) схлопываем.
  return parts.join(' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ');
}

/** Все текстовые строки раскладки (клиентский документ). */
function layoutTexts(): string[] {
  return buildQuoteLayout(data, pdfMeasure())
    .flatMap((p) => p.items.filter((i) => i.kind === 'text').map((i: any) => i.text as string));
}

describe('Word повторяет клиентский документ', () => {
  it('каждая строка раскладки присутствует в DOCX', async () => {
    const doc = await docxText();
    // Строки раскладки могут быть разбиты переносом по ширине колонки —
    // сравниваем по словам, а не по кускам строк.
    const words = new Set(doc.split(' '));
    const missing: string[] = [];
    for (const t of layoutTexts()) {
      for (const w of t.split(/\s+/)) {
        if (w && !doc.includes(w)) missing.push(`${w} (из «${t}»)`);
      }
    }
    expect(missing, `в Word нет: ${missing.slice(0, 5).join('; ')}`).toEqual([]);
    expect(words.size).toBeGreaterThan(50);
  });

  it('суммы, НДС и сумма прописью совпадают с макетом', async () => {
    const doc = (await docxText()).replace(/ /g, ' ');
    expect(doc).toContain('ИТОГО в т.ч. НДС 5%: 590 000,00 ₽');
    expect(doc).toContain('НДС 5%: 28 095,24 ₽');
    expect(doc).toContain('(Пятьсот девяносто тысяч) рублей 00 копеек');
  });

  it('оговорка и условия — те же, что у клиента', async () => {
    const doc = await docxText();
    expect(doc).toContain('не является публичной офертой');
    expect(doc).toContain('Форма поставки: в электронном виде.');
    expect(doc).toContain('100% аванс');
  });

  it('водяных знаков в Word нет — внутренний документ', async () => {
    const doc = await docxText();
    expect(doc).not.toContain(STAMP_LINE_1);
    // Прежние полосы «BIZSoft · BZ-…» из версии до 28.08.2026.
    expect(doc).not.toMatch(/BIZSoft\s+·\s+BZ-/);
  });

  it('исходящий номер и колонки — как в спецификации на сайте', async () => {
    const doc = await docxText();
    expect(doc).toContain(`Исх. № ${data.quoteNo}`);
    expect(doc).toContain('Описание');
    expect(doc).toContain('Кол-во');
    // Отдельной колонки артикула нет — он внутри описания позиции.
    expect(doc).not.toContain('Наименование');
    expect(doc).toContain(`Артикул: ${data.items[0].sku}`);
  });

  it('описание позиции совпадает со страницей спецификации', async () => {
    const doc = await docxText();
    expect(doc).toContain('Adobe Inc. / Adobe Creative Cloud для команд');
    expect(doc).toContain('Оказание услуг по предоставлению доступа');
  });

  it('листы пронумерованы — документ печатают и подшивают', async () => {
    const doc = await docxText();
    expect(doc).toContain('Лист');
  });
});
