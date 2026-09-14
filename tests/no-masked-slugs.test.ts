/**
 * Журналы GitHub Actions скрывают значения секретов: слово «deploy» в слаге
 * выводится как «***». 13.09.2026 четыре ключа me-os-***er-* попали из
 * журнала выгрузки в product-descriptions.json, и описания OS Deployer не
 * применились (ops-apply-descriptions #44: «не найдено: 4»). Правило —
 * docs/rules/prod-access.md: ключи и слаги в данных не содержат «***».
 */
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const FILES = [
  'data/seo/product-descriptions.json',
  'data/catalog/logo-requests.json',
  'data/catalog/logo-choices.json',
  'src/data/product-icon-map.json',
  'src/data/card-terms.json',
  'docs/catalog-product-icons-manifest.json',
];

describe('слаги из журналов Actions', () => {
  for (const file of FILES) {
    it(`${file}: нет замаскированных слагов «***»`, () => {
      const text = readFileSync(file, 'utf8');
      const hits = text.split('\n').filter((l) => l.includes('***')).map((l) => l.trim().slice(0, 80));
      expect(hits, `замаскированные слаги: ${hits.join(' | ')}`).toEqual([]);
    });
  }
});
