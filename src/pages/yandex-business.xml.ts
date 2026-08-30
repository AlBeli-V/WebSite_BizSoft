export const prerender = false;

/**
 * YML-фид товаров для Яндекс Бизнеса (карточки в профиле организации).
 * Вся логика — в src/lib/feeds/* (реестр «yandex-business»).
 */
import type { APIRoute } from 'astro';
import { feedResponse } from '../lib/feeds/endpoint';

export const GET: APIRoute = () => feedResponse('yandex-business');
