/**
 * Механизм товарных фидов (src/lib/feeds/*): отбор под требования площадок,
 * ранжирование по спросу Вордстата, лимит позиций и сериализация YML.
 */
import { describe, it, expect, afterEach } from 'vitest';
import type { Product } from '../src/lib/types';
import { feedEligible, rankProducts, selectFeedProducts, offerDescription, plainText } from '../src/lib/feeds/select';
import { buildYml, toFeedOffer, YML_DESCRIPTION_LIMIT } from '../src/lib/feeds/yml';
import { FEEDS, renderFeed, envMaxOffers, feedEnabled } from '../src/lib/feeds/registry';

const NOW = new Date('2026-08-29T12:00:00Z');

function product(over: Partial<Product> = {}): Product {
  return {
    id: 1,
    name: 'Figma Professional',
    sku: 'FIGMA-PRO',
    vendor: 'Figma',
    origin: 'foreign',
    category: { id: 10, name: 'Дизайн и графика', slug: 'design', status: 'published' },
    slug: 'figma-professional',
    short_description: 'Тариф Professional для дизайн-команд.',
    price: 12000,
    currency: 'RUB',
    status: 'published',
    ...over,
  } as Product;
}

describe('feedEligible: базовые требования площадок', () => {
  it('обычная карточка с ценой проходит', () => {
    expect(feedEligible(product(), NOW)).toBe(true);
  });

  it('цена по запросу (0) не проходит', () => {
    expect(feedEligible(product({ price: 0 }), NOW)).toBe(false);
  });

  it('noindex-карточка не проходит', () => {
    expect(feedEligible(product({ noindex: true }), NOW)).toBe(false);
  });

  it('плагины JB-PLG-*, личные *-IND и продления *-RENEWAL не проходят', () => {
    expect(feedEligible(product({ sku: 'JB-PLG-RAINBOW' }), NOW)).toBe(false);
    expect(feedEligible(product({ sku: 'JB-IDEA-IND' }), NOW)).toBe(false);
    expect(feedEligible(product({ sku: 'FIGMA-PRO-RENEWAL' }), NOW)).toBe(false);
  });

  it('карточка без slug или sku не проходит', () => {
    expect(feedEligible(product({ slug: '' }), NOW)).toBe(false);
    expect(feedEligible(product({ sku: '' }), NOW)).toBe(false);
  });

  it('акция с нулевой промоценой не делает карточку бесплатной', () => {
    // promo_price=0 не активирует акцию — карточка идёт с базовой ценой
    expect(feedEligible(product({ promo_price: 0 }), NOW)).toBe(true);
  });
});

describe('rankProducts: спрос Вордстата и порядок внутри вендора', () => {
  const demand = { Zoom: 1_000_000, Figma: 250_000 };

  it('вендор с большим спросом идёт первым, без данных — в хвост', () => {
    const ranked = rankProducts(
      [
        product({ id: 1, vendor: 'Figma', name: 'Figma' }),
        product({ id: 2, vendor: 'NoName', name: 'NoName App' }),
        product({ id: 3, vendor: 'Zoom', name: 'Zoom Workplace', sku: 'ZOOM-WORKPLACE' }),
      ],
      demand,
    );
    expect(ranked.map((p) => p.vendor)).toEqual(['Zoom', 'Figma', 'NoName']);
  });

  it('внутри вендора основной продукт раньше дополнения', () => {
    const ranked = rankProducts(
      [
        product({ id: 1, vendor: 'Zoom', sku: 'ZOOM-PHONE-PRO', name: 'Zoom Phone' }),
        product({ id: 2, vendor: 'Zoom', sku: 'ZOOM-WORKPLACE-PRO', name: 'Zoom Workplace Pro' }),
      ],
      demand,
    );
    expect(ranked[0].sku).toBe('ZOOM-WORKPLACE-PRO');
  });
});

describe('selectFeedProducts: конвейер с лимитом', () => {
  it('фильтрует, ранжирует и режет по maxOffers', () => {
    const items = [
      product({ id: 1, vendor: 'Figma' }),
      product({ id: 2, vendor: 'Zoom', sku: 'ZOOM-1', slug: 'zoom-1' }),
      product({ id: 3, vendor: 'Zoom', sku: 'ZOOM-2', slug: 'zoom-2', price: 0 }), // отсеется
    ];
    const picked = selectFeedProducts(items, { demand: { Zoom: 10, Figma: 5 }, maxOffers: 1, now: NOW });
    expect(picked).toHaveLength(1);
    expect(picked[0].vendor).toBe('Zoom');
  });
});

describe('описание оффера', () => {
  it('чистит HTML и схлопывает пробелы', () => {
    expect(plainText('<p>Тариф&nbsp;Pro</p>  <b>для команд</b>')).toBe('Тариф Pro для команд');
  });

  it('не бывает пустым и не превышает лимит', () => {
    const empty = offerDescription(product({ short_description: null }), YML_DESCRIPTION_LIMIT);
    expect(empty.length).toBeGreaterThan(0);
    const long = offerDescription(
      product({ short_description: 'слово '.repeat(1000) }),
      YML_DESCRIPTION_LIMIT,
    );
    expect(long.length).toBeLessThanOrEqual(YML_DESCRIPTION_LIMIT);
    expect(long.endsWith('…')).toBe(true);
  });
});

describe('buildYml: структура и экранирование', () => {
  const shop = { name: 'BIZSoft', company: 'ИП Тест', url: 'https://biz-soft.pro' };

  it('собирает валидный каркас с датой, категориями и оффером', () => {
    const p = product({ name: 'Tom & Jerry <Suite>' });
    const xml = buildYml([toFeedOffer(p, shop.url, NOW)], shop, NOW);
    expect(xml).toContain('<yml_catalog date="2026-08-29 12:00">');
    expect(xml).toContain('<currency id="RUR" rate="1"/>');
    expect(xml).toContain('<category id="1">Дизайн и графика</category>');
    expect(xml).toContain('<offer id="FIGMA-PRO" available="true">');
    expect(xml).toContain('<name>Tom &amp; Jerry &lt;Suite&gt;</name>');
    expect(xml).toContain('<url>https://biz-soft.pro/product/figma-professional</url>');
    expect(xml).toContain('<picture>https://biz-soft.pro/og/product/figma-professional.png</picture>');
    expect(xml).toContain('<price>12000</price>');
    expect(xml).not.toContain('<oldprice>');
  });

  it('активная акция даёт price=промо и oldprice=база', () => {
    const p = product({ promo_price: 9000, promo_start: '2026-08-01', promo_end: '2026-09-01' });
    const xml = buildYml([toFeedOffer(p, shop.url, NOW)], shop, NOW);
    expect(xml).toContain('<price>9000</price>');
    expect(xml).toContain('<oldprice>12000</oldprice>');
  });

  it('категории нумеруются стабильно по алфавиту', () => {
    const a = toFeedOffer(product({ id: 1 }), shop.url, NOW);
    const b = toFeedOffer(
      product({ id: 2, sku: 'X-1', slug: 'x-1', category: { id: 2, name: 'AI-сервисы', slug: 'ai', status: 'published' } }),
      shop.url,
      NOW,
    );
    const xml = buildYml([a, b], shop, NOW);
    // Локаль ru ставит кириллицу раньше латиницы — порядок стабилен
    expect(xml).toContain('<category id="1">Дизайн и графика</category>');
    expect(xml).toContain('<category id="2">AI-сервисы</category>');
  });
});

describe('реестр фидов', () => {
  afterEach(() => {
    delete process.env.YANDEX_PRODUCTS_FEED_MAX;
  });

  it('все яндекс-фиды объявлены с путями и env-лимитами', () => {
    expect(FEEDS['yandex-products'].path).toBe('/yandex-products.yml');
    expect(FEEDS['yandex-business'].path).toBe('/yandex-business.xml');
    expect(FEEDS['yandex-direct'].path).toBe('/yandex-direct.yml');
    expect(FEEDS['yandex-market'].path).toBe('/yandex-market.yml');
    // у каждого фида свой env-лимит — лимиты сервисов включаются независимо
    const envs = Object.values(FEEDS).map((f) => f.maxOffersEnv);
    expect(new Set(envs).size).toBe(envs.length);
  });

  it('renderFeed уважает лимит из переменной окружения', () => {
    process.env.YANDEX_PRODUCTS_FEED_MAX = '1';
    const items = [
      product({ id: 1, vendor: 'Figma' }),
      product({ id: 2, vendor: 'Zoom', sku: 'ZOOM-1', slug: 'zoom-1' }),
    ];
    const { offerCount, body } = renderFeed('yandex-products', items, NOW);
    expect(offerCount).toBe(1);
    // Zoom популярнее Figma в спросе Вордстата — под лимит попадает он
    expect(body).toContain('ZOOM-1');
    expect(body).not.toContain('FIGMA-PRO');
  });

  it('envMaxOffers: мусор и отрицательные значения = без лимита', () => {
    process.env.YANDEX_PRODUCTS_FEED_MAX = 'abc';
    expect(envMaxOffers('YANDEX_PRODUCTS_FEED_MAX')).toBe(0);
    process.env.YANDEX_PRODUCTS_FEED_MAX = '-5';
    expect(envMaxOffers('YANDEX_PRODUCTS_FEED_MAX')).toBe(0);
  });

  it('неизвестный фид — явная ошибка', () => {
    expect(() => renderFeed('nope', [], NOW)).toThrow('Неизвестный фид');
  });
});

describe('рубильник фидов (решение руководителя 29.08.2026)', () => {
  it('по умолчанию все фиды закрыты', () => {
    for (const id of Object.keys(FEEDS)) expect(feedEnabled(id, undefined)).toBe(false);
    expect(feedEnabled('yandex-products', '')).toBe(false);
  });

  it('all открывает все, список — только перечисленные', () => {
    expect(feedEnabled('yandex-market', 'all')).toBe(true);
    expect(feedEnabled('yandex-products', 'yandex-products, yandex-business')).toBe(true);
    expect(feedEnabled('yandex-market', 'yandex-products, yandex-business')).toBe(false);
  });
});
