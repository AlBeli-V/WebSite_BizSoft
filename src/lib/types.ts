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
  for_whom?: string | null;
  use_cases?: (string | { value?: string })[] | null;
  former_names?: (string | { value?: string })[] | null;
  old_slugs?: (string | { value?: string })[] | null;
  related_products?: (string | { value?: string })[] | null;
  related_solutions?: (string | { value?: string })[] | null;
  price_from?: boolean | null;
}

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

/** Позиция корзины на клиенте (localStorage). */
export interface CartItem {
  sku: string;
  slug: string;
  name: string;
  /** Производитель — колонка КП-таблицы избранного (у старых записей может отсутствовать). */
  vendor?: string;
  price: number; // эффективная цена на момент добавления
  qty: number;
}
