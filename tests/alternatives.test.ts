import { describe, expect, it } from 'vitest';
import { alternativesPages } from '../src/data/alternatives';
import { comparisons } from '../src/data/comparisons';
import { landingSlugs } from '../src/lib/vendor-links';

// Слой «Аналоги X» (PAGES-EXP-001): страница существует только под замеренный
// кластер спроса, альтернативы — живые внутренние ссылки каталога.
describe('Страницы «Аналоги X» (/alternatives/*)', () => {
  // Все лендинги вендоров: шаблонные (VENDORS) + bespoke (vendorLandings).
  const vendorSlugs = landingSlugs;
  const compareSlugs = new Set(comparisons.map((c) => c.slug));

  it('слаги уникальны', () => {
    const slugs = alternativesPages.map((p) => p.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
  });

  it('метаданные в лимитах: title ≤ 70, description ≤ 165, есть TL;DR', () => {
    for (const p of alternativesPages) {
      expect(p.metaTitle.length, p.slug).toBeLessThanOrEqual(70);
      expect(p.metaDescription.length, p.slug).toBeLessThanOrEqual(165);
      expect(p.summaryAnswer.length, p.slug).toBeGreaterThan(100);
      expect(p.h1.startsWith('Аналоги '), p.slug).toBe(true);
    }
  });

  it('альтернативы: 1–6 штук, внутренние ссылки ведут на существующие разделы', () => {
    for (const p of alternativesPages) {
      expect(p.alternatives.length, p.slug).toBeGreaterThanOrEqual(1);
      expect(p.alternatives.length, p.slug).toBeLessThanOrEqual(6);
      for (const a of p.alternatives) {
        expect(a.href.startsWith('/'), `${p.slug}: ${a.href}`).toBe(true);
        const m = a.href.match(/^\/vendors\/([a-z0-9-]+)$/);
        if (m) expect(vendorSlugs.has(m[1]), `${p.slug}: нет вендора ${m[1]}`).toBe(true);
        const c = a.href.match(/^\/compare\/([a-z0-9-]+)$/);
        if (c) expect(compareSlugs.has(c[1]), `${p.slug}: нет сравнения ${c[1]}`).toBe(true);
      }
    }
  });

  it('таблица согласована: значения строк по числу альтернатив', () => {
    for (const p of alternativesPages) {
      for (const r of p.rows) {
        expect(r.values.length, `${p.slug}: ${r.label}`).toBe(p.alternatives.length);
      }
    }
  });

  it('FAQ: 3–4 вопроса, есть оффер оформления на юрлицо', () => {
    for (const p of alternativesPages) {
      expect(p.faq.length, p.slug).toBeGreaterThanOrEqual(3);
      expect(p.faq.length, p.slug).toBeLessThanOrEqual(4);
      const all = p.faq.map((f) => `${f.q} ${f.a}`).join(' ') + ' ' + p.summaryAnswer;
      expect(all, p.slug).toMatch(/юрлицо|юридическое лицо/i);
      expect(all, p.slug).toMatch(/ЭДО/);
    }
  });

  it('related-ссылки внутренние и существующие (для vendors/compare)', () => {
    for (const p of alternativesPages) {
      for (const r of p.related) {
        expect(r.href.startsWith('/'), `${p.slug}: ${r.href}`).toBe(true);
        const m = r.href.match(/^\/vendors\/([a-z0-9-]+)$/);
        if (m) expect(vendorSlugs.has(m[1]), `${p.slug}: нет вендора ${m[1]}`).toBe(true);
        const c = r.href.match(/^\/compare\/([a-z0-9-]+)$/);
        if (c) expect(compareSlugs.has(c[1]), `${p.slug}: нет сравнения ${c[1]}`).toBe(true);
      }
    }
  });
});
