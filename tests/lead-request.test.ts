/**
 * Разбор обращения по каталогу.
 *
 * Центральный случай — настоящая заявка 21.09.2026: «Требуется закупка 3-х
 * лицензий Perplexity Personal PRO на 6 месяцев». В каталоге такой позиции
 * нет: есть Perplexity Enterprise Pro и Enterprise Max, обе командные и
 * годовые. Письмо заказчику не имеет права назвать Enterprise Pro
 * подтверждённым предметом его заказа.
 */
import { describe, expect, it } from 'vitest';
import {
  detectQty, detectTerm, detectVendor, identifyRequest, productPhrase,
} from '../src/lib/lead-request';
import type { Product } from '../src/lib/types';

const product = (over: Partial<Product>): Product => ({
  id: over.slug!, name: '', sku: '', slug: '', category: null, ...over,
} as Product);

const CATALOG: Product[] = [
  product({ slug: 'perplexity-enterprise-pro', sku: 'PPLX-LIC-ENTPRO-TEAM-1Y-USER',
    name: 'Perplexity Enterprise Pro', vendor: 'Perplexity' }),
  product({ slug: 'perplexity-enterprise-max', sku: 'PPLX-LIC-ENTMAX-TEAM-1Y-USER',
    name: 'Perplexity Enterprise Max', vendor: 'Perplexity' }),
  product({ slug: 'adobe-cc-pro-team', sku: 'ADBE-LIC-CCPRO-TEAM-1Y-USER',
    name: 'Adobe Creative Cloud Pro для команд (все приложения)', vendor: 'Adobe' }),
  product({ slug: 'adobe-cc-pro', sku: 'ADBE-LIC-CCPRO-IND-1Y-USER',
    name: 'Adobe Creative Cloud Pro (все приложения)', vendor: 'Adobe' }),
];

const REAL = 'Добрый день,\n\nТребуется закупка 3-х лицензий Perplexity Personal PRO '
  + 'на 6 месяцев.\n\nПредоплата по счёту-оферте (сразу за три лицензии на 6 месяцев).\n\n'
  + 'Просьба уточнить, возможна ли оплата по счёту-оферте и оформление закрывающих '
  + 'документов сразу на 6 месяцев?';

describe('настоящая заявка 21.09.2026', () => {
  const review = identifyRequest(CATALOG, { productRef: 'количество: 3', message: REAL });

  it('производитель опознан — он есть в реестре', () => {
    expect(review.request.vendor).toBe('Perplexity');
  });

  it('продукт НЕ подтверждён: Personal Pro в каталоге нет', () => {
    expect(review.request.product).toBeUndefined();
    expect(review.request.matched).toBeUndefined();
    // Именно здесь нестрогий поиск подставил бы Enterprise Pro.
    expect(review.request.plan).toBeUndefined();
  });

  it('менеджеру уходит разбор: чего нет и что есть рядом', () => {
    expect(review.notes.join(' ')).toContain('«Perplexity Personal PRO» в каталоге не найдена');
    expect(review.candidates.map((p) => p.name)).toEqual([
      'Perplexity Enterprise Pro', 'Perplexity Enterprise Max',
    ]);
  });

  it('срок и количество разобраны', () => {
    expect(review.term).toEqual({ months: 6, label: '6 месяцев' });
    expect(review.request.qty).toBe('3');
  });

  it('прямой вопрос в обращении замечен', () => {
    expect(review.hasQuestion).toBe(true);
    expect(review.notes.join(' ')).toContain('прямой вопрос');
  });
});

describe('однозначное совпадение', () => {
  const review = identifyRequest(CATALOG, {
    productRef: 'количество: 5',
    message: 'Нужен Adobe Creative Cloud Pro для команд (все приложения), 5 мест.',
  });

  it('позиция подтверждена и получила тип плана из артикула', () => {
    expect(review.request.product).toBe('Adobe Creative Cloud Pro для команд (все приложения)');
    expect(review.request.plan).toBe('team');
    expect(review.request.qty).toBe('5');
  });

  it('альтернатива — тот же продукт другого плана, а не другой продукт', () => {
    // Тот же код продукта CCPRO, другой сегмент плана. Creative Cloud
    // Standard альтернативой не является: это другой продукт.
    expect(review.request.alternative?.slug).toBe('adobe-cc-pro');
  });
});

describe('на что письмо не ведёт', () => {
  const withNoise: Product[] = [
    ...CATALOG,
    // Вариант-номинал подарочной карты: его страница отдаёт 301 на родителя.
    product({ slug: 'jetbrains-gift-50', sku: 'JB-GFT-CARD-UNI-PERP-CARD-50',
      name: 'JetBrains подарочная карта 50', vendor: 'JetBrains', parent_sku: 'JB-GFT-CARD-UNI-PERP-CARD' }),
  ];

  it('вариант подарочной карты в разбор не попадает', () => {
    const r = identifyRequest(withNoise, { message: 'JetBrains подарочная карта 50' });
    expect(r.request.matched).toBeUndefined();
  });

  it('личный план ведётся в письмо, хотя закрыт от поисковиков', () => {
    // productNoindex закрывает индивидуальные планы от индексации, но
    // письмо не поисковик: страница жива, и это ровно то, за чем пришли.
    const r = identifyRequest(withNoise, {
      message: 'Нужен Adobe Creative Cloud Pro (все приложения), 1 лицензия.',
    });
    expect(r.request.matched?.slug).toBe('adobe-cc-pro');
    expect(r.request.plan).toBe('individual');
  });
});

describe('расхождения — менеджеру', () => {
  it('количество в поле и в тексте не совпало', () => {
    const r = identifyRequest(CATALOG, {
      productRef: 'количество: 3', message: 'Нужно 10 лицензий Perplexity.',
    });
    expect(r.request.qty).toBe('3');
    expect(r.notes.join(' ')).toContain('расходятся');
  });
});

describe('границы разбора', () => {
  it('без производителя разбор пуст, но это не сбой', () => {
    const r = identifyRequest(CATALOG, { message: 'Здравствуйте, нужен счёт на оплату.' });
    expect(r.request.vendor).toBeUndefined();
    expect(r.candidates).toEqual([]);
  });

  it('название без различителя плана остаётся неоднозначным', () => {
    // «Adobe Creative Cloud Pro» — это и личная позиция, и командная.
    // Подставить любую из них значило бы решить за клиента.
    const r = identifyRequest(CATALOG, { message: 'Интересует Adobe Creative Cloud Pro.' });
    expect(r.request.vendor).toBe('Adobe');
    expect(r.request.product).toBeUndefined();
    expect(r.notes.join(' ')).toContain('точная не определена');
  });

  it('вендор есть, продукт назван расплывчато — позиция не подтверждается', () => {
    const r = identifyRequest(CATALOG, { message: 'Интересует Perplexity для отдела.' });
    expect(r.request.vendor).toBe('Perplexity');
    expect(r.request.product).toBeUndefined();
    expect(r.candidates.length).toBe(2);
  });

  it('ссылки берутся из каталога, а не из текста обращения', () => {
    const r = identifyRequest(CATALOG, {
      message: 'Adobe Creative Cloud Pro, подробности https://evil.example/pay',
    });
    expect(JSON.stringify(r.request)).not.toContain('evil.example');
  });

  it.each([
    ['на 6 месяцев', 6], ['на 12 мес', 12], ['на год', 12], ['на 1 месяц', 1],
  ])('срок «%s» → %i мес.', (text, months) => {
    expect(detectTerm(text)?.months).toBe(months);
  });

  it('количество из поля формы главнее числа в тексте', () => {
    expect(detectQty({ productRef: 'количество: 3', message: 'нужно 10 лицензий' })).toBe('3');
    expect(detectQty({ message: 'нужно 10 лицензий' })).toBe('10');
  });

  it('имя продукта тянется только по латинским словам после марки', () => {
    expect(productPhrase('закупка Perplexity Personal PRO на 6 месяцев', 'Perplexity'))
      .toBe('Perplexity Personal PRO');
  });

  it('длинное имя марки не подменяется коротким', () => {
    expect(detectVendor('нужен Adobe Creative Cloud')).toBe('Adobe');
  });
});
