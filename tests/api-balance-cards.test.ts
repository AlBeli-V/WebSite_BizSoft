/**
 * Пополнения баланса API: формула цены и защита от каннибализации.
 *
 * Механизм заведён 11.09.2026 по решению руководителя: программный доступ
 * продаётся не местами, а суммой на балансе, и у одного вендора таких карточек
 * десяток — отличаются они одним числом. Отсюда две опасности, которые и
 * сторожит этот тест.
 *
 * Первая — цена. Себестоимость = номинал × 1,22 (НДС поставщика), витрина
 * считается штатно: себестоимость × 1,9 × курс ЦБ. Ошибка в одном номинале из
 * одиннадцати незаметна глазом и уезжает в прод счётом клиенту.
 *
 * Вторая — поиск. Одиннадцать почти одинаковых страниц под один интент —
 * малоценные страницы и каннибализация страницы вендора. Артикул
 * <вендор>-CRD-<продукт>-UNI-BAL-NOM-<номинал> закрыт правилом productNoindex; индекс держит
 * родительская карточка «Пополнение баланса …». Стоит кому-то назвать артикул
 * иначе — правило перестанет срабатывать молча.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
// @ts-expect-error — сборщик карточек на JS, типов у него нет
import { renderCards } from '../scripts/build-api-balance-cards.mjs';
import { productKind, productNoindex } from '../src/lib/catalog';

const root = resolve(__dirname, '..');
const registry = JSON.parse(readFileSync(resolve(root, 'scripts/api-balance.json'), 'utf8'));
const cards = JSON.parse(readFileSync(resolve(root, 'scripts/api-balance-cards.json'), 'utf8'));

interface Card {
  sku: string; name: string; base_price?: number; currency?: string;
  markup_coeff?: number; price_on_request?: boolean; sort: number;
  short_desc_ru: string; description_ru: string; features_ru: string[];
}
const all: Card[] = cards.vendors.flatMap((v: { products: Card[] }) => v.products);
const topups = all.filter((c) => /-NOM-\d+$/.test(c.sku));
const parents = all.filter((c) => !/-NOM-\d+$/.test(c.sku));

describe('Пополнения баланса API: реестр и карточки', () => {
  it('сгенерированный файл не разошёлся с реестром', () => {
    expect(readFileSync(resolve(root, 'scripts/api-balance-cards.json'), 'utf8')).toBe(renderCards());
  });

  it('в ряду ровно те номиналы, что заведены у вендора', () => {
    for (const v of registry.vendors) {
      const got = all
        .filter((c) => c.sku.startsWith(`${v.parent_sku}-`))
        .map((c) => Number(c.sku.split('-').pop()));
      expect(got).toEqual(v.denominations);
    }
  });

  it('себестоимость — номинал × коэффициент НДС, коэффициент наценки на месте', () => {
    const { vat_coeff: vat, markup_coeff: markup } = registry.defaults;
    for (const c of topups) {
      const nominal = Number(c.sku.split('-').pop());
      expect(c.base_price).toBe(Math.round(nominal * vat * 100) / 100);
      expect(c.currency).toBe('USD');
      expect(c.markup_coeff).toBe(markup);
      expect(c.price_on_request).toBe(false);
    }
  });

  it('родительская карточка — по запросу и без себестоимости', () => {
    expect(parents.length).toBe(registry.vendors.length);
    for (const p of parents) {
      expect(p.price_on_request).toBe(true);
      expect(p.base_price).toBeUndefined();
    }
  });

  it('номиналы закрыты от индексации, родитель — нет', () => {
    for (const c of topups) {
      expect(productNoindex(c.sku), `${c.sku} должен быть noindex`).toBe(true);
      expect(productKind({ sku: c.sku })).toBe('addon');
    }
    for (const p of parents) {
      expect(productNoindex(p.sku), `${p.sku} должен индексироваться`).toBe(false);
      expect(productKind({ sku: p.sku })).toBe('main');
    }
  });

  it('артикулы уникальны, порядок не совпадает у двух карточек', () => {
    expect(new Set(all.map((c) => c.sku)).size).toBe(all.length);
    expect(new Set(all.map((c) => c.sort)).size).toBe(all.length);
  });

  it('карточка не выдаёт себя за подписку и несёт своё описание', () => {
    for (const c of all) {
      expect(c.description_ru.length).toBeGreaterThan(200);
      expect(c.description_ru).not.toContain('подписка оформляется на компанию');
      expect(c.features_ru.length).toBeGreaterThanOrEqual(4);
      expect(c.short_desc_ru).toContain('баланс');
    }
  });
});
