/**
 * Приём согласий на входе публичных форм.
 *
 * Общий шаг для /api/lead и /api/quote: разобрать поля блока согласий,
 * записать события в журнал и обновить рассылочный реестр — и только после
 * этого отдавать контакт дальше, в воронку и в Bitrix24.
 *
 * Порядок здесь и есть требование ТЗ (п. 3): сначала надёжно зафиксировать
 * доказательство, потом лид. Обратный порядок означал бы, что в работе у
 * менеджера оказывается обращение, законность обработки которого нечем
 * подтвердить, — а именно это и спрашивают при проверке.
 *
 * Что НЕ принимается от клиента ни при каких условиях: версия документа,
 * контрольный хэш, текст согласия. Всё это сервер берёт из своей
 * конфигурации — иначе доказательством было бы то, что прислал браузер.
 */
import { randomUUID } from 'node:crypto';
import { CONSENT_SOURCE_ACTIONS, CONSENT_UI, type ConsentSourceAction } from '../config/legal';
import { logFormConsents, type ConsentSubject } from './consent-log';
import { subscribe } from './marketing-registry';

export interface ConsentIntakeInput {
  body: Record<string, unknown>;
  subject: ConsentSubject;
  /** Идентификатор формы по умолчанию, если клиент его не прислал. */
  fallbackFormId: string;
  /** Зачем собираются данные — уходит в consent_scope. */
  purpose: string;
  ip?: string;
  userAgent?: string;
  leadId?: number | null;
}

export interface ConsentIntakeResult {
  personalDataEventId: string;
  marketingEventId: string | null;
  marketingStatus: 'subscribed' | 'not_requested';
  requestId: string;
}

/** Способ ввода из формы. Незнакомое значение приводится к обычному чекбоксу. */
function sourceAction(raw: unknown): ConsentSourceAction {
  const v = String(raw || 'checkbox');
  return (CONSENT_SOURCE_ACTIONS as readonly string[]).includes(v)
    ? (v as ConsentSourceAction)
    : 'checkbox';
}

/**
 * Зафиксировать согласия отправленной формы.
 *
 * Бросает исключение, если журнал не принял запись: вызывающий обязан в этом
 * случае отказать в приёме формы, а не продолжить «как-нибудь».
 */
export async function intakeFormConsents(input: ConsentIntakeInput): Promise<ConsentIntakeResult> {
  const { body } = input;
  const requestId = randomUUID();
  const marketing = body.marketing_consent === true || body.marketing_consent === '1';
  const formId = String(body.consent_form_id || input.fallbackFormId).slice(0, 120);
  const pageUrl = String(body.consent_page_url || '').slice(0, 2000);
  const action = sourceAction(body.consent_source_action);

  const { personalDataEventId, marketingEventId } = await logFormConsents({
    personalData: true,
    marketing,
    sourceAction: action,
    source: formId,
    formId,
    pageUrl,
    requestId,
    subject: input.subject,
    texts: {
      personalData: CONSENT_UI.personalData.text,
      marketing: CONSENT_UI.marketing.text,
    },
    scope: {
      purpose: input.purpose,
      channels: marketing ? ['email_service', 'email_marketing'] : ['email_service'],
      fields: ['name', 'email', 'phone', 'company', 'inn', 'message'],
    },
    ip: input.ip,
    userAgent: input.userAgent,
    leadId: input.leadId ?? null,
  });

  // В реестр адрес попадает только вместе со ссылкой на состоявшееся
  // событие MARKETING granted. Отправка формы сама по себе в рассылку не
  // подписывает — это прямой запрет дополнения к ТЗ (п. 12).
  if (marketingEventId && input.subject.email) {
    await subscribe({
      email: input.subject.email,
      consentEventId: marketingEventId,
      source: formId,
    }).catch((e) => {
      // Реестр — производная от журнала: событие уже записано, и молча
      // потерять подписку нельзя, но и отказать в приёме заявки из-за
      // рассылочной таблицы — тоже. Ошибка уходит в журнал прогона, а
      // расхождение видно в админ-разделе: событие granted есть, записи в
      // реестре нет.
      console.error('marketing registry subscribe failed', e);
    });
  }

  return {
    personalDataEventId,
    marketingEventId,
    marketingStatus: marketingEventId ? 'subscribed' : 'not_requested',
    requestId,
  };
}
