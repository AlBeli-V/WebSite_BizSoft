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

export function planType(name: string, extra = ''): PlanType | null {
  const s = `${name} ${extra}`.toLowerCase();
  if (/\b(teams?|business|enterprise|corporate|company|organizations?|workspace)\b|организаци|команд|корпоратив/.test(s)) return 'team';
  if (/\b(individual|personal|solo|plus)\b|индивидуальн|персональн|личн/.test(s)) return 'individual';
  return null;
}
