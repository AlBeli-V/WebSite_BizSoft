/**
 * robots.txt и незначащие GET-параметры.
 *
 * Файл ломался дважды, и оба раза тихо:
 *   18.09.2026 — у Googlebot, YandexBot и ИИ-краулеров стояли собственные
 *                группы с единственной строкой «Allow: /». Робот применяет
 *                одну подходящую группу целиком, поэтому служебные разделы
 *                были открыты ровно тем роботам, ради которых файл писался;
 *   15.09.2026 — в индексе лежали пять копий страниц вендоров с «?etext=»;
 *                22.09.2026 письмо Вебмастера принесло те же дубли по блогу
 *                и вендорам. Директиву Clean-param добавили руками, и
 *                перечень меток с тех пор жил в одном экземпляре в тексте
 *                файла: добавить метку в рекламу и забыть про robots.txt
 *                ничего не стоило.
 *
 * Отсюда правило (docs/rules/url-params.md): перечень параметров ведётся в
 * реестре data/seo/url-params.json, блок Clean-param собирается из него
 * («pnpm robots:sync»), а этот тест стережёт и сборку, и структуру файла.
 * Параметр, меняющий содержимое страницы, в Clean-param не попадает никогда:
 * директива склеила бы разные страницы в одну.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
// @ts-expect-error — скрипты SEO живут вне типизированного src
import { auditRobots, cleanParamLines, parseCleanParams, readRegistry, syncRobots, userAgentGroups, CLEAN_PARAM_LIMIT } from '../scripts/seo/robots-lib.mjs';

const robots = readFileSync('public/robots.txt', 'utf8');
const registry = readRegistry();

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    return statSync(full).isDirectory() ? walk(full) : [full];
  });
}

describe('robots.txt', () => {
  it('проходит разбор без нарушений', () => {
    expect(auditRobots(robots, registry)).toEqual([]);
  });

  it('блок Clean-param собран из реестра, а не написан руками', () => {
    expect(syncRobots(robots, registry)).toBe(robots);
  });

  it('все агенты перечислены одной группой', () => {
    const groups = userAgentGroups(robots);
    expect(groups).toHaveLength(1);
    expect(groups[0].agents).toContain('YandexBot');
    expect(groups[0].agents).toContain('Googlebot');
    expect(groups[0].directives.join('\n')).toContain('Disallow: /admin');
  });

  it('строка Clean-param укладывается в предел Яндекса', () => {
    for (const line of robots.split('\n').filter((l) => /^Clean-param:/i.test(l))) {
      expect(line.length).toBeLessThanOrEqual(CLEAN_PARAM_LIMIT);
    }
  });

  it('обход адресов с параметрами не запрещён: иначе робот не увидит canonical', () => {
    const disallow = robots.split('\n').filter((l) => /^\s*Disallow:/i.test(l));
    expect(disallow.some((l) => l.includes('?'))).toBe(false);
  });
});

describe('реестр GET-параметров', () => {
  const params = parseCleanParams(robots);

  it('незначащие метки все в Clean-param', () => {
    for (const p of registry.insignificant) expect(params).toContain(p);
    expect(params).toContain('etext');
  });

  it('значащие параметры в Clean-param не попадают', () => {
    for (const p of registry.meaningful) expect(params).not.toContain(p);
  });

  it('метки, которые читает атрибуция, объявлены незначащими', () => {
    // Новая метка в src/lib/attribution.ts без записи в реестре — это новый
    // дубль в выдаче: страницу с ней робот обойдёт как отдельный адрес.
    const attribution = readFileSync('src/lib/attribution.ts', 'utf8');
    const marks = [
      ...(attribution.match(/const UTM_FIELDS = \[(.*?)\]/s)?.[1] || ''),
      ...(attribution.match(/const CLICK_IDS = \[(.*?)\]/s)?.[1] || ''),
    ].join('');
    const names = [...marks.matchAll(/'([a-z_]+)'/g)].map((m) => m[1]);
    expect(names.length).toBeGreaterThan(5);
    for (const n of names) expect(registry.insignificant).toContain(n);
  });

  it('каждый параметр, который читает страница, описан в реестре', () => {
    // Страницы (в отличие от /api) обходит робот, поэтому любой их параметр
    // либо меняет содержимое — и тогда у него есть запись «meaningful» с
    // указанием, чем закрыт дубль, — либо незначащий и уходит в Clean-param.
    const pages = walk('src/pages').filter((f) => !f.startsWith(join('src/pages', 'api')) && /\.(astro|ts)$/.test(f));
    const known = new Set<string>([...registry.insignificant, ...registry.meaningful]);
    const unknown = new Map<string, string>();
    for (const file of pages) {
      for (const m of readFileSync(file, 'utf8').matchAll(/searchParams\.get\(\s*'([^']+)'/g)) {
        if (!known.has(m[1])) unknown.set(m[1], file);
      }
    }
    expect([...unknown.entries()].map(([p, f]) => `${p} (${f})`)).toEqual([]);
  });

  it('у каждой записи реестра есть примечание', () => {
    for (const rec of [...registry.entries.insignificant, ...registry.entries.meaningful]) {
      expect(rec.name).toMatch(/^[a-z_]+$/);
      expect((rec.note || '').length).toBeGreaterThan(10);
    }
  });
});

describe('разбор ловит поломки', () => {
  const broken = (text: string) => auditRobots(text, registry).join(' | ');

  it('видит отдельную группу User-agent с одним Allow', () => {
    const text = robots.replace('User-agent: YandexBot\n', 'User-agent: YandexBot\nAllow: /\n\n');
    expect(broken(text)).toContain('групп User-agent');
  });

  it('видит потерянную метку', () => {
    expect(broken(robots.replace('etext&', ''))).toContain('etext');
  });

  it('видит значащий параметр в Clean-param', () => {
    expect(broken(robots.replace('Clean-param: ', 'Clean-param: q&'))).toContain('значащие параметры');
  });

  it('видит запрет обхода адресов с параметрами', () => {
    expect(broken(robots.replace('Disallow: /admin', 'Disallow: /*?\nDisallow: /admin'))).toContain('закрывает обход');
  });

  it('видит потерянную карту сайта', () => {
    expect(broken(robots.replace(/^Sitemap:.*$/m, ''))).toContain('Sitemap');
  });

  it('разбивает длинный перечень на строки в пределе Яндекса', () => {
    const many = Array.from({ length: 120 }, (_, i) => `utm_very_long_param_${i}`);
    const lines = cleanParamLines(many);
    expect(lines.length).toBeGreaterThan(1);
    for (const l of lines) expect(l.length).toBeLessThanOrEqual(CLEAN_PARAM_LIMIT);
    expect(lines.join('&').replace(/Clean-param: /g, '').split('&')).toEqual(many);
  });
});
