/**
 * Рассылочный реестр: кому сейчас можно слать рекламное письмо.
 *
 * Разделение с журналом согласий принципиально. Журнал отвечает на вопрос
 * «что было и чем это подтверждается» и не меняется никогда. Реестр отвечает
 * на вопрос «можно ли слать письмо прямо сейчас» и меняется при каждой
 * подписке и отписке.
 *
 * Три запрета, которые здесь закреплены кодом:
 *
 *  • аудитория рассылки — только `status = subscribed` И непустой
 *    `consent_event_id`. Адрес без ссылки на событие согласия в выгрузку не
 *    попадает, даже если статус почему-то оказался подписным;
 *  • адрес после отзыва из реестра не удаляется. Удалённый адрес — это
 *    адрес, которого «нет в списке отписавшихся», и следующая загрузка
 *    контактов подпишет человека заново (ТЗ 16.09.2026, п. 4);
 *  • повторная подписка возможна только новым событием granted. Функция
 *    подписки требует идентификатор события и без него ничего не меняет.
 */
import {
  createMarketingEntry,
  findMarketingEntry,
  patchMarketingEntry,
  queryMarketingRegistry,
  type MarketingRegistryRow,
} from './directus';
import { normalizeEmail, subjectIdFor } from './consent-log';
import type { MarketingStatus } from '../config/legal';

export type { MarketingRegistryRow };

/** Статусы, при которых рекламное письмо отправлять нельзя. */
export const SUPPRESSED_STATUSES: readonly MarketingStatus[] = ['unsubscribed', 'suppressed', 'bounced'];

/**
 * Подписать адрес по состоявшемуся событию MARKETING granted.
 *
 * `consentEventId` обязателен: подписка без ссылки на доказательство — это и
 * есть тот случай, из-за которого рассылка становится нарушением.
 */
export async function subscribe(args: {
  email: string;
  consentEventId: string;
  source: string;
  /**
   * Снять блокировку вместе с подпиской. Доступно только владельцу из
   * админ-раздела и только после проверки, что событие granted существует
   * и относится к этому адресу: жалоба и hard bounce не должны сниматься
   * галочкой в форме.
   */
  allowBlocked?: boolean;
}): Promise<void> {
  const email = normalizeEmail(args.email);
  if (!email || !args.consentEventId) {
    throw new Error('подписка без адреса или без события согласия невозможна');
  }
  const now = new Date().toISOString();
  const existing = await findMarketingEntry(email);

  if (!existing) {
    await createMarketingEntry({
      subject_id: subjectIdFor(email),
      email_normalized: email,
      status: 'subscribed',
      consent_event_id: args.consentEventId,
      subscribed_at: now,
      source: args.source.slice(0, 120),
    });
    return;
  }

  // Жалоба и hard bounce — это не «пока отписан». Их снимает человек в
  // админ-разделе, а не новая галочка в форме: адрес, помеченный как
  // suppressed, мог попасть туда по решению площадки или по требованию
  // самого получателя, и молча вернуть его в рассылку нельзя.
  if (!args.allowBlocked && (existing.status === 'suppressed' || existing.status === 'bounced')) return;

  await patchMarketingEntry(existing.id!, {
    status: 'subscribed',
    consent_event_id: args.consentEventId,
    subscribed_at: now,
    unsubscribed_at: null,
    unsubscribe_reason: null,
    source: args.source.slice(0, 120),
  });
}

/**
 * Снять разрешение на рассылку. Запись остаётся — меняется только статус.
 *
 * Идемпотентна: повторный переход по ссылке отписки из старого письма не
 * должен ни падать, ни создавать вторую запись.
 */
export async function unsubscribe(args: {
  email: string;
  reason: string;
  status?: Extract<MarketingStatus, 'unsubscribed' | 'suppressed' | 'bounced'>;
}): Promise<{ changed: boolean }> {
  const email = normalizeEmail(args.email);
  if (!email) throw new Error('отписка без адреса невозможна');
  const status = args.status || 'unsubscribed';
  const now = new Date().toISOString();
  const existing = await findMarketingEntry(email);

  if (!existing) {
    // Адрес, которого в реестре не было, всё равно заводится записью:
    // отписка «впрок» — это тоже волеизъявление, и следующая попытка
    // подписать его должна упереться в существующий статус.
    await createMarketingEntry({
      subject_id: subjectIdFor(email),
      email_normalized: email,
      status,
      subscribed_at: null,
      unsubscribed_at: now,
      unsubscribe_reason: args.reason.slice(0, 120),
      source: 'unsubscribe',
    });
    return { changed: true };
  }

  if (existing.status === status) return { changed: false };

  await patchMarketingEntry(existing.id!, {
    status,
    unsubscribed_at: now,
    unsubscribe_reason: args.reason.slice(0, 120),
  });
  return { changed: true };
}

/** Можно ли слать рекламное письмо на этот адрес прямо сейчас. */
export function isMailable(row: MarketingRegistryRow | null | undefined): boolean {
  if (!row) return false;
  return row.status === 'subscribed' && Boolean(row.consent_event_id);
}

export async function marketingStatusOf(email: string): Promise<MarketingStatus | 'unknown'> {
  const row = await findMarketingEntry(normalizeEmail(email));
  return (row?.status as MarketingStatus) || 'unknown';
}

/**
 * Разрешённая аудитория рассылки.
 *
 * Единственная точка, из которой формируется список получателей. Выборка
 * идёт по реестру и ещё раз просеивается `isMailable`: фильтр на стороне
 * Directus — удобство, а не гарантия, и полагаться на него одного в вопросе,
 * где ошибка стоит штрафа ФАС, нельзя.
 *
 * Контакты Bitrix24 сюда не попадают ни при каких условиях: в портале нет
 * `consent_event_id`, а значит, нет и доказательства согласия.
 */
export async function allowedAudience(limit = 5000): Promise<MarketingRegistryRow[]> {
  const rows = await queryMarketingRegistry({ 'filter[status][_eq]': 'subscribed' }, limit);
  const seen = new Set<string>();
  return rows.filter((r) => {
    if (!isMailable(r)) return false;
    // Дедупликация перед передачей провайдеру (HELP администратора, п. 6).
    if (seen.has(r.email_normalized)) return false;
    seen.add(r.email_normalized);
    return true;
  });
}
