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

/**
 * Запасной счёт в памяти процесса — на время недоступности общего хранилища.
 *
 * В нормальной работе счётчик обязан быть общим: у процесса свой отдельный
 * счёт означает, что при двух контейнерах порог удваивается. Но выбор в
 * момент сбоя стоит не между «точно» и «неточно», а между «неточно» и
 * «никак»: без запасного счёта отсутствие коллекции app_kv или падение базы
 * молча превращают защиту форм в её отсутствие, и об этом никто не узнает,
 * пока не придёт счёт от справочника.
 *
 * Пороги те же. Потолок при этом получается мягче настоящего ровно во
 * столько раз, сколько запущено инстансов (сейчас один) — но это потолок,
 * а не его отсутствие. Записи живут до конца своего окна и не переживают
 * рестарт: восстановившееся хранилище сразу возвращает точный счёт.
 */
const fallbackCounters = new Map<string, { count: number; expires: number }>();

function fallbackPrune(now: number): void {
  for (const [key, rec] of fallbackCounters) {
    if (rec.expires <= now) fallbackCounters.delete(key);
  }
}

function fallbackRead(key: string, now: number): number {
  const rec = fallbackCounters.get(key);
  return rec && rec.expires > now ? rec.count : 0;
}

function fallbackIncr(key: string, ttlSec: number, now: number): void {
  const rec = fallbackCounters.get(key);
  if (rec && rec.expires > now) rec.count += 1;
  else fallbackCounters.set(key, { count: 1, expires: now + ttlSec * 1000 });
  // Ключей немного (два на адрес в окне), но при переборе адресов карта
  // растёт — подчищаем просроченное, а не ждём рестарта.
  if (fallbackCounters.size > 5000) fallbackPrune(now);
}

/**
 * Переход в запасной режим и обратно — в лог, явно и разборчиво.
 *
 * Без этого недоступность хранилища видна только по строкам «shared-store
 * … failed», которые читаются как единичная ошибка записи, а не как
 * «пороги форм сейчас держатся на запасном счёте». Повтор — не чаще раза в
 * минуту: при сбое сообщение иначе идёт на каждую заявку и топит лог.
 */
const DEGRADED_LOG_EVERY_MS = 60_000;
let degradedSince = 0;
let degradedLoggedAt = 0;

function noteDegraded(now: number): void {
  if (!degradedSince) {
    degradedSince = now;
    degradedLoggedAt = now;
    console.error(
      'form-guard: общее хранилище лимитов недоступно (коллекция app_kv или '
      + 'сама база). Пороги форм держатся на запасном счёте в памяти процесса; '
      + 'при нескольких инстансах фактический потолок выше настроенного.',
    );
    return;
  }
  if (now - degradedLoggedAt < DEGRADED_LOG_EVERY_MS) return;
  degradedLoggedAt = now;
  console.error(
    `form-guard: хранилище лимитов недоступно уже ${Math.round((now - degradedSince) / 60000)} мин, `
    + 'счёт по-прежнему запасной.',
  );
}

function noteRecovered(): void {
  if (!degradedSince) return;
  degradedSince = 0;
  degradedLoggedAt = 0;
  fallbackCounters.clear();
  console.log('form-guard: хранилище лимитов снова доступно, счёт снова общий.');
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
  const read = (key: string) => store.get<number>(key).catch(() => null);
  const [sharedHour, sharedDay] = await Promise.all([read(keys.hour), read(keys.day)]);

  // Хранилище не ответило — считаем по запасному счёту и говорим об этом в
  // лог. Прежде здесь стоял простой пропуск: недоступность базы бесшумно
  // снимала оба порога, и заметить это было можно только по расходу
  // справочника.
  const degraded = !store.available();
  if (degraded) noteDegraded(now); else noteRecovered();

  const hourly = degraded ? fallbackRead(keys.hour, now) : Number(sharedHour ?? 0);
  const daily = degraded ? fallbackRead(keys.day, now) : Number(sharedDay ?? 0);

  if (daily >= DAILY_LIMIT) return { ok: false, kind: 'rate_limited', scope: 'day' };
  if (hourly >= HOURLY_LIMIT) return { ok: false, kind: 'rate_limited', scope: 'hour' };

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
  const now = opts.now ?? Date.now();
  const keys = keysFor(ip, now);
  await Promise.all([
    store.incr(keys.hour, HOUR_SEC).catch(() => null),
    store.incr(keys.day, DAY_SEC).catch(() => null),
  ]);
  // Не записалось в общее — записываем в запасное, иначе в запасном счёте
  // окажется ноль ровно тогда, когда он единственный.
  if (!store.available()) {
    fallbackIncr(keys.hour, HOUR_SEC, now);
    fallbackIncr(keys.day, DAY_SEC, now);
  }
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
