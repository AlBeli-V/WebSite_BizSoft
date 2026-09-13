import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Пакет позиций ManageEngine: что уходит в базу.
 *
 * Две вещи, которые сломать легче всего и заметить труднее всего:
 * пара «вечная лицензия + сопровождение» и граница между карточкой с
 * поисковой страницей и скрытой позицией конфигуратора.
 */

interface Position {
  sku: string;
  slug: string;
  name: string;
  status: string;
  official_name: string;
  base_price_usd: number | null;
  billing: string;
  notes: string;
  keywords: string;
  features: string[];
  pair_of?: string;
}

const pkg = JSON.parse(
  readFileSync(resolve(__dirname, '../scripts/catalog/zoho.json'), 'utf8'),
) as { products: Position[] };

const positions = pkg.products;
const bySku = new Map(positions.map((p) => [p.sku, p]));
const published = positions.filter((p) => p.status === 'published');
const hidden = positions.filter((p) => p.status === 'draft');
const ams = positions.filter((p) => p.pair_of);
const amsOf = new Map(ams.map((a) => [a.pair_of!, a]));
const perpetual = positions.filter(
  (p) => p.official_name.includes('(Perpetual License)') && !p.pair_of);

describe('состав пакета', () => {
  it('позиции есть, и карточек заметно меньше, чем скрытых', () => {
    expect(positions.length).toBeGreaterThan(1000);
    expect(published.length).toBeGreaterThan(0);
    expect(hidden.length).toBeGreaterThan(published.length);
  });

  it('артикулы и адреса уникальны по всему пакету', () => {
    expect(new Set(positions.map((p) => p.sku)).size).toBe(positions.length);
    expect(new Set(positions.map((p) => p.slug)).size).toBe(positions.length);
  });

  it('у каждой позиции есть цена источника', () => {
    for (const p of positions) {
      expect(p.base_price_usd, `${p.sku}: нет цены`).not.toBeNull();
      expect(p.base_price_usd!, `${p.sku}: цена не положительная`).toBeGreaterThan(0);
    }
  });
});

describe('вечная лицензия и сопровождение продаются парой', () => {
  it('у каждого контракта сопровождения есть своя вечная лицензия', () => {
    for (const a of ams) {
      const licenceSku = a.pair_of!;
      const licence = bySku.get(licenceSku);
      expect(licence, `${a.sku}: нет лицензии ${licenceSku}`).toBeDefined();
      // Модель лицензии берём из официального названия, а не из хвоста
      // артикула: у части позиций артикул несёт ещё и суффикс разведения
      // совпадений, и разбор строки тут врал бы.
      expect(licence!.official_name, `${a.sku}: пара не вечная лицензия`)
        .toContain('(Perpetual License)');
    }
  });

  it('у каждой вечной лицензии есть свой контракт сопровождения', () => {
    // Разовые работы вендора — перенос данных, установка, обучение — стоят в
    // тех же таблицах вечной лицензии, но лицензией не являются и
    // сопровождения не имеют. Их из проверки исключаем.
    const ONE_TIME = /one-?time|migration|training|installation|setup|onboarding|implementation/i;
    const licences = perpetual.filter((p) => !ONE_TIME.test(p.official_name));
    const withoutPair = licences.filter((p) => !amsOf.has(p.sku));
    if (withoutPair.length) console.log('без пары:', withoutPair.map((p) => p.sku).slice(0, 20));
    // Остаются только позиции, где вендор написал «Included»: сопровождение
    // уже в цене лицензии, отдельной строки прайса нет.
    expect(withoutPair.length, `вечных лицензий без пары: ${withoutPair.length}`)
      .toBeLessThanOrEqual(15);
  });

  it('сопровождение дешевле своей лицензии — это годовой процент, а не вторая лицензия', () => {
    for (const a of ams) {
      const licence = bySku.get(a.pair_of!)!;
      expect(a.base_price_usd!, `${a.sku}: сопровождение дороже лицензии`)
        .toBeLessThan(licence.base_price_usd!);
    }
  });

  it('контракт сопровождения не выносится карточкой на сайт', () => {
    for (const a of ams) {
      expect(a.status, `${a.sku}: сопровождение опубликовано отдельной страницей`).toBe('draft');
    }
  });

  it('в названии контракта видно, что это сопровождение', () => {
    for (const a of ams) {
      expect(a.name.toLowerCase(), `${a.sku}: непонятное название`).toContain('сопровождение');
    }
  });
});

describe('граница карточек и скрытых позиций', () => {
  it('карточка несёт поисковый текст, скрытая позиция — нет', () => {
    for (const p of published) {
      expect(p.keywords.length, `${p.sku}: карточка без ключевых слов`).toBeGreaterThan(10);
      expect(p.features.length, `${p.sku}: карточка без списка возможностей`).toBeGreaterThanOrEqual(3);
    }
  });

  it('скрытая позиция помечена в notes — иначе её происхождение не восстановить', () => {
    for (const p of hidden) {
      expect(p.notes, `${p.sku}: нет пометки`).toContain('конфигуратора');
      expect(p.notes, `${p.sku}: нет ссылки на снимок`).toMatch(/снимок [0-9a-f]{12}/);
    }
  });

  it('опубликованные карточки ServiceDesk Plus сохраняют прежние адреса', () => {
    for (const [sku, slug] of [['ZOHO-LIC-SDPSTD-TEAM-1Y-PACK-10TECH', 'manageengine-servicedesk-standard-10'], ['ZOHO-LIC-SDPPRO-TEAM-1Y-PACK-5TECH', 'manageengine-servicedesk-professional-5']]) {
      const p = bySku.get(sku);
      expect(p, `нет позиции ${sku}`).toBeDefined();
      expect(p!.slug).toBe(slug);
    }
  });
});
