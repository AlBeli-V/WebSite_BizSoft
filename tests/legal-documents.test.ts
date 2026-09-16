/**
 * Правовые документы: редакции, хэши, страницы.
 *
 * Проверка держит то, на чём стоит вся доказательная конструкция: версия и
 * контрольная сумма документа, записанные в событие согласия, должны
 * совпадать с текстом, который лежит в репозитории. Разъехались — и
 * предъявить в ответ на запрос нечего.
 */
import { describe, expect, it } from 'vitest';
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { canonicalText, parseLegalDoc, LEGAL_DOC_IDS } from '../src/lib/legal-doc';
import manifest from '../src/legal/legal-manifest.json';

const ROOT = resolve(__dirname, '..');
const read = (rel: string) => readFileSync(resolve(ROOT, rel), 'utf8');
const sha = (text: string) => createHash('sha256').update(canonicalText(text), 'utf8').digest('hex');

type Revision = { version: string; path: string; sha256: string };
type Doc = { title: string; url: string; version: string; path: string; sha256: string; revisions: Revision[] };
const DOCS = manifest as unknown as Record<string, Doc>;

describe('реестр редакций', () => {
  it('в манифесте ровно пять документов ТЗ и ни одного лишнего', () => {
    expect(Object.keys(DOCS).sort()).toEqual([...LEGAL_DOC_IDS].sort());
  });

  it.each(LEGAL_DOC_IDS)('%s: SHA-256 каждой редакции сходится с файлом', (id) => {
    const doc = DOCS[id];
    for (const rev of doc.revisions) {
      expect(existsSync(resolve(ROOT, rev.path)), rev.path).toBe(true);
      expect(sha(read(rev.path)), `${rev.path}: хэш не сходится — редакцию правили после выпуска`)
        .toBe(rev.sha256);
      expect(rev.sha256).toMatch(/^[0-9a-f]{64}$/);
    }
  });

  it.each(LEGAL_DOC_IDS)('%s: действующая редакция — последняя по дате', (id) => {
    const doc = DOCS[id];
    const versions = doc.revisions.map((r) => r.version);
    expect(doc.version).toBe([...versions].sort().pop());
    expect(doc.sha256).toBe(doc.revisions.find((r) => r.version === doc.version)!.sha256);
  });

  it.each(LEGAL_DOC_IDS)('%s: версия — дата редакции в ISO', (id) => {
    for (const rev of DOCS[id].revisions) expect(rev.version).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it('на диске нет редакций мимо манифеста', () => {
    for (const id of LEGAL_DOC_IDS) {
      const onDisk = readdirSync(resolve(ROOT, 'src/legal', id))
        .filter((f) => f.endsWith('.md')).map((f) => f.replace(/\.md$/, '')).sort();
      expect(onDisk, `src/legal/${id}: пересоберите node scripts/legal/build-manifest.mjs`)
        .toEqual(DOCS[id].revisions.map((r) => r.version).sort());
    }
  });

  it('адрес документа постоянный и совпадает с идентификатором', () => {
    for (const id of LEGAL_DOC_IDS) expect(DOCS[id].url).toBe(`/legal/${id}`);
  });
});

describe('содержание документов', () => {
  it.each(LEGAL_DOC_IDS)('%s: разбирается, имеет название и разделы', (id) => {
    const parsed = parseLegalDoc(read(DOCS[id].path));
    expect(parsed.title.length).toBeGreaterThan(10);
    expect(parsed.title).toBe(DOCS[id].title);
    expect(parsed.blocks.some((b) => b.kind === 'heading')).toBe(true);
    expect(parsed.blocks.some((b) => b.kind === 'paragraph')).toBe(true);
  });

  it('политика и политика cookies содержат таблицы — они есть в исходных документах', () => {
    for (const id of ['privacy', 'cookies'] as const) {
      const parsed = parseLegalDoc(read(DOCS[id].path));
      const table = parsed.blocks.find((b) => b.kind === 'table');
      expect(table, `${id}: таблица потерялась при переносе`).toBeTruthy();
      if (table && table.kind === 'table') {
        expect(table.head.length).toBeGreaterThan(1);
        expect(table.rows.length).toBeGreaterThan(0);
      }
    }
  });

  it('согласие на рассылку прямо называет себя добровольным', () => {
    const text = read(DOCS['marketing-consent'].path);
    expect(text).toMatch(/не является условием отправки заявки/);
  });

  it('политика cookies фиксирует, что аналитика выключена до выбора', () => {
    const text = read(DOCS.cookies.path);
    expect(text).toMatch(/выключена до выбора пользователя/);
  });
});

describe('страницы и навигация', () => {
  it('страницы документов и архив редакций собраны одним шаблоном', () => {
    expect(existsSync(resolve(ROOT, 'src/pages/legal/[doc].astro'))).toBe(true);
    expect(existsSync(resolve(ROOT, 'src/pages/legal/[doc]/[version].astro'))).toBe(true);
    expect(existsSync(resolve(ROOT, 'src/pages/legal/index.astro'))).toBe(true);
  });

  it('старые адреса отдают 301 на постоянные, а не 404 и не meta-refresh', () => {
    for (const [file, target] of [
      ['src/pages/privacy.astro', 'LEGAL_LINKS.privacy'],
      ['src/pages/consent.astro', 'LEGAL_LINKS.personalDataConsent'],
    ]) {
      const src = read(file);
      expect(src, `${file}: редирект должен быть серверным`).toContain('export const prerender = false');
      expect(src).toContain(`Astro.redirect(${target}, 301)`);
    }
  });

  it('подвал несёт блок «Правовая информация» и вход в настройки cookies', () => {
    const footer = read('src/components/Footer.astro');
    expect(footer).toContain('LEGAL_FOOTER_NAV');
    expect(footer).toContain('data-cookie-settings');
    expect(footer).toContain('Правовая информация');
  });

  it('в главное меню правовые документы не выносятся', () => {
    const site = read('src/config/site.ts');
    const mainNav = site.slice(site.indexOf('export const mainNav'), site.indexOf('export const vendorLandings'));
    expect(mainNav).not.toContain('/legal');
    expect(mainNav).not.toContain('/privacy');
  });

  it('действующие редакции — в карте сайта, архивные — нет', () => {
    const sitemap = read('src/pages/sitemap.xml.ts');
    expect(sitemap).toContain('LEGAL_DOC_IDS');
    expect(sitemap).toContain("path: '/legal'");
    // Архив отдаётся только по прямой ссылке из карточки доказательства.
    const archive = read('src/pages/legal/[doc]/[version].astro');
    expect(archive).toContain('noindex={true}');
  });
});
