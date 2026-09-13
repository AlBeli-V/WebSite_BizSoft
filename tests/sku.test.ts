/**
 * Единая система артикулов (правило docs/rules/sku-system.md): грамматика,
 * сборка и разбор, реестры вендоров и продуктов, расстановка по каталогу,
 * автоприсваивание в импорте и чтение сегментов карточкой.
 */
import { describe, expect, it } from 'vitest';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  buildSku, findDuplicateSkus, isSystemSku, parseSku, proposeProductCode, termMonths, validateSkuParts,
  SKU_KINDS, SKU_PLANS, SKU_UNITS,
} from '../src/lib/sku';
import { productKind, productNoindex } from '../src/lib/catalog';
import { planType } from '../src/lib/plan-type';
import { termLabel, TERM } from '../src/lib/card-display';
import { cardComposition } from '../src/lib/product-composition';
import { autoSku, buildPlan } from '../src/lib/bulk-import';
import { isZohoConfiguratorSku } from '../src/lib/directus';
import { VENDORS } from '../src/data/vendors';

const ROOT = resolve(__dirname, '..');
const readJson = (rel: string) => JSON.parse(readFileSync(resolve(ROOT, rel), 'utf8'));
const vendors = readJson('data/catalog/sku-vendors.json').vendors as Record<string, string>;
const assignment = readJson('data/catalog/sku-assignment.json') as {
  total: number;
  items: { old: string; new: string; vendor: string; name: string; kind: string; plan: string; term: string; unit: string; variant: string | null; source: string; review?: string[] }[];
};
const registry = readJson('data/catalog/sku-products.json') as { products: Record<string, Record<string, string>>; plugins: Record<string, string> };

describe('грамматика артикула', () => {
  it('собирает семь сегментов и разбирает обратно', () => {
    const parts = { vendor: 'ADBE', kind: 'LIC', product: 'PHOTOSHOP', plan: 'TEAM', term: '1Y', unit: 'USER', variant: null } as const;
    const sku = buildSku(parts);
    expect(sku).toBe('ADBE-LIC-PHOTOSHOP-TEAM-1Y-USER');
    expect(parseSku(sku)).toEqual(parts);
    const withVariant = buildSku({ ...parts, kind: 'GFT', plan: 'UNI', term: 'BAL', unit: 'NOM', variant: 'RU1000' });
    expect(withVariant).toBe('ADBE-GFT-PHOTOSHOP-UNI-BAL-NOM-RU1000');
    expect(parseSku(withVariant)?.variant).toBe('RU1000');
  });

  it('старые артикулы за новую систему не принимает', () => {
    for (const s of ['JB-PLG-log-ORG', 'OPENAI-CREDITS-100', 'APP-STORE-ITUNES-GIFT-CARD-RU-1000', 'ME-ADAUDIT-PLUS-STANDARD-2-DOMAIN-CONTROLLERS-PERP', 'ADOBE-PS', 'INT-AI-CHATGPT', '', 'A-B-C-D-E-F-G-H']) {
      expect(isSystemSku(s), s).toBe(false);
    }
  });

  it('словари закрыты: чужое слово в сегменте — ошибка', () => {
    expect(validateSkuParts({ vendor: 'ADBE', kind: 'SUB' as never, product: 'PS', plan: 'TEAM', term: '1Y', unit: 'USER' })).toHaveLength(1);
    expect(validateSkuParts({ vendor: 'adbe', kind: 'LIC', product: 'PS', plan: 'TEAM', term: '1Y', unit: 'USER' })).toHaveLength(1);
    expect(validateSkuParts({ vendor: 'ADBE', kind: 'LIC', product: 'PS', plan: 'TEAM', term: '13X', unit: 'USER' })).toHaveLength(1);
    expect(validateSkuParts({ vendor: 'ADBE', kind: 'LIC', product: 'PHOTOSHOPELEMENTS', plan: 'TEAM', term: '1Y', unit: 'USER' })).toHaveLength(1);
    expect(validateSkuParts({ vendor: 'ADBE', kind: 'LIC', product: 'PS', plan: 'TEAM', term: '1Y', unit: 'USER', variant: 'RU-1000' })).toHaveLength(1);
    expect(() => buildSku({ vendor: 'ADBE', kind: 'LIC', product: 'PS', plan: 'TEAM', term: '1Y', unit: 'NOM' })).toThrow(/NOM/);
  });

  it('у кредитов и карт план UNI и единица NOM, срок BAL — только у них', () => {
    expect(validateSkuParts({ vendor: 'OPAI', kind: 'CRD', product: 'API', plan: 'TEAM', term: 'BAL', unit: 'NOM' })).toHaveLength(1);
    expect(validateSkuParts({ vendor: 'OPAI', kind: 'CRD', product: 'API', plan: 'UNI', term: 'BAL', unit: 'USER' })).toHaveLength(1);
    expect(validateSkuParts({ vendor: 'ADBE', kind: 'LIC', product: 'PS', plan: 'UNI', term: 'BAL', unit: 'USER' })).toHaveLength(1);
    expect(validateSkuParts({ vendor: 'OPAI', kind: 'CRD', product: 'API', plan: 'UNI', term: 'BAL', unit: 'NOM', variant: '100' })).toEqual([]);
  });

  it('срок: месяцы из <n>M и <n>Y, бессрочно и баланс — без числа', () => {
    expect(termMonths('1Y')).toBe(12);
    expect(termMonths('3M')).toBe(3);
    expect(termMonths('2Y')).toBe(24);
    expect(termMonths('PERP')).toBeNull();
    expect(termMonths('BAL')).toBeNull();
  });

  it('код продукта из названия: латиница до 12 знаков, длинное — первое слово и инициалы', () => {
    expect(proposeProductCode('Photoshop')).toBe('PHOTOSHOP');
    expect(proposeProductCode('aem-ide')).toBe('AEMIDE');
    expect(proposeProductCode('codegenbyvelocity')).toBe('CODEGENBYVEL');
    expect(proposeProductCode('aem-repository-tools')).toBe('AEMRT');
    expect(proposeProductCode('IntelliJ IDEA Ultimate')).toBe('INTELLIU');
    expect(proposeProductCode('Яндекс Трекер')).toBe('');
  });

  it('словари документированы: у каждого значения есть подпись', () => {
    for (const dict of [SKU_KINDS, SKU_PLANS, SKU_UNITS]) {
      for (const [k, v] of Object.entries(dict)) {
        expect(k).toMatch(/^[A-Z]{3,4}$/);
        expect(v.length).toBeGreaterThan(5);
      }
    }
  });
});

describe('реестр кодов вендоров', () => {
  it('коды уникальны и по форме', () => {
    const codes = Object.values(vendors);
    const dups = findDuplicateSkus(codes).filter((c) => c !== 'JB'); // JetBrains и JetBrains Marketplace — один вендор
    expect(dups).toEqual([]);
    for (const c of codes) expect(c).toMatch(/^[A-Z][A-Z0-9]{1,3}$/);
  });

  it('у каждого вендора реестра витрины есть код', () => {
    const missing = VENDORS.map((v) => v.vendor).filter((v) => !vendors[v]);
    expect(missing).toEqual([]);
  });
});

describe('расстановка по каталогу (data/catalog/sku-assignment.json)', () => {
  it('файлы расстановки совпадают с результатом генератора', () => {
    const out = execFileSync(process.execPath, ['scripts/catalog/sku-assign.mjs', '--check'], { cwd: ROOT, encoding: 'utf8' });
    expect(out).toMatch(/файлы актуальны/);
  });

  it('все позиции выгрузки получили артикул новой системы, без дублей', () => {
    expect(assignment.items.length).toBe(assignment.total);
    expect(findDuplicateSkus(assignment.items.map((i) => i.new))).toEqual([]);
    expect(findDuplicateSkus(assignment.items.map((i) => i.old))).toEqual([]);
    for (const i of assignment.items) {
      expect(isSystemSku(i.new), `${i.old} → ${i.new}`).toBe(true);
      expect(parseSku(i.new)?.vendor).toBe(vendors[i.vendor]);
    }
  });

  it('вид позиции совпадает с тем, что показывает карточка', () => {
    const byOld = new Map(assignment.items.map((i) => [i.old, i]));
    // Плагин Marketplace — дополнение, пакет кредитов — дополнение, подписка — основной продукт.
    expect(byOld.get('JB-PLG-log-ORG')?.new).toBe('JB-ADD-LOG-TEAM-1Y-USER');
    expect(byOld.get('KLING-CREDITS-1320')?.new).toBe('KLNG-CRD-CREDITS-UNI-BAL-NOM-1320');
    expect(byOld.get('OPENAI-API-BALANCE')?.new).toBe('OPAI-CRD-API-UNI-BAL-NOM');
    expect(byOld.get('APP-STORE-ITUNES-GIFT-CARD')?.new).toBe('APPL-GFT-APPSTORE-UNI-BAL-NOM');
    expect(byOld.get('APP-STORE-ITUNES-GIFT-CARD-RU-1000')?.new).toBe('APPL-GFT-APPSTORE-UNI-BAL-NOM-RU1000');
    expect(byOld.get('ME-ADAUDIT-PLUS-STANDARD-2-DOMAIN-CONTROLLERS-PERP')?.new).toBe('ZOHO-LIC-ADAUDITSTD-TEAM-PERP-PACK-2DC');
    expect(byOld.get('MAXON-REDGIANT-TEAMS')?.new).toBe('MAXN-LIC-REDGIANT-TEAM-1Y-USER');
    expect(byOld.get('MS-OFFICE-HB-2021-MAC')?.new).toBe('MSFT-LIC-OFFICEHB-UNI-PERP-DEV-2021MAC');
    for (const i of assignment.items) {
      if (i.old.startsWith('JB-PLG-')) expect(i.kind, i.old).toBe('ADD');
      if (/-CREDITS-\d+$/.test(i.old)) expect(i.kind, i.old).toBe('CRD');
      if (/-PERP$/.test(i.old)) expect(i.term, i.old).toBe('PERP');
      if (/-IND$/.test(i.old)) expect(i.plan, i.old).toBe('IND');
      if (/-ORG$/.test(i.old)) expect(i.plan, i.old).toBe('TEAM');
    }
  });

  it('вид позиции читается из новых артикулов так же, как из старых, кроме исправленных', () => {
    // Старая схема не называла вид у этих позиций; новая ставит ADD/CRD по
    // сути: надстройка AnyDesk, продление обновлений Principle, пакет
    // изображений Depositphotos, дополнения OpManager и OpUtils.
    const corrected = /^(ANYDESK-NAMESPACE|PRINCIPLE-UPDATES|DEPOSIT-PACK-100|ME-OPMANAGER-(NEXUS-FLOW|APM)-|ME-OPUTILS-)/;
    // Скрытые позиции конфигуратора ManageEngine старой схемой не различались вовсе.
    const diff = assignment.items.filter((i) => i.source !== 'zoho-hidden' && productKind({ sku: i.new }) !== productKind({ sku: i.old }) && !corrected.test(i.old));
    expect(diff.map((i) => `${i.old} → ${i.new}`)).toEqual([]);
  });

  it('индексная матрица: единственное расхождение со старой — личные планы без суффикса -IND', () => {
    // Старое правило ловило личные лицензии только по суффиксу -IND; новая
    // система называет план сегментом, и правило «личные лицензии любого
    // вендора — noindex» начинает действовать на все личные планы. Это
    // осознанное расхождение; любое другое — ошибка перевода.
    const other = assignment.items.filter((i) => i.source !== 'zoho-hidden' && productNoindex(i.new) !== productNoindex(i.old) && !(i.plan === 'IND' && !/-IND$/.test(i.old)) && i.old !== 'DEPOSIT-PACK-100');
    expect(other.map((i) => `${i.old} → ${i.new}`)).toEqual([]);
  });

  it('коды продуктов уникальны у вендора, плагины закреплены', () => {
    for (const [v, codes] of Object.entries(registry.products)) {
      for (const c of Object.keys(codes)) expect(c, `${v}/${c}`).toMatch(/^[A-Z0-9]{2,12}$/);
    }
    for (const [slug, code] of Object.entries(registry.plugins)) {
      expect(registry.products.JB[code], slug).toBeTruthy();
    }
  });

  it('умолчания в расстановке названы: перечень на проверку короткий и известный', () => {
    const flagged = assignment.items.filter((i) => i.review?.length);
    expect(flagged.length).toBeLessThanOrEqual(20);
    for (const i of flagged) expect(i.vendor).toMatch(/^(Adobe|Autodesk)$/);
  });

  it('раздел ManageEngine переведён целиком: карточки, скрытые позиции, сопровождение', () => {
    const zoho = assignment.items.filter((i) => i.vendor === 'Zoho');
    expect(zoho.length).toBeGreaterThan(4000);
    expect(zoho.filter((i) => i.kind === 'SVC').length).toBeGreaterThan(1000);
    for (const i of zoho) expect(parseSku(i.new)?.vendor, i.new).toBe('ZOHO');
  });
});

describe('карточка читает сегменты нового артикула', () => {
  it('тип плана — из сегмента, без эвристики по названию', () => {
    expect(planType('Что угодно Business', '', 'ADBE-LIC-PHOTOSHOP-IND-1Y-USER')).toBe('individual');
    expect(planType('Личная подписка', '', 'ADBE-LIC-PHOTOSHOP-TEAM-1Y-USER')).toBe('team');
    // UNI — деления нет, и название плана не подсказывает.
    expect(planType('Visual Studio Professional для команд', '', 'MSFT-LIC-VSPRO-UNI-PERP-USER-2022')).toBeNull();
  });

  it('срок — из сегмента: год, месяцы, бессрочно, баланс', () => {
    expect(termLabel({ sku: 'ADBE-LIC-PHOTOSHOP-TEAM-1Y-USER', name: 'Adobe Photoshop' }, 'unit_subscription')).toBe(TERM.year);
    expect(termLabel({ sku: 'SLDW-LIC-XDESIGN-UNI-3M-USER', name: 'SOLIDWORKS xDesign' }, 'unit_subscription')).toBe('3 месяца');
    expect(termLabel({ sku: 'MSFT-LIC-WIN11PRO-UNI-PERP-DEV', name: 'Windows 11 Pro' }, 'unit_subscription')).toBe(TERM.perpetual);
    expect(termLabel({ sku: 'OPAI-CRD-API-UNI-BAL-NOM-100', name: 'OpenAI API' }, 'addon')).toBe(TERM.balance);
    expect(termLabel({ sku: 'DISC-GFT-NITRO-UNI-1M-NOM-GL', name: 'Discord Nitro' }, 'balance_topup')).toBe('1 месяц');
    expect(termLabel({ sku: 'DISC-GFT-NITRO-UNI-12M-NOM-GL', name: 'Discord Nitro' }, 'balance_topup')).toBe(TERM.year);
  });

  it('композиция: кредиты и плагины — дополнение, подписка — расчётная единица', () => {
    expect(cardComposition({ sku: 'KLNG-CRD-CREDITS-UNI-BAL-NOM-1320', price: 3118 })).toBe('addon');
    expect(cardComposition({ sku: 'JB-ADD-LOG-TEAM-1Y-USER', price: 18842 })).toBe('addon');
    expect(cardComposition({ sku: 'ADBE-LIC-PHOTOSHOP-TEAM-1Y-USER', price: 58361 })).toBe('unit_subscription');
    expect(cardComposition({ sku: 'ANTH-LIC-CLAUDEENT-TEAM-1Y-USER', price: 0 })).toBe('quote_only');
  });

  it('noindex: личные планы, номиналы, плагины Marketplace, бессрочные ManageEngine, продления', () => {
    expect(productNoindex('JB-ADD-LOG-TEAM-1Y-USER')).toBe(true);
    expect(productNoindex('JB-LIC-CLION-TEAM-1Y-USER')).toBe(false);
    expect(productNoindex('JB-LIC-CLION-IND-1Y-USER')).toBe(true);
    expect(productNoindex('ZOHO-LIC-ADAUDITSTD-TEAM-PERP-PACK-2DC')).toBe(true);
    expect(productNoindex('ZOHO-LIC-ADAUDITSTD-TEAM-1Y-PACK-2DC')).toBe(false);
    expect(productNoindex('WPC-LIC-BUSINESS-UNI-1Y-ORG-RENEWAL')).toBe(true);
    expect(productNoindex('OPAI-CRD-API-UNI-BAL-NOM-100')).toBe(true);
    expect(productNoindex('OPAI-CRD-API-UNI-BAL-NOM')).toBe(false);
    expect(productNoindex('APPL-GFT-APPSTORE-UNI-BAL-NOM-RU1000')).toBe(true);
    expect(productNoindex('APPL-GFT-APPSTORE-UNI-BAL-NOM')).toBe(false);
  });

  it('конфигуратор ManageEngine принимает и старые, и новые артикулы', () => {
    expect(isZohoConfiguratorSku('ZOHO-LIC-ADAUDITSTD-TEAM-1Y-PACK-2DC')).toBe(true);
    expect(isZohoConfiguratorSku('ME-ADAUDIT-PLUS-STANDARD-2-DOMAIN-CONTROLLERS')).toBe(true);
    expect(isZohoConfiguratorSku('ADBE-LIC-PHOTOSHOP-TEAM-1Y-USER')).toBe(false);
  });
});

describe('автоприсваивание в импорте', () => {
  it('собирает артикул из сегментов строки с умолчаниями правила', () => {
    expect(autoSku({ vendor: 'Adobe', sku_product: 'Photoshop', sku_plan: 'team' })).toEqual({ sku: 'ADBE-LIC-PHOTOSHOP-TEAM-1Y-USER' });
    expect(autoSku({ vendor: 'OpenAI', sku_kind: 'CRD', sku_product: 'API', sku_variant: '100' })).toEqual({ sku: 'OPAI-CRD-API-UNI-BAL-NOM-100' });
  });

  it('вендор без кода и кривой сегмент — ошибка строки, а не молчаливый артикул', () => {
    expect(autoSku({ vendor: 'Неизвестный', sku_product: 'X1' })).toMatchObject({ errors: [expect.stringContaining('нет кода вендора')] });
    expect(autoSku({ vendor: 'Adobe', sku_product: 'Photoshop', sku_term: 'год' })).toMatchObject({ errors: [expect.stringContaining('срок')] });
  });

  it('план импорта: строка без sku, но с сегментами, создаёт карточку с собранным артикулом', () => {
    const plan = buildPlan(
      [{ name: 'Adobe Photoshop для команд', vendor: 'Adobe', sku_product: 'PHOTOSHOP', sku_plan: 'TEAM', price: '100' },
       { name: 'Без сегментов', vendor: 'Adobe', price: '100' }],
      [], () => null,
    );
    expect(plan.items[0]).toMatchObject({ sku: 'ADBE-LIC-PHOTOSHOP-TEAM-1Y-USER', mode: 'create' });
    expect(plan.items[0].payload.sku).toBe('ADBE-LIC-PHOTOSHOP-TEAM-1Y-USER');
    expect(plan.items[1]).toMatchObject({ mode: 'skip', errors: ['пустой sku'] });
  });
});
