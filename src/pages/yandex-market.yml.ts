export const prerender = false;

/**
 * YML-фид ассортимента для Яндекс Маркета (кабинет продавца).
 * Вся логика — в src/lib/feeds/* (реестр «yandex-market»).
 */
import type { APIRoute } from 'astro';
import { feedResponse } from '../lib/feeds/endpoint';

export const GET: APIRoute = () => feedResponse('yandex-market');
