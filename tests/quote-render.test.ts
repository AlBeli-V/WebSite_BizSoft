/**
 * Отрисовка КП: PDF и JPG строятся из одной раскладки.
 *
 * Проверяем не «красиво», а то, что можно сломать молча: наличие водяных
 * знаков, поля исходящего номера, даты скачивания и совпадение содержимого
 * двух форматов.
 */
import { describe, expect, it } from 'vitest';
import { buildQuoteLayout, validityLine, watermarks, workdaysBetween, WATERMARK, LOGO_FILE } from '../src/lib/quote-layout';
import { generateQuotePdf, pdfMeasure, resolveAsset } from '../src/lib/pdf-quote';
import { generateQuoteJpgPages, jpgFileNames, quotePageSvg } from '../src/lib/jpg-quote';
import { leadFromQuote } from '../src/lib/quote-lead';
import { defaultLeadOwner } from '../src/config/site';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';

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
    // vendor приходит от API вместе с позицией: из него документ берёт
    // юридическое название производителя и форму поставки для фразы.
    { sku: 'ADOBE-CC-TEAMS', name: 'Adobe Creative Cloud для команд', vendor: 'Adobe', qty: 5, price: 100000, sum: 500000 },
    { sku: 'FIGMA-PRO', name: 'Figma Professional', vendor: 'Figma', qty: 3, price: 30000, sum: 90000 },
  ],
  total: 590000,
};

describe('раскладка КП', () => {
  const pages = buildQuoteLayout(data, pdfMeasure());

  it('штампов шесть на каждой странице — сетка 2×3, решение 28.08.2026', () => {
    for (const p of pages) {
      const marks = p.items.filter((i) => i.kind === 'watermark');
      expect(marks.length).toBe(WATERMARK.cols * WATERMARK.rows);
      expect(marks.length).toBe(6);
    }
  });

  it('знаки полупрозрачные и распределены по всей странице, а не в одном углу', () => {
    const marks = watermarks('проба');
    expect(WATERMARK.opacity).toBeGreaterThan(0);
    expect(WATERMARK.opacity).toBeLessThan(0.5);
    expect(new Set(marks.map((m) => m.kind === 'watermark' && m.x)).size).toBe(WATERMARK.cols);
    expect(new Set(marks.map((m) => m.kind === 'watermark' && m.y)).size).toBe(WATERMARK.rows);
  });

  it('это штамп с рамкой, а не просто надпись', () => {
    const [m] = watermarks('BZ-1') as any[];
    expect(m.w).toBeGreaterThan(0);
    expect(m.h).toBeGreaterThan(0);
    expect(m.radius).toBeGreaterThan(0);
    expect(m.stroke).toBeGreaterThan(0);
    expect(m.dash.length).toBeGreaterThan(2);
    expect(m.angle).not.toBe(0);
  });

  it('в оттиске статус, марка и номер, а не пометка «черновик»', () => {
    // Документ действующий: «черновик» на живом предложении обесценил бы
    // его в глазах получателя, а знак должен мешать присвоить, а не отменять.
    const [m] = watermarks('BZ-20260821-0042') as any[];
    expect(m.text).toBe('ПРЕДВАРИТЕЛЬНОЕ КП');
    expect(m.text2).toBe('BIZSoft');
    expect(m.sub).toBe('BZ-20260821-0042');
    expect(/draft|черновик|копия/i.test(`${m.text} ${m.text2} ${m.sub}`)).toBe(false);
  });

  it('штамп красный, тонкая рамка — решение 28.08.2026', () => {
    const [m] = watermarks('BZ-1') as any[];
    expect(m.color).toBe('#C81E1E');
    expect(m.stroke).toBeLessThan(2);
  });

  it('рамка попадает в оба формата одинаково', () => {
    const page = buildQuoteLayout(data, pdfMeasure())[0];
    const svg = quotePageSvg(page.items);
    expect(svg).toContain('stroke-dasharray');
    expect(svg).toMatch(/<rect[^>]+fill="none"/);
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

  it('исходящий номер — это номер КП, а не отдельное пустое поле', () => {
    // Два разных номера на одном документе рано или поздно приводят к
    // ссылке не на тот. Распоряжение руководителя 21.08.2026.
    expect(texts).toContain(`Исх. № ${data.quoteNo}`);
    expect(texts.some((t) => t.includes('Исх. № ____'))).toBe(false);
  });

  it('заданный вручную исходящий номер перекрывает номер КП', () => {
    const p = buildQuoteLayout({ ...data, outgoingNo: '17/2026' }, pdfMeasure());
    const tt = p.flatMap((x) => x.items.filter((i) => i.kind === 'text').map((i: any) => i.text));
    expect(tt).toContain('Исх. № 17/2026');
  });

  it('предмет предложения — услуги доступа, а не поставка лицензий', () => {
    // Формулировка руководителя 15.09.2026: шапка обязана совпадать с
    // предметом договора и с описанием позиций в таблице.
    const all = texts.join(' ');
    expect(all).toContain('Направляем Вам предварительное коммерческое предложение');
    expect(all).toContain('на оказание комплексных услуг по обеспечению доступа к программному обеспечению (ПО)');
    expect(all).toContain('web-сервисам и/или пополнению балансов API токенов');
    expect(all).toContain('Детальная спецификация состава услуг отражена в таблице настоящего предложения:');
    expect(all).not.toMatch(/поставку лицензий/);
  });

  it('условия поставки — по распоряжению, без ЭДО и договора', () => {
    const all = texts.join(' ');
    expect(all).toContain('Форма поставки: в электронном виде.');
    expect(all).toContain('100% аванс');
    expect(all).toContain('по согласованию сторон');
    expect(all).not.toMatch(/ЭДО|закрывающие документы/);
    expect(all).not.toMatch(/1–3 рабочих дня/);
  });

  it('срок действия назван рабочими днями и датой', () => {
    // Формулировка руководителя 15.09.2026: одна дата не говорит покупателю,
    // сколько у него времени на согласование.
    const all = texts.join(' ');
    // 21.08.2026 — пятница; до 05.09 (суббота) — десять рабочих дней.
    expect(all).toContain('Срок действия предложения: 10 (десять) рабочих дней до 05.09.2026.');
  });

  it('склонение и границы счёта рабочих дней', () => {
    expect(validityLine('15.09.2026', '16.09.2026')).toContain('1 (один) рабочий день до 16.09.2026.');
    expect(validityLine('15.09.2026', '18.09.2026')).toContain('3 (три) рабочих дня до 18.09.2026.');
    // Выходные не считаются: с пятницы по понедельник — один рабочий день.
    expect(workdaysBetween('18.09.2026', '21.09.2026')).toBe(1);
    // Нераспознанная дата не даёт выдумать срок.
    expect(workdaysBetween('нет даты', '21.09.2026')).toBe(null);
    expect(validityLine('нет даты', '21.09.2026')).toBe('Срок действия предложения: до 21.09.2026.');
  });

  it('оговорка о курсе ЦБ названа датой формирования КП', () => {
    // Цены привязаны к курсу ЦБ, и между КП и оплатой счёта он двигается:
    // условие пересчёта обязано стоять в самом предложении.
    const all = texts.join(' ');
    expect(all).toContain('рублёвый эквивалент стоимости рассчитан по курсу ЦБ РФ на дату 21.08.2026');
    expect(all).toContain('более чем на 5%');
    expect(all).toContain('как в большую, так и в меньшую сторону');
  });

  it('итог подписан «в т.ч. НДС», а налог выделен отдельной строкой', () => {
    // «В том числе» и «плюс» различаются на пять процентов суммы договора,
    // поэтому формулировка проверяется, а не подразумевается.
    const all = texts.join(' ');
    expect(all).toContain('ИТОГО в т.ч. НДС 5%');
    expect(all).toMatch(/НДС 5%: /);
    expect(all).not.toMatch(/НДС не облагается|специальный налоговый режим/);
  });

  it('сумма НДС посчитана изнутри суммы, а не сверху', () => {
    const vat = texts.find((t) => /^НДС 5%: /.test(t))!;
    // 590 000 × 5 / 105 = 28 095,24. Начисление сверху дало бы 29 500.
    expect(vat.replace(/\u00A0/g, ' ')).toContain('28 095,24');
  });

  it('итог и НДС показаны с копейками — их сверяют до копейки', () => {
    const total = texts.find((t) => t.startsWith('ИТОГО'))!;
    expect(total.replace(/\u00A0/g, ' ')).toContain('590 000,00');
  });

  it('строки итога жирные и прижаты к правому полю', () => {
    const rows = (buildQuoteLayout(data, pdfMeasure())[0].items as any[])
      .filter((i) => i.kind === 'text' && /ИТОГО|^НДС 5%: /.test(i.text));
    expect(rows.length).toBe(2);
    for (const r of rows) {
      expect(r.bold, r.text).toBe(true);
      expect(r.align, r.text).toBe('right');
    }
  });

  it('сумма прописью идёт по образцу руководителя', () => {
    const all = texts.join(' ');
    expect(all).toContain('Стоимость предложения:');
    expect(all).toMatch(/\(Пятьсот девяносто тысяч\) рублей 00 копеек/);
    expect(all).toMatch(/в т\.ч\. НДС 5% .*копе[ейк]/);
  });

  it('позиция без НДС не облагается налогом за компанию остальных', () => {
    // Одна ставка на весь документ добавила бы к налогу пять процентов
    // стоимости позиции, которая налогом не облагается.
    const mixed = buildQuoteLayout({
      ...data,
      items: [
        { sku: 'A', name: 'С налогом', qty: 1, price: 105000, sum: 105000, vat_percent: 5 },
        { sku: 'B', name: 'Без налога', qty: 1, price: 100000, sum: 100000, vat_percent: 0 },
      ],
      total: 205000,
    }, pdfMeasure());
    const tt = mixed.flatMap((p) => p.items.filter((i) => i.kind === 'text').map((i: any) => i.text));
    const vatRow = tt.find((t: string) => /^НДС/.test(t))!;
    // 105 000 × 5 / 105 = 5 000. Общая ставка дала бы 9 761,90.
    expect(vatRow.replace(/\u00A0/g, ' ')).toContain('5 000,00');
  });

  it('при разных ставках единая ставка в заголовке не пишется', () => {
    const mixed = buildQuoteLayout({
      ...data,
      items: [
        { sku: 'A', name: 'Пять', qty: 1, price: 100, sum: 100, vat_percent: 5 },
        { sku: 'B', name: 'Двадцать', qty: 1, price: 100, sum: 100, vat_percent: 20 },
      ],
      total: 200,
    }, pdfMeasure());
    const tt = mixed.flatMap((p) => p.items.filter((i) => i.kind === 'text').map((i: any) => i.text));
    const total = tt.find((t: string) => t.startsWith('ИТОГО'))!;
    // Иначе в заголовке стояла бы ставка, по которой посчитана часть суммы.
    expect(total).toContain('в т.ч. НДС:');
    expect(total).not.toMatch(/НДС 5%|НДС 20%/);
  });

  it('без указанной ставки берётся ставка по умолчанию', () => {
    const tt = texts.join(' ');
    expect(tt).toContain('НДС 5%');
  });

  it('оговорка — предварительный характер и «не оферта», без «проверки сотрудником»', () => {
    // Распоряжение 28.08.2026: прежняя формулировка «требует проверки и
    // коррекции сотрудником» говорила клиенту, что документ может быть
    // неверным. Новая — коммерческая: предварительный характер, скидки за
    // объём и условия — предмет переговоров; и это не публичная оферта.
    const all = texts.join(' ');
    expect(all).toContain('носит предварительный характер');
    expect(all).toContain('не является публичной офертой');
    expect(all).toContain('скидки за объём');
    expect(all).not.toMatch(/проверки и коррекции сотрудником|бюджетной оценкой/);
  });

  it('банковских реквизитов в предложении нет', () => {
    // Документ предварительный и гуляет по почте: платёжные данные
    // выставляются счётом, здесь они лишний риск.
    const all = texts.join(' ');
    expect(all).not.toMatch(/Р\/с|К\/с|БИК|Реквизиты для оплаты/);
  });

  it('колонки — как в спецификации на сайте: описание, кол-во, цена, сумма', () => {
    // Отдельной колонки артикула нет: он стоит внутри описания, как в
    // предмете договора. Прежняя колонка в 96 pt не вмещала системный
    // артикул, и он наезжал на название (находка руководителя 15.09.2026).
    expect(texts).toContain('Описание');
    expect(texts).toContain('Кол-во');
    expect(texts).toContain('Цена, ₽');
    expect(texts).toContain('Сумма, ₽');
    expect(texts).not.toContain('Артикул');
    expect(texts).not.toContain('Наименование');
  });

  it('описание позиции — то же, что в спецификации на сайте', () => {
    const all = texts.join(' ');
    // Юрлицо и название первой строкой, артикул второй, договорная фраза
    // третьей: документ и страница обязаны совпадать слово в слово.
    expect(all).toContain('Adobe Inc. / Adobe Creative Cloud для команд');
    expect(all).toContain('Артикул: ADOBE-CC-TEAMS');
    expect(all).toContain('Оказание услуг по предоставлению доступа');
  });

  it('аренда почты названа в фразе, но сноски «в цене учтена» в бланке нет', () => {
    const rent = buildQuoteLayout({
      ...data,
      items: [{ sku: 'ANTH-LIC-CLAUDETEAM-TEAM-1Y-USER-STD', name: 'Claude Team, Standard seat',
                vendor: 'Anthropic', qty: 1, price: 46421, sum: 46421, email_rent: true }],
      total: 46421,
    }, pdfMeasure());
    const all = rent.flatMap((p) => p.items.filter((i) => i.kind === 'text').map((i: any) => i.text)).join(' ');
    expect(all).toContain('учетной записи электронной почты');
    expect(all).not.toMatch(/В цене учтена аренда/);
  });

  it('каждый лист подписан номером и реквизитами продавца', () => {
    // Распечатанный лист многостраничного КП обязан называть себя сам:
    // раньше колонтитул стоял только на последнем.
    const many = buildQuoteLayout({
      ...data,
      items: Array.from({ length: 12 }, (_, i) => ({
        sku: `ANTH-LIC-CLAUDETEAM-TEAM-1Y-USER-${i}`, name: 'Claude Team, Standard seat',
        vendor: 'Anthropic', qty: 1, price: 46421, sum: 46421,
      })),
      total: 46421 * 12,
    }, pdfMeasure());
    expect(many.length).toBeGreaterThan(1);
    many.forEach((page, i) => {
      const tt = page.items.filter((x) => x.kind === 'text').map((x: any) => x.text);
      expect(tt, `лист ${i + 1}`).toContain(`Лист ${i + 1} из ${many.length}`);
      expect(tt.some((t: string) => t.includes('ИНН 507202054051')), `лист ${i + 1}`).toBe(true);
      // На листах продолжения — шапка с номером КП, чтобы лист не потерялся.
      if (i > 0) expect(tt.some((t: string) => t.includes('продолжение')), `лист ${i + 1}`).toBe(true);
    });
  });

  it('шапка таблицы повторяется на каждом листе с позициями', () => {
    const many = buildQuoteLayout({
      ...data,
      items: Array.from({ length: 12 }, (_, i) => ({
        sku: `ANTH-LIC-CLAUDETEAM-TEAM-1Y-USER-${i}`, name: 'Claude Team, Standard seat',
        vendor: 'Anthropic', qty: 1, price: 46421, sum: 46421,
      })),
      total: 46421 * 12,
    }, pdfMeasure());
    const withRows = many.filter((p) => p.items.some((x) => x.kind === 'text' && /^Артикул: /.test((x as any).text)));
    expect(withRows.length).toBeGreaterThan(1);
    for (const p of withRows) {
      expect(p.items.some((x) => x.kind === 'text' && (x as any).text === 'Описание')).toBe(true);
    }
  });
});

describe('форматы КП', () => {
  it('PDF собирается', async () => {
    const pdf = await generateQuotePdf(data);
    expect(pdf.subarray(0, 4).toString()).toBe('%PDF');
    expect(pdf.length).toBeGreaterThan(2000);
  });

  it('JPG собирается по файлу на лист, и это действительно JPEG', () => {
    const pages = generateQuoteJpgPages(data);
    expect(pages.length).toBeGreaterThan(0);
    for (const jpg of pages) {
      expect(jpg[0]).toBe(0xFF);
      expect(jpg[1]).toBe(0xD8);
      expect(jpg.length).toBeGreaterThan(10000);
    }
  });

  it('имена файлов называют лист только у многостраничного КП', () => {
    // Лента из склеенных страниц не печаталась: лист документа — лист файла
    // (решение руководителя 15.09.2026).
    expect(jpgFileNames('BZ-1', 1)).toEqual(['KP_BZ-1.jpg']);
    expect(jpgFileNames('BZ-1', 3)).toEqual([
      'KP_BZ-1_лист1.jpg', 'KP_BZ-1_лист2.jpg', 'KP_BZ-1_лист3.jpg',
    ]);
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

  it('в ответ уходит подтверждение, а не файл', () => {
    // Файл в ответе открывался просмотрщиком как страница «сохранить и
    // напечатать»: человек видел документ вместо ответа на вопрос,
    // отправили ему что-нибудь или нет.
    expect(api).toMatch(/'Content-Type': 'application\/json'/);
    expect(api).not.toMatch(/'Content-Type': 'image\/jpeg'[\s\S]{0,120}Content-Disposition/);
    expect(api).toContain('sent_to');
  });

  it('письмо клиенту отправляется до ответа, а не в фоне', () => {
    // Иначе экран говорит «отправлено» при упавшем SMTP.
    expect(api).toMatch(/await sendMail\(\{[\s\S]{0,200}to: data\.email/);
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

describe('логотип находится и в собранном приложении', () => {
  // В рантайм-образ копируется только dist: исходников и public/ там нет,
  // а сам модуль лежит в dist/server/pages/api. Прежний расчёт «два уровня
  // вверх» давал dist/public — файла по этому пути не существует, чтение
  // падало, и КП не уходило вовсе: сервер отвечал 500.
  it('берётся из dist/client, когда public/ рядом нет', () => {
    const root = mkdtempSync(join(tmpdir(), 'quote-asset-'));
    const dir = join(root, 'dist', 'client', 'brand');
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, 'sample-mark.png'), 'PNG');

    const cwd = process.cwd();
    try {
      process.chdir(root);
      expect(resolveAsset('public/brand/sample-mark.png'))
        .toBe(join(dir, 'sample-mark.png'));
    } finally {
      process.chdir(cwd);
      rmSync(root, { recursive: true, force: true });
    }
  });

  it('берётся из public/, когда работаем из исходников', () => {
    expect(resolveAsset(LOGO_FILE)).toContain(join('public', 'brand'));
  });

  it('о ненайденном файле сообщает с перечнем проверенных путей', () => {
    expect(() => resolveAsset('public/brand/нет-такого.png'))
      .toThrow(/проверены пути/);
  });
});
