/**
 * Зеркало заявки в Bitrix24.
 *
 * Решение руководителя 14.09.2026: источником воронки остаётся Directus —
 * по его стадиям считаются конверсия, выручка и срок сделки (`scripts/seo/leads.py`,
 * кабинет `/admin/leads`, письмо `ops-lead-source-mail`). Битрикс получает
 * копию обращения, чтобы менеджер работал в привычном окне. Обратной
 * синхронизации нет: стадия, проставленная в Битриксе, в отчёт не попадает.
 *
 * Отсюда три свойства, заложенные в код, а не в договорённость.
 *
 * 1. Вызов не может уронить заявку. Он идёт фоном, после записи в Directus,
 *    и ни одна ошибка Битрикса наружу не выходит: функция возвращает исход,
 *    а не бросает. Контакт дороже зеркала — та же логика, что в lead-write.ts.
 * 2. Адрес вебхука — это пароль: он даёт на портале права выписавшего его
 *    пользователя. Поэтому он не попадает ни в ответ клиенту, ни в лог:
 *    всё, что уходит в console, проходит через `maskWebhook`.
 * 3. Не настроен — не ошибка. Без переменной окружения зеркало молча
 *    выключено, и сайт работает ровно как до интеграции.
 *
 * Модуль живёт в src/lib, а не в src/crm: там граница (tests/crm-isolation.test.ts)
 * запрещает сетевые вызовы, и это правильно — фиксация контакта дело сайта.
 */

/** Сколько ждём портал. Заявка уже сохранена, торопиться некуда, но и висеть нельзя. */
const TIMEOUT_MS = 8000;

export interface B24LeadInput {
  /** Заголовок лида: что именно произошло — заявка с формы или скачивание КП. */
  title: string;
  /** ФИО одной строкой: в форме одно поле, разбивать его догадкой нельзя. */
  name: string;
  company: string;
  inn: string;
  email: string;
  phone?: string;
  /** Текст обращения или состав КП. */
  comments: string;
  /** Идентификатор формы (`form_source`), а не канал трафика. */
  formSource?: string;
  /** Канал перехода по метке браузера — со сроком доверия из lead-attribution.md. */
  channel?: string;
  /** Товар, с карточки которого пришло обращение. */
  productRef?: string;
  utm?: {
    utm_source?: string;
    utm_medium?: string;
    utm_campaign?: string;
    utm_content?: string;
    utm_term?: string;
  };
}

export type B24Result =
  | { status: 'created'; id: number }
  | { status: 'skipped'; reason: string }
  | { status: 'failed'; reason: string };

/**
 * Адрес вебхука из окружения, приведённый к виду `https://…/rest/<id>/<код>/`.
 *
 * Читается при каждом вызове, а не при загрузке модуля: значение приезжает
 * на сервер отдельным прогоном (`ops-b24-setup`), и перечитать его должен
 * перезапуск контейнера, а не пересборка образа.
 */
export function b24Base(): string {
  const raw = String(process.env.B24_WEBHOOK_URL || import.meta.env.B24_WEBHOOK_URL || '').trim();
  if (!raw) return '';
  return raw.endsWith('/') ? raw : `${raw}/`;
}

export function b24Configured(): boolean {
  return b24Base() !== '';
}

/**
 * Убрать код вебхука из любой строки, которая может попасть в лог.
 *
 * Маскируются оба случая: точное значение из окружения и любой адрес вида
 * `/rest/<id>/<код>/` — портал возвращает его в текстах некоторых ошибок,
 * и одного лишь сравнения с переменной там не хватит.
 */
export function maskWebhook(text: string): string {
  const base = b24Base();
  let out = text;
  if (base) out = out.split(base).join('<вебхук>');
  return out.replace(/\/rest\/\d+\/[A-Za-z0-9]+\/?/g, '/rest/***/');
}

/** Непустая строка после trim — пустые поля в портал не отправляем. */
function filled(v: unknown): v is string {
  return typeof v === 'string' && v.trim().length > 0;
}

/**
 * Поля лида для `crm.lead.add`.
 *
 * ИНН уходит в комментарий, а не в отдельное поле: в типовом лиде Битрикса
 * поля ИНН нет, а заводить пользовательское поле — решение владельца портала,
 * а не сайта. Как только поле появится, его имя добавляется здесь.
 */
export function b24LeadFields(input: B24LeadInput): Record<string, unknown> {
  const comments = [
    input.comments,
    '',
    `ИНН: ${input.inn || '—'}`,
    input.productRef ? `Товар: ${input.productRef}` : '',
    input.formSource ? `Форма: ${input.formSource}` : '',
    input.channel ? `Канал (метка браузера): ${input.channel}` : '',
    'Источник записи: сайт biz-soft.pro. Воронка ведётся в Directus.',
  ].filter((l) => l !== '').join('\n');

  const fields: Record<string, unknown> = {
    TITLE: input.title,
    NAME: input.name,
    COMPANY_TITLE: input.company,
    STATUS_ID: 'NEW',
    OPENED: 'Y',
    SOURCE_ID: 'WEB',
    COMMENTS: comments,
  };
  if (filled(input.channel)) fields.SOURCE_DESCRIPTION = input.channel;
  if (filled(input.email)) fields.EMAIL = [{ VALUE: input.email, VALUE_TYPE: 'WORK' }];
  if (filled(input.phone)) fields.PHONE = [{ VALUE: input.phone, VALUE_TYPE: 'WORK' }];
  for (const [key, value] of Object.entries(input.utm || {})) {
    if (filled(value)) fields[key.toUpperCase()] = value;
  }
  return fields;
}

/**
 * Завести лид в Битриксе. Не бросает: исход возвращается значением.
 */
export async function mirrorLeadToB24(input: B24LeadInput): Promise<B24Result> {
  const base = b24Base();
  if (!base) return { status: 'skipped', reason: 'B24_WEBHOOK_URL не задан' };

  try {
    const res = await fetch(`${base}crm.lead.add.json`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ fields: b24LeadFields(input), params: { REGISTER_SONET_EVENT: 'Y' } }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    // Портал отвечает ошибкой и с кодом 200, и с 4xx, причём тело разбирается
    // в обоих случаях: читаем его до проверки статуса, иначе причина теряется.
    const data = await res.json().catch(() => null) as
      { result?: number; error?: string; error_description?: string } | null;
    if (data && data.error) {
      return { status: 'failed', reason: maskWebhook(`${data.error}: ${data.error_description || ''}`.trim()) };
    }
    if (!res.ok) return { status: 'failed', reason: `HTTP ${res.status}` };
    if (!data || typeof data.result !== 'number') {
      return { status: 'failed', reason: 'портал не вернул номер лида' };
    }
    return { status: 'created', id: data.result };
  } catch (e) {
    return { status: 'failed', reason: maskWebhook(e instanceof Error ? e.message : String(e)) };
  }
}

/**
 * Зеркало с записью исхода в лог. Единственная форма вызова из обработчиков:
 * сбой зеркала виден в логе приложения и не виден клиенту.
 */
export async function mirrorLeadAndLog(input: B24LeadInput): Promise<B24Result> {
  const out = await mirrorLeadToB24(input);
  if (out.status === 'created') console.info(`b24: лид ${out.id} заведён`);
  else if (out.status === 'failed') console.error(`b24: лид не заведён — ${out.reason}`);
  return out;
}
