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

import { patchLead } from './directus';

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

export type B24Call<T> = { ok: true; result: T } | { ok: false; reason: string };

/**
 * Вызов метода REST. Не бросает: и сетевой сбой, и отказ портала возвращаются
 * значением с уже промаскированной причиной.
 */
export async function b24Call<T>(method: string, payload: Record<string, unknown>): Promise<B24Call<T>> {
  const base = b24Base();
  if (!base) return { ok: false, reason: 'B24_WEBHOOK_URL не задан' };
  try {
    const res = await fetch(`${base}${method}.json`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    // Портал отвечает ошибкой и с кодом 200, и с 4xx, причём тело разбирается
    // в обоих случаях: читаем его до проверки статуса, иначе причина теряется.
    const data = await res.json().catch(() => null) as
      { result?: T; error?: string; error_description?: string } | null;
    if (data && data.error) {
      return { ok: false, reason: maskWebhook(`${data.error}: ${data.error_description || ''}`.trim()) };
    }
    if (!res.ok) return { ok: false, reason: `HTTP ${res.status}` };
    if (!data || data.result === undefined) return { ok: false, reason: `${method}: портал не вернул результата` };
    return { ok: true, result: data.result };
  } catch (e) {
    return { ok: false, reason: maskWebhook(e instanceof Error ? e.message : String(e)) };
  }
}

/**
 * Завести лид в Битриксе. Не бросает: исход возвращается значением.
 */
export async function mirrorLeadToB24(input: B24LeadInput): Promise<B24Result> {
  if (!b24Configured()) return { status: 'skipped', reason: 'B24_WEBHOOK_URL не задан' };
  const out = await b24Call<number>('crm.lead.add', {
    fields: b24LeadFields(input),
    params: { REGISTER_SONET_EVENT: 'Y' },
  });
  if (!out.ok) return { status: 'failed', reason: out.reason };
  if (typeof out.result !== 'number') return { status: 'failed', reason: 'портал не вернул номер лида' };
  return { status: 'created', id: out.result };
}

/** Стадия и сумма лида в портале — то, ради чего обратный канал существует. */
export interface B24LeadState {
  statusId: string;
  /** Сумма лида в портале; 0 и пусто приводятся к null — это «не заполнено». */
  opportunity: number | null;
  title: string;
}

export async function b24GetLead(id: number | string): Promise<B24Call<B24LeadState>> {
  const out = await b24Call<Record<string, unknown>>('crm.lead.get', { id });
  if (!out.ok) return out;
  const r = out.result || {};
  const sum = Number(r.OPPORTUNITY);
  return {
    ok: true,
    result: {
      statusId: String(r.STATUS_ID || ''),
      opportunity: Number.isFinite(sum) && sum > 0 ? sum : null,
      title: String(r.TITLE || ''),
    },
  };
}

/**
 * Пароль исходящего вебхука: портал присылает его в каждом событии, и это
 * единственное, чем событие отличается от подделки — адрес приёмника публичен.
 */
export function b24AppToken(): string {
  return String(process.env.B24_APP_TOKEN || import.meta.env.B24_APP_TOKEN || '').trim();
}

/**
 * Зеркало с записью исхода в лог. Сбой зеркала виден в логе приложения и не
 * виден клиенту.
 */
export async function mirrorLeadAndLog(input: B24LeadInput): Promise<B24Result> {
  const out = await mirrorLeadToB24(input);
  if (out.status === 'created') console.info(`b24: лид ${out.id} заведён`);
  else if (out.status === 'failed') console.error(`b24: лид не заведён — ${out.reason}`);
  return out;
}

/**
 * Зеркало плюс запись связи «заявка ↔ лид портала». Единственная форма вызова
 * из обработчиков форм.
 *
 * Без этой связи обратный канал (`/api/b24/hook`) не знает, к какой заявке
 * относится событие портала, и стадия не возвращается. Незаписанная связь —
 * не повод считать зеркало несостоявшимся: лид в портале уже есть, и заявку
 * это не касается вовсе.
 */
export async function mirrorLeadAndLink(
  directusId: string | number | null | undefined,
  input: B24LeadInput,
): Promise<B24Result> {
  const out = await mirrorLeadAndLog(input);
  if (out.status !== 'created' || directusId === null || directusId === undefined) return out;
  try {
    await patchLead(directusId, { b24_lead_id: out.id });
  } catch (e) {
    console.error(`b24: связь заявки ${directusId} с лидом ${out.id} не записана`, e);
  }
  return out;
}
