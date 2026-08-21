/**
 * Единая точка отправки целей в Яндекс.Метрику и события в GA4.
 *
 * Раньше вызов был скопирован в десять мест, и идентификатор счётчика в
 * каждом читался напрямую из import.meta.env.PUBLIC_METRIKA_ID. В пяти
 * копиях к нему дописали фолбэк, в пяти забыли — а поскольку PUBLIC_*
 * не доходят до сборки (BLD-002), в этих пяти выражение схлопывалось в
 * `void 0`, условие становилось заведомо ложным и минификатор удалял
 * вызов цели целиком. Из отчётов пропадали ровно конверсии: заявки,
 * добавления в подборку и скачивания КП.
 *
 * Поэтому идентификаторы живут здесь и всегда имеют непустое значение:
 * даже при незаданной переменной окружения код остаётся достижимым.
 */

/** Счётчик Яндекс.Метрики biz-soft.pro. */
export const METRIKA_ID = import.meta.env.PUBLIC_METRIKA_ID || '110206070';
/** Поток Google Analytics 4 biz-soft.pro. */
export const GA_ID = import.meta.env.PUBLIC_GA_ID || 'G-V9BK2D1431';

/**
 * Реестр целей: одно имя в коде, своё имя в каждой системе.
 *
 * Метрика принимает произвольные имена, GA4 — тоже, но у него есть
 * рекомендованные: под них он сам строит отчёты по воронке покупки и
 * поиску. Поэтому в GA4 уходит стандартное имя там, где оно существует,
 * а в Метрику — наше. Событие в коде при этом одно: два реестра целей
 * разъехались бы при первой же правке, и системы перестали бы сходиться.
 *
 * key — считается конверсией: такие цели размечаются ключевыми в GA4 и
 * идут в отчёт как обращения. Остальные показывают намерение и нужны,
 * чтобы видеть, на каком шаге теряем.
 */
export interface GoalSpec {
  /** Имя в GA4. Стандартное, если такое есть. */
  ga4: string;
  /** Конверсия (ключевое событие), а не сигнал намерения. */
  key: boolean;
  /** Что означает — для реестра целей и отчётов. */
  meaning: string;
}

export const GOALS: Record<string, GoalSpec> = {
  // ── Конверсии: клиент назвал себя ───────────────────────────────────
  lead_sent: { ga4: 'generate_lead', key: true,
    meaning: 'Отправлена заявка с формы' },
  quote_pdf: { ga4: 'generate_lead', key: true,
    meaning: 'Скачано коммерческое предложение — назвали организацию и ИНН' },
  click_phone: { ga4: 'contact', key: true,
    meaning: 'Клик по телефону' },
  click_email: { ga4: 'contact', key: true,
    meaning: 'Клик по адресу почты' },
  click_messenger: { ga4: 'contact', key: true,
    meaning: 'Переход в мессенджер' },

  // ── Намерение: до контакта, но уже не просто просмотр ───────────────
  add_to_cart: { ga4: 'add_to_cart', key: false,
    meaning: 'Товар добавлен в подборку' },
  remove_from_cart: { ga4: 'remove_from_cart', key: false,
    meaning: 'Товар убран из подборки' },
  view_cart: { ga4: 'view_cart', key: false,
    meaning: 'Открыта подборка' },
  begin_checkout: { ga4: 'begin_checkout', key: false,
    meaning: 'Начато заполнение формы КП' },
  form_start: { ga4: 'form_start', key: false,
    meaning: 'Начато заполнение формы заявки' },

  // Реквизиты подставлены из справочника, а не введены руками. Показывает,
  // пользуются ли подсказками: если нет — поле или подсказка не работают.
  company_autofill: { ga4: 'form_autofill', key: false,
    meaning: 'Организация выбрана из справочника, реквизиты подставлены' },

  // ── Интерес: что смотрят ────────────────────────────────────────────
  view_product: { ga4: 'view_item', key: false,
    meaning: 'Открыта карточка товара' },
  view_vendor_landing: { ga4: 'view_item_list', key: false,
    meaning: 'Открыт лендинг производителя' },
  view_solution: { ga4: 'view_item_list', key: false,
    meaning: 'Открыта страница назначения ПО' },

  // ── Спрос, которого у нас нет ───────────────────────────────────────
  // Поиск по каталогу — единственный канал, где посетитель прямо называет,
  // что ему нужно. Пустая выдача по запросу дороже любого замера частотности:
  // это спрос, пришедший к нам и ушедший ни с чем.
  search_used: { ga4: 'search', key: false,
    meaning: 'Воспользовались поиском по каталогу' },
  search_no_results: { ga4: 'search_no_results', key: false,
    meaning: 'Поиск не дал результатов — спрос есть, товара нет' },

  // ── Трение: тихие потери ────────────────────────────────────────────
  // Без этих целей сбой формы неотличим от того, что клиент передумал.
  lead_error: { ga4: 'form_error', key: false,
    meaning: 'Заявка не отправилась из-за ошибки' },
  quote_error: { ga4: 'form_error', key: false,
    meaning: 'КП не сформировалось из-за ошибки' },
};

/** Цели, которые размечаются конверсиями в обеих системах. */
export const KEY_GOALS = Object.keys(GOALS).filter((g) => GOALS[g].key);

type Ym = (id: number, action: string, goal?: string, params?: Record<string, unknown>) => void;
type Gtag = (command: string, event: string, params?: Record<string, unknown>) => void;

/**
 * Отправить цель. Безопасна до загрузки счётчика и при отключённой аналитике:
 * счётчик Метрики буферизует вызовы, а отсутствие gtag просто пропускается.
 */
export function trackGoal(name: string, params: Record<string, unknown> = {}): void {
  if (typeof window === 'undefined') return;
  const w = window as unknown as { ym?: Ym; gtag?: Gtag };
  try {
    if (typeof w.ym === 'function') w.ym(Number(METRIKA_ID), 'reachGoal', name, params);
    // В GA4 уходит рекомендованное имя, если оно есть: под стандартные имена
    // он сам строит отчёты. Наше имя при этом сохраняется параметром, иначе
    // generate_lead от формы и от скачивания КП слились бы в одно число.
    if (typeof w.gtag === 'function') {
      const spec = GOALS[name];
      w.gtag('event', spec ? spec.ga4 : name, spec ? { ...params, bz_goal: name } : params);
    }
  } catch {
    // Аналитика не должна ломать сценарий пользователя: заявка уже отправлена.
  }
}
