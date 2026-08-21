/**
 * Наполненные посадочные решений: три адреса, которые до 20.08.2026 отдавали
 * заглушку «в подготовке» с noindex. Проверяем, что они действительно
 * наполнены и попадают в sitemap, а не вернулись в заготовки.
 */
import { describe, expect, it } from 'vitest';
import { solutions } from '../src/data/solutions';
import { plannedSolutions } from '../src/data/scaffold';

const FILLED = ['po-dlya-yurlic-po-schetu', 'inostrannoe-po-po-dogovoru', 'ai-servisy-dlya-biznesa'];

describe('посадочные решений под измеренный спрос', () => {
  it('три адреса больше не заготовки', () => {
    const planned = plannedSolutions.map((p) => p.slug);
    for (const s of FILLED) expect(planned, `${s} всё ещё заготовка`).not.toContain(s);
  });

  it('каждая страница наполнена: лид, боли, предложение, FAQ', () => {
    for (const slug of FILLED) {
      const s = solutions.find((x) => x.slug === slug);
      expect(s, `нет решения ${slug}`).toBeTruthy();
      expect(s!.lead.length).toBeGreaterThan(80);
      expect(s!.pains.length).toBeGreaterThanOrEqual(3);
      expect(s!.offer.length).toBeGreaterThanOrEqual(3);
      expect(s!.faq.length).toBeGreaterThanOrEqual(4);
      expect(s!.relatedCategories.length).toBeGreaterThanOrEqual(2);
    }
  });

  it('метаданные в пределах лимитов выдачи', () => {
    for (const s of solutions) {
      expect(s.metaTitle.length, `${s.slug}.metaTitle`).toBeLessThanOrEqual(65);
      expect(s.metaDescription.length, `${s.slug}.metaDescription`).toBeLessThanOrEqual(160);
    }
  });
});
