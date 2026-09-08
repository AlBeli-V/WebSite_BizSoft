import { describe, it, expect } from 'vitest';
import { alternativesPages } from '../src/data/alternatives';
import { comparisons } from '../src/data/comparisons';
import { solutions } from '../src/data/solutions';

/**
 * lastmod — единственный сигнал планирования обхода, который Google
 * действительно читает (priority и changefreq он игнорирует). Разбор
 * 08.09.2026: 411 из 729 URL карты уходили вообще без даты, и при темпе
 * обхода в 2 URL в сутки поисковик выбирал, что скачивать, без нашего участия.
 *
 * Здесь проверяется не покрытие вообще, а то, что новая запись файлового слоя
 * не появится без даты: карту собирает sitemap.xml.ts прямо из этих полей.
 * Даты задним числом не выдумываются — правило достоверности отчётов; первичное
 * заполнение снято из истории git.
 */
const LAYERS: { name: string; records: { slug: string; updated?: string }[] }[] = [
  { name: 'Аналоги X', records: alternativesPages },
  { name: 'Сравнения', records: comparisons },
  { name: 'Решения', records: solutions },
];

describe('sitemap: у каждой записи файлового слоя есть дата изменения', () => {
  for (const layer of LAYERS) {
    it(`${layer.name}: updated заполнен и правдоподобен`, () => {
      for (const r of layer.records) {
        expect(r.updated, `${layer.name}/${r.slug}: нет поля updated`).toBeTruthy();
        expect(r.updated, `${layer.name}/${r.slug}: формат даты`).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        // Дата из будущего в lastmod — ложный сигнал: Google перестаёт
        // доверять полю по всему сайту, а не только на этой странице.
        expect(new Date(r.updated!).getTime(), `${layer.name}/${r.slug}: дата из будущего`)
          .toBeLessThanOrEqual(Date.now() + 86_400_000);
      }
    });
  }
});
