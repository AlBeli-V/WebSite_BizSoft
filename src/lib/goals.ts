/**
 * Реестр целей сайта: единственный список того, что мы отправляем и на каком
 * уровне воронки это находится.
 *
 * Реестр нужен по двум причинам.
 *
 * Первая: без него нельзя проверить, что имя цели, отправленное кодом, кто-то
 * завёл в счётчике. Проверка `GOAL_NOT_CONFIGURED` сверяет отправляемые имена
 * со списком целей Метрики, но сверять надо не все — только те, что обязаны
 * там быть.
 *
 * Вторая: уровни нельзя смешивать. Клик по кнопке «получить КП» — это ещё не
 * заявка: после него человек должен заполнить шесть обязательных полей. Если
 * засчитать его конверсией наравне с `lead_sent`, конверсия сайта окажется
 * завышена в разы. Уровень задаётся здесь один раз и дальше не переспрашивается.
 */

export type GoalLevel =
  | 'lead'        // сервер принял заявку — единственное, что зовётся конверсией
  | 'micro'       // предметный интерес к товару
  | 'intent'      // нажал на CTA, но заявку не отправил
  | 'engagement'  // посмотрел, полистал, раскрыл
  | 'diagnostic'; // ошибки: нужны, чтобы отличить «не было» от «сломалось»

/** Уровни, цели которых обязаны быть заведены в Яндекс.Метрике. */
export const METRIKA_REQUIRED: GoalLevel[] = ['lead', 'micro', 'intent'];

export const GOAL_LEVELS: Record<string, GoalLevel> = {
  // ── lead ──
  lead_sent: 'lead',
  quote_pdf: 'lead',

  // ── micro ──
  add_to_cart: 'micro',
  form_start: 'micro',
  quiz_complete: 'micro',

  // ── intent ──
  contact_click: 'intent',
  click_get_quote: 'intent',
  click_choose_plan: 'intent',
  click_clarify_price: 'intent',
  click_request_invoice: 'intent',
  click_buy_org: 'intent',
  click_renew: 'intent',
  header_kp: 'intent',
  cta_primary: 'intent',
  catalog_discuss: 'intent',
  hero_discuss: 'intent',
  solution_calc: 'intent',
  compare_calc: 'intent',

  // ── engagement ──
  view_vendor_landing: 'engagement',
  view_jetbrains_landing: 'engagement',
  view_zoom_landing: 'engagement',
  view_figma_landing: 'engagement',
  view_openai_landing: 'engagement',
  click_product_card: 'engagement',
  click_related_link: 'engagement',
  click_plugins_catalog: 'engagement',
  click_pick_licenses: 'engagement',
  click_compare_app: 'engagement',
  open_comparison_table: 'engagement',
  expand_plugins_category: 'engagement',
  quiz_step: 'engagement',
  hero_catalog: 'engagement',
  hero_product: 'engagement',
  home_category: 'engagement',

  // ── diagnostic ──
  form_error: 'diagnostic',
};

/** Уровень цели; неизвестное имя считается engagement и не требует цели в Метрике. */
export function levelOf(name: string): GoalLevel {
  return GOAL_LEVELS[name] ?? 'engagement';
}
