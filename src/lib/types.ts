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

export interface ProductImage {
  /** id файла в медиатеке Directus */
  id: string;
  alt?: string | null;
}

export interface Product {
  id: string | number;
  name: string;
  sku: string;
  category: string | number | Category | null;
  slug: string;
  short_description?: string | null;
  description?: string | null;
  seo_text?: string | null;
  meta_title?: string | null;
  meta_description?: string | null;
  price: number; // ₽
  currency: string; // RUB
  base_price_usd?: number | null;
  peg_to_usd?: boolean | null;
  markup_percent?: number | null;
  promo_price?: number | null;
  promo_label?: string | null;
  promo_start?: string | null; // ISO date
  promo_end?: string | null; // ISO date
  images?: ProductImage[] | null;
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
