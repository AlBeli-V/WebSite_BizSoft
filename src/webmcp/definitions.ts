/**
 * WebMCP: определения инструментов (имя, описание, схема входа).
 *
 * Файл изоморфный — его импортируют и браузерный регистратор
 * (src/webmcp/client.ts), и серверный эндпоинт (/api/agent/[tool]).
 * Поэтому здесь ЗАПРЕЩЕНЫ импорты серверных модулей (directus, mailer,
 * form-guard и т.п.): любая такая зависимость утянула бы серверный код
 * в клиентский бандл. Исполняемая логика живёт отдельно —
 * в src/webmcp/handlers.ts (сервер).
 *
 * Разделение «определение ↔ логика ↔ данные» — требование безопасности:
 * контент из Directus (описания товаров, тексты) не может влиять на
 * то, какие инструменты существуют и что они делают.
 *
 * Спецификация: WebMCP (W3C Web Machine Learning CG, CG-Draft),
 * редакция августа 2026 — см. docs/webmcp/architecture.md.
 */

/** Подмножество JSON Schema, которое понимает наш валидатор (validate.ts). */
export interface ToolParamSchema {
  type: 'string' | 'integer';
  description?: string;
  minLength?: number;
  maxLength?: number;
  minimum?: number;
  maximum?: number;
  enum?: string[];
}

export interface ToolInputSchema {
  type: 'object';
  properties: Record<string, ToolParamSchema>;
  required?: string[];
  additionalProperties: false;
}

export interface ToolDefinition {
  /** Имя инструмента (машинное, ≤128 символов по спецификации). */
  name: string;
  /** Короткий заголовок для UI агента. */
  title: string;
  /** Описание для выбора инструмента агентом. */
  description: string;
  inputSchema: ToolInputSchema;
  /** v1 целиком read-only; писать сюда false можно только вместе с
   *  отдельным решением по безопасности (см. docs/webmcp/security.md). */
  readOnly: true;
}

const vendorParam: ToolParamSchema = {
  type: 'string',
  minLength: 2,
  maxLength: 120,
  description: 'Производитель: имя (например «JetBrains», «Zoom») или slug его страницы (например «jetbrains»).',
};

const limitParam = (def: number, max: number): ToolParamSchema => ({
  type: 'integer',
  minimum: 1,
  maximum: max,
  description: `Максимум результатов (по умолчанию ${def}, не больше ${max}).`,
});

/**
 * Набор v1 — только чтение каталога. Универсальные инструменты:
 * новые товары и производители в Directus подхватываются автоматически,
 * инструментов «под конкретный продукт» не существует и создавать их нельзя.
 */
export const TOOL_DEFINITIONS: ToolDefinition[] = [
  {
    name: 'search_products',
    title: 'Поиск по каталогу BIZSoft',
    description:
      'Найти ПО или AI-сервис в каталоге BIZSoft (biz-soft.pro) по названию, производителю, артикулу (SKU) '
      + 'или ключевым словам. Возвращает список товаров с ценами в рублях и ссылками на карточки. '
      + 'Только чтение, ничего не покупает и не отправляет.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          minLength: 2,
          maxLength: 120,
          description: 'Что ищем: название продукта, производитель, SKU или ключевые слова (например «Claude для команды»).',
        },
        vendor: vendorParam,
        limit: limitParam(10, 30),
      },
      required: ['query'],
      additionalProperties: false,
    },
    readOnly: true,
  },
  {
    name: 'get_product',
    title: 'Карточка товара BIZSoft',
    description:
      'Получить полные данные одного товара каталога BIZSoft по slug страницы или артикулу (SKU): '
      + 'цена в рублях с НДС, тип лицензии, описание, условия приобретения для юрлица, ссылка на страницу. '
      + 'Нужно передать slug ИЛИ sku (хотя бы одно). Только чтение.',
    inputSchema: {
      type: 'object',
      properties: {
        slug: {
          type: 'string',
          minLength: 2,
          maxLength: 200,
          description: 'Slug карточки товара — последний сегмент адреса /product/<slug>.',
        },
        sku: {
          type: 'string',
          minLength: 2,
          maxLength: 120,
          description: 'Артикул товара (SKU), например «JB-ALL-PACK».',
        },
      },
      additionalProperties: false,
    },
    readOnly: true,
  },
  {
    name: 'list_vendors',
    title: 'Производители в каталоге BIZSoft',
    description:
      'Список всех производителей (вендоров) каталога BIZSoft с количеством товаров и ссылками '
      + 'на их страницы. Полезно, чтобы понять, какое ПО вообще доступно. Только чтение.',
    inputSchema: {
      type: 'object',
      properties: {},
      additionalProperties: false,
    },
    readOnly: true,
  },
  {
    name: 'get_vendor',
    title: 'Производитель в BIZSoft',
    description:
      'Информация об одном производителе из каталога BIZSoft: юридическое название, описание, '
      + 'число товаров, ссылка на страницу производителя. Только чтение.',
    inputSchema: {
      type: 'object',
      properties: { vendor: vendorParam },
      required: ['vendor'],
      additionalProperties: false,
    },
    readOnly: true,
  },
  {
    name: 'list_vendor_products',
    title: 'Товары производителя в BIZSoft',
    description:
      'Все товары одного производителя в каталоге BIZSoft: названия, тарифы/варианты лицензий, '
      + 'цены в рублях, ссылки на карточки. Помогает выбрать подходящий вариант. Только чтение.',
    inputSchema: {
      type: 'object',
      properties: {
        vendor: vendorParam,
        limit: limitParam(50, 100),
      },
      required: ['vendor'],
      additionalProperties: false,
    },
    readOnly: true,
  },
];

export const TOOL_NAMES = TOOL_DEFINITIONS.map((t) => t.name);

export function toolByName(name: string): ToolDefinition | undefined {
  return TOOL_DEFINITIONS.find((t) => t.name === name);
}
