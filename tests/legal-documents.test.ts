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
import { canonicalText, parseLegalDoc, LEGAL_DOC_IDS, legalDateRu, effectiveFrom } from '../src/lib/legal-doc';
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

  // Версия начинается с даты вступления редакции в силу. Хвост `-N` нужен
  // для второй и последующих редакций того же дня: выпущенный текст не
  // правится (иначе согласия, записанные утром, ссылались бы на исчезнувший
  // документ), а имя файла с датой занято. Публично хвост не показывается —
  // на странице стоит только дата.
  it.each(LEGAL_DOC_IDS)('%s: версия начинается с даты редакции в ISO', (id) => {
    for (const rev of DOCS[id].revisions) expect(rev.version).toMatch(/^\d{4}-\d{2}-\d{2}(-\d+)?$/);
  });

  it.each(LEGAL_DOC_IDS)('%s: дата редакции выводится словами, без версии и хэша', (id) => {
    const doc = DOCS[id];
    expect(legalDateRu(doc.version)).toMatch(/^\d{1,2} [а-я]+ \d{4} года$/);
    // Повторная редакция того же дня датируется тем же днём.
    expect(effectiveFrom(doc.version)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
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

  // Проверки держат суть, а не формулировку: текст документа переписывается
  // редакциями, и привязка к точной фразе ломала бы набор на каждой правке,
  // ничего при этом не гарантируя.
  it('согласие на рассылку прямо называет себя добровольным', () => {
    const text = read(DOCS['marketing-consent'].path);
    expect(text).toMatch(/[Дд]обровольн/);
    expect(text).toMatch(/не является условием/);
    // Отказ от рекламы не должен стоить человеку ответа и документов.
    expect(text).toMatch(/коммерческого предложения/);
  });

  it('политика cookies фиксирует, что аналитика выключена до выбора', () => {
    const text = read(DOCS.cookies.path);
    expect(text).toMatch(/[Вв]ыключен[аы]? до выбора/);
    // Google Analytics сохраняется как отдельная управляемая категория.
    expect(text).toContain('Google Analytics');
    expect(text).toContain('Яндекс.Метрика');
  });

  it('публичные документы не раскрывают внутреннюю инфраструктуру', () => {
    // ТЗ 16.09.2026 (уточнение), п. 4: названия хостинга, портала, почтового
    // провайдера и внутренних таблиц пользователю ничего не объясняют, а
    // злоумышленнику дают карту. Их место — во внутреннем реестре.
    const forbidden = [
      'Beget', 'Bitrix', 'REG.RU', 'webhook', 'API',
      'consent_audit_log', 'marketing_registry', 'SHA-256', 'CRM',
    ];
    for (const id of LEGAL_DOC_IDS) {
      const text = read(DOCS[id].path);
      for (const word of forbidden) {
        expect(text, `${id}: в публичном документе не место слову «${word}»`)
          .not.toMatch(new RegExp(word.replace(/\./g, '\\.'), 'i'));
      }
    }
  });

  it('единый публичный контакт — hello@, личного адреса в документах нет', () => {
    for (const id of LEGAL_DOC_IDS) {
      const text = read(DOCS[id].path);
      expect(text, `${id}: контакт оператора должен быть указан`).toContain('hello@biz-soft.pro');
      expect(text, `${id}: личный адрес публичным контактом не публикуется`)
        .not.toMatch(/avbelyaev@/i);
    }
  });

  it('полное имя ИП звучит один раз, дальше — «Оператор»', () => {
    // ТЗ, п. 2: идентификация нужна однажды; повтор полного имени в каждом
    // разделе превращает документ в анкету.
    const text = read(DOCS.privacy.path);
    expect(text).toContain('далее — «Оператор»');
    // Имя допустимо ровно там, где идентифицируют лицо: вводная фраза и
    // реквизитный блок. Дальше по документу — только «Оператор».
    const body = text.slice(text.indexOf('## 3.'));
    expect(body, 'после раздела реквизитов полное имя не повторяется')
      .not.toMatch(/Беляев/);
    expect(body).toContain('Оператор');
  });

  it('в Политике все разделы ТЗ на месте', () => {
    const parsed = parseLegalDoc(read(DOCS.privacy.path));
    const headings = parsed.blocks.filter((b) => b.kind === 'heading');
    expect(headings.length, 'структура Политики — 22 раздела (ТЗ, п. 8)').toBe(22);
    for (const required of [
      'Правовые основания', 'Локализация', 'Трансграничная передача',
      'Права субъекта', 'Порядок обращения', 'Отзыв согласия',
      'Сроки хранения', 'Меры защиты',
    ]) {
      expect(
        headings.some((h) => h.kind === 'heading' && h.text.includes(required)),
        `в Политике нет раздела «${required}»`,
      ).toBe(true);
    }
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
