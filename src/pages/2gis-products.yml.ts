export const prerender = false;

/**
 * YML-фид товаров для 2ГИС («Товары и цены» карточки компании).
 * Вся логика — в src/lib/feeds/* (реестр «2gis», особенности — dgis.ts).
 */
import type { APIRoute } from 'astro';
import { feedResponse } from '../lib/feeds/endpoint';

export const GET: APIRoute = () => feedResponse('2gis');
