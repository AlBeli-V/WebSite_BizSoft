/**
 * Перелинковка «лендинг вендора → экспертный слой» (задача IDX-001).
 *
 * Проверка нужна потому, что раздел без входящих ссылок молча выпадает из
 * индекса: у `/alternatives/*` не было ни одной внутренней ссылки на всём
 * сайте, и в индексе Google не оказалось ни одной из семи страниц. Тест
 * фиксирует и обратное направление — что связь выводится из уже
 * существующих данных, а не из второго реестра, который разъедется.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  belongsToVendor, normalizePath, vendorInterlinks,
  alternativesDocs, comparisonDocs, articleDocs,
} from '../src/lib/vendor-interlinks';
import { alternativesPages } from '../src/data/alternatives';
import { comparisons } from '../src/data/comparisons';
import { footerNav } from '../src/config/site';

const ROOT = resolve(__dirname, '..');
const read = (rel: string) => readFileSync(resolve(ROOT, rel), 'utf8');

describe('нормализация пути', () => {
  it('снимает хвостовой слеш, query и hash', () => {
    expect(normalizePath('/vendors/framer/')).toBe('/vendors/framer');
    expect(normalizePath('/vendors/framer?utm_source=x')).toBe('/vendors/framer');
    expect(normalizePath('/compare/a-vs-b#table')).toBe('/compare/a-vs-b');
    expect(normalizePath('/')).toBe('/');
  });
});

describe('принадлежность документа вендору', () => {
  const doc = (...outbound: string[]) => ({ href: '/blog/x', label: 'x', outbound });

  it('ссылка на лендинг вендора', () => {
    expect(belongsToVendor(doc('/vendors/framer'), 'framer', [])).toBe(true);
  });

  it('ссылка на карточку товара вендора', () => {
    expect(belongsToVendor(doc('/product/framer-pro'), 'framer', ['framer-pro'])).toBe(true);
  });

  it('чужой вендор и чужой товар не считаются', () => {
    expect(belongsToVendor(doc('/vendors/figma', '/product/figma-org'), 'framer', ['framer-pro']))
      .toBe(false);
  });

  it('частичное совпадение пути не срабатывает', () => {
    // /vendors/framer-x — другой вендор, а не тот же с суффиксом.
    expect(belongsToVendor(doc('/vendors/framer-x'), 'framer', [])).toBe(false);
  });
});

describe('группы ссылок лендинга', () => {
  const articles = [
    { href: '/blog/kak-oplatit-framer', label: 'Как оплатить Framer', outbound: ['/vendors/framer'] },
    { href: '/blog/chuzhaya', label: 'Чужая', outbound: ['/vendors/figma'] },
  ];
  const alternatives = [
    { href: '/alternatives/figma', label: 'Аналоги Figma', outbound: ['/vendors/framer'] },
  ];
  const comparisons_ = [
    { href: '/compare/a-vs-b', label: 'A vs B', outbound: ['/product/framer-pro'] },
  ];

  it('собирает только своё и раскладывает по группам', () => {
    const groups = vendorInterlinks({
      vendorSlug: 'framer', productSlugs: ['framer-pro'],
      articles, alternatives, comparisons: comparisons_,
    });
    expect(groups.map((g) => g.title))
      .toEqual(['Разборы и инструкции', 'Чем заменить', 'Сравнения']);
    expect(groups[0].links).toEqual([
      { label: 'Как оплатить Framer', href: '/blog/kak-oplatit-framer' },
    ]);
  });

  it('пустые группы не выводятся', () => {
    const groups = vendorInterlinks({
      vendorSlug: 'framer', productSlugs: [],
      articles: [], alternatives, comparisons: [],
    });
    expect(groups).toHaveLength(1);
    expect(groups[0].title).toBe('Чем заменить');
  });

  it('страница не ссылается сама на себя', () => {
    const groups = vendorInterlinks({
      vendorSlug: 'framer', productSlugs: [],
      articles: [{ href: '/vendors/framer', label: 'сам лендинг', outbound: ['/vendors/framer'] }],
      alternatives: [], comparisons: [],
    });
    expect(groups).toHaveLength(0);
  });

  it('список ограничен, чтобы блок не превращался в простыню', () => {
    const many = Array.from({ length: 12 }, (_, i) => ({
      href: `/blog/p${i}`, label: `p${i}`, outbound: ['/vendors/framer'],
    }));
    const groups = vendorInterlinks({
      vendorSlug: 'framer', productSlugs: [], articles: many,
      alternatives: [], comparisons: [], limit: 6,
    });
    expect(groups[0].links).toHaveLength(6);
  });
});

describe('адаптеры источников', () => {
  it('черновики и noindex-статьи не участвуют в перелинковке', () => {
    const docs = articleDocs([
      { id: 'ok', data: { title: 'ok', related: [{ label: 'v', href: '/vendors/framer' }] } },
      { id: 'draft', data: { title: 'draft', draft: true, related: [] } },
      { id: 'hidden', data: { title: 'hidden', noindex: true, related: [] } },
    ]);
    expect(docs.map((d) => d.href)).toEqual(['/blog/ok']);
  });

  it('реальные данные аналогов и сравнений дают непустые связи', () => {
    // Если реестры перестанут ссылаться на лендинги вендоров, блок молча
    // опустеет — тест это ловит на реальных данных, а не на выдуманных.
    const alts = alternativesDocs();
    const cmps = comparisonDocs();
    expect(alts).toHaveLength(alternativesPages.length);
    expect(cmps).toHaveLength(comparisons.length);
    expect(alts.some((d) => d.outbound.some((h) => h.startsWith('/vendors/')))).toBe(true);
    expect(cmps.some((d) => d.outbound.some((h) => h.startsWith('/vendors/') || h.startsWith('/product/')))).toBe(true);
  });
});

describe('точки входа в разделы', () => {
  it('хабы сравнений и аналогов есть в подвале', () => {
    const hrefs = footerNav.map((i) => i.href);
    expect(hrefs).toContain('/compare');
    expect(hrefs).toContain('/alternatives');
  });

  it('хабы есть в карте сайта', () => {
    const sitemap = read('src/pages/sitemap.xml.ts');
    expect(sitemap).toContain("path: '/compare'");
    expect(sitemap).toContain("path: '/alternatives'");
  });

  it('блок перелинковки стоит на всех лендингах вендоров', () => {
    // Своей страницей остался только Zoom: остальные вендоры переехали на
    // общий шаблон 11.09.2026, и блок приходит из VendorLanding.
    const files = [
      'src/components/VendorLanding.astro',
      'src/components/VendorGenericLanding.astro',
      'src/pages/vendors/zoom.astro',
    ];
    for (const f of files) expect(read(f), f).toContain('<VendorInterlinks');
  });
});
