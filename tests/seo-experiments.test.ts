import { describe, expect, it } from 'vitest';
import { SEO_EXPERIMENTS, SEO_EXPERIMENT_LINKS } from '../src/data/seo-experiments';

const SLUGS = ['canva', 'depositphotos', 'coreldraw', 'heygen', 'marmoset'];

describe('SEO-эксперимент snippets-5-vendors', () => {
  it('ровно 5 целевых страниц — контрольная группа не затронута', () => {
    expect(Object.keys(SEO_EXPERIMENTS).sort()).toEqual([...SLUGS].sort());
    expect(SEO_EXPERIMENT_LINKS.map((l) => l.slug).sort()).toEqual([...SLUGS].sort());
  });

  it('бренд в title ровно один раз, до 65 символов без учёта «| BIZSoft»', () => {
    for (const s of SLUGS) {
      const { title } = SEO_EXPERIMENTS[s];
      expect(title.split('BIZSoft').length - 1).toBe(1);
      const core = title.replace(/\s*\|\s*BIZSoft\s*$/, '');
      expect(core.length).toBeLessThanOrEqual(65);
    }
  });

  it('description по формуле и ≤160 символов', () => {
    for (const s of SLUGS) {
      const { description } = SEO_EXPERIMENTS[s];
      expect(description.length).toBeLessThanOrEqual(160);
      expect(description).toMatch(/^Оплатим подписку .+ в рублях по счёту\./);
      expect(description).toContain('ЭДО');
      expect(description).toContain('1–3 дня');
    }
  });

  it('FAQ-блок «Как купить … на юрлицо»: 3–4 вопроса с нужными темами', () => {
    for (const s of SLUGS) {
      const { faqTitle, faq } = SEO_EXPERIMENTS[s];
      expect(faqTitle).toMatch(/^Как купить .+ на юрлицо$/);
      expect(faq.length).toBeGreaterThanOrEqual(3);
      expect(faq.length).toBeLessThanOrEqual(4);
      const all = faq.map((f) => `${f.q} ${f.a}`).join(' ');
      expect(all).toMatch(/сч[её]т/i);
      expect(all).toMatch(/договор/i);
      expect(all).toMatch(/ЭДО/);
      expect(all).toMatch(/1–3/);
      expect(all).toMatch(/курсу ЦБ/);
    }
  });
});
