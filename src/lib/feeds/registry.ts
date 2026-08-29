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
