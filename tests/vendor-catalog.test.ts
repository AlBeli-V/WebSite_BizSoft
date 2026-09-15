/**
 * Приёмка партии новых вендоров (scripts/catalog/*.json + VENDORS).
 * Проверяет: уникальность слагов, отсутствие stop-list, полноту полей SKU,
 * правила Microsoft (ключи с припиской про 5 дней, M365 — черновики без цены),
 * контрольные расчёты цены по штатной формуле computePegRub.
 */
import { describe, expect, it } from 'vitest';
import { isSystemSku } from '../src/lib/sku';
import { readFileSync, readdirSync, existsSync, rmSync } from 'node:fs';
import { resolve, basename } from 'node:path';
import { tmpdir } from 'node:os';
import { execFileSync } from 'node:child_process';
import * as XLSX from 'xlsx';
import { VENDORS } from '../src/data/vendors';
import { computePegRub } from '../src/lib/pricing';

const CATALOG = resolve(__dirname, '../scripts/catalog');
const allPackages = existsSync(CATALOG)
  ? readdirSync(CATALOG).filter((f) => f.endsWith('.json')).map((f) => ({
      slug: basename(f, '.json'),
      pkg: JSON.parse(readFileSync(resolve(CATALOG, f), 'utf8')),
    }))
  : [];
// removed-пакеты содержат только архивные стабы (вендор снят с витрины);
// архивные стабы {sku, archive} не проверяются на полноту полей.
const packages = allPackages
  .filter(({ pkg }) => !pkg.removed)
  .map(({ slug, pkg }) => ({ slug, pkg: { ...pkg, products: pkg.products.filter((p: { archive?: boolean }) => !p.archive) } }));

// Из стоп-листа выведены решением руководителя 20.08.2026: SOLIDWORKS (прайс
// вендора получен, восемь тарифов заведены), Atlassian и TeamViewer
// (self-service checkout и оплата картой подтверждены, тарифы сняты со страниц
// вендоров). Остальные позиции стоп-листа (docs/vendors-expansion-prompt.md,
// раздел 6) остаются в силе.
// Добавлены решением руководителя 29.08.2026: NordVPN и любые VPN-сервисы
// (реклама VPN в России запрещена — штрафы и ответственность), Ansys (цен на
// сайте нет, узкоспециализированное инженерное ПО вне формата магазина).
const STOP_LIST = ['sap', 'oracle', 'vmware', 'broadcom', 'veeam', 'citrix', 'cisco',
  'salesforce', 'ibm', 'archicad', 'red hat', 'redhat', 'canonical',
  'mathworks', 'mongodb', 'elastic', 'eset',
  'nordvpn', 'vpn', 'ansys'];

const ALLOWED_CATEGORIES = ['system', 'security', 'development', 'collaboration',
  'architecture', 'vcs', 'office', 'design', 'ai', 'media', 'pm', 'monitoring',
  'database', 'engineering',
  // Заведены 21.08.2026 под партию ManageEngine: четыре тысячи позиций про
  // учётные записи, службу поддержки и парк рабочих мест не помещаются ни в
  // один из прежних разделов. Создаёт их воркфлоу ops-categories по
  // data/catalog/categories.json.
  'iam', 'helpdesk', 'endpoint',
  // Заведён 30.08.2026 решением руководителя: сайты компании и интернет-
  // магазины (WordPress.com) — не «Дизайн и графика».
  'web',
  // AI-подкатегории хаба /catalog/ai (заведены миграцией ai-catalog-migrate):
  // профильный AI-товар лежит в подкатегории, а не в родительском ai — иначе
  // его нет в выдаче /catalog/ai/<sub>. Родительский ai остаётся для позиций
  // вне подкатегорий (например, API-доступ к моделям).
  'ai-text', 'ai-code', 'ai-image', 'ai-video', 'ai-audio', 'ai-office',
  'ai-marketing', 'ai-enterprise',
  // Заведён 05.09.2026 под подарочные карты (Apple Gift Card): цифровой код
  // пополнения баланса — не лицензия и не подписка, в прежние разделы не
  // ложится. Создаёт ops-categories по data/catalog/categories.json.
  'gift-cards',
  // Заведён 15.09.2026 решением руководителя под TryHackMe: практическое
  // обучение кибербезопасности — не антивирус и не системное ПО. Создаёт
  // ops-categories по data/catalog/categories.json.
  'training'];

describe('VENDORS', () => {
  it('слаги уникальны', () => {
    const slugs = VENDORS.map((v) => v.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
  });

  it('stop-list вендоры отсутствуют', () => {
    for (const v of VENDORS) {
      // legalName не проверяем: там законно встречается материнская компания
      // (например, Slack Technologies, LLC (Salesforce)).
      const hay = `${v.slug} ${v.vendor}`.toLowerCase();
      for (const bad of STOP_LIST) expect(hay, `${v.slug} содержит ${bad}`).not.toContain(bad);
    }
  });

  it('новые вендоры партии заведены в VENDORS с совпадающим vendor', () => {
    for (const { slug, pkg } of packages) {
      const entry = VENDORS.find((v) => v.slug === slug);
      expect(entry, `нет записи VENDORS для ${slug}`).toBeTruthy();
      expect(entry!.vendor).toBe(pkg.vendor_entry.vendor);
    }
  });
});

describe('пакеты scripts/catalog', () => {
  it('партия загружена', () => {
    expect(packages.length).toBeGreaterThanOrEqual(9);
  });

  it('цена из веб-исследования помечена честно, а не выдана за прайс поставщика', () => {
    // Сайты части вендоров из среды недоступны: цена собрана по обзорам.
    // Такая карточка обязана нести пометку и оговорку в notes — иначе через
    // месяц никто не вспомнит, что число нужно подтвердить на checkout.
    for (const { pkg } of packages) {
      for (const p of pkg.products) {
        if (p.price_confidence !== 'search-estimate') continue;
        expect(String(p.notes || '').length, `${p.slug}.notes без пояснения происхождения цены`)
          .toBeGreaterThan(40);
      }
    }
  });

  it('обязательные поля SKU заполнены, артикул — единой системы, слаг на месте', () => {
    for (const { pkg } of packages) {
      for (const p of pkg.products) {
        // Архивные стабы снимают с витрины позиции под прежними артикулами;
        // черновики, не выложенные на витрину, переводятся при публикации.
        if (p.archive || p.status === 'draft') continue;
        expect(isSystemSku(p.sku), `${p.slug}: артикул «${p.sku}» не по единой системе`).toBe(true);
        expect(String(p.slug)).toMatch(/^[a-z0-9-]+$/);
        expect(ALLOWED_CATEGORIES, `категория ${p.category} (${p.slug})`).toContain(p.category);
        expect(['published', 'draft']).toContain(p.status);
        // Скрытая позиция конфигуратора страницы не имеет и в поиск не идёт:
        // ключевые слова и список возможностей ей не нужны. Название, краткое
        // описание и подпись к цене нужны — они уходят в КП покупателю.
        const fields = p.status === 'published'
          ? ['name', 'short_description', 'description', 'keywords', 'billing']
          : ['name', 'short_description', 'billing'];
        for (const f of fields) {
          expect(String(p[f] || '').length, `${p.slug}.${f} пуст`).toBeGreaterThan(3);
        }
        if (p.status === 'published') {
          expect(Array.isArray(p.features) && p.features.length >= 3, `${p.slug}.features`).toBe(true);
        }
      }
    }
  });

  it('слаги товаров уникальны, enterprise/quote-only тарифы не заведены', () => {
    const all = packages.flatMap(({ pkg }) =>
      pkg.products.map((p: { slug: string; name: string; base_price_usd?: number | null;
        price_confidence?: string | null }) => p));
    expect(new Set(all.map((p) => p.slug)).size).toBe(all.length);
    // Запрет на enterprise-тарифы существует потому, что у большинства
    // вендоров «Enterprise» означает «цены нет, обращайтесь в отдел продаж».
    // У ManageEngine это не так: магазин вендора публикует цены редакций
    // Enterprise и продаёт их тем же самообслуживаемым checkout'ом, а у
    // PAM360 редакция Enterprise вообще единственная. Исключение узкое —
    // только карточки, у которых есть подтверждённая снимком цена; позиции
    // «по запросу» пайплайн Zoho в каталог не заводит вовсе.
    // Подтверждено владельцем 21.08.2026: «Энтерпрайз он у этого вендора
    // покупается как и остальные и доступен, его будем добавлять».
    const fromZohoPipeline = (slug: string) =>
      slug.startsWith('me-') || slug.startsWith('manageengine-');
    // Postman Enterprise — то же послабление, что у ManageEngine: вендор
    // публикует цену ($49 за пользователя в месяц при годовой оплате,
    // ops-probe #248 13.09.2026) и продаёт план самообслуживанием.
    // Руководитель 13.09.2026: «Solo, Teams, Enterprise действуют и
    // доступны по карте, на сайте оставляем» (docs/rules/catalog.md).
    const PRICED_ENTERPRISE = new Set(['postman-enterprise']);
    for (const p of all) {
      // Продукт, у которого вендор не публикует цену вовсе: страница магазина
      // отдаёт конфигуратор с нулевым итогом (docs/rules/catalog.md, решение
      // руководителя 14.09.2026). Послабление узкое — оно про продукт
      // целиком, а не про старшую редакцию линейки, где соседние редакции
      // стоят с ценой: такой тариф ниже по-прежнему требует цену со страницы.
      if (p.price_confidence === 'quote-only') {
        expect(p.base_price_usd, `${p.slug}: у позиции по запросу стоит цена`).toBeNull();
        expect(p.name.toLowerCase(), `enterprise-тариф по запросу ${p.slug}`)
          .not.toContain('enterprise');
        continue;
      }
      if (fromZohoPipeline(p.slug) || PRICED_ENTERPRISE.has(p.slug)) {
        // Условие послабления: цена карточки взята со страницы вендора.
        expect(p.base_price_usd, `${p.slug}: позиция без цены источника`).toBeGreaterThan(0);
        expect(p.price_confidence, `${p.slug}: цена не со страницы вендора`).toBe('vendor-page');
        continue;
      }
      expect(p.name.toLowerCase(), `enterprise-тариф ${p.slug}`).not.toContain('enterprise');
    }
    // docker-business разрешён с 19.08.2026: поставка подтверждена поставщиком
    for (const bad of ['gitlab-ultimate', 'gitlab-dedicated', 'slack-enterprise']) {
      expect(all.map((p) => p.slug), `${bad} под запретом`).not.toContain(bad);
    }
  });

  it('карточки с публикуемой ценой привязаны к валюте вендора, «по запросу» — без базовой цены', () => {
    for (const { pkg } of packages) {
      for (const p of pkg.products) {
        // Себестоимость — в одной валюте: две сразу означают, что никто не
        // знает, по какому курсу считается цена (import-vendors такую строку
        // отвергает, тест ловит её раньше прогона).
        expect(p.base_price_usd != null && p.base_price_eur != null,
          `${p.slug}: себестоимость сразу в долларах и евро`).toBe(false);
        if (p.base_price_eur != null) expect(p.base_price_eur).toBeGreaterThan(0);
        if (p.base_price_usd != null) {
          expect(p.base_price_usd).toBeGreaterThan(0);
          // Цена без страницы допустима только у скрытых позиций
          // конфигуратора: они лежат в базе черновиками, цену им считает та же
          // ежедневная переоценка, а в поиск и каталог они не попадают.
          if (p.status !== 'published') {
            expect(p.status, `${p.slug}: цена у позиции со статусом ${p.status}`).toBe('draft');
            expect(String(p.notes || ''), `${p.slug}: скрытая позиция без пометки`)
              .toContain('конфигуратора');
          }
        }
      }
    }
  });
});

describe('Microsoft', () => {
  const ms = packages.find(({ slug }) => slug === 'microsoft');
  const products: Record<string, unknown>[] = ms ? ms.pkg.products : [];
  const keys = products.filter((p) => String(p.slug).startsWith('ms-'));
  const m365 = products.filter((p) => String(p.slug).startsWith('m365-'));

  it('коробочные ключи: приписка про 5 дней, поставка ключом, коэффициент 1.0, без «Ключ активации» в имени', () => {
    expect(keys.length).toBe(13);
    for (const p of keys) {
      expect(String(p.description)).toContain('в течение 5 дней');
      expect(String(p.description)).toMatch(/замене и возврату не подлежит/);
      expect(String(p.name).toLowerCase()).not.toContain('ключ активации');
      expect(p.markup_coeff).toBe(1.0);
      expect(p.base_price_usd).toBeGreaterThan(0);
      expect((p.features as string[]).join(' ').toLowerCase()).toContain('ключ активации');
    }
  });

  it('подписки Microsoft 365 — всегда условные: черновик, без цены, с текстом о приостановке продаж', () => {
    expect(m365.length).toBe(5);
    for (const p of m365) {
      expect(p.status).toBe('draft');
      expect(p.base_price_usd == null).toBe(true);
      expect(String(p.description)).toMatch(/приостановлен/);
    }
  });
});

describe('контрольные расчёты цены (формула computePegRub)', () => {
  const rates = { usd: 80, eur: null };
  const cases: [string, number, number | null, number][] = [
    // [описание, base_usd, coeff|null(=1.85), ожидаемые ₽ при курсе 80]
    ['подписка docker-pro', 130, null, 19240],
    ['подписка anydesk-solo', 403, null, 59644],
    ['подписка dropbox-standard', 200, null, 29600],
    ['ключ ms-office-hb-2021-win (коэф. 1.0)', 257, 1.0, 20560],
    ['ключ ms-windows-11-pro (коэф. 1.0)', 222, 1.0, 17760],
  ];
  it.each(cases)('%s', (_label, base, coeff, expected) => {
    const rub = computePegRub(
      { peg_to_usd: true, peg_currency: 'USD', base_price_usd: base, base_price_eur: null, markup_coeff: coeff },
      rates,
    );
    expect(rub).toBe(expected);
  });

  // Закупка в евро (TryHackMe, 15.09.2026): та же формула, другая колонка
  // курса. Пересчёта евро в доллары в цепочке нет — он сделал бы рублёвую
  // цену заложницей движения EUR/USD.
  const eurRates = { usd: 80, eur: 95 };
  const eurCases: [string, number, number][] = [
    // [описание, base_eur, ожидаемые ₽ при курсе 95 и коэффициенте 1.9]
    ['личная подписка tryhackme-premium', 255, 46028],
    ['личная подписка tryhackme-max', 445, 80323],
    ['пакет мест tryhackme-business-5-seats', 1488, 268584],
  ];
  it.each(eurCases)('%s', (_label, base, expected) => {
    const rub = computePegRub(
      { peg_to_usd: true, peg_currency: 'EUR', base_price_usd: null, base_price_eur: base, markup_coeff: 1.9 },
      eurRates,
    );
    expect(rub).toBe(expected);
  });
});

describe('сборка xlsx для штатного импорта (scripts/import-vendors.mjs)', () => {
  it('пакет с закупкой в евро уезжает в импорт евро, а не долларами', () => {
    const out = resolve(tmpdir(), `vendors-eur-${process.pid}.xlsx`);
    execFileSync(process.execPath, ['scripts/import-vendors.mjs', '--emit', out, 'tryhackme'],
      { cwd: resolve(__dirname, '..'), encoding: 'utf8' });
    const wb = XLSX.read(readFileSync(out));
    const rows = XLSX.utils.sheet_to_json<Record<string, string | number>>(wb.Sheets['Товары']);
    rmSync(out, { force: true });
    const premium = rows.find((r) => r.sku === 'THM-LIC-PREMIUM-IND-1Y-USER')!;
    expect(premium, 'позиция не попала в файл импорта').toBeTruthy();
    expect(premium.base_price_eur).toBe(255);
    expect(premium.base_price_usd).toBe('');
    expect(premium.peg_currency).toBe('EUR');
    expect(premium.markup_coeff).toBe(1.9);
    expect(premium.price, 'цена считается по курсу ЦБ, а не проставляется файлом').toBe('');
    expect(premium.slug).toBe('tryhackme-premium');
  });
});
