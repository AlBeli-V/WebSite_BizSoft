import { describe, it, expect } from 'vitest';
import { ZOHO_GROUPS, ZOHO_RULES, zohoGroup, zohoFamily, zohoFamilyAnywhere } from '../src/data/zoho-hierarchy';
import { isSystemSku } from '../src/lib/sku';

/**
 * Иерархия Zoho ManageEngine собирается скриптом из снимков магазина вендора.
 * Тесты стерегут то, что при пересборке легко сломать молча: адреса уже
 * опубликованных карточек, уникальность артикулов и осмысленность правил
 * совместимости.
 */

const families = ZOHO_GROUPS.flatMap((g) => g.families);
const offers = families.flatMap((f) => f.deployments.flatMap((d) => d.offers));
const variants = offers.flatMap((o) => o.variants);

describe('группы', () => {
  it('их ровно десять — столько разделов у витрины магазина', () => {
    expect(ZOHO_GROUPS).toHaveLength(10);
  });

  it('слаги групп уникальны и находятся по слагу', () => {
    const slugs = ZOHO_GROUPS.map((g) => g.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
    for (const g of ZOHO_GROUPS) expect(zohoGroup(g.slug)?.name).toBe(g.name);
  });

  it('у каждой группы есть русское название и подводка', () => {
    for (const g of ZOHO_GROUPS) {
      expect(g.name.length).toBeGreaterThan(3);
      expect(g.lead.length).toBeGreaterThan(20);
    }
  });
});

describe('семейства', () => {
  it('слаг семейства уникален внутри группы и находится по паре слагов', () => {
    for (const g of ZOHO_GROUPS) {
      const slugs = g.families.map((f) => f.slug);
      expect(new Set(slugs).size).toBe(slugs.length);
      for (const f of g.families) expect(zohoFamily(g.slug, f.slug)?.name).toBe(f.name);
    }
  });

  it('у семейства с прайсом есть источник и время снятия', () => {
    for (const f of families.filter((x) => x.priced)) {
      expect(f.sourceUrl).toMatch(/^https:\/\/store\.manageengine\.com/);
      expect(f.sourceSnapshotId).toMatch(/^[0-9a-f]{12}$/);
      expect(f.sourceCheckedAt).toMatch(/^\d{4}-\d{2}-\d{2}/);
    }
  });

  it('у семейства без прайса нет ни одной позиции — цену за вендора не придумываем', () => {
    for (const f of families.filter((x) => !x.priced)) {
      expect(f.deployments).toHaveLength(0);
    }
  });

  it('обратный поиск семейства работает для всех', () => {
    for (const f of families) {
      expect(zohoFamilyAnywhere(f.slug)?.family.name).toBe(f.name);
    }
  });
});

describe('позиции', () => {
  it('артикулы уникальны по всему разделу', () => {
    const skus = variants.map((v) => v.sku);
    expect(new Set(skus).size).toBe(skus.length);
  });

  it('артикул — единой системы, адрес — прежний артикул в нижнем регистре', () => {
    for (const v of variants) {
      if (!v.sku) continue; // строка прайса без цены — позиции нет
      expect(isSystemSku(v.sku), v.sku).toBe(true);
      expect(v.slug).toMatch(/^(me|manageengine)-[a-z0-9-]+$/);
    }
  });

  it('опубликованные карточки ServiceDesk Plus сохраняют артикул и адрес', () => {
    // Обе позиции проиндексированы. Смена слага дала бы 404 на живой странице.
    const pinned = [
      { sku: 'ZOHO-LIC-SDPSTD-TEAM-1Y-PACK-10TECH', slug: 'manageengine-servicedesk-standard-10', name: '10 Technicians' },
      { sku: 'ZOHO-LIC-SDPPRO-TEAM-1Y-PACK-5TECH', slug: 'manageengine-servicedesk-professional-5', name: '5 Technicians (500 IT Assets)' },
    ];
    for (const p of pinned) {
      const found = variants.find((v) => v.sku === p.sku);
      expect(found, `нет позиции ${p.sku}`).toBeDefined();
      expect(found!.name).toBe(p.name);
      expect(found!.slug).toBe(p.slug);
    }
  });

  it('у опубликованной цены есть положительная сумма источника', () => {
    for (const v of variants.filter((x) => x.priceStatus === 'listed')) {
      expect(v.amountUsd).not.toBeNull();
      expect(v.amountUsd!).toBeGreaterThan(0);
    }
  });

  it('позиция «по запросу» суммы не несёт', () => {
    for (const v of variants.filter((x) => x.priceStatus === 'on_request')) {
      expect(v.amountUsd).toBeNull();
    }
  });
});

describe('правила совместимости', () => {
  it('каждое правило указывает на существующее семейство и предложение', () => {
    for (const rule of ZOHO_RULES) {
      const familySlug = rule.appliesTo.familySlug;
      expect(familySlug, `правило ${rule.id} без семейства`).toBeTruthy();
      const found = zohoFamilyAnywhere(familySlug!);
      expect(found, `правило ${rule.id}: нет семейства ${familySlug}`).toBeDefined();
      if (rule.appliesTo.offerSlug) {
        const slugs = found!.family.deployments.flatMap((d) => d.offers.map((o) => o.slug));
        expect(slugs, `правило ${rule.id}: нет предложения ${rule.appliesTo.offerSlug}`)
          .toContain(rule.appliesTo.offerSlug);
      }
    }
  });

  it('у каждого правила есть причина, которую видит покупатель', () => {
    for (const rule of ZOHO_RULES) {
      expect(rule.reason.length, `правило ${rule.id} без причины`).toBeGreaterThan(15);
    }
  });

  it('правило несёт ровно один вид связи', () => {
    for (const rule of ZOHO_RULES) {
      const kinds = [rule.requires, rule.excludes, rule.extends].filter(Boolean).length;
      expect(kinds, `правило ${rule.id}: видов связи ${kinds}`).toBe(1);
    }
  });

  it('идентификаторы правил уникальны', () => {
    const ids = ZOHO_RULES.map((r) => r.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('исключающее правило ссылается на предложение того же семейства', () => {
    for (const rule of ZOHO_RULES.filter((r) => r.excludes?.offerSlug)) {
      const found = zohoFamilyAnywhere(rule.appliesTo.familySlug!)!;
      const slugs = found.family.deployments.flatMap((d) => d.offers.map((o) => o.slug));
      expect(slugs).toContain(rule.excludes!.offerSlug);
    }
  });
});
