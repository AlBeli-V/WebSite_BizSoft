import { describe, expect, it } from 'vitest';
import { SEO_EXPERIMENTS, SEO_EXPERIMENT_LINKS, mergeExperimentFaq } from '../src/data/seo-experiments';

const SLUGS = ['canva', 'depositphotos', 'coreldraw', 'heygen', 'marmoset'];

describe('SEO-эксперимент P0-1', () => {
  it('ровно 5 целевых страниц — контрольная группа не затронута', () => {
    expect(Object.keys(SEO_EXPERIMENTS).sort()).toEqual([...SLUGS].sort());
    expect(SEO_EXPERIMENT_LINKS.map((l) => l.slug).sort()).toEqual([...SLUGS].sort());
  });

  it('бренд в title ровно один раз, description ≤ 165 символов', () => {
    for (const s of SLUGS) {
      const { title, description } = SEO_EXPERIMENTS[s];
      expect(title.split('BIZSoft').length - 1).toBe(1);
      expect(description.length).toBeLessThanOrEqual(165);
    }
  });

  it('merge заменяет близкий вопрос и не создаёт дубль', () => {
    const base = [
      { q: 'Можно ли оплатить Canva по счёту в рублях, без зарубежной карты?', a: 'Да.' },
      { q: 'Другой вопрос про Canva?', a: 'Ответ.' },
    ];
    const out = mergeExperimentFaq(base, 'canva', 'Canva');
    expect(out[0].q).toBe(SEO_EXPERIMENTS.canva.faq.q);
    expect(out).toHaveLength(2);
    expect(out.filter((f) => /оплатить canva/i.test(f.q))).toHaveLength(1);
  });

  it('merge не трогает FAQ контрольной группы', () => {
    const base = [{ q: 'Вопрос про Figma?', a: 'Ответ.' }];
    expect(mergeExperimentFaq(base, 'figma', 'Figma')).toEqual(base);
  });
});
