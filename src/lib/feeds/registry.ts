/**
 * Реестр товарных фидов сайта.
 *
 * Подключение нового сервиса — новая запись здесь (плюс, при новом формате,
 * свой сериализатор рядом с yml.ts). Ядро отбора и страницы-обёртки при этом
 * не меняются.
 *
 * Лимит позиций каждого фида задаётся переменной окружения (0 или пусто —
 * без лимита): если сервис начнёт ограничивать количество, лимит включается
 * на проде без пересборки кода. Ранжирование по спросу Вордстата гарантирует,
 * что под лимит первыми попадают самые востребованные товары.
 */
import { site, seller } from '../../config/site';
import type { Product } from '../types';
import { selectFeedProducts } from './select';
import { buildYml, toFeedOffer } from './yml';
import type { FeedSpec } from './types';
import vendorDemand from '../../data/vendor-demand.json';

const DEMAND: Record<string, number> = vendorDemand.vendors;

const SHOP = { name: site.name, company: seller.shortName, url: site.url };

/** Лимит из переменной окружения; мусор и отрицательные значения — без лимита. */
export function envMaxOffers(envName: string): number {
  const raw = Number(process.env[envName] ?? '');
  return Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : 0;
}

/**
 * Открыт ли фид наружу. Решение руководителя 29.08.2026: фиды готовы, но
 * НЕ раздаются никому, пока руководитель не даст команду на открытие.
 *
 * По умолчанию (переменная не задана) все фиды закрыты и отдают 404.
 * Открытие — на проде, без пересборки кода:
 *   YANDEX_FEEDS_ENABLED=all                     — открыть все;
 *   YANDEX_FEEDS_ENABLED=yandex-products,...     — открыть перечисленные.
 */
export function feedEnabled(specId: string, env: string | undefined = process.env.YANDEX_FEEDS_ENABLED): boolean {
  const ids = (env || '').toLowerCase().split(',').map((s) => s.trim()).filter(Boolean);
  return ids.includes('all') || ids.includes(specId);
}

function buildYandexYml(products: Product[], opts: { now?: Date }): string {
  const now = opts.now ?? new Date();
  return buildYml(products.map((p) => toFeedOffer(p, site.url, now)), SHOP, now);
}

export const FEEDS: Record<string, FeedSpec> = {
  /** Яндекс Товары (кабинет merchants.yandex.ru), YML по ссылке. */
  'yandex-products': {
    id: 'yandex-products',
    service: 'Яндекс Товары',
    path: '/yandex-products.yml',
    contentType: 'application/xml; charset=utf-8',
    maxOffersEnv: 'YANDEX_PRODUCTS_FEED_MAX',
    build: buildYandexYml,
  },
  /** Яндекс Бизнес (карточки товаров в профиле организации), тот же YML. */
  'yandex-business': {
    id: 'yandex-business',
    service: 'Яндекс Бизнес',
    path: '/yandex-business.xml',
    contentType: 'application/xml; charset=utf-8',
    maxOffersEnv: 'YANDEX_BUSINESS_FEED_MAX',
    build: buildYandexYml,
  },
  /**
   * Яндекс Директ («Библиотека» → «Фиды»): товарные кампании и смарт-баннеры.
   * Упрощённый YML-фид Директа обязывает categoryId, name, url, price,
   * picture — всё это выдаёт общий сериализатор.
   */
  'yandex-direct': {
    id: 'yandex-direct',
    service: 'Яндекс Директ',
    path: '/yandex-direct.yml',
    contentType: 'application/xml; charset=utf-8',
    maxOffersEnv: 'YANDEX_DIRECT_FEED_MAX',
    build: buildYandexYml,
  },
  /**
   * Яндекс Маркет (кабинет partner.market.yandex.ru): выгрузка ассортимента
   * тем же YML. Сам выход на Маркет — отдельное бизнес-решение (модель DBS
   * для цифровых товаров, комиссии, обработка заказов) — см. docs/yandex-feeds.md.
   */
  'yandex-market': {
    id: 'yandex-market',
    service: 'Яндекс Маркет',
    path: '/yandex-market.yml',
    contentType: 'application/xml; charset=utf-8',
    maxOffersEnv: 'YANDEX_MARKET_FEED_MAX',
    build: buildYandexYml,
  },
};

/** Собрать документ фида из выборки каталога по спецификации из реестра. */
export function renderFeed(specId: string, products: Product[], now: Date = new Date()): { body: string; contentType: string; offerCount: number } {
  const spec = FEEDS[specId];
  if (!spec) throw new Error(`Неизвестный фид: ${specId}`);
  const picked = selectFeedProducts(products, {
    demand: DEMAND,
    maxOffers: envMaxOffers(spec.maxOffersEnv),
    extraFilter: spec.extraFilter,
    now,
  });
  return { body: spec.build(picked, { now }), contentType: spec.contentType, offerCount: picked.length };
}
