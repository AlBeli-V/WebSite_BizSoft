/**
 * Защита публичных форм (SEC-RL-001).
 *
 * Формы /api/lead и /api/quote стоили денег при каждом вызове: справочник
 * организаций, генерация документов, письмо с вложением на произвольный
 * адрес от имени hello@biz-soft.pro. Ограничений не было никаких.
 *
 * Здесь — второй рубеж, прикладной. Первый (limit_req по IP) стоит в nginx
 * и режет шторм ещё до Node; см. deploy/nginx-rate-limit.conf. Прикладной
 * рубеж делает то, чего nginx не умеет: отличает человека от скрипта по
 * поведению и отвечает человеческим текстом вместо страницы ошибки.
 *
 * Четыре проверки, в порядке дешевизны:
 *
 *   1. Приманка. Поле, скрытое от глаз и от клавиатуры. Человек его не
 *      видит и заполнить не может, автозаполнение форм — обходит (у поля
 *      autocomplete="off" и бессмысленное для браузера имя). Заполнено —
 *      значит форму разбирал робот. Отвечаем «принято» и молча выбрасываем:
 *      честный отказ подсказал бы автору, что приманку надо обойти.
 *   2. Отсечка по времени. Живой человек не заполнит пять полей за три
 *      секунды. Метку ставит браузер при открытии формы. Метки нет вовсе
 *      (страница из кэша, JS не отработал) — проверку не применяем: терять
 *      живую заявку из-за собственного кэша хуже, чем пропустить робота,
 *      которого дальше встретят лимиты по адресу.
 *   3. Пять заявок в час с адреса. Сколько nginx выразить не может: его
 *      limit_req знает только r/s и r/m.
 *   4. Тридцать заявок в сутки с адреса — потолок на случай медленного
 *      перебора, размазанного по часам.
 *
 * Про NAT. За одним адресом сидит целая организация, и упереться в порог
 * может человек, который ничего плохого не делал. Поэтому при превышении
 * возвращается не «ошибка», а объяснение с телефоном: заявку всё равно
 * примут, только голосом. По той же причине лимиты не блокируют адрес
 * и ничего не «банят» — окно истекает само.
 */
import { createHash } from 'node:crypto';
import { seller } from '../config/site';
import { sharedStore, type SharedStore } from './shared-store';

/** Имя поля-приманки. Правдоподобное для робота, ненужное для формы. */
export const HONEYPOT_FIELD = 'company_site';
/** Имя поля с меткой открытия формы (мс epoch, ставит браузер). */
export const OPENED_AT_FIELD = 'form_opened_at';

/** Быстрее этого форму заполняет только скрипт. */
export const MIN_FILL_MS = 3000;
/** Заявок с одного адреса в час. */
export const HOURLY_LIMIT = 5;
/** Заявок с одного адреса в сутки. */
export const DAILY_LIMIT = 30;

const HOUR_SEC = 60 * 60;
const DAY_SEC = 24 * HOUR_SEC;

/**
 * Соль для хэша адреса. Ключи лимитов лежат в базе рядом с заявками, и
 * хранить в них открытый IP незачем: для счётчика достаточно стабильного
 * псевдонима. Значение можно задать через окружение; дефолт годится —
 * хэш здесь не защищает секрет, а лишь избавляет базу от лишних
 * персональных данных.
 */
const SALT = process.env.FORM_GUARD_SALT || 'biz-soft.pro/form-guard';

const ipKey = (ip: string): string =>
  createHash('sha256').update(SALT).update(ip).digest('hex').slice(0, 16);

/**
 * Метка суток по Москве (правило проекта — всё время в МСК, UTC+3).
 * Сутки, съезжающие относительно рабочего дня, читались бы в отчётах как
 * чужие: заявка в 02:00 МСК попадала бы во вчерашний счёт.
 */
function moscowDay(now: number): string {
  return new Date(now + 3 * HOUR_SEC * 1000).toISOString().slice(0, 10);
}

/** Метка часа — в UTC: окно скользит одинаково в любом поясе. */
function hourStamp(now: number): string {
  return new Date(now).toISOString().slice(0, 13).replace(/[-T]/g, '');
}

export type GuardVerdict =
  | { ok: true }
  /** Приманка сработала: ответить успехом, но ничего не делать. */
  | { ok: false; kind: 'honeypot' }
  | { ok: false; kind: 'too_fast' }
  | { ok: false; kind: 'rate_limited'; scope: 'hour' | 'day' };

export interface GuardInput {
  body: Record<string, unknown>;
  ip: string;
  /** Хранилище счётчиков; по умолчанию — общее. Параметр нужен тестам. */
  store?: SharedStore;
  now?: number;
}

/** Ключи окон учёта для адреса. */
function keysFor(ip: string, now: number): { hour: string; day: string } {
  const id = ipKey(ip);
  // Окно общее для обеих форм: заявка и запрос КП — один и тот же поток,
  // и раздельные счётчики удвоили бы фактический порог.
  return {
    hour: `rl-forms-h-${hourStamp(now)}-${id}`,
    day: `rl-forms-d-${moscowDay(now).replace(/-/g, '')}-${id}`,
  };
}

/** Значение поля-приманки: заполнено ли оно хоть чем-то. */
function honeypotFilled(body: Record<string, unknown>): boolean {
  const v = body[HONEYPOT_FIELD];
  if (typeof v === 'string') return v.trim().length > 0;
  // Робот мог прислать что угодно, кроме пустоты и отсутствия поля.
  return v !== undefined && v !== null && v !== false && v !== '';
}

/**
 * Слишком быстрая отправка.
 *
 * Метка приходит от браузера, то есть подделывается — это не подпись, а
 * фильтр против типового скрипта, который постит форму без её открытия.
 * Мусор и метка из будущего трактуются как «не проверяли»: сломанные часы
 * на клиенте встречаются чаще, чем изобретательный робот, а за роботом
 * остаются приманка и лимиты.
 */
function tooFast(body: Record<string, unknown>, now: number): boolean {
  const raw = body[OPENED_AT_FIELD];
  const opened = Number(raw);
  if (!raw || !Number.isFinite(opened) || opened <= 0) return false;
  const elapsed = now - opened;
  if (elapsed < 0) return false;
  return elapsed < MIN_FILL_MS;
}

/**
 * Проверить обращение перед тем, как тратить на него деньги и время.
 *
 * Только проверка: счётчик увеличивает countSubmission, и делает это уже
 * после разбора полей. Порог в пять заявок в час тесный, и тратить его на
 * опечатки нельзя — человек, трижды промахнувшийся мимо формата телефона,
 * не должен остаться без формы до конца часа. Робота это не выручает: его
 * ловят приманка и отсечка по времени раньше любой валидации, а шторм
 * пустых запросов срезает nginx.
 */
export async function guardSubmission(input: GuardInput): Promise<GuardVerdict> {
  const { body, ip } = input;
  const now = input.now ?? Date.now();
  const store = input.store ?? sharedStore();

  if (honeypotFilled(body)) return { ok: false, kind: 'honeypot' };
  if (tooFast(body, now)) return { ok: false, kind: 'too_fast' };

  // Адрес не определён — за этим стоит неверно настроенный прокси, а не
  // злоупотребление. Считать нечего, отказывать не за что.
  if (!ip) return { ok: true };

  const keys = keysFor(ip, now);
  // Сбой хранилища читается как «счёта нет»: порог применить не к чему,
  // пропускаем и полагаемся на nginx. Отказ живому человеку из-за сбоя
  // нашей базы — худший из возможных исходов.
  const read = (key: string) => store.get<number>(key).catch(() => null);
  const [hourly, daily] = await Promise.all([read(keys.hour), read(keys.day)]);

  if (Number(daily ?? 0) >= DAILY_LIMIT) return { ok: false, kind: 'rate_limited', scope: 'day' };
  if (Number(hourly ?? 0) >= HOURLY_LIMIT) return { ok: false, kind: 'rate_limited', scope: 'hour' };

  return { ok: true };
}

/**
 * Засчитать принятое обращение в оба окна.
 *
 * Вызывается, когда форма разобрана и признана заявкой: порог тратят
 * заявки, а не попытки их отправить.
 */
export async function countSubmission(
  ip: string,
  opts: { store?: SharedStore; now?: number } = {},
): Promise<void> {
  if (!ip) return;
  const store = opts.store ?? sharedStore();
  const keys = keysFor(ip, opts.now ?? Date.now());
  await Promise.all([
    store.incr(keys.hour, HOUR_SEC).catch(() => null),
    store.incr(keys.day, DAY_SEC).catch(() => null),
  ]);
}

const CALL_US = `Если нужно срочно — позвоните: ${seller.phone}.`;

/** Тексты отказов. Человек за корпоративным NAT должен понять, что делать. */
export const GUARD_MESSAGES = {
  too_fast:
    'Форма отправлена слишком быстро — так отправляют роботы. '
    + `Проверьте поля и попробуйте ещё раз. ${CALL_US}`,
  hour:
    'С вашего адреса уже пришло несколько заявок подряд. Приём с него '
    + 'откроется в течение часа — если заявку отправляли не вы, просто '
    + `подождите. ${CALL_US}`,
  day:
    'С вашего адреса за сутки пришло слишком много заявок. Если вы в '
    + 'офисной сети, порог мог израсходовать кто-то из коллег. Приём '
    + `откроется завтра. ${CALL_US}`,
} as const;

/**
 * Ответ на отклонённое обращение.
 *
 * Приманка отвечает успехом: автор скрипта не должен понять, на чём его
 * поймали, иначе следующая версия обойдёт проверку. Для человека этот
 * ответ недостижим — поле ему не показывают.
 */
export function guardResponse(verdict: GuardVerdict): Response {
  const json = (body: unknown, status: number, headers: Record<string, string> = {}) =>
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json', ...headers },
    });

  if (verdict.ok) throw new Error('guardResponse вызван для пропущенного обращения');

  if (verdict.kind === 'honeypot') return json({ ok: true }, 200);
  if (verdict.kind === 'too_fast') return json({ error: GUARD_MESSAGES.too_fast }, 422);

  const retryAfter = verdict.scope === 'day' ? DAY_SEC : HOUR_SEC;
  return json({ error: GUARD_MESSAGES[verdict.scope] }, 429, {
    'Retry-After': String(retryAfter),
  });
}
