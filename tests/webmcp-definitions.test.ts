/**
 * Реестр WebMCP-инструментов: инварианты, которые нельзя нарушать
 * при добавлении/правке инструментов.
 */
import { describe, expect, it } from 'vitest';
import { TOOL_DEFINITIONS, TOOL_NAMES, toolByName } from '../src/webmcp/definitions';

describe('WebMCP definitions', () => {
  it('имена уникальны, машинные и укладываются в лимит спецификации (128)', () => {
    expect(new Set(TOOL_NAMES).size).toBe(TOOL_NAMES.length);
    for (const name of TOOL_NAMES) {
      expect(name.length).toBeLessThanOrEqual(128);
      expect(name).toMatch(/^[a-z][a-z0-9_]*$/);
    }
  });

  it('v1 целиком read-only: write-инструменты требуют отдельного решения', () => {
    for (const t of TOOL_DEFINITIONS) expect(t.readOnly).toBe(true);
  });

  it('описания и заголовки заполнены — агент выбирает инструмент по ним', () => {
    for (const t of TOOL_DEFINITIONS) {
      expect(t.title.length).toBeGreaterThan(3);
      expect(t.description.length).toBeGreaterThan(40);
      // Read-only заявлен и словами: агенту важно знать, что вызов безопасен.
      expect(t.description).toContain('чтение');
    }
  });

  it('inputSchema — валидное подмножество JSON Schema', () => {
    for (const t of TOOL_DEFINITIONS) {
      expect(t.inputSchema.type).toBe('object');
      expect(t.inputSchema.additionalProperties).toBe(false);
      for (const req of t.inputSchema.required ?? []) {
        expect(t.inputSchema.properties).toHaveProperty(req);
      }
      for (const [key, prop] of Object.entries(t.inputSchema.properties)) {
        expect(['string', 'integer']).toContain(prop.type);
        expect(prop.description, `${t.name}.${key} без description`).toBeTruthy();
      }
    }
  });

  it('никаких инструментов под конкретный продукт (get_claude и т.п.)', () => {
    for (const name of TOOL_NAMES) {
      expect(name).toMatch(/^(search_|get_product$|get_vendor$|list_)/);
    }
  });

  it('toolByName находит инструмент и не находит мусор', () => {
    expect(toolByName('get_product')?.name).toBe('get_product');
    expect(toolByName('get_chatgpt')).toBeUndefined();
  });
});
