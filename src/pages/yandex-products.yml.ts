export const prerender = false;

/**
 * YML-фид для Яндекс Товаров (кабинет merchants.yandex.ru).
 * Вся логика — в src/lib/feeds/* (реестр «yandex-products»).
 */
import type { APIRoute } from 'astro';
import { feedResponse } from '../lib/feeds/endpoint';

export const GET: APIRoute = () => feedResponse('yandex-products');
