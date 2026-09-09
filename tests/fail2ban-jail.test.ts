import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';

/**
 * Конфиг fail2ban — INI: ключ до первого заголовка секции делает файл
 * нечитаемым целиком.
 *
 * Инцидент 09.09.2026: `ignoreip` с сетями поисковиков был добавлен над
 * строкой `[nginx-noscript]`. Файл перестал разбираться
 * (MissingSectionHeaderError), то есть при установке на сервер fail2ban не
 * прочитал бы jail вовсе — и правка, задуманная как защита обхода, оставила
 * бы сайт без самого jail. Поймано вопросом руководителя до установки.
 *
 * Проверка идёт по файлу репозитория: на сервер он попадает копией.
 */
const JAIL = 'deploy/fail2ban/jail.d/nginx-noscript.local';
const FILTER = 'deploy/fail2ban/filter.d/nginx-noscript.conf';

/** Разбор INI в объём, достаточный для проверки: секция → ключи. */
function parseIni(text: string): Record<string, Record<string, string>> {
  const out: Record<string, Record<string, string>> = {};
  let section: string | null = null;
  let key: string | null = null;
  for (const raw of text.split('\n')) {
    if (!raw.trim() || raw.trimStart().startsWith('#')) continue;
    const head = raw.match(/^\[([^\]]+)\]\s*$/);
    if (head) { section = head[1]; out[section] = {}; key = null; continue; }
    // Продолжение многострочного значения — со сдвигом вправо.
    if (/^\s/.test(raw) && section && key) { out[section][key] += ' ' + raw.trim(); continue; }
    const kv = raw.match(/^([^=]+?)\s*=\s*(.*)$/);
    if (!kv) continue;
    if (!section) throw new Error(`ключ "${kv[1].trim()}" до заголовка секции — fail2ban не прочитает файл`);
    key = kv[1].trim();
    out[section][key] = kv[2].trim();
  }
  return out;
}

describe('fail2ban: jail против сканеров читается и не банит поисковиков', () => {
  it('файл разбирается: ни одного ключа до заголовка секции', () => {
    expect(() => parseIni(readFileSync(JAIL, 'utf8'))).not.toThrow();
  });

  it('секция [nginx-noscript] несёт порог, фильтр и лог', () => {
    const jail = parseIni(readFileSync(JAIL, 'utf8'))['nginx-noscript'];
    expect(jail, 'секции [nginx-noscript] нет').toBeTruthy();
    expect(jail.enabled).toBe('true');
    expect(jail.filter).toBe('nginx-noscript');
    expect(Number(jail.maxretry)).toBeGreaterThan(0);
    expect(jail.logpath).toContain('/var/log/nginx/');
  });

  it('сети поисковиков — внутри секции, иначе исключение не действует', () => {
    const jail = parseIni(readFileSync(JAIL, 'utf8'))['nginx-noscript'];
    const nets = (jail.ignoreip || '').split(/\s+/).filter(Boolean);
    // Googlebot, Яндекс и Bing: без них собственная защита гасит обход,
    // а обход — единственный дефицитный ресурс сайта (разбор 08.09.2026).
    for (const must of ['66.249.64.0/19', '87.250.224.0/19', '95.108.128.0/17', '40.77.160.0/19']) {
      expect(nets, `в ignoreip нет ${must}`).toContain(must);
    }
  });

  it('backend задан явно — иначе jail читал бы systemd-журнал', () => {
    // В сборке для Debian/Ubuntu backend по умолчанию systemd: jail без своего
    // backend игнорирует logpath и смотрит в журнал, где логов доступа nginx
    // нет. Проверка 09.09.2026 поймала это через четыре часа после установки —
    // jail был активен, «Total failed: 0» при живом сканере, а в статусе стояло
    // «Journal matches» вместо «File list».
    const jail = parseIni(readFileSync(JAIL, 'utf8'))['nginx-noscript'];
    expect(jail.backend, 'backend не задан — logpath не будет работать').toBeTruthy();
    expect(['polling', 'auto', 'pyinotify', 'gamin']).toContain(jail.backend);
  });

  it('имя фильтра из jail совпадает с файлом фильтра', () => {
    const jail = parseIni(readFileSync(JAIL, 'utf8'))['nginx-noscript'];
    expect(FILTER).toContain(`${jail.filter}.conf`);
    expect(readFileSync(FILTER, 'utf8')).toMatch(/^\[Definition\]$/m);
  });
});
