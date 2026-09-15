/**
 * Поиск предложения по токену страницы `/offer/<токен>`.
 *
 * Токен — подпись номера КП (`offer-token.ts`), поэтому в базе его нет и
 * искать приходится перебором последних предложений со сверкой подписи.
 * Сверка дешёвая (HMAC на строку), список ограничен, зато схема Directus
 * не меняется и выпуск страницы не ждёт правки в проде.
 *
 * Документ и содержимое страницы собираются из сохранённой записи теми же
 * модулями, что и при выпуске КП: цены берутся из записи, а не считаются
 * заново — клиент должен видеть ровно то, что ему выслали.
 */
import { getProductsBySkus, getQuotes } from './directus';
import { site } from '../config/site';
import { addDays, formatDateRu, type QuoteData } from './quote-layout';
import { offerExpired, offerTokenMatches, offerTokensReady } from './offer-token';
import type { Product, QuoteItem } from './types';

export interface ResolvedOffer {
  data: QuoteData;
  issued: Date;
  expired: boolean;
  products: Product[];
}

/** Сколько последних КП просматриваем. Больше — только старше срока жизни ссылки. */
const SCAN_LIMIT = 500;

export async function resolveOffer(token: string): Promise<ResolvedOffer | null> {
  if (!offerTokensReady()) return null;
  const clean = String(token || '').trim();
  if (!/^[A-Za-z0-9_-]{16,64}$/.test(clean)) return null;

  let quotes;
  try {
    quotes = await getQuotes(SCAN_LIMIT);
  } catch (e) {
    console.error('offer lookup: getQuotes failed', e);
    return null;
  }

  const found = quotes.find((q) => q.quote_no && offerTokenMatches(String(q.quote_no), clean));
  if (!found) return null;

  const stored = Array.isArray(found.items) ? found.items : [];
  const items: QuoteItem[] = stored.map((i) => ({
    sku: i.sku,
    name: i.name,
    qty: i.qty,
    price: (i as QuoteItem).price ?? (i.qty > 0 ? i.sum / i.qty : i.sum),
    sum: i.sum,
    vat_percent: (i as QuoteItem).vat_percent,
    vendor: (i as QuoteItem).vendor || '',
    email_rent: Boolean((i as QuoteItem).email_rent),
  }));

  // Производитель и слаг карточки — из каталога по артикулу: у КП, выпущенных
  // до 15.09.2026, марки в записи нет, а ссылки на товары нужны все.
  let products: Product[] = [];
  try {
    products = await getProductsBySkus(items.map((i) => i.sku));
  } catch (e) {
    console.error('offer lookup: getProductsBySkus failed', e);
  }

  const issued = found.created_at ? new Date(found.created_at) : new Date();
  const data: QuoteData = {
    quoteNo: String(found.quote_no || ''),
    date: formatDateRu(issued),
    validUntil: formatDateRu(addDays(issued, site.quoteValidDays)),
    buyerCompany: String(found.buyer_company || ''),
    buyerInn: String(found.buyer_inn || ''),
    contactName: String(found.contact_name || ''),
    email: String(found.email || ''),
    phone: String(found.phone || ''),
    items,
    total: Number(found.total) || items.reduce((s, i) => s + i.sum, 0),
  };

  return { data, issued, products, expired: offerExpired(issued, site.quoteValidDays) };
}
