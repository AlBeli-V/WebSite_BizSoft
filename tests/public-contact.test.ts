/**
 * Единый публичный контакт и граница публичного контура.
 *
 * Два правила, которые нельзя удержать вычиткой. Первое: наружу сайт
 * показывает один адрес — hello@biz-soft.pro. Личный ящик руководителя
 * публичным контактом не публикуется: он остаётся адресом внутренней
 * переписки, и попав в подвал или в правовой документ, начинает собирать
 * спам и внешние обращения мимо общего ящика.
 *
 * Граница проходит по публикации, а не по упоминанию. Страница, правовой
 * документ, разметка и robots — публикация: адрес там виден любому, включая
 * сборщиков. Письмо конкретному адресату публикацией не является, и в
 * подписи под именем менеджера с 21.09.2026 стоит его личный адрес
 * (решение руководителя): заказчик отвечает человеку, а не в приёмную.
 *
 * Второе: названия хостинга, портала и почтового провайдера пользователю
 * ничего не объясняют, а злоумышленнику дают карту инфраструктуры. Их место
 * во внутреннем реестре, а не в публичном тексте (ТЗ 16.09.2026, уточнение,
 * пп. 1 и 4).
 *
 * Проверка статическая — она смотрит на исходники. Расхождение здесь не
 * падает в рантайме: сайт с личным адресом в подвале работает прекрасно,
 * и обнаруживается это через месяц по письмам не туда.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { seller, expert, offerManager } from '../src/config/site';
import manifest from '../src/legal/legal-manifest.json';

const ROOT = resolve(__dirname, '..');
const PUBLIC_EMAIL = 'hello@biz-soft.pro';

/**
 * Внутренний контур: сюда личный адрес попадать вправе.
 *
 * `mailer.ts` — умолчание для MANAGER_EMAIL, адреса получателя заявок и
 * копий КП. Это не публикация контакта, а маршрут доставки внутрь.
 */
const INTERNAL_ALLOWED = new Set([
  'src/lib/mailer.ts',
  // Подпись писем заказчику: адрес уходит адресату, а не на страницу.
  'src/config/site.ts',
  'src/lib/email/client-shell.ts',
  'src/lib/email/lead-customer.ts',
  'src/lib/email/quote-customer.ts',
  // Повтор подтверждения задним числом: письмо тому же адресату.
  'src/pages/api/admin/lead-confirm.ts',
]);

/**
 * Действующие редакции правовых документов.
 *
 * Архивные редакции под эти правила не подпадают и не должны: выпущенный
 * текст не правится ни ради новой почты, ни ради чего-либо ещё. Правка
 * сменила бы его контрольную сумму, и согласия, записанные при действии той
 * редакции, перестали бы разрешаться в свой текст — то есть перестали бы
 * быть доказательством. Архив говорит то, что говорил.
 */
const CURRENT_LEGAL = new Set(
  Object.values(manifest as Record<string, { path: string }>).map((d) => d.path),
);
const isArchivedLegal = (rel: string) =>
  rel.startsWith('src/legal/') && rel.endsWith('.md') && !CURRENT_LEGAL.has(rel);

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else out.push(full);
  }
  return out;
}

const FILES = [...walk(resolve(ROOT, 'src')), ...walk(resolve(ROOT, 'public'))]
  .map((f) => f.slice(ROOT.length + 1))
  .filter((f) => /\.(ts|astro|mjs|js|json|md|txt|xml)$/.test(f));

describe('единый публичный контакт', () => {
  it('в конфиге продавца — общий ящик, второго поля почты нет', () => {
    expect(seller.email).toBe(PUBLIC_EMAIL);
    // salesEmail снят: после перехода на общий ящик он дублировал бы email
    // символ в символ, а два поля с одним значением однажды разойдутся.
    expect(seller).not.toHaveProperty('salesEmail');
  });

  it('публичный автор и ящик отправителя — общий адрес', () => {
    expect(expert.email).toBe(PUBLIC_EMAIL);
    expect(offerManager.email).toBe(PUBLIC_EMAIL);
  });

  it('в подписи письма — личный адрес менеджера, а не приёмная', () => {
    // Решение руководителя 21.09.2026: под именем в подписи стоит человек.
    // Общий ящик при этом остаётся отправителем и адресом заготовок mailto.
    expect(offerManager.signatureEmail).toBe('avbelyaev@biz-soft.pro');
    expect(offerManager.signatureEmail).not.toBe(offerManager.email);
  });

  it('личного адреса нет нигде в публичном контуре', () => {
    const offenders = FILES.filter((rel) => {
      if (INTERNAL_ALLOWED.has(rel) || isArchivedLegal(rel)) return false;
      return /avbelyaev@biz-soft\.pro/i.test(readFileSync(resolve(ROOT, rel), 'utf8'));
    });
    expect(offenders, `публичный контакт — только ${PUBLIC_EMAIL}`).toEqual([]);
  });

  it('на страницах сайта личного адреса нет и в исключениях', () => {
    // Исключения выше — почтовый слой. Страница остаётся публикацией: если
    // личный адрес однажды переедет в .astro, тест обязан это поймать.
    const pages = FILES.filter((rel) => rel.startsWith('src/pages/') && rel.endsWith('.astro'));
    const offenders = pages.filter((rel) =>
      /avbelyaev@biz-soft\.pro/i.test(readFileSync(resolve(ROOT, rel), 'utf8')));
    expect(offenders).toEqual([]);
  });
});

describe('внутренняя инфраструктура не называется публично', () => {
  // Служебные страницы и код — внутренний контур: администратору названия
  // как раз нужны, иначе инструкция превращается в ребус.
  const isPublicText = (rel: string) =>
    CURRENT_LEGAL.has(rel)
    || (rel.startsWith('src/pages/') && rel.endsWith('.astro') && !rel.startsWith('src/pages/admin/'));

  it.each(['Beget', 'REG.RU', 'Bitrix24'])('%s не упоминается на публичных страницах', (word) => {
    const needle = word.toLowerCase().replace('.', '\\.');
    const offenders = FILES.filter(isPublicText).filter((rel) =>
      new RegExp(needle, 'i').test(readFileSync(resolve(ROOT, rel), 'utf8')));
    expect(offenders, `${word}: название поставщика — во внутреннем реестре, не в публичном тексте`)
      .toEqual([]);
  });
});
