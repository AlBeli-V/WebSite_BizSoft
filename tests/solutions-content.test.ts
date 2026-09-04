/**
 * Наполненные посадочные решений: три адреса, которые до 20.08.2026 отдавали
 * заглушку «в подготовке» с noindex. Проверяем, что они действительно
 * наполнены и попадают в sitemap, а не вернулись в заготовки.
 */
import { describe, expect, it } from 'vitest';
import { solutions } from '../src/data/solutions';
import { plannedSolutions } from '../src/data/scaffold';

const FILLED = ['po-dlya-yurlic-po-schetu', 'inostrannoe-po-po-dogovoru', 'ai-servisy-dlya-biznesa', 'ai-dlya-marketinga'];
// Страницы, снятые Яндексом как малоценные 31.08–02.09.2026: их отличие от
// раздела каталога — блок «Как выбрать» (план thin-pages, группа F).
const GUIDED = ['ai-servisy-dlya-biznesa', 'ai-dlya-marketinga'];

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

  it('у снятых Яндексом страниц есть блок «Как выбрать»', () => {
    for (const slug of GUIDED) {
      const s = solutions.find((x) => x.slug === slug)!;
      expect(s.sections?.length ?? 0, `${slug}: разделов блока`).toBeGreaterThanOrEqual(3);
      for (const sec of s.sections!) expect(sec.text.length, `${slug}: «${sec.title}»`).toBeGreaterThan(200);
      expect(s.faq.length, `${slug}: вопросов`).toBeGreaterThanOrEqual(5);
    }
  });

  it('связанные разделы ведут на основные адреса, а не на слитые дубли с 301', () => {
    const merged = ['graphics-design', 'ai-services', 'communications', 'developer-tools'];
    for (const s of solutions) {
      for (const c of s.relatedCategories) expect(merged, `${s.slug} → /catalog/${c.slug}`).not.toContain(c.slug);
    }
  });

  it('метаданные в пределах лимитов выдачи', () => {
    for (const s of solutions) {
      expect(s.metaTitle.length, `${s.slug}.metaTitle`).toBeLessThanOrEqual(65);
      expect(s.metaDescription.length, `${s.slug}.metaDescription`).toBeLessThanOrEqual(160);
    }
  });
});
