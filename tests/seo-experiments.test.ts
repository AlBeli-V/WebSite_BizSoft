import { describe, expect, it } from 'vitest';
import { SEO_EXPERIMENTS, SEO_EXPERIMENT_LINKS } from '../src/data/seo-experiments';

// Эксперименты живут в одном файле, но считаются раздельно: даты старта
// разные, и смешивать их метрики нельзя.
// CorelDRAW ушёл из EXP_1 в EXP_4 02.09.2026: решение по SEO-EXP-001 принято
// (EXPAND), страница освободилась под запросную формулу.
const EXP_1 = ['canva', 'depositphotos', 'heygen', 'marmoset'];
const EXP_2 = ['adobe', 'autodesk', 'procreate', 'blackmagic', 'midjourney', 'clip-studio-paint'];
// «snippet-anthropic-demand» (29.08.2026): GAP-D — показы есть, кликов нет.
const EXP_3 = ['anthropic'];
// «snippets-3-gap-d» (01.09.2026): запросная формула «оплата {vendor}
// юридическим лицом» вместо общей коммерческой.
const EXP_4 = ['artlist', 'motion-array', 'coreldraw'];
// «snippets-10-expand» (02.09.2026): тираж формулы EXP_1 по решению
// руководителя. Формула та же — иначе тиражируется не то, что оценивалось.
const EXP_5 = ['google', 'microsoft', 'github', 'unity', 'docker', 'runway',
  'solidworks', 'acronis', 'unreal-engine', 'perplexity'];
// Запросная формула каждой страницы EXP_4: она обязана стоять в title,
// description, заголовке блока вопросов и в первом вопросе — в этом и есть
// вся правка, поэтому проверяется явно, а не по общему шаблону.
const EXP_4_PHRASE: Record<string, string> = {
  artlist: 'оплата artlist юридическим лицом',
  'motion-array': 'оплата motion array юридическим лицом',
  coreldraw: 'оплата coreldraw для россиян',
};
// Группы с общей коммерческой формулой title/description.
const COMMERCIAL = [...EXP_1, ...EXP_2, ...EXP_3, ...EXP_5];
const SLUGS = [...COMMERCIAL, ...EXP_4];

describe('SEO-эксперименты на vendor-страницах', () => {
  it('все группы на месте, пересечений нет — иначе метрики смешаются', () => {
    expect(Object.keys(SEO_EXPERIMENTS).sort()).toEqual([...SLUGS].sort());
    expect(SEO_EXPERIMENT_LINKS.map((l) => l.slug).sort()).toEqual([...SLUGS].sort());
    expect(EXP_1.filter((s) => EXP_2.includes(s))).toEqual([]);
    expect(SLUGS.filter((s) => EXP_4.includes(s) && COMMERCIAL.includes(s))).toEqual([]);
  });

  it('контрольная группа не затронута: правок ровно 24 vendor-страницы', () => {
    expect(Object.keys(SEO_EXPERIMENTS)).toHaveLength(24);
  });

  it('бренд в title ровно один раз, до 65 символов без учёта «| BIZSoft»', () => {
    for (const s of SLUGS) {
      const { title } = SEO_EXPERIMENTS[s];
      expect(title.split('BIZSoft').length - 1).toBe(1);
      const core = title.replace(/\s*\|\s*BIZSoft\s*$/, '');
      expect(core.length).toBeLessThanOrEqual(65);
    }
  });

  it('title и description уникальны — одинаковые Яндекс считает дублями', () => {
    const titles = SLUGS.map((s) => SEO_EXPERIMENTS[s].title);
    const descriptions = SLUGS.map((s) => SEO_EXPERIMENTS[s].description);
    expect(new Set(titles).size).toBe(titles.length);
    expect(new Set(descriptions).size).toBe(descriptions.length);
  });

  it('description по формуле группы и ≤160 символов', () => {
    for (const s of COMMERCIAL) {
      const { description } = SEO_EXPERIMENTS[s];
      expect(description.length).toBeLessThanOrEqual(160);
      expect(description).toMatch(/^Оплатим подписку .+ в рублях по счёту\./);
      expect(description).toContain('ЭДО');
      expect(description).toContain('1–3 дня');
    }
    for (const s of EXP_4) {
      const { description } = SEO_EXPERIMENTS[s];
      expect(description.length).toBeLessThanOrEqual(160);
      // Формулировка запроса идёт первой, оффер — сразу за двоеточием.
      expect(description).toMatch(/^Оплата .+: сч[её]т, договор/);
      expect(description).toContain('ЭДО');
      expect(description).toContain('1–3 дня');
    }
  });

  it('FAQ-блок «Как купить … на юрлицо»: 3–4 вопроса с нужными темами', () => {
    for (const s of COMMERCIAL) {
      const { faqTitle, faq } = SEO_EXPERIMENTS[s];
      expect(faqTitle).toMatch(/^Как купить .+ на юрлицо$/);
      expect(faq).toBeDefined();
      expect(faq!.length).toBeGreaterThanOrEqual(3);
      expect(faq!.length).toBeLessThanOrEqual(4);
      const all = faq!.map((f) => `${f.q} ${f.a}`).join(' ');
      expect(all).toMatch(/сч[её]т/i);
      expect(all).toMatch(/договор/i);
      expect(all).toMatch(/ЭДО/);
      expect(all).toMatch(/1–3/);
      expect(all).toMatch(/курсу ЦБ/);
    }
  });

  it('snippets-3-gap-d: вопрос добавляется к bespoke-FAQ, а не заменяет его', () => {
    for (const s of EXP_4) {
      const { faqTitle, faq, faqAdd } = SEO_EXPERIMENTS[s];
      // Замена целиком стёрла бы собственный FAQ страницы — это другой
      // эксперимент и другой объём правки.
      expect(faq).toBeUndefined();
      expect(faqAdd).toHaveLength(1);
      expect(faqTitle).toMatch(/^Оплата /);
      const [{ q, a }] = faqAdd!;
      expect(q).toMatch(/^Как оплатить .+\?$/);
      expect(a).toMatch(/сч[её]т/i);
      expect(a).toMatch(/договор/i);
      expect(a).toMatch(/ЭДО/);
      expect(a).toMatch(/1–3/);
      expect(a).toMatch(/курсу ЦБ/);
    }
  });

  it('snippets-3-gap-d: формулировка запроса стоит в сниппете и в вопросе', () => {
    for (const s of EXP_4) {
      const phrase = EXP_4_PHRASE[s];
      const { title, description, faqTitle, faqAdd } = SEO_EXPERIMENTS[s];
      // Слова запроса, а не строка целиком: в заголовке они идут с заглавной
      // и в том же порядке, но между ними может стоять тире или двоеточие.
      const words = phrase.split(' ');
      const head = new RegExp(words.join('\\s+'), 'i');
      expect(title).toMatch(head);
      expect(description).toMatch(head);
      expect(faqTitle.toLowerCase()).toBe(phrase);
      expect(`${faqAdd![0].q} ${faqAdd![0].a}`).toMatch(head);
    }
  });

  it('faq и faqAdd взаимоисключающи — иначе вопросы задвоятся', () => {
    for (const s of SLUGS) {
      const e = SEO_EXPERIMENTS[s];
      expect(Boolean(e.faq) !== Boolean(e.faqAdd)).toBe(true);
    }
  });

  // Решение руководителя 02.09.2026 — EXPAND: формула snippets-5-vendors
  // тиражируется без изменений. Тираж с «улучшенной» формулой оценивал бы
  // не то изменение, которое признано удачным.
  it('тираж повторяет формулу исходного эксперимента дословно', () => {
    for (const s of EXP_5) {
      const { title } = SEO_EXPERIMENTS[s];
      expect(title).toMatch(/^Оплата .+ для юрлиц из России — счёт, договор, ЭДО \| BIZSoft$/);
    }
  });
});
