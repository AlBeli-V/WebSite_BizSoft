/**
 * Барьер против дублей заголовков на этапе заведения карточек.
 *
 * Заголовок страницы товара — это meta_title из Directus, а при пустом
 * meta_title подставляется название товара (src/pages/product/[slug].astro).
 * В пакетах scripts/catalog/*.json меты нет вовсе, значит две позиции с
 * одинаковым `name` дают две страницы с одинаковым <title> — ровно то, за что
 * Яндекс снял с индексации карточки Depositphotos (01.09.2026).
 *
 * Тест не требует разгребать старый долг разом: известные группы записаны в
 * data/seo/known-duplicate-names.json и пропускаются. Новая группа —
 * это падение сборки: развести названия дешевле до импорта, чем после
 * попадания страниц в индекс.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { resolve, basename } from 'node:path';

type Product = { sku: string; slug: string; name?: string; archive?: boolean; short_description?: string };
type Package = { removed?: boolean; products?: Product[] };

const CATALOG = resolve(__dirname, '../scripts/catalog');
const BASELINE = resolve(__dirname, '../data/seo/known-duplicate-names.json');

const packages = existsSync(CATALOG)
  ? readdirSync(CATALOG)
      .filter((f) => f.endsWith('.json'))
      .map((f) => ({ file: basename(f), pkg: JSON.parse(readFileSync(resolve(CATALOG, f), 'utf8')) as Package }))
  : [];

/** Живые позиции: снятые вендоры и архивные стабы витрины не касаются. */
const live = packages
  .filter(({ pkg }) => !pkg.removed)
  .flatMap(({ file, pkg }) => (pkg.products ?? [])
    .filter((p) => !p.archive)
    .map((p) => ({ ...p, file })));

const baseline = JSON.parse(readFileSync(BASELINE, 'utf8'));
const knownDuplicates: Record<string, string[]> = baseline.duplicate_names ?? {};
const knownDuplicateTexts: Record<string, number> = baseline.duplicate_short_descriptions ?? {};

function groupBy(field: 'name' | 'short_description') {
  const groups = new Map<string, string[]>();
  for (const p of live) {
    const value = (p[field] ?? '').trim();
    if (!value) continue;
    groups.set(value, [...(groups.get(value) ?? []), p.slug]);
  }
  return [...groups.entries()].filter(([, slugs]) => slugs.length > 1);
}

describe('каталог: карточка различима до импорта в Directus', () => {
  it('новых групп с одинаковым названием не появилось', () => {
    const fresh = groupBy('name')
      .filter(([name]) => !(name in knownDuplicates))
      .map(([name, slugs]) => `«${name}» — ${slugs.sort().join(', ')}`);

    expect(fresh, [
      'У этих позиций одинаковое название, а meta_title в пакетах не задаётся —',
      'значит страницы получат одинаковый <title> и Яндекс сочтёт их дублями.',
      'Вынесите различитель (объём, модуль, период, редакцию) в само название,',
      'как это сделано для ManageEngine ADManager Plus MSP и DataSecurity Plus.',
      '',
      ...fresh,
    ].join('\n')).toEqual([]);
  });

  it('известный долг по названиям не растёт', () => {
    const current = new Set(groupBy('name').map(([name]) => name));
    const grown = Object.entries(knownDuplicates)
      .filter(([name, slugs]) => current.has(name) && groupBy('name')
        .find(([n]) => n === name)![1].length > slugs.length)
      .map(([name]) => name);

    expect(grown, [
      'В известные группы дублей добавились новые позиции — так долг не разгребают,',
      'а увеличивают. Дайте новым карточкам различимое название.',
      '',
      ...grown,
    ].join('\n')).toEqual([]);
  });

  it('новых групп с одинаковым коротким описанием не появилось', () => {
    // short_description — это лид карточки, Product.description в разметке
    // и описание в фидах. Один текст на всю линейку означает столько же
    // одинаковых страниц; развести помогает scripts/seo/dedupe-descriptions.mjs.
    const fresh = groupBy('short_description')
      .filter(([text]) => !(text in knownDuplicateTexts))
      .map(([text, slugs]) => `«${text.slice(0, 70)}» — ${slugs.sort().join(', ')}`);

    expect(fresh, [
      'У этих позиций одинаковое короткое описание — одинаковый лид карточки',
      'и одинаковый Product.description в разметке. Различитель (редакция,',
      'объём, модуль, тип лицензии) есть в названии: разведите тексты',
      'скриптом scripts/seo/dedupe-descriptions.mjs.',
      '',
      ...fresh,
    ].join('\n')).toEqual([]);
  });

  it('известный долг по описаниям не растёт', () => {
    const grown = groupBy('short_description')
      .filter(([text, slugs]) => text in knownDuplicateTexts && slugs.length > knownDuplicateTexts[text])
      .map(([text, slugs]) => `«${text.slice(0, 70)}»: было ${knownDuplicateTexts[text]}, стало ${slugs.length}`);
    expect(grown).toEqual([]);
  });

  it('у каждой живой позиции есть название и слаг', () => {
    const broken = live
      .filter((p) => !(p.name ?? '').trim() || !(p.slug ?? '').trim())
      .map((p) => `${p.file}: ${p.sku}`);
    expect(broken).toEqual([]);
  });

  it('слаги уникальны по всему каталогу', () => {
    const seen = new Map<string, string[]>();
    for (const p of live) seen.set(p.slug, [...(seen.get(p.slug) ?? []), p.file]);
    const clashes = [...seen.entries()]
      .filter(([, files]) => files.length > 1)
      .map(([slug, files]) => `${slug}: ${files.join(', ')}`);
    expect(clashes).toEqual([]);
  });
});

describe('тексты SEO-партий: развод дублей, а не их размножение', () => {
  const file = resolve(__dirname, '../data/seo/product-descriptions.json');
  const payload = JSON.parse(readFileSync(file, 'utf8'));
  const products: Record<string, { meta_title?: string; meta_description?: string; short_description?: string }> =
    payload.products ?? payload;

  it('meta_title в партиях уникальны между собой', () => {
    const seen = new Map<string, string[]>();
    for (const [slug, texts] of Object.entries(products)) {
      const t = (texts.meta_title ?? '').trim();
      if (t) seen.set(t, [...(seen.get(t) ?? []), slug]);
    }
    const dups = [...seen.entries()]
      .filter(([, slugs]) => slugs.length > 1)
      .map(([title, slugs]) => `«${title}» — ${slugs.join(', ')}`);
    expect(dups).toEqual([]);
  });

  it('short_description и meta_description в партиях уникальны', () => {
    const dups: string[] = [];
    for (const field of ['short_description', 'meta_description'] as const) {
      const seen = new Map<string, string[]>();
      for (const [slug, texts] of Object.entries(products)) {
        const v = ((texts as Record<string, string>)[field] ?? '').trim();
        if (v) seen.set(v, [...(seen.get(v) ?? []), slug]);
      }
      dups.push(...[...seen.entries()]
        .filter(([, slugs]) => slugs.length > 1)
        .map(([v, slugs]) => `${field} «${v.slice(0, 60)}» — ${slugs.join(', ')}`));
    }
    expect(dups).toEqual([]);
  });

  it('meta_title не длиннее 60 символов, meta_description — 160', () => {
    const tooLong: string[] = [];
    for (const [slug, texts] of Object.entries(products)) {
      const t = (texts.meta_title ?? '').trim();
      const d = (texts.meta_description ?? '').trim();
      if (t.length > 60) tooLong.push(`${slug}: meta_title ${t.length} симв.`);
      if (d.length > 160) tooLong.push(`${slug}: meta_description ${d.length} симв.`);
    }
    expect(tooLong).toEqual([]);
  });

  it('пустых значений в партиях нет — иначе воркфлоу затрёт живой текст', () => {
    const empty = Object.entries(products)
      .flatMap(([slug, texts]) => Object.entries(texts)
        .filter(([, value]) => !String(value ?? '').trim())
        .map(([field]) => `${slug}: ${field}`));
    expect(empty).toEqual([]);
  });
});

/**
 * Тот же барьер для реестра AI-каталога. Пакеты scripts/catalog/*.json — не
 * единственный вход карточек в Directus: партия раздела /catalog/ai заведена
 * из scripts/ai-catalog-cards.json, и там же живут пары «базовое место +
 * место Premium» (Claude Team, Cursor Business, ChatGPT Business). У пары
 * тарифов описания похожи по построению — это ровно тот случай, когда две
 * карточки склеиваются в дубль и одна из них выпадает из индекса.
 */
describe('реестр AI-каталога: два типа мест — две различимые карточки', () => {
  const registry = JSON.parse(
    readFileSync(resolve(__dirname, '../scripts/ai-catalog-cards.json'), 'utf8'),
  ) as { vendors: { prefix: string; products: { key?: string; sku?: string; name: string; short_desc_ru?: string }[] }[] };

  const cards = registry.vendors.flatMap((v) => v.products.map((p) => ({
    sku: (p.sku || `${v.prefix}-${p.key}`).toUpperCase(),
    name: (p.name ?? '').trim(),
    short: (p.short_desc_ru ?? '').trim(),
  })));

  function dups(field: 'sku' | 'name' | 'short') {
    const seen = new Map<string, string[]>();
    for (const c of cards) {
      if (!c[field]) continue;
      seen.set(c[field], [...(seen.get(c[field]) ?? []), c.sku]);
    }
    return [...seen.entries()].filter(([, skus]) => skus.length > 1)
      .map(([value, skus]) => `«${value.slice(0, 60)}» — ${skus.join(', ')}`);
  }

  it('sku уникальны — иначе одна карточка затирает другую при upsert', () => {
    expect(dups('sku')).toEqual([]);
  });

  it('названия уникальны — заголовок страницы берётся из названия', () => {
    expect(dups('name')).toEqual([]);
  });

  it('краткие описания уникальны — они уходят в лид карточки и в сниппет', () => {
    expect(dups('short')).toEqual([]);
  });

  it('у каждой карточки есть название и краткое описание', () => {
    const broken = cards
      .filter((c) => !c.name || c.short.length < 40)
      .map((c) => c.sku);
    expect(broken).toEqual([]);
  });
});
