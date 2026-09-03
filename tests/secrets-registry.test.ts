/**
 * Реестр секретов: каждое имя, которое читают воркфлоу, зарегистрировано
 * с назначением, а второе имя одного и того же токена — долг со сроком.
 *
 * Аудит 03.09.2026: токен Вебмастера жил под двумя именами (YANDEX_OAUTH и
 * YANDEX_WEBMASTER_TOKEN), токен Директа — тоже (DIRECT_TOKEN и
 * YANDEX_DIRECT_TOKEN). Воркфлоу, читавший «не то» имя, печатал в журнал
 * «токен не задан», хотя токен был, — и эта фраза две недели попадала в
 * письмо руководителю как факт. Реестр делает имя единственным.
 */
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(__dirname, '..');
const dir = resolve(root, '.github/workflows');

type Entry = {
  name: string;
  purpose: string;
  consumers: string[];
  alias_of?: string;
  resolve_by?: string;
};

const registry = JSON.parse(readFileSync(resolve(root, 'ops/secrets/registry.json'), 'utf8')) as {
  secrets: Entry[];
};
const byName = new Map(registry.secrets.map((e) => [e.name, e]));

function usedSecrets(): Map<string, Set<string>> {
  const out = new Map<string, Set<string>>();
  for (const name of readdirSync(dir).filter((n) => n.endsWith('.yml'))) {
    const text = readFileSync(resolve(dir, name), 'utf8');
    for (const m of text.matchAll(/secrets\.([A-Z0-9_]+)/g)) {
      if (!out.has(m[1])) out.set(m[1], new Set());
      out.get(m[1])!.add(name);
    }
  }
  return out;
}

const used = usedSecrets();
const today = new Date().toISOString().slice(0, 10);

describe('реестр секретов', () => {
  it('каждый secrets.X из воркфлоу зарегистрирован с назначением', () => {
    const missing = [...used.keys()].filter((n) => !byName.has(n));
    expect(missing, 'не в реестре ops/secrets/registry.json').toEqual([]);
    const blank = registry.secrets.filter((e) => !e.purpose || e.purpose === '?').map((e) => e.name);
    expect(blank, 'без назначения').toEqual([]);
  });

  it('в реестре нет секретов, которые никто не читает', () => {
    const unused = registry.secrets.filter((e) => !used.has(e.name)).map((e) => e.name);
    expect(unused, 'удалить из реестра (и из настроек репозитория)').toEqual([]);
  });

  it('список потребителей совпадает с фактом', () => {
    const drift: string[] = [];
    for (const e of registry.secrets) {
      const actual = [...(used.get(e.name) ?? [])].sort();
      if (JSON.stringify(actual) !== JSON.stringify([...e.consumers].sort())) {
        drift.push(`${e.name}: в реестре ${e.consumers.join(', ')}; фактически ${actual.join(', ')}`);
      }
    }
    expect(drift).toEqual([]);
  });

  it('дубль имени (alias_of) ссылается на основное имя и имеет срок, который не вышел', () => {
    const problems: string[] = [];
    for (const e of registry.secrets) {
      if (!e.alias_of) continue;
      if (!byName.has(e.alias_of)) problems.push(`${e.name}: alias_of ${e.alias_of} не в реестре`);
      if (!e.resolve_by) problems.push(`${e.name}: у дубля нет resolve_by`);
      else if (e.resolve_by < today) problems.push(`${e.name}: срок ${e.resolve_by} вышел — перевести потребителей на ${e.alias_of}`);
    }
    expect(problems).toEqual([]);
  });
});
