/**
 * Что заказчик может попросить подготовить по предложению.
 *
 * Один список на три поверхности: визуальный перечень в письме, настоящие
 * чекбоксы на странице предложения и заготовка ответного письма. Список
 * живёт здесь, потому что три копии разъехались бы на первой же правке, а
 * заказчик отметил бы пункт, которого менеджер в своём письме не увидит.
 *
 * `id` уходит в аналитику и в уведомление менеджеру; человеку показывается
 * только `label`. Идентификаторы латиницей и без пробелов: они попадают в
 * параметры событий Метрики и GA4.
 */
export interface OfferAction {
  id: string;
  label: string;
}

export const OFFER_ACTIONS: readonly OfferAction[] = [
  { id: 'credentials', label: 'Отправить реквизиты BIZSoft' },
  { id: 'phone_call', label: 'Связаться со мной по телефону' },
  { id: 'security_docs', label: 'Отправить уставные документы для проверки СЭБ' },
  { id: 'invoice', label: 'Выставить счёт на оплату по КП' },
  { id: 'sample_contract', label: 'Отправить образец договора (Рамочный + ДС №1)' },
  { id: 'contract_and_invoice', label: 'Подготовить договор по КП и счёт на оплату' },
  // Приглашение в ЭДО отправляем мы: у заказчика на это уходит поход в
  // бухгалтерию, а у нас — два клика в кабинете. Инициатива на нашей стороне.
  { id: 'edo_invite', label: 'Отправить приглашение в Контур.Диадок' },
] as const;

/** Подписи выбранных действий — для письма менеджеру. */
export function actionLabels(ids: readonly string[]): string[] {
  return OFFER_ACTIONS.filter((a) => ids.includes(a.id)).map((a) => a.label);
}

/** Известные идентификаторы: всё остальное с формы отбрасывается. */
export function knownActionIds(ids: unknown): string[] {
  if (!Array.isArray(ids)) return [];
  const known = new Set(OFFER_ACTIONS.map((a) => a.id));
  return [...new Set(ids.map(String))].filter((id) => known.has(id));
}
