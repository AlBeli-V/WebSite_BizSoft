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
  // Открытие формы и начало ввода — разные шаги, и путать их нельзя.
  // Замер кампании 04.09.2026: 226 визитов рекламы, ноль form_start. По
  // одному этому числу нельзя было сказать, не дошли до формы вовсе или
  // открыли и не стали заполнять — лечение у этих случаев разное.
  form_open: { ga4: 'form_open', key: false,
    meaning: 'Форма заявки открыта: модальная — по кнопке, инлайн — показана на экране' },
  form_start: { ga4: 'form_start', key: false,
    meaning: 'Начато заполнение формы заявки — первый ввод в поле' },

  // Клик по главному призыву лендингов вендоров. Отправляется механизмом
  // data-ev с 21.08.2026, но в реестре не значился: цель уходила в счётчик
  // незаведённой, то есть в отчёте её не существовало.
  click_get_quote: { ga4: 'click_get_quote', key: false,
    meaning: 'Клик по кнопке «Получить расчёт и КП» на лендинге' },

  // Реквизиты подставлены из справочника, а не введены руками. Показывает,
  // пользуются ли подсказками: если нет — поле или подсказка не работают.
  company_autofill: { ga4: 'form_autofill', key: false,
    meaning: 'Организация выбрана из справочника, реквизиты подставлены' },

  // ── Интерес: что смотрят ────────────────────────────────────────────
  view_product: { ga4: 'view_item', key: false,
    meaning: 'Открыта карточка товара' },
  view_vendor_landing: { ga4: 'view_item_list', key: false,
    meaning: 'Открыт лендинг производителя' },
  // Между «открыл страницу» и «выбрал тариф» был провал: по view_vendor_landing
  // нельзя сказать, дошёл ли посетитель до цен вообще. Раз на страницу.
  view_tariffs: { ga4: 'view_item_list', key: false,
    meaning: 'Сетка тарифов показана на экране лендинга' },
  // Раскрытый вопрос — это названное сомнение. Какое именно, видно в
  // параметре: список самых раскрываемых вопросов и есть список возражений.
  faq_expand: { ga4: 'faq_expand', key: false,
    meaning: 'Раскрыт вопрос в блоке частых вопросов' },
  view_solution: { ga4: 'view_item_list', key: false,
    meaning: 'Открыта страница назначения ПО' },

  // ── Клики по лендингам производителей (механизм data-ev) ────────────
  // Все они отправлялись с 21.08.2026, но в реестре не значились: цель,
  // не заведённая в кабинете, принимается счётчиком и нигде не видна.
  // Решение руководителя 07.09.2026 — завести весь набор.
  click_related_link: { ga4: 'click_related_link', key: false,
    meaning: 'Переход по связанной ссылке лендинга' },
  click_product_card: { ga4: 'click_product_card', key: false,
    meaning: 'Переход в карточку товара с лендинга' },
  click_choose_plan: { ga4: 'click_choose_plan', key: false,
    meaning: 'Переход к тарифам на самой странице' },
  click_clarify_price: { ga4: 'click_clarify_price', key: false,
    meaning: 'Нажата кнопка «уточнить цену» — открывает форму вопроса' },
  click_request_invoice: { ga4: 'click_request_invoice', key: false,
    meaning: 'Нажата кнопка запроса счёта — открывает форму вопроса' },
  click_renew: { ga4: 'click_renew', key: false,
    meaning: 'Нажата кнопка продления подписки — открывает форму вопроса' },
  click_buy_org: { ga4: 'click_buy_org', key: false,
    meaning: 'Нажата покупка тарифа на организацию — открывает форму вопроса' },
  click_pick_licenses: { ga4: 'click_pick_licenses', key: false,
    meaning: 'Переход к подборщику лицензий на странице' },
  click_plugins_catalog: { ga4: 'click_plugins_catalog', key: false,
    meaning: 'Переход в каталог из блока плагинов' },
  expand_plugins_category: { ga4: 'expand_plugins_category', key: false,
    meaning: 'Раскрыта категория плагинов' },
  quiz_step: { ga4: 'quiz_step', key: false,
    meaning: 'Шаг подборщика тарифа пройден' },
  quiz_complete: { ga4: 'quiz_complete', key: false,
    meaning: 'Подборщик тарифа доведён до конца — открывает форму вопроса' },
  // ── Лендинг вендора: шаги выбора тарифа (макет «сегменты по ролям») ──
  // Решение руководителя 11.09.2026. Прежние click_* показывали клики, но не
  // путь: где посетитель отсеялся — на выборе ситуации, на карточке тарифа
  // или на форме — по ним было не увидеть.
  vendor_tariff_view: { ga4: 'view_item_list', key: false,
    meaning: 'Сетка тарифов вендора показана на экране' },
  vendor_selector_step: { ga4: 'vendor_selector_step', key: false,
    meaning: 'Выбрана ситуация в подборщике лендинга вендора' },
  vendor_cart_add: { ga4: 'vendor_cart_add', key: false,
    meaning: 'Тариф добавлен в подборку с лендинга вендора' },
  vendor_quote_request: { ga4: 'vendor_quote_request', key: false,
    meaning: 'Запрошен расчёт по конкретному тарифу — тариф подставлен в форму' },
  vendor_kp_download: { ga4: 'vendor_kp_download', key: false,
    meaning: 'КП по подборке сформировано — в составе есть позиции вендора' },
  vendor_faq_expand: { ga4: 'vendor_faq_expand', key: false,
    meaning: 'Раскрыт вопрос FAQ на лендинге вендора' },

  click_compare_app: { ga4: 'click_compare_app', key: false,
    meaning: 'Таблица сравнения приложений показана на экране' },
  open_comparison_table: { ga4: 'open_comparison_table', key: false,
    meaning: 'Таблица сравнения тарифов показана на экране' },

  // ── Раздел производителей (/vendors) ────────────────────────────────
  // До 11.09.2026 страница не шла ни одной цели: не было видно ни того,
  // что ищут, ни того, на каком вендоре уходят, ни того, пользуются ли
  // подбором. Пять целей закрывают весь путь по странице.
  vendors_search: { ga4: 'search', key: false,
    meaning: 'Поиск по производителям на /vendors' },
  vendors_filter_click: { ga4: 'vendors_filter_click', key: false,
    meaning: 'Выбран фильтр по назначению или порядок показа на /vendors' },
  vendors_card_click: { ga4: 'select_item', key: false,
    meaning: 'Переход на страницу производителя из каталога производителей' },
  vendors_multiselect_add: { ga4: 'vendors_multiselect_add', key: false,
    meaning: 'Производитель отмечен «в подбор» на /vendors' },
  vendors_multiselect_submit: { ga4: 'vendors_multiselect_submit', key: false,
    meaning: 'Запрошен общий расчёт по нескольким отмеченным производителям' },

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

/**
 * Отправить цель не более одного раза за загрузку страницы.
 *
 * Нужна там, где один и тот же шаг воронки могут заметить несколько
 * независимых блоков: на лендинге производителя форма стоит и в первом
 * экране, и внизу страницы, плюс есть модальная. Каждая из них считает
 * своё «форму открыли», и без общего замка один визит давал бы три
 * события вместо одного шага.
 */
const onceSent = new Set<string>();

export function trackGoalOnce(name: string, params: Record<string, unknown> = {}): void {
  if (onceSent.has(name)) return;
  onceSent.add(name);
  trackGoal(name, params);
}

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
