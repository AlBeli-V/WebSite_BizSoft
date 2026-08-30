import { describe, expect, it } from 'vitest';
import { SEO_EXPERIMENTS, SEO_EXPERIMENT_LINKS } from '../src/data/seo-experiments';

// Два эксперимента живут в одном файле, но считаются раздельно: даты старта
// разные, и смешивать их метрики нельзя.
const EXP_1 = ['canva', 'depositphotos', 'coreldraw', 'heygen', 'marmoset'];
const EXP_2 = ['adobe', 'autodesk', 'procreate', 'blackmagic', 'midjourney', 'clip-studio-paint'];
// «snippet-anthropic-demand» (29.08.2026): GAP-D — показы есть, кликов нет.
const EXP_3 = ['anthropic'];
const SLUGS = [...EXP_1, ...EXP_2, ...EXP_3];

describe('SEO-эксперименты на vendor-страницах', () => {
  it('обе группы на месте, пересечений нет — иначе метрики смешаются', () => {
    expect(Object.keys(SEO_EXPERIMENTS).sort()).toEqual([...SLUGS].sort());
    expect(SEO_EXPERIMENT_LINKS.map((l) => l.slug).sort()).toEqual([...SLUGS].sort());
    expect(EXP_1.filter((s) => EXP_2.includes(s))).toEqual([]);
  });

  it('контрольная группа не затронута: правок ровно 12 vendor-страниц', () => {
    expect(Object.keys(SEO_EXPERIMENTS)).toHaveLength(12);
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
