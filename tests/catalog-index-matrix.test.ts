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
import { parseSku } from '../src/lib/sku';

const CATALOG = resolve(__dirname, '../scripts/catalog');
const creditPacks: { sku: string; slug: string }[] = existsSync(CATALOG)
  ? readdirSync(CATALOG)
      .filter((f) => f.endsWith('.json'))
      .flatMap((f) => (JSON.parse(readFileSync(resolve(CATALOG, f), 'utf8')).products ?? []))
      .filter((p: { sku?: string }) => { const k = parseSku(p.sku); return k?.kind === 'CRD' && Boolean(k.variant); })
  : [];

describe('productNoindex', () => {
  it('пакеты кредитов не индексируются', () => {
    expect(productNoindex('KLNG-CRD-CREDITS-UNI-BAL-NOM-330')).toBe(true);
    expect(productNoindex('KLNG-CRD-CREDITS-UNI-BAL-NOM-96000')).toBe(true);
    expect(productNoindex('kling-credits-3500')).toBe(true);
  });

  it('личные лицензии любого вендора не индексируются (03.09.2026)', () => {
    expect(productNoindex('BITD-LIC-TOTALSEC-IND-1Y-PACK-SINGLE')).toBe(true);
    expect(productNoindex('MONO-LIC-FONTSPRO-IND-1Y-USER')).toBe(true);    // сегмент плана IND — личная
    expect(productNoindex('MONO-IND-PRO')).toBe(false);   // старая схема: -IND- в середине — не суффикс
    expect(productNoindex('MRMS-LIC-TOOLBAG5-IND-PERP-USER')).toBe(true);
    expect(productNoindex('MONO-LIC-FONTS-IND-1Y-USER')).toBe(true);
  });

  it('бессрочные дубли ManageEngine не индексируются, подписки — да', () => {
    expect(productNoindex('ZOHO-LIC-OPMGRSTD-TEAM-PERP-PACK-10DEV2USR')).toBe(true);
    expect(productNoindex('ZOHO-LIC-OPMGRSTD-TEAM-1Y-PACK-10DEV2USR')).toBe(false);
    expect(productNoindex('AVID-LIC-MEDIACOMP-UNI-PERP-USER')).toBe(false);   // не ManageEngine — точечно, не правилом
  });

  it('прежние правила не сломаны', () => {
    expect(productNoindex('JB-PLG-12345')).toBe(true);
    expect(productNoindex('JB-IDEA-IND')).toBe(true);
    expect(productNoindex('ADOBE-CC-RENEWAL')).toBe(true);
  });

  it('основные товары индексируются', () => {
    // Тарифы того же вендора остаются в поиске: из линейки уходят только пакеты
    // кредитов, а не всё, где встречается слово credits.
    expect(productNoindex('KLNG-LIC-STANDARD-UNI-1Y-USER')).toBe(false);
    expect(productNoindex('KLNG-LIC-PRO-UNI-1Y-USER')).toBe(false);
    expect(productNoindex('JB-LIC-ALLPACK-TEAM-1Y-USER')).toBe(false);
    expect(productNoindex('ACRONIS-CREDITS')).toBe(false); // без объёма — не пакет кредитов
  });
});

describe('productKind', () => {
  it('пакет кредитов — дополнение, тариф — основной продукт', () => {
    expect(productKind({ sku: 'KLNG-CRD-CREDITS-UNI-BAL-NOM-7500' })).toBe('addon');
    expect(productKind({ sku: 'KLNG-LIC-PREMIER-UNI-1Y-USER' })).toBe('main');
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

describe('партия ManageEngine и правило бессрочных дублей', () => {
  it('у каждой опубликованной бессрочной карточки есть парная подписка, и в индекс идёт только подписка', () => {
    const raw = JSON.parse(readFileSync('scripts/catalog/zoho.json', 'utf8'));
    const items: { sku: string; status?: string }[] = Array.isArray(raw) ? raw : raw.products ?? raw.items;
    const me = items.filter((i) => i.sku.startsWith('ZOHO-') && i.status === 'published');
    const skus = new Set(me.map((i) => i.sku));
    const perp = me.filter((i) => parseSku(i.sku)?.term === 'PERP');
    expect(perp.length).toBeGreaterThan(0);
    for (const i of perp) {
      expect(skus.has(i.sku.replace('-PERP-', '-1Y-')), `у ${i.sku} нет парной подписки`).toBe(true);
      expect(productNoindex(i.sku)).toBe(true);
    }
    for (const i of me.filter((i) => parseSku(i.sku)?.term !== 'PERP')) {
      expect(productNoindex(i.sku), `${i.sku} должна индексироваться`).toBe(false);
    }
  });
});
