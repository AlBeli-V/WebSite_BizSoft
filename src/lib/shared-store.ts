/**
 * Общее хранилище для счётчиков лимитов и кэша справочника.
 *
 * Требование одно и оно определяет всю конструкцию: состояние живёт СНАРУЖИ
 * процесса. Счётчик в памяти инстанса при двух контейнерах даёт двойной
 * порог, при перезапуске — чистый лист, а при откате деплоя молча теряет
 * историю. Хранилищем работает Directus — та же база, где лежат заявки:
 * она уже развёрнута, уже доступна приложению и переживает рестарт.
 *
 * Второе требование — недоступность хранилища не должна ронять приём заявок.
 * Все операции при сбое возвращают «не знаю» (null), а вызывающий код
 * трактует это как «пропустить». Рубеж nginx при этом остаётся на месте,
 * так что открытым остаётся не всё, а только точный порог.
 */
import { kvGet, kvPut } from './directus';

export interface SharedStore {
  /** Значение по ключу; null — нет записи ИЛИ хранилище недоступно. */
  get<T>(key: string): Promise<T | null>;
  set(key: string, value: unknown, ttlSec: number): Promise<void>;
  /**
   * Увеличить счётчик и вернуть новое значение.
   * null — хранилище недоступно, порог применять нельзя.
   */
  incr(key: string, ttlSec: number): Promise<number | null>;
}

const expiryIso = (ttlSec: number): string =>
  new Date(Date.now() + ttlSec * 1000).toISOString();

/** Хранилище поверх коллекции app_kv в Directus. Рабочий вариант для прода. */
export const directusStore: SharedStore = {
  async get<T>(key: string): Promise<T | null> {
    try {
      const rec = await kvGet(key);
      return rec ? (rec.value as T) : null;
    } catch (e) {
      console.error('shared-store get failed', key, e);
      return null;
    }
  },

  async set(key: string, value: unknown, ttlSec: number): Promise<void> {
    try {
      await kvPut({ key, value, expires_at: expiryIso(ttlSec) });
    } catch (e) {
      // Не смогли сохранить — потеряли кэш или один шаг счётчика.
      // Это дешевле, чем отказ клиенту, поэтому только лог.
      console.error('shared-store set failed', key, e);
    }
  },

  async incr(key: string, ttlSec: number): Promise<number | null> {
    try {
      const rec = await kvGet(key);
      const next = Number(rec?.value ?? 0) + 1;
      // Окно отсчитывается от первого запроса в нём, а не продлевается
      // каждым следующим: иначе непрерывный поток держал бы запись вечно.
      const expires = rec?.expires_at || expiryIso(ttlSec);
      await kvPut({ key, value: next, expires_at: expires });
      return next;
    } catch (e) {
      console.error('shared-store incr failed', key, e);
      return null;
    }
  },
};

/**
 * Хранилище в памяти — ТОЛЬКО для тестов и локальной разработки без Directus.
 * В проде оно неверно по построению (у каждого инстанса свой счёт), поэтому
 * подставляется исключительно явным вызовом setSharedStore.
 */
export function createMemoryStore(): SharedStore {
  const data = new Map<string, { value: unknown; expires: number }>();
  const alive = (key: string) => {
    const hit = data.get(key);
    if (!hit) return undefined;
    if (hit.expires <= Date.now()) { data.delete(key); return undefined; }
    return hit;
  };
  return {
    async get<T>(key: string): Promise<T | null> {
      return (alive(key)?.value as T) ?? null;
    },
    async set(key: string, value: unknown, ttlSec: number): Promise<void> {
      data.set(key, { value, expires: Date.now() + ttlSec * 1000 });
    },
    async incr(key: string, ttlSec: number): Promise<number | null> {
      const hit = alive(key);
      const next = Number(hit?.value ?? 0) + 1;
      data.set(key, { value: next, expires: hit?.expires ?? Date.now() + ttlSec * 1000 });
      return next;
    },
  };
}

let current: SharedStore = directusStore;

/** Хранилище, которым пользуются лимиты и кэш. */
export function sharedStore(): SharedStore {
  return current;
}

/** Подмена хранилища в тестах. В рантайме сайта не вызывается. */
export function setSharedStore(store: SharedStore): void {
  current = store;
}
