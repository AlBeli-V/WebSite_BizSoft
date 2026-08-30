export const prerender = false;

/**
 * YML-фид для Яндекс Директа (товарные кампании, смарт-баннеры).
 * Вся логика — в src/lib/feeds/* (реестр «yandex-direct»).
 */
import type { APIRoute } from 'astro';
import { feedResponse } from '../lib/feeds/endpoint';

export const GET: APIRoute = () => feedResponse('yandex-direct');
