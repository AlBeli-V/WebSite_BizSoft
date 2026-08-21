/**
 * Отрисовка КП: PDF и JPG строятся из одной раскладки.
 *
 * Проверяем не «красиво», а то, что можно сломать молча: наличие водяных
 * знаков, поля исходящего номера, даты скачивания и совпадение содержимого
 * двух форматов.
 */
import { describe, expect, it } from 'vitest';
import { buildQuoteLayout, watermarks, WATERMARK } from '../src/lib/quote-layout';
import { generateQuotePdf, pdfMeasure } from '../src/lib/pdf-quote';
import { generateQuoteJpg, quotePageSvg } from '../src/lib/jpg-quote';
import { leadFromQuote } from '../src/lib/quote-lead';
import { defaultLeadOwner } from '../src/config/site';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const data = {
  quoteNo: 'BZ-20260821-0042',
  date: '21.08.2026',
  validUntil: '05.09.2026',
  buyerCompany: 'ООО «Энкор Менеджмент»',
  buyerInn: '7701234567',
  contactName: 'Екатерина Кувшинова',
  email: 'k@encoreresort.ru',
  phone: '+79167898651',
  items: [
    { sku: 'ADOBE-CC-TEAMS', name: 'Adobe Creative Cloud для команд', qty: 5, price: 100000, sum: 500000 },
    { sku: 'FIGMA-PRO', name: 'Figma Professional', qty: 3, price: 30000, sum: 90000 },
  ],
  total: 590000,
};

describe('раскладка КП', () => {
  const pages = buildQuoteLayout(data, pdfMeasure());

  it('водяных знаков не меньше девяти на каждой странице', () => {
    for (const p of pages) {
      const marks = p.items.filter((i) => i.kind === 'watermark');
      expect(marks.length).toBeGreaterThanOrEqual(9);
    }
  });

  it('знаки полупрозрачные и распределены по всей странице, а не в одном углу', () => {
    const marks = watermarks('проба');
    expect(WATERMARK.opacity).toBeGreaterThan(0);
    expect(WATERMARK.opacity).toBeLessThan(0.5);
    expect(new Set(marks.map((m) => m.kind === 'watermark' && m.x)).size).toBe(WATERMARK.cols);
    expect(new Set(marks.map((m) => m.kind === 'watermark' && m.y)).size).toBe(WATERMARK.rows);
  });

  it('знак идёт под содержимым: рисуется раньше текста', () => {
    const first = pages[0].items.findIndex((i) => i.kind !== 'watermark');
    const lastMark = pages[0].items.map((i) => i.kind).lastIndexOf('watermark');
    expect(lastMark).toBeLessThan(first);
  });

  const texts = pages.flatMap((p) => p.items.filter((i) => i.kind === 'text').map((i: any) => i.text));

  it('дата скачивания подписана словами, а не просто «от»', () => {
    expect(texts.some((t) => t.includes('Дата скачивания: 21.08.2026'))).toBe(true);
  });

  it('поле исходящего номера есть и пустое', () => {
    expect(texts.some((t) => t.startsWith('Исх. №') && t.includes('_'))).toBe(true);
  });

  it('заполненный исходящий номер подставляется вместо прочерка', () => {
    const p = buildQuoteLayout({ ...data, outgoingNo: '17/2026' }, pdfMeasure());
    const tt = p.flatMap((x) => x.items.filter((i) => i.kind === 'text').map((i: any) => i.text));
    expect(tt).toContain('Исх. № 17/2026');
    expect(tt.some((t: string) => t.includes('Исх. № ____'))).toBe(false);
  });
});

describe('форматы КП', () => {
  it('PDF собирается', async () => {
    const pdf = await generateQuotePdf(data);
    expect(pdf.subarray(0, 4).toString()).toBe('%PDF');
    expect(pdf.length).toBeGreaterThan(2000);
  });

  it('JPG собирается и это действительно JPEG', () => {
    const jpg = generateQuoteJpg(data);
    expect(jpg[0]).toBe(0xFF);
    expect(jpg[1]).toBe(0xD8);
    expect(jpg.length).toBeGreaterThan(10000);
  });

  it('SVG страницы содержит те же тексты, что и раскладка', () => {
    const page = buildQuoteLayout(data, pdfMeasure())[0];
    const svg = quotePageSvg(page.items);
    expect(svg).toContain('Дата скачивания: 21.08.2026');
    expect(svg).toContain('Adobe Creative Cloud для команд');
    expect(svg).toContain('ООО «Энкор Менеджмент»');
  });
});

/**
 * Кому какой формат достаётся.
 *
 * Распоряжение руководителя 21.08.2026: клиент получает картинку, PDF
 * отправляет руководитель лично. Проверка нужна потому, что откатить это
 * можно одной строкой в обработчике, и заметит откат уже клиент.
 */
describe('форматы по получателям', () => {
  const api = readFileSync(resolve(__dirname, '../src/pages/api/quote.ts'), 'utf8');

  it('клиенту со страницы отдаётся JPEG, а не PDF', () => {
    expect(api).toMatch(/'Content-Type': 'image\/jpeg'/);
    expect(api).not.toMatch(/'Content-Type': 'application\/pdf'/);
  });

  it('в письме клиенту вложена картинка', () => {
    expect(api).toContain('clientAttachment');
    expect(api).toMatch(/contentType: 'image\/jpeg'/);
  });

  it('руководителю уходят Word и PDF', () => {
    expect(api).toContain('generateQuoteDocx');
    expect(api).toContain('wordprocessingml.document');
    expect(api).toMatch(/KP_\$\{quoteNo\}\.pdf/);
  });
});

describe('ответственный за заявку', () => {
  it('проставляется сам при скачивании КП', () => {
    expect(leadFromQuote({
      quoteNo: 'BZ-1', buyerCompany: 'ООО', buyerInn: '1', contactName: 'И',
      email: 'a@b.ru', phone: '', items: [], total: 0,
    }).owner).toBe(defaultLeadOwner);
  });

  it('это Беляев Алексей', () => {
    expect(defaultLeadOwner).toBe('Беляев Алексей');
  });

  it('проставляется и в заявке из формы сайта', () => {
    const src = readFileSync(resolve(__dirname, '../src/pages/api/lead.ts'), 'utf8');
    expect(src).toContain('owner: defaultLeadOwner');
  });
});
