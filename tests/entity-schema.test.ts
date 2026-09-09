/**
 * Сущность организации и публичного эксперта (задача ENT-001).
 *
 * Проверка нужна потому, что разметка утверждала об организации всё нужное
 * и не подтверждалась ничем: `sameAs` не было ни одного, автором статей
 * значилась организация, а Google по запросу собственного бренда «bizsoft»
 * ставил сайт на позицию 15,7 — различать омонимов ему было нечем.
 * Здесь же фиксируется главное правило заполнения: в `sameAs` попадает
 * только подтверждённый профиль, а пустой массив в разметку не выводится.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { organizationSchema, expertSchema, EXPERT_ID, ORG_ID } from '../src/lib/seo';
import { expert, knowsAbout, sameAs, seller, site } from '../src/config/site';

const ROOT = resolve(__dirname, '..');
const read = (rel: string) => readFileSync(resolve(ROOT, rel), 'utf8');

describe('Organization', () => {
  const org = organizationSchema() as Record<string, unknown>;

  it('заявляет специализацию и рынок', () => {
    expect(org.knowsAbout).toEqual(knowsAbout);
    expect(org.areaServed).toEqual({ '@type': 'Country', name: 'RU' });
    expect(org.currenciesAccepted).toBe('RUB');
  });

  it('дата регистрации переведена в формат schema.org', () => {
    // В реквизитах она хранится по-русски — так её видит человек на /documents.
    expect(seller.registrationDate).toMatch(/^\d{2}\.\d{2}\.\d{4}$/);
    expect(org.foundingDate).toBe('2022-11-07');
  });

  it('основатель — узел Person, а не строка', () => {
    expect(org.founder).toEqual({ '@id': EXPERT_ID });
  });

  it('пустой sameAs в разметку не попадает', () => {
    // `sameAs: []` — не сигнал, а шум: он утверждает, что подтверждений нет.
    if (sameAs.length === 0) expect(org).not.toHaveProperty('sameAs');
    else expect(org.sameAs).toEqual(sameAs);
  });

  it('в sameAs только абсолютные ссылки', () => {
    for (const u of sameAs) expect(u, u).toMatch(/^https:\/\//);
  });
});

describe('публичный эксперт', () => {
  const person = expertSchema() as Record<string, unknown>;

  it('связан с организацией в обе стороны', () => {
    expect(person['@id']).toBe(EXPERT_ID);
    expect(person.worksFor).toEqual({ '@id': ORG_ID });
    expect((organizationSchema() as Record<string, unknown>).founder).toEqual({ '@id': EXPERT_ID });
  });

  it('у сущности есть собственный адрес', () => {
    // Person без страницы подтверждать нечем: @id должен указывать на
    // существующий маршрут, а он — в карте сайта.
    expect(person.url).toBe(`${site.url}/authors/${expert.slug}`);
    expect(read('src/pages/sitemap.xml.ts')).toContain(`/authors/${expert.slug}`);
  });

  it('эксперт — настоящий человек, а не «редакция»', () => {
    expect(expert.fullName).not.toMatch(/редакц/i);
    expect(expert.bio.length).toBeGreaterThan(120);
  });
});

describe('авторство статей', () => {
  const page = read('src/pages/blog/[slug].astro');

  it('статьи по умолчанию подписаны экспертом, а не организацией', () => {
    expect(page).toContain('EXPERT_ID');
    expect(page).toContain('isExpertAuthor');
  });

  it('подпись ведёт на страницу автора', () => {
    expect(page).toContain('rel="author"');
  });

  it('явно указанный другой автор не подменяется', () => {
    expect(page).toContain("d.author === 'Редакция BIZSoft'");
  });
});

describe('ссылки на сущность с индексируемых страниц', () => {
  it('/about ведёт на страницу эксперта', () => {
    // /about — одна из немногих страниц, которые Google уже индексирует;
    // без ссылки отсюда страница автора остаётся сиротой.
    expect(read('src/pages/about.astro')).toContain('/authors/${expert.slug}');
  });
});
