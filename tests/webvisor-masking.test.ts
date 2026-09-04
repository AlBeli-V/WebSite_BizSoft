/**
 * Вебвизор и персональные данные (решение руководителя 03.09.2026: вебвизор
 * остаётся, поля с ПДн маскируются в коде, а не только настройкой кабинета).
 *
 * Проверка статическая: любое поле ввода с именем из списка ПДн обязано
 * нести класс ym-disable-keys — Метрика тогда не записывает нажатия клавиш в
 * нём независимо от настроек Вебвизора в кабинете. Новая форма без класса
 * роняет сборку, а не уезжает на прод.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const PII_FIELDS = new Set([
  'name', 'contact_name', 'email', 'phone', 'company', 'buyer_company',
  'inn', 'buyer_inn', 'message',
]);

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

const files = walk('src')
  .filter((f) => f.endsWith('.astro') || f.endsWith('.tsx'))
  .filter((f) => !f.includes(`${join('pages', 'admin')}`)); // админка — не для посетителей

describe('Вебвизор: поля с персональными данными маскируются', () => {
  it('вебвизор включён в счётчике — значит, маскирование обязательно', () => {
    const analytics = readFileSync('src/components/Analytics.astro', 'utf8');
    expect(analytics).toMatch(/webvisor:\s*true/);
  });

  it('каждое поле ПДн несёт класс ym-disable-keys', () => {
    const missing: string[] = [];
    for (const f of files) {
      const text = readFileSync(f, 'utf8');
      for (const m of text.matchAll(/<(input|textarea)\b[^>]*>/g)) {
        const tag = m[0];
        if (/type="hidden"/.test(tag)) continue;
        const name = tag.match(/\bname="([a-zA-Z_]+)"/)?.[1];
        if (!name || !PII_FIELDS.has(name)) continue;
        if (!/class="[^"]*\bym-disable-keys\b/.test(tag)) missing.push(`${f}: ${name}`);
      }
    }
    expect(missing, `поля без маскирования:\n${missing.join('\n')}`).toEqual([]);
  });

  it('список ПДн-полей покрывает все публичные формы', () => {
    // Страховка от переименования: формы заявки, вопроса и КП должны найтись.
    const found = new Set<string>();
    for (const f of files) {
      for (const m of readFileSync(f, 'utf8').matchAll(/\bname="([a-zA-Z_]+)"/g)) found.add(m[1]);
    }
    for (const must of ['email', 'phone', 'inn', 'buyer_inn', 'contact_name']) {
      expect(found.has(must), `поле ${must} не найдено в формах`).toBe(true);
    }
  });
});
