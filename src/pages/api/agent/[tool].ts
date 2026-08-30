export const prerender = false;

/**
 * Read-only JSON-API для WebMCP-инструментов страницы (см. src/webmcp/).
 *
 * GET /api/agent/<tool>?<аргументы>. Только чтение каталога: эндпоинт не
 * пишет ни в Directus, ни в почту, ни в аналитику. Вход — недоверенный
 * (агент), проверяется схемой инструмента на сервере (runTool).
 *
 * Технический служебный URL: не индексируется (X-Robots-Tag) и в sitemap
 * не попадает. Выключенный рубильник (PUBLIC_WEBMCP=0) отвечает 404
 * с X-Agent-Api: disabled — по образцу закрытых товарных фидов, чтобы
 * мониторинг отличал «выключено решением» от «сломан маршрут».
 */
import type { APIRoute } from 'astro';
import { webmcpApiEnabled } from '../../../webmcp/flag';
import { runTool } from '../../../webmcp/handlers';
import { TOOL_NAMES } from '../../../webmcp/definitions';
import { isSourceUnavailable } from '../../../lib/http';

const json = (data: unknown, status = 200, cache = 'no-store') =>
  new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': cache,
      'X-Robots-Tag': 'noindex, nofollow',
    },
  });

export const GET: APIRoute = async ({ params, url }) => {
  if (!webmcpApiEnabled()) {
    return new Response(JSON.stringify({ ok: false, error: 'WebMCP API отключён' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json; charset=utf-8', 'X-Agent-Api': 'disabled', 'Cache-Control': 'no-store' },
    });
  }

  const tool = params.tool || '';
  // Дешёвая проверка до чтения аргументов и похода в каталог.
  if (!TOOL_NAMES.includes(tool)) {
    return json({ ok: false, error: `инструмент не существует; доступны: ${TOOL_NAMES.join(', ')}` }, 404);
  }

  const input: Record<string, string> = {};
  for (const [k, v] of url.searchParams.entries()) input[k] = v;

  try {
    const result = await runTool(tool, input);
    // Успешные ответы каталога недолго кэшируются: данные и так идут через
    // серверный кэш каталога (60 с), минута на CDN/браузере ничего не ломает.
    return json(result.body, result.status, result.status === 200 ? 'public, max-age=60' : 'no-store');
  } catch (e) {
    console.error(`agent api ${tool}`, e);
    if (isSourceUnavailable(e)) {
      return json({ ok: false, error: 'каталог временно недоступен, повторите позже' }, 503);
    }
    return json({ ok: false, error: 'внутренняя ошибка' }, 500);
  }
};
