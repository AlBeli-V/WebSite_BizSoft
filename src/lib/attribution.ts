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
const STEPS_KEY = 'bizsoft_attr_steps';
const TTL_DAYS = 90;

/**
 * Сколько шагов посетителя помнит браузер.
 *
 * Двенадцати хватает, чтобы увидеть путь «вход → каталог → карточка →
 * форма», и мало, чтобы раздуть тело заявки: поле уезжает в Directus и в
 * письмо, а не в аналитическое хранилище. Переполнение вытесняет самые
 * старые шаги, а не самые новые: ближе к заявке путь важнее.
 */
const MAX_STEPS = 12;

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
  /** Путь по сайту в этом браузере: «дд.мм чч:мм~/страница» через «|». */
  visit_path?: string;
}

/** Один шаг пути: когда и какая страница. */
interface Step { t: string; p: string }

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

/** Шаги пути из хранилища. Порченая запись равносильна пустому пути. */
function readSteps(): Step[] {
  try {
    const raw = localStorage.getItem(STEPS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((s): s is Step => Boolean(s && typeof s.p === 'string'));
  } catch {
    return [];
  }
}

/** «дд.мм чч:мм» по московскому времени — так же, как в письмах. */
function stamp(d: Date): string {
  return d.toLocaleString('ru-RU', {
    timeZone: 'Europe/Moscow', day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit',
  }).replace(',', '');
}

/**
 * Записать шаг пути. Ведётся на каждой странице, а не только на визите с
 * меткой: путь «вход из выдачи → сравнение → карточка → форма» и есть ответ
 * на вопрос, что клиент смотрел до заявки, а Метрика тот же путь отдаёт с
 * задержкой в часы.
 */
function recordStep(): void {
  try {
    const steps = readSteps();
    const page = location.pathname.slice(0, 120);
    const last = steps[steps.length - 1];
    // Перезагрузка страницы шагом не является: путь должен читаться как
    // маршрут, а не как журнал нажатий F5.
    if (last && last.p === page) return;
    steps.push({ t: stamp(new Date()), p: page });
    localStorage.setItem(STEPS_KEY, JSON.stringify(steps.slice(-MAX_STEPS)));
  } catch {
    // Хранилище недоступно — заявка уйдёт без пути, но уйдёт.
  }
}

/** Путь для тела заявки: «дд.мм чч:мм~/страница» через «|». */
function visitPath(): string {
  return readSteps().map((s) => `${s.t}~${s.p}`).join('|').slice(0, 1000);
}

/**
 * Зафиксировать текущий визит. Вызывается один раз при загрузке страницы.
 * Идемпотентна: повторный вызов в том же визите ничего не меняет.
 */
export function captureVisit(): void {
  if (typeof window === 'undefined') return;
  recordStep();
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
    return { first: read(FIRST_KEY), last: read(LAST_KEY), visit_path: visitPath(), ...ids };
  } catch {
    return { first: read(FIRST_KEY), last: read(LAST_KEY), visit_path: visitPath() };
  }
}
