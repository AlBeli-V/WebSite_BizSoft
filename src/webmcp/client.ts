/**
 * Браузерный регистратор WebMCP-инструментов.
 *
 * Прогрессивное улучшение: если браузер не поддерживает Web Model Context
 * API (а это пока Chrome/Edge за origin trial или флагом
 * chrome://flags/#enable-webmcp-testing), функция молча выходит — ни
 * исключений в консоли, ни влияния на страницу. Отсутствие API — норма,
 * а не ошибка.
 *
 * Исполнение инструментов — на сервере (/api/agent/<tool>): браузерная
 * часть только описывает инструменты и переправляет вызовы. Логики,
 * данных и цен здесь нет — единственный источник остаётся серверным.
 *
 * Аналитика сознательно не трогается: вызов инструмента агентом — не
 * визит человека, целей и «просмотров» он порождать не должен.
 */
import { TOOL_DEFINITIONS } from './definitions';

/** Минимальные типы актуальной редакции спецификации (см. docs/webmcp/architecture.md).
 *  Свои, а не пакет webmcp-types: стандарт экспериментальный и меняется,
 *  зависимость от его типов связала бы сборку сайта с чужим релизным циклом. */
interface ToolResponse {
  content: { type: 'text'; text: string }[];
}
interface ModelContextLike {
  registerTool(tool: {
    name: string;
    title?: string;
    description: string;
    inputSchema: object;
    annotations?: { readOnlyHint?: boolean };
    execute: (input: Record<string, unknown>) => Promise<ToolResponse>;
  }): Promise<void> | void;
}

function modelContext(): ModelContextLike | null {
  // Актуальная точка входа — document.modelContext; navigator.modelContext —
  // устаревший алиас ранних сборок Chrome, оставлен как фолбэк.
  const d = document as Document & { modelContext?: ModelContextLike };
  const n = navigator as Navigator & { modelContext?: ModelContextLike };
  const mc = d.modelContext ?? n.modelContext;
  return mc && typeof mc.registerTool === 'function' ? mc : null;
}

const textResponse = (text: string): ToolResponse => ({ content: [{ type: 'text', text }] });

/** Вызов серверного обработчика инструмента. Ошибки возвращаются агенту текстом. */
async function callTool(name: string, input: Record<string, unknown>): Promise<ToolResponse> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(input || {})) {
    if (v !== undefined && v !== null) qs.set(k, String(v));
  }
  try {
    const res = await fetch(`/api/agent/${name}?${qs}`, { headers: { Accept: 'application/json' } });
    const body = await res.json().catch(() => null) as { ok?: boolean; data?: unknown; error?: string } | null;
    if (!body) return textResponse(`Ошибка: сервер вернул не-JSON (HTTP ${res.status}).`);
    if (!res.ok || body.ok === false) {
      return textResponse(`Ошибка: ${body.error || `HTTP ${res.status}`}`);
    }
    return textResponse(JSON.stringify(body.data));
  } catch {
    return textResponse('Ошибка: сеть недоступна, повторите попытку.');
  }
}

let registered = false;

/** Зарегистрировать инструменты сайта. Повторный вызов — no-op (идемпотентно). */
export function initWebMCP(): void {
  try {
    if (registered) return;
    const mc = modelContext();
    if (!mc) return; // браузер без WebMCP — молча ничего не делаем
    registered = true;
    for (const def of TOOL_DEFINITIONS) {
      // registerTool может вернуть Promise — гасим возможный reject,
      // чтобы экспериментальный API не сорил в консоль обычным посетителям.
      Promise.resolve(
        mc.registerTool({
          name: def.name,
          title: def.title,
          description: def.description,
          inputSchema: def.inputSchema,
          annotations: { readOnlyHint: true },
          execute: (input) => callTool(def.name, input),
        }),
      ).catch(() => {});
    }
  } catch {
    // Любой сбой экспериментального API не должен затронуть страницу.
  }
}
