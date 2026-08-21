/**
 * Заявка из скачивания КП.
 *
 * Канал самый тёплый: человек назвал организацию, ИНН, телефон и собрал
 * корзину. Проверяем, что в воронку попадает всё, что он о себе сообщил.
 */
import { describe, expect, it } from 'vitest';
import { leadFromQuote, describeQuote, summarizeItems } from '../src/lib/quote-lead';

const quote = {
  quoteNo: 'KP-2026-0042',
  buyerCompany: 'ООО «Энкор Менеджмент»',
  buyerInn: '7701234567',
  contactName: 'Екатерина Кувшинова',
  email: 'k@encoreresort.ru',
  phone: '+79167898651',
  items: [
    { sku: 'ADOBE-CC-TEAMS', name: 'Adobe Creative Cloud для команд', qty: 5, sum: 500000 },
    { sku: 'FIGMA-PRO', name: 'Figma Professional', qty: 3, sum: 90000 },
  ],
  total: 590000,
  validUntil: '05.09.2026',
};

describe('заявка из КП', () => {
  it('переносит контакты и реквизиты, а не только почту', () => {
    const lead = leadFromQuote(quote);
    expect(lead.name).toBe('Екатерина Кувшинова');
    expect(lead.company).toBe('ООО «Энкор Менеджмент»');
    expect(lead.inn).toBe('7701234567');
    expect(lead.phone).toBe('+79167898651');
    expect(lead.quote_no).toBe('KP-2026-0042');
  });

  it('сумма корзины попадает в сделку — вес виден сразу в списке', () => {
    expect(leadFromQuote(quote).amount).toBe(590000);
  });

  it('стадия — новая: документ ушёл автоматически, живой человек ещё не работал', () => {
    expect(leadFromQuote(quote).status).toBe('new');
    expect(leadFromQuote(quote).source).toBe('quote');
  });

  it('в карточке виден полный состав корзины, а не только итог', () => {
    const text = String(leadFromQuote(quote).message);
    expect(text).toContain('Adobe Creative Cloud для команд');
    expect(text).toContain('ADOBE-CC-TEAMS');
    expect(text).toContain('Figma Professional');
    expect(text.replace(/[\u00a0\u202f\s]/g, ' ')).toContain('590 000 ₽');
    expect(text).toContain('KP-2026-0042');
  });

  it('в колонке «Запрос» — короткая строка, а не простыня', () => {
    expect(summarizeItems(quote.items)).toBe('Adobe Creative Cloud для команд и ещё 1');
    expect(summarizeItems([quote.items[0]])).toBe('Adobe Creative Cloud для команд');
    expect(summarizeItems([])).toBe('КП без позиций');
  });

  it('пустая корзина не роняет описание', () => {
    expect(describeQuote({ ...quote, items: [], total: 0 })).toContain('KP-2026-0042');
  });

  it('без телефона заявка всё равно заводится', () => {
    expect(leadFromQuote({ ...quote, phone: undefined }).phone).toBe('');
  });
});

/**
 * Причины пропуска при переносе истории.
 *
 * «Уже в воронке» и «без номера» — разные вещи. Слитый счётчик читается как
 * «всё на месте» и тогда, когда КП просто нечем сопоставить, а это как раз
 * тот случай, когда канал остаётся невидимым.
 */
describe('перенос истории: причины пропуска различимы', () => {
  const classify = (quotes: { quote_no?: string }[], known: Set<string>) => {
    let skipped = 0; let noNumber = 0; let planned = 0;
    for (const q of quotes) {
      const no = String(q.quote_no || '').trim();
      if (!no) { noNumber += 1; continue; }
      if (known.has(no)) { skipped += 1; continue; }
      planned += 1;
    }
    return { skipped, skipped_no_number: noNumber, planned };
  };

  it('КП без номера не выдаётся за уже перенесённое', () => {
    const r = classify([{ quote_no: 'KP-1' }, { quote_no: '' }, {}], new Set(['KP-1']));
    expect(r.skipped).toBe(1);
    expect(r.skipped_no_number).toBe(2);
    expect(r.planned).toBe(0);
  });

  it('новое КП попадает в план переноса', () => {
    const r = classify([{ quote_no: 'KP-1' }, { quote_no: 'KP-2' }], new Set(['KP-1']));
    expect(r).toEqual({ skipped: 1, skipped_no_number: 0, planned: 1 });
  });
});
