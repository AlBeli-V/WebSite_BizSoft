/** Общие типы модели данных (соответствуют коллекциям Directus). */

export type PublishStatus = 'published' | 'draft' | 'archived';

export interface Category {
  id: string | number;
  name: string;
  slug: string;
  seo_text?: string | null;
  meta_title?: string | null;
  meta_description?: string | null;
  sort?: number | null;
  status: PublishStatus;
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
  price: number; // ₽
  price_note?: string | null;
  vat_percent?: number | null;
  currency: string; // RUB
  base_price_usd?: number | null;
  peg_to_usd?: boolean | null;
  markup_percent?: number | null;
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
  rate_date?: string | null;
  source?: string | null;
  updated_at?: string | null;
  auto_recalc?: boolean | null;
}

/** Позиция корзины на клиенте (localStorage). */
export interface CartItem {
  sku: string;
  slug: string;
  name: string;
  price: number; // эффективная цена на момент добавления
  qty: number;
}
