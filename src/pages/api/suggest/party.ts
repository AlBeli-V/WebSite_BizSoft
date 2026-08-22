export const prerender = false;

import type { APIRoute } from 'astro';
import { suggestParty } from '../../../lib/dadata';

const json = (d: unknown, s = 200, cache = 'no-store') =>
  new Response(JSON.stringify(d), {
    status: s,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': cache },
  });

/**
 * Подсказки по организациям для формы заявки.
 *
 * Прокси, а не прямой запрос из браузера: ключ справочника остаётся на
 * сервере. DaData допускает клиентский ключ с ограничением по домену, но
 * ограничение задаётся в чужом кабинете и незаметно снимается, а утёкший
 * ключ расходует наш суточный лимит в десять тысяч запросов.
 *
 * Ответ короткий и без служебных полей: браузеру нужно показать список и
 * подставить реквизиты, всё остальное — лишний вес и лишние данные.
 */
export const GET: APIRoute = async ({ url }) => {
  const q = (url.searchParams.get('q') || '').trim();
  if (q.length < 3) return json({ items: [] });

  try {
    const found = await suggestParty(q);
    return json({
      items: found.map((c) => ({
        name: c.name,
        fullName: c.fullName,
        inn: c.inn,
        kpp: c.kpp,
        address: c.address,
        manager: c.manager,
      })),
      // Ответы по одному запросу одинаковы минутами; кэш экономит суточный
      // лимит, который делится между всеми видами подсказок.
    }, 200, 'private, max-age=120');
  } catch (e) {
    // Подсказки — удобство, а не условие работы формы. Справочник молчит —
    // человек заполняет поля руками, как раньше.
    console.error('suggest party failed', e);
    return json({ items: [], unavailable: true });
  }
};
