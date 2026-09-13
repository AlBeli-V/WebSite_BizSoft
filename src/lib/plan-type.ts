/**
 * Определение аудитории тарифа по названию/описанию: командный (для организаций)
 * или индивидуальный. Показываем бейдж только при уверенном совпадении,
 * чтобы не маркировать карточки неверно.
 */
export type PlanType = 'team' | 'individual';

export const PLAN_LABEL: Record<PlanType, string> = {
  team: 'Для организаций',
  individual: 'Индивидуальный',
};

/**
 * Маркер первого экрана карточки. «Для организаций» отвечает на вопрос
 * «кому можно», а покупателю на карточке нужен коммерческий тип плана:
 * от него зависит, что он покупает — пул мест на компанию или подписку
 * одного специалиста.
 */
export const PLAN_MARKER: Record<PlanType, string> = {
  team: 'Командный план',
  individual: 'Индивидуальный план',
};

/**
 * Плашка позиции, у которой деления на командный и индивидуальный нет вовсе:
 * Visual Studio Professional, Perforce Helix Core, Photon Fusion CCU и
 * подобные. Решение руководителя 13.09.2026 — не оставлять карточку без
 * первой плашки и не угадывать тип плана по названию.
 *
 * Это не то же самое, что «Универсальный продукт» у пополнений и номиналов:
 * там нет плана, здесь план есть, но он один для всех.
 */
export const PLAN_MARKER_UNIVERSAL = 'Универсальный план';

/** Значение строки «Тип плана» в параметрах: там слово «план» уже в подписи. */
export const PLAN_SHORT: Record<PlanType, string> = {
  team: 'Командный',
  individual: 'Индивидуальный',
};

/**
 * Суффикс артикула — данные, а не догадка: `-ORG` и `-IND` у плагинов
 * JetBrains, `-TEAM`/`-TEAMS` и `-INDIVIDUAL(S)` у подписок ставятся при
 * заведении позиции и означают ровно тип плана. Поэтому артикул старше
 * эвристики по названию и описанию.
 */
function planBySku(sku: string): PlanType | null {
  if (/-(ORG|TEAMS?)$/i.test(sku)) return 'team';
  if (/-(IND|INDIVIDUALS?)$/i.test(sku)) return 'individual';
  return null;
}

export function planType(name: string, extra = '', sku = ''): PlanType | null {
  const bySku = sku ? planBySku(sku) : null;
  if (bySku) return bySku;
  const s = `${name} ${extra}`.toLowerCase();
  if (/\b(teams?|business|enterprise|corporate|company|organizations?|workspace)\b|организаци|команд|корпоратив/.test(s)) return 'team';
  if (/\b(individual|personal|solo|plus)\b|индивидуальн|персональн|личн/.test(s)) return 'individual';
  return null;
}
