/** Общие типы модели данных (соответствуют коллекциям Directus). */

export type PublishStatus = 'published' | 'draft' | 'archived';

export interface Category {
  id: string | number;
  name: string;
  slug: string;
  seo_text?: string | null;
  intro?: string | null;
  faqs?: { q: string; a: string }[] | null;
  meta_title?: string | null;
  meta_description?: string | null;
  sort?: number | null;
  status: PublishStatus;
  noindex?: boolean | null;
  related_products?: (string | { value?: string })[] | null;
  related_articles?: (string | { value?: string })[] | null;
}

export interface ProductFaqItem {
  q: string;
  a: string;
}

/** Происхождение ПО — верхний уровень каталога. */
export type Origin = 'domestic' | 'foreign';
/** Тип лицензии. */
export type LicenseType = 'org' | 'individual' | 'student';

export const ORIGIN_LABEL: Record<Origin, string> = {
  domestic: 'Отечественное ПО',
  foreign: 'Иностранное ПО',
};
export const LICENSE_LABEL: Record<LicenseType, string> = {
  org: 'Для организаций',
  individual: 'Индивидуальное использование',
  student: 'Студенческая версия',
};

/** Элемент галереи (строка junction products_files с раскрытым файлом). */
export interface ProductImageRef {
  directus_files_id: string | { id: string; title?: string | null } | null;
}

export interface Product {
  id: string | number;
  name: string;
  sku: string;
  vendor?: string | null;
  origin?: Origin | null;
  category: string | number | Category | null;
  license_type?: LicenseType | null;
  slug: string;
  short_description?: string | null;
  description?: string | null;
  seo_text?: string | null;
  keywords?: string | null;
  meta_title?: string | null;
  meta_description?: string | null;
  price: number; // ₽ — итоговая рублёвая цена
  price_note?: string | null;
  vat_percent?: number | null;
  currency: string; // RUB
  /** Закупочная себестоимость в валюте (с сайта производителя). */
  base_price_usd?: number | null;
  base_price_eur?: number | null;
  /** Валюта закупки для пересчёта в рубли. */
  peg_currency?: 'USD' | 'EUR' | null;
  peg_to_usd?: boolean | null; // привязка к курсу включена
  /** Коэффициент наценки: цена = себестоимость × курс × коэф. База 1.85. */
  markup_coeff?: number | null;
  /** Когда закупочная цена сверялась с сайтом производителя в последний раз. */
  purchase_updated_at?: string | null;
  /** Откуда взята закупочная цена (страница прайса вендора и т.п.). */
  purchase_source?: string | null;
  /** Цена зафиксирована вручную — массовые переоценки её не меняют. */
  price_locked?: boolean | null;
  markup_percent?: number | null; // устаревшее, не используется в новой логике
  promo_price?: number | null;
  promo_label?: string | null;
  promo_start?: string | null; // ISO date
  promo_end?: string | null; // ISO date
  /** Логотип (одиночный файл, M2O). */
  image?: string | null;
  /** Галерея (M2M медиатека). */
  images?: ProductImageRef[] | null;
  features?: string[] | null;
  faq?: ProductFaqItem[] | null;
  sort?: number | null;
  status: PublishStatus;
  // ── SEO-архитектура / масштабирование ──
  noindex?: boolean | null;
  date_updated?: string | null;
  /** Дата содержательного изменения карточки — источник lastmod в sitemap.
   *  date_updated для этого не годится: его сдвигает ежедневная переоценка. */
  content_updated_at?: string | null;
  for_whom?: string | null;
  use_cases?: (string | { value?: string })[] | null;
  former_names?: (string | { value?: string })[] | null;
  old_slugs?: (string | { value?: string })[] | null;
  related_products?: (string | { value?: string })[] | null;
  related_solutions?: (string | { value?: string })[] | null;
  price_from?: boolean | null;
  // ── Тип товара и варианты (подарочные карты) ──
  /** Тип товара: null/undefined — обычная лицензия или подписка; gift_card —
   *  цифровая подарочная карта (см. docs/gift-cards.md). */
  product_type?: ProductType | null;
  /** Артикул родительской карточки: заполнен у варианта (номинал в регионе),
   *  пуст у самостоятельного товара и у родителя. Вариант страницы не имеет —
   *  отдаёт 301 на родителя, в sitemap и фиды не попадает. */
  parent_sku?: string | null;
  /** Регион карты (ISO 3166-1 alpha-2: RU, KZ, TR) и его название для витрины. */
  region_code?: string | null;
  region_name?: string | null;
  /** Номинал — сумма, которая зачисляется на баланс аккаунта, и её валюта.
   *  В расчёте цены не участвует: цена считается от base_price_usd. */
  denomination?: number | null;
  denomination_currency?: string | null;
  /** Подпись варианта для витрины, когда номинал — не сумма в валюте
   *  (например, «Discord Nitro, 12 месяцев»). Пусто — подпись из номинала. */
  variant_label?: string | null;
  /** Наличие кодов: in_stock — есть; limited — ограничено; out_of_stock — нет. */
  availability?: Availability | null;
}

export type ProductType = 'gift_card';
export type Availability = 'in_stock' | 'limited' | 'out_of_stock';

export const AVAILABILITY_LABEL: Record<Availability, string> = {
  in_stock: 'В наличии',
  limited: 'Ограниченное количество',
  out_of_stock: 'Нет в наличии',
};

/** Нормализовать list-поле Directus ([{value}] или [string]) в string[]. */
export function listValues(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.map((x) => (typeof x === 'string' ? x : (x as { value?: string })?.value || '')).filter(Boolean);
}

export interface Lead {
  name?: string;
  company?: string;
  email: string;
  phone?: string;
  message?: string;
  product_ref?: string;
  consent: boolean;
  source?: string;
}

export interface QuoteItem {
  sku: string;
  name: string;
  qty: number;
  price: number; // цена за единицу (с учётом акции)
  sum: number; // qty * price
  /**
   * Ставка НДС позиции, %. Налог включён в цену.
   *
   * Хранится у позиции, а не одной константой на документ: ставка задаётся
   * у товара, и предложение из позиций с разными ставками иначе посчиталось
   * бы по одной — с ошибкой ровно на разницу ставок.
   */
  vat_percent?: number | null;
}

export interface Quote {
  buyer_company: string;
  buyer_inn: string;
  contact_name: string;
  email: string;
  phone?: string;
  items: QuoteItem[];
  total: number;
  quote_no: string;
  consent: boolean;
}

export type CurrencyMode = 'manual' | 'auto';

export interface CurrencyRate {
  id?: string | number;
  mode: CurrencyMode;
  usd_rate: number;
  eur_rate?: number | null;
  rate_date?: string | null;
  source?: string | null;
  updated_at?: string | null;
  auto_recalc?: boolean | null;
}

/** Базовый коэффициент наценки по умолчанию. */
export const DEFAULT_MARKUP_COEFF = 1.85;
/**
 * Коэффициент подарочных карт (product_type = gift_card): цена = закупка в USD
 * × курс ЦБ × 3,00 — то есть 300 % от закупочной стоимости (ровно ×3, а не
 * «+300 %»). Номинал карты в расчёте не участвует.
 */
export const GIFT_CARD_MARKUP_COEFF = 3.0;

/** Позиция корзины на клиенте (localStorage). */
export interface CartItem {
  sku: string;
  slug: string;
  name: string;
  /** Производитель — колонка КП-таблицы расчёта (у старых записей может отсутствовать). */
  vendor?: string;
  price: number; // эффективная цена на момент добавления
  qty: number;
}
