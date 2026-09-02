/**
 * Индексная матрица каталога: какие карточки уходят из поиска и фидов и какие
 * считаются дополнением к основному продукту.
 *
 * Пакеты кредитов (<VENDOR>-CREDITS-<объём>) — линейка, где позиции отличаются
 * только числом. Замер Вордстата 02.09.2026 показал, что на весь покупательский
 * интент по кредитам Kling приходится около сотни показов в месяц, тогда как
 * брендовый спрос вендорской страницы — 312 («kling ai купить»). Отдельная
 * индексируемая страница на каждый объём — малоценные страницы и каннибализация,
 * поэтому карточки живут на витрине и в КП, но не в поиске. Тест сторожит и само
 * правило, и то, что заведённые пакеты ему соответствуют.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { productNoindex, productKind } from '../src/lib/catalog';

const CATALOG = resolve(__dirname, '../scripts/catalog');
const creditPacks: { sku: string; slug: string }[] = existsSync(CATALOG)
  ? readdirSync(CATALOG)
      .filter((f) => f.endsWith('.json'))
      .flatMap((f) => (JSON.parse(readFileSync(resolve(CATALOG, f), 'utf8')).products ?? []))
      .filter((p: { sku?: string }) => /-CREDITS-\d+$/.test(String(p.sku || '')))
  : [];

describe('productNoindex', () => {
  it('пакеты кредитов не индексируются', () => {
    expect(productNoindex('KLING-CREDITS-330')).toBe(true);
    expect(productNoindex('KLING-CREDITS-96000')).toBe(true);
    expect(productNoindex('kling-credits-3500')).toBe(true);
  });

  it('прежние правила не сломаны', () => {
    expect(productNoindex('JB-PLG-12345')).toBe(true);
    expect(productNoindex('JB-IDEA-IND')).toBe(true);
    expect(productNoindex('ADOBE-CC-RENEWAL')).toBe(true);
  });

  it('основные товары индексируются', () => {
    // Тарифы того же вендора остаются в поиске: из линейки уходят только пакеты
    // кредитов, а не всё, где встречается слово credits.
    expect(productNoindex('KLING-STANDARD')).toBe(false);
    expect(productNoindex('KLING-PRO')).toBe(false);
    expect(productNoindex('JB-ALL-PACK-ORG')).toBe(false);
    expect(productNoindex('ACRONIS-CREDITS')).toBe(false); // без объёма — не пакет кредитов
  });
});

describe('productKind', () => {
  it('пакет кредитов — дополнение, тариф — основной продукт', () => {
    expect(productKind({ sku: 'KLING-CREDITS-7500' })).toBe('addon');
    expect(productKind({ sku: 'KLING-PREMIER' })).toBe('main');
  });
});

describe('заведённые пакеты кредитов', () => {
  it('партия на месте и вся подчиняется правилу', () => {
    expect(creditPacks.length).toBeGreaterThanOrEqual(8);
    for (const p of creditPacks) {
      expect(productNoindex(p.sku), `${p.sku} обязан быть noindex`).toBe(true);
      expect(productKind({ sku: p.sku }), `${p.sku} обязан быть дополнением`).toBe('addon');
    }
  });
});
