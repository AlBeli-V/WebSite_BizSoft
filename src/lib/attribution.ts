/**
 * Источник обращения: first-touch и last-touch.
 *
 * До этого модуля разметки не было вовсе — ни utm_*, ни yclid, ни gclid не
 * читались нигде в проекте, а поле `source` заявки хранило идентификатор формы
 * («pricing», «question», «quote»), а не канал. Связать заявку с каналом было
 * невозможно ни в одну сторону: в аналитике нет события заявки, в CRM нет
 * источника визита. Любой платный тест означал бы расход, который нечем
 * оценить.
 *
 * Две записи ведутся одновременно и не затирают друг друга:
 *
 *   first — первое касание. Пишется один раз и живёт 90 дней. Отвечает на
 *           вопрос «откуда клиент узнал о нас», а его в B2B-цикле длиной в
 *           недели переписывать нельзя.
 *   last  — последнее касание. Обновляется при каждом визите с непустым
 *           источником. Отвечает на вопрос «что привело к заявке сейчас».
 *
 * Прямой заход источником не считается: отсутствие метки и реферера — это
 * отсутствие сведений, а не канал «direct». Поэтому пустое касание никогда не
 * перезаписывает непустое, иначе последний источник у половины заявок
 * оказался бы стёрт возвратом по закладке.
 */

import { METRIKA_ID, GA_ID } from './analytics';

const FIRST_KEY = 'bizsoft_attr_first';
const LAST_KEY = 'bizsoft_attr_last';
const TTL_DAYS = 90;

const UTM_FIELDS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'] as const;
const CLICK_IDS = ['yclid', 'gclid', 'ysclid', 'fbclid'] as const;

export interface Touch {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_content?: string;
  utm_term?: string;
  yclid?: string;
  gclid?: string;
  ysclid?: string;
  fbclid?: string;
  referrer?: string;
  landing_path?: string;
  ts?: string;
}

export interface Attribution {
  first: Touch | null;
  last: Touch | null;
  ym_client_id?: string;
  ga_client_id?: string;
}

/** Есть ли в касании хоть один признак источника. */
function isMeaningful(t: Touch): boolean {
  if (UTM_FIELDS.some((f) => t[f])) return true;
  if (CLICK_IDS.some((f) => t[f])) return true;
  // Реферер с собственного домена источником не является: это переход внутри
  // сайта, а не приход извне.
  return Boolean(t.referrer);
}

/** Касание из текущего URL и реферера. */
export function currentTouch(): Touch {
  const t: Touch = {};
  try {
    const q = new URLSearchParams(location.search);
    for (const f of UTM_FIELDS) {
      const v = q.get(f);
      if (v) t[f] = v.slice(0, 200);
    }
    for (const f of CLICK_IDS) {
      const v = q.get(f);
      if (v) t[f] = v.slice(0, 200);
    }
    const ref = document.referrer;
    if (ref && !ref.includes(location.host)) t.referrer = ref.slice(0, 300);
    t.landing_path = location.pathname.slice(0, 300);
    t.ts = new Date().toISOString();
  } catch {
    // Приватный режим или запрет на доступ к location — атрибуция не должна
    // ломать страницу.
  }
  return t;
}

function read(key: string): Touch | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Touch;
    if (parsed.ts && Date.now() - Date.parse(parsed.ts) > TTL_DAYS * 864e5) return null;
    return parsed;
  } catch {
    return null;
  }
}

function write(key: string, value: Touch): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Хранилище недоступно — заявка уйдёт без атрибуции, но уйдёт.
  }
}

/**
 * Зафиксировать текущий визит. Вызывается один раз при загрузке страницы.
 * Идемпотентна: повторный вызов в том же визите ничего не меняет.
 */
export function captureVisit(): void {
  if (typeof window === 'undefined') return;
  const touch = currentTouch();
  if (!isMeaningful(touch)) return;
  if (!read(FIRST_KEY)) write(FIRST_KEY, touch);
  write(LAST_KEY, touch);
}

/** Идентификатор посетителя в счётчике — ключ к обратной сверке «заявка ↔ визит». */
function clientIds(): Promise<Pick<Attribution, 'ym_client_id' | 'ga_client_id'>> {
  const w = window as unknown as {
    ym?: (id: number, action: string, cb: (v: string) => void) => void;
    gtag?: (cmd: string, target: string, field: string, cb: (v: string) => void) => void;
  };
  const out: Pick<Attribution, 'ym_client_id' | 'ga_client_id'> = {};
  const wait = <T>(fn: (done: () => void) => void): Promise<void> =>
    new Promise((resolve) => {
      let settled = false;
      const done = () => {
        if (!settled) {
          settled = true;
          resolve();
        }
      };
      // Счётчик может не ответить (блокировщик, не загрузился) — не держим
      // отправку формы дольше 400 мс.
      setTimeout(done, 400);
      try {
        fn(done);
      } catch {
        done();
      }
    });

  return Promise.all([
    wait((done) => {
      if (typeof w.ym !== 'function') return done();
      w.ym(Number(METRIKA_ID), 'getClientID', (v) => {
        out.ym_client_id = v;
        done();
      });
    }),
    wait((done) => {
      if (typeof w.gtag !== 'function') return done();
      w.gtag('get', GA_ID, 'client_id', (v) => {
        out.ga_client_id = v;
        done();
      });
    }),
  ]).then(() => out);
}

/**
 * Блок атрибуции для тела заявки. Никогда не бросает: заявка важнее источника.
 */
export async function attributionPayload(): Promise<Attribution> {
  if (typeof window === 'undefined') return { first: null, last: null };
  try {
    const ids = await clientIds();
    return { first: read(FIRST_KEY), last: read(LAST_KEY), ...ids };
  } catch {
    return { first: read(FIRST_KEY), last: read(LAST_KEY) };
  }
}
