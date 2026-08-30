/**
 * Валидация входа WebMCP-инструментов по их inputSchema.
 *
 * Вход агента — недоверенные данные, и проверяются они на СЕРВЕРЕ
 * (эндпоинт /api/agent/[tool]), а не только в браузере: клиентскую
 * проверку любой прямой запрос к эндпоинту обходит.
 *
 * Свой разбор вместо ajv: схемы v1 — плоские объекты со строками и целыми
 * (см. definitions.ts, тип ToolInputSchema ровно это и допускает),
 * а ajv с зависимостями — сотни килобайт в серверный бандл ради пяти схем.
 * Расширится подмножество схем — расширится и валидатор (тесты рядом).
 */
import type { ToolInputSchema } from './definitions';

export interface ValidationResult {
  ok: boolean;
  /** Человекочитаемые (для агента) причины отказа. */
  errors: string[];
  /** Нормализованный вход: только известные поля, строки обрезаны. */
  value: Record<string, string | number>;
}

/** Убрать управляющие символы и лишние пробелы: дальше строка пойдёт в фильтры и логи. */
function normalizeString(raw: string): string {
  return raw.replace(/[\u0000-\u001f\u007f]+/g, ' ').replace(/\s+/g, ' ').trim();
}

export function validateInput(schema: ToolInputSchema, input: unknown): ValidationResult {
  const errors: string[] = [];
  const value: Record<string, string | number> = {};

  if (input === null || typeof input !== 'object' || Array.isArray(input)) {
    return { ok: false, errors: ['вход должен быть объектом'], value };
  }
  const obj = input as Record<string, unknown>;

  // additionalProperties: false — неизвестные поля это ошибка, а не «пропустим»:
  // молчаливое отбрасывание маскирует опечатку агента в имени параметра.
  for (const key of Object.keys(obj)) {
    if (!(key in schema.properties)) errors.push(`неизвестное поле «${key}»`);
  }

  for (const [key, prop] of Object.entries(schema.properties)) {
    const raw = obj[key];
    const required = schema.required?.includes(key) ?? false;
    if (raw === undefined || raw === null || raw === '') {
      if (required) errors.push(`не заполнено обязательное поле «${key}»`);
      continue;
    }
    if (prop.type === 'string') {
      if (typeof raw !== 'string') {
        errors.push(`поле «${key}» должно быть строкой`);
        continue;
      }
      const s = normalizeString(raw);
      if (prop.minLength != null && s.length < prop.minLength) {
        errors.push(`поле «${key}» короче ${prop.minLength} символов`);
        continue;
      }
      if (prop.maxLength != null && s.length > prop.maxLength) {
        errors.push(`поле «${key}» длиннее ${prop.maxLength} символов`);
        continue;
      }
      if (prop.enum && !prop.enum.includes(s)) {
        errors.push(`поле «${key}» должно быть одним из: ${prop.enum.join(', ')}`);
        continue;
      }
      value[key] = s;
    } else {
      // integer. Число принимаем и числом, и строкой цифр: инструмент зовут
      // и через JSON (число), и через GET-параметры (строка).
      const n = typeof raw === 'number' ? raw : (typeof raw === 'string' && /^-?\d+$/.test(raw.trim()) ? Number(raw.trim()) : NaN);
      if (!Number.isInteger(n)) {
        errors.push(`поле «${key}» должно быть целым числом`);
        continue;
      }
      if (prop.minimum != null && n < prop.minimum) {
        errors.push(`поле «${key}» меньше ${prop.minimum}`);
        continue;
      }
      if (prop.maximum != null && n > prop.maximum) {
        errors.push(`поле «${key}» больше ${prop.maximum}`);
        continue;
      }
      value[key] = n;
    }
  }

  return { ok: errors.length === 0, errors, value };
}
