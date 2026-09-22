/**
 * Запись заявки в воронку, устойчивая к отставанию схемы прода.
 *
 * Directus отвергает запись с незнакомым полем целиком: пока на проде не
 * выполнен ops-directus-schema, новое поле экономики или источника роняет
 * всю заявку. Контакт дороже любой аналитической колонки, поэтому при отказе
 * запись повторяется без необязательных полей, а не теряется.
 *
 * Раньше этот откат жил в обработчике КП и знал только про поля экономики;
 * с полями источника (реферер, путь по сайту) их стало две группы, и общий
 * список удобнее держать в одном месте.
 */
import { createLead } from './directus';
import {
  ATTRIBUTION_EXTRA_FIELDS, LEAD_CONSENT_FIELDS, LEAD_ECONOMICS_FIELDS, LEAD_REQUEST_FIELDS,
} from './quote-lead';

const OPTIONAL_FIELDS: readonly string[] = [
  ...LEAD_ECONOMICS_FIELDS,
  ...ATTRIBUTION_EXTRA_FIELDS,
  ...LEAD_CONSENT_FIELDS,
  ...LEAD_REQUEST_FIELDS,
];

export async function createLeadTolerant(record: Record<string, unknown>): Promise<string | number | null> {
  try {
    return await createLead(record);
  } catch (e) {
    const stripped = { ...record };
    const dropped: string[] = [];
    for (const f of OPTIONAL_FIELDS) {
      if (f in stripped) { delete stripped[f]; dropped.push(f); }
    }
    // Полей не было — значит, дело не в схеме, и глушить ошибку нельзя.
    if (!dropped.length) throw e;
    console.warn(`lead: поля не приняты (${dropped.join(', ')}), повтор без них`, e);
    return await createLead(stripped);
  }
}
