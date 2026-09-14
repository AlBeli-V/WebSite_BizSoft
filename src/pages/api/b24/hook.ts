export const prerender = false;

/**
 * Обратный канал Bitrix24 → Directus: стадия заявки.
 *
 * Решение руководителя 14.09.2026. Зеркало (`src/lib/bitrix24.ts`) отдаёт
 * заявку в портал, а этот приёмник возвращает оттуда единственную вещь —
 * стадию. Источником воронки Directus при этом остаётся: по его стадиям
 * считают конверсию, выручку и срок сделки, и обратный канал существует
 * ровно для того, чтобы менеджеру не приходилось проставлять стадию дважды.
 *
 * Что принимается и что нет:
 *  — только `ONCRMLEADUPDATE`. Лид, заведённый в портале руками, нашей
 *    заявкой не является: связи с Directus у него нет, и выдумывать её
 *    нельзя. Остальные события — штатный пропуск, а не ошибка.
 *  — только стадия и (если у нас пусто) сумма. Контакты, текст обращения и
 *    источник из портала не принимаются: это история заявки, и она не
 *    меняется задним числом — то же правило, что в кабинете.
 *  — только известные стадии портала (`data/sales/b24-stages.json`).
 *    Неизвестный код заявку не трогает, а пишется событием в её историю.
 *
 * Петли нет по устройству: приёмник в портал ничего не пишет, а наш
 * `crm.lead.add` поднимает `ONCRMLEADADD`, которое здесь пропускается.
 *
 * Адрес приёмника публичен (портал ходит по нему снаружи), поэтому
 * единственное, чем событие отличается от подделки, — `application_token`
 * из настроек исходящего вебхука. Он сверяется до любого обращения к базе.
 */
import type { APIRoute } from 'astro';
import { b24AppToken, b24GetLead } from '../../../lib/bitrix24';
import { mapB24Status } from '../../../lib/b24-stages';
import { stageDatePatch } from '../../../lib/lead-stage';
import { findLeadByB24Id, patchLead, createLeadEvent } from '../../../lib/directus';

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });

/**
 * Сравнение пароля за постоянное время: длина ответа не должна зависеть от
 * того, сколько символов угадано.
 */
function sameToken(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

/**
 * Тело события. Портал шлёт форму (`application/x-www-form-urlencoded`) с
 * ключами вида `data[FIELDS][ID]`; JSON принимается на случай ручной проверки
 * прогоном, чтобы не собирать форму руками.
 */
async function readBody(request: Request): Promise<Record<string, string>> {
  const type = request.headers.get('content-type') || '';
  if (type.includes('application/json')) {
    const raw = await request.json().catch(() => ({}));
    const out: Record<string, string> = {};
    const walk = (value: unknown, path: string) => {
      if (value && typeof value === 'object') {
        for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
          walk(v, path ? `${path}[${k}]` : k);
        }
      } else if (value !== undefined && value !== null) {
        out[path] = String(value);
      }
    };
    walk(raw, '');
    return out;
  }
  const form = await request.formData().catch(() => null);
  const out: Record<string, string> = {};
  if (form) for (const [k, v] of form.entries()) out[k] = String(v);
  return out;
}

export const POST: APIRoute = async ({ request }) => {
  const expected = b24AppToken();
  if (!expected) {
    // Не настроен — не притворяемся работающим: молчаливый 200 здесь означал бы,
    // что события приняты и учтены, а их никто не читал.
    console.error('b24 hook: B24_APP_TOKEN не задан, событие не принято');
    return json({ ok: false, error: 'обратный канал не настроен' }, 503);
  }

  const body = await readBody(request);
  if (!sameToken(String(body['auth[application_token]'] || ''), expected)) {
    console.warn('b24 hook: событие с неверным application_token отклонено');
    return json({ ok: false, error: 'forbidden' }, 403);
  }

  const event = String(body.event || '').toUpperCase();
  if (event !== 'ONCRMLEADUPDATE') return json({ ok: true, skipped: `событие ${event || '—'} не обрабатывается` });

  const b24Id = String(body['data[FIELDS][ID]'] || '').trim();
  if (!b24Id) return json({ ok: true, skipped: 'в событии нет номера лида' });

  // Событие приносит только номер: стадию и сумму читаем у портала сами —
  // так в заявку не попадёт состояние, устаревшее к моменту доставки.
  const state = await b24GetLead(b24Id);
  if (!state.ok) {
    console.error(`b24 hook: лид ${b24Id} не прочитан — ${state.reason}`);
    return json({ ok: false, error: 'портал не отдал лид' }, 502);
  }

  let lead;
  try {
    lead = await findLeadByB24Id(b24Id);
  } catch (e) {
    console.error(`b24 hook: поиск заявки по лиду ${b24Id} не удался`, e);
    return json({ ok: false, error: 'база недоступна' }, 502);
  }
  if (!lead) {
    // Лид портала, заведённый не нами: связи нет, и сопоставлять его с заявкой
    // по почте или названию — та самая догадка, от которой отчёт потом врёт.
    console.info(`b24 hook: лид ${b24Id} нашей заявке не соответствует, пропуск`);
    return json({ ok: true, skipped: 'заявки с таким лидом нет' });
  }

  const next = mapB24Status(state.result.statusId);
  if (!next) {
    await createLeadEvent({
      lead: Number(lead.id),
      kind: 'stage',
      subject: `Bitrix24: стадия «${state.result.statusId}» не описана в карте`,
      text: 'Заявка не изменена. Добавьте код стадии в data/sales/b24-stages.json, чтобы обратный канал её понимал.',
      author: 'Bitrix24',
    }).catch((e) => console.error('b24 hook: событие истории не записано', e));
    return json({ ok: true, skipped: `стадия ${state.result.statusId} не описана` });
  }

  const prev = String(lead.status || 'new');
  const patch: Record<string, unknown> = {};
  if (next !== prev) patch.status = next;
  // Сумму портала берём только в пустое поле: цифра, введённая менеджером у
  // нас, старше и точнее — она попала в счёт.
  if (state.result.opportunity && !lead.amount) patch.amount = state.result.opportunity;
  if (!Object.keys(patch).length) return json({ ok: true, skipped: 'изменений нет' });

  Object.assign(patch, stageDatePatch(
    typeof patch.status === 'string' ? patch.status : undefined,
    lead,
    new Date().toISOString(),
  ));

  try {
    await patchLead(lead.id, patch);
  } catch (e) {
    console.error(`b24 hook: заявка ${lead.id} не обновлена`, e);
    return json({ ok: false, error: 'не удалось сохранить стадию' }, 502);
  }

  if (patch.status) {
    await createLeadEvent({
      lead: Number(lead.id),
      kind: 'stage',
      subject: `Стадия: ${prev} → ${patch.status}`,
      text: `Изменено в Bitrix24 (лид ${b24Id}, стадия портала ${state.result.statusId}).`,
      author: 'Bitrix24',
    }).catch((e) => console.error('b24 hook: событие истории не записано', e));
  }

  return json({ ok: true, lead: lead.id, patch });
};

/**
 * Портал проверяет адрес обычным запросом при сохранении исходящего вебхука.
 * Отвечаем коротко и без подробностей: что здесь стоит, посторонним знать
 * незачем.
 */
export const GET: APIRoute = async () => json({ ok: true }, 200);
