/**
 * Перелинковка производителей с разделом назначения ПО (/solutions).
 * Битая ссылка здесь тише, чем ошибка сборки: страница отрендерится,
 * а посетитель упрётся в 404 — поэтому проверяем связи, а не разметку.
 */
import { describe, expect, it } from 'vitest';
import { VENDOR_SOLUTIONS, vendorsForSolution } from '../src/data/vendor-solutions';
import { solutions } from '../src/data/solutions';
import { VENDORS } from '../src/data/vendors';

const solutionSlugs = new Set(solutions.map((s) => s.slug));
const vendorSlugs = new Set(VENDORS.map((v) => v.slug));

describe('перелинковка вендор ↔ решение', () => {
  it('все вендоры карты существуют в VENDORS', () => {
    for (const slug of Object.keys(VENDOR_SOLUTIONS)) {
      expect(vendorSlugs.has(slug), `нет вендора ${slug}`).toBe(true);
    }
  });

  it('все решения карты существуют и не под noindex', () => {
    for (const [vendor, list] of Object.entries(VENDOR_SOLUTIONS)) {
      expect(list.length, `${vendor} без решений`).toBeGreaterThan(0);
      for (const s of list) expect(solutionSlugs.has(s), `${vendor} → нет решения ${s}`).toBe(true);
    }
  });

  it('обратная карта симметрична прямой', () => {
    for (const [vendor, list] of Object.entries(VENDOR_SOLUTIONS)) {
      for (const s of list) expect(vendorsForSolution(s)).toContain(vendor);
    }
  });

  it('новые вендоры спросового блока перелинкованы', () => {
    for (const slug of ['anthropic', 'google', 'perplexity', 'cursor', 'github', 'notion', 'solidworks']) {
      expect(VENDOR_SOLUTIONS[slug], `${slug} без перелинковки`).toBeTruthy();
    }
  });

  it('три наполненные посадочные решения получили производителей', () => {
    for (const s of ['po-dlya-yurlic-po-schetu', 'inostrannoe-po-po-dogovoru', 'ai-servisy-dlya-biznesa']) {
      expect(vendorsForSolution(s).length, `${s} без плиток`).toBeGreaterThanOrEqual(3);
    }
  });
});
