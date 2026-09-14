/**
 * Стадия лида Bitrix24 → стадия нашей воронки.
 *
 * Карта лежит данными (`data/sales/b24-stages.json`), а не в коде: коды стадий
 * задаёт владелец портала, там заводят свои (`UC_XXXXXX`), и дописывать
 * строку в реестр должен оператор, а не сессия с правкой кода.
 *
 * Неизвестная стадия соответствия не получает. Догадка здесь дороже пробела:
 * заявка, переведённая по ошибке в «отказ», уходит из отчёта, и заметят это
 * в лучшем случае через неделю. Пробел, наоборот, виден сразу — событие с
 * исходным кодом пишется в историю заявки.
 *
 * Совпадение значений карты с реальными стадиями воронки проверяет
 * tests/b24-stages.test.ts: переименование стадии в src/crm/stages.ts роняет
 * тест, а не тихо выключает обратный канал.
 */
import REGISTRY from '../../data/sales/b24-stages.json';

const MAP = REGISTRY.map as Record<string, string | null>;

/** Стадии воронки, в которые карта вообще умеет переводить. */
export function mappedStatuses(): string[] {
  return [...new Set(Object.values(MAP).filter((v): v is string => typeof v === 'string'))];
}

/**
 * @returns стадия нашей воронки; null — стадия портала неизвестна или
 * намеренно игнорируется, и заявку трогать нельзя.
 */
export function mapB24Status(statusId: string): string | null {
  const key = String(statusId || '').trim();
  if (!key) return null;
  return MAP[key] ?? null;
}
