/**
 * Барьер против расхождения реестра операционных Routine с промптами.
 *
 * Routine (расписания Claude) живут в аккаунте, а не в репозитории, и их
 * состояние ниоткуда не следует. Дважды подряд — 02.09 и 03.09.2026 — контур
 * вставал молча: Routine формально была настроена верно, а прогон уходил в
 * сессию без рабочей копии и без GitHub MCP. Источником истины сделан
 * ops/routines/registry.json: ежедневный сторож routine-health читает его из
 * main и приводит живое состояние к нему.
 *
 * Отсюда цена ошибки в реестре: битая ссылка на промпт или кривой cron
 * означают, что сторож либо не починит контур, либо пересоздаст его неверно —
 * и узнает об этом никто, потому что контур молчит по замыслу. Поэтому реестр
 * проверяется сборкой: файл разбирается, у каждой автоматически чинимой записи
 * есть непустой промпт, cron валиден, имена Routine уникальны.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

type Entry = {
  name?: string;
  cron_expression?: string;
  prompt_file?: string | null;
  session_title?: string | null;
  model?: string;
  tags?: string[];
  data_branch?: string;
  autoheal?: boolean;
};

type Registry = {
  repository?: string;
  environment_id?: string;
  journal_issue?: number;
  routines?: Record<string, Entry>;
};

const root = resolve(__dirname, '..');
const registryPath = resolve(root, 'ops/routines/registry.json');

const registry = JSON.parse(readFileSync(registryPath, 'utf8')) as Registry;
const entries = Object.entries(registry.routines ?? {});

/** Пять полей стандартного cron; сторож задаёт расписание в UTC. */
function cronIsValid(expression: string): boolean {
  const fields = expression.trim().split(/\s+/);
  if (fields.length !== 5) return false;
  const ranges = [
    [0, 59],
    [0, 23],
    [1, 31],
    [1, 12],
    [0, 7],
  ] as const;
  return fields.every((field, index) => {
    const [min, max] = ranges[index];
    return field.split(',').every((part) => {
      const [range, step] = part.split('/');
      if (step !== undefined && !/^\d+$/.test(step)) return false;
      if (range === '*') return true;
      return range.split('-').every((bound) => {
        if (!/^\d+$/.test(bound)) return false;
        const value = Number(bound);
        return value >= min && value <= max;
      });
    });
  });
}

describe('реестр операционных Routine', () => {
  it('заполнен и знает свой репозиторий, окружение и журнал', () => {
    expect(entries.length).toBeGreaterThan(0);
    expect(registry.repository).toMatch(/^https:\/\/github\.com\/.+\/.+$/);
    expect(registry.environment_id).toMatch(/^env_/);
    expect(typeof registry.journal_issue).toBe('number');
  });

  it('у каждой записи есть имя и корректное расписание', () => {
    for (const [key, entry] of entries) {
      expect(entry.name, `${key}: пустое имя`).toBeTruthy();
      expect(
        cronIsValid(entry.cron_expression ?? ''),
        `${key}: некорректный cron «${entry.cron_expression}»`,
      ).toBe(true);
    }
  });

  it('имена Routine уникальны — сторож ищет живую Routine по имени', () => {
    const names = entries.map(([, entry]) => entry.name);
    expect(new Set(names).size).toBe(names.length);
  });

  it('у автоматически чинимых контуров есть непустой промпт и данные для сессии', () => {
    for (const [key, entry] of entries) {
      if (entry.autoheal !== true) continue;

      const promptFile = entry.prompt_file;
      expect(promptFile, `${key}: не указан prompt_file`).toBeTruthy();

      const promptPath = resolve(root, promptFile as string);
      expect(existsSync(promptPath), `${key}: нет файла ${promptFile}`).toBe(true);
      expect(
        readFileSync(promptPath, 'utf8').trim().length,
        `${key}: пустой промпт ${promptFile}`,
      ).toBeGreaterThan(200);

      expect(entry.session_title, `${key}: не указан session_title`).toBeTruthy();
      expect(entry.model, `${key}: не указана модель`).toBeTruthy();
      expect(entry.data_branch, `${key}: не указана ветка данных`).toBeTruthy();
      expect(
        entry.tags ?? [],
        `${key}: сессия-исполнитель должна нести тег ops-routine`,
      ).toContain('ops-routine');
    }
  });

  it('промпты исполнителей не поднимают тревогу руководителю на поломке привязки', () => {
    for (const [key, entry] of entries) {
      if (entry.autoheal !== true || !entry.prompt_file) continue;
      const text = readFileSync(resolve(root, entry.prompt_file), 'utf8');
      expect(
        /привязк/i.test(text),
        `${key}: в промпте нет раздела о привязке сессии`,
      ).toBe(true);
      expect(
        /чинить (её )?должен человек/i.test(text),
        `${key}: промпт всё ещё требует вмешательства человека при поломке привязки`,
      ).toBe(false);
    }
  });

  it('у сторожа есть присматривающий: сам себя он починить не может', () => {
    const health = registry.routines?.['routine-health'];
    expect(health, 'в реестре нет записи routine-health').toBeTruthy();

    const guard = (health as Entry & { guarded_by?: string }).guarded_by;
    expect(guard, 'у routine-health не указан guarded_by').toBeTruthy();

    const guardEntry = registry.routines?.[guard as string];
    expect(guardEntry, `guarded_by указывает на неизвестный контур «${guard}»`).toBeTruthy();
    expect(guardEntry?.autoheal, `присматривающий «${guard}» сам не чинится`).toBe(true);

    const guardPrompt = readFileSync(resolve(root, guardEntry!.prompt_file as string), 'utf8');
    expect(
      /Взаимный присмотр за сторожем/i.test(guardPrompt),
      `в промпте «${guard}» нет раздела присмотра за сторожем`,
    ).toBe(true);
  });
});
