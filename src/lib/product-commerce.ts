/**
 * Коммерческая модель позиции каталога: минимум заказа, модель цены,
 * доступность и подпись главного призыва.
 *
 * Правило одно: цена, которую видит покупатель, — наименьшая сумма, которую
 * он реально может заплатить за валидный заказ. У командных тарифов минимум
 * часто больше единицы (Claude Team — от 2 мест, Enterprise — от 20), и
 * карточка, показывающая цену одного места, обещает вдвое-вдесятеро меньше
 * того, что придёт в счёте. Минимум ведётся в контенте вендора
 * (VendorCardMeta.minQty) и до 12.09.2026 держался только счётчиком лендинга:
 * на карточке товара тот же тариф начинался с единицы.
 *
 * Модель выводится из данных, а не из слага, названия или вендора. Чего в
 * данных нет, здесь не додумывается: отдельного поля модели цены в схеме
 * каталога пока нет, поэтому позиция с ценой считается продаваемой за
 * единицу, а позиция без цены — договорной. Появится поле — правится эта
 * функция, а не разметка страницы.
 */
import { pluralForm } from './rub-words';

/** Как назначается цена. Поля в схеме каталога пока нет — см. заголовок. */
export type PricingModel = 'per_unit' | 'quote_only';
/** Коммерческая доступность. Значения — из поля availability каталога. */
export type CommercialAvailability = 'available' | 'limited' | 'out_of_stock';

export interface CommerceState {
  /** Минимальный объём валидного заказа. */
  minQty: number;
  /** Подпись единиц в именительном падеже: «Мест», «Лицензий». */
  qtyLabel: string;
  /** Оговорка вендора к позиции (порог входа, условие тарифа). */
  check: string;
  pricing: PricingModel;
  availability: CommercialAvailability;
  /** Цена одной единицы с учётом акции. */
  unitPrice: number;
  /** Наименьшая сумма валидного заказа: цена единицы × минимум. */
  purchasePrice: number;
  /** Показывать цену как «от»: минимум больше единицы либо флаг каталога. */
  priceFrom: boolean;
}

/**
 * Формы единиц для подписи призыва. Новая подпись единиц заводится здесь же:
 * без форм кнопка скажет «на 1 мест». Полноту стережёт тест
 * product-card-conversion.
 */
export const UNIT_FORMS: Record<string, [string, string, string]> = {
  'лицензий': ['лицензию', 'лицензии', 'лицензий'],
  'мест': ['место', 'места', 'мест'],
  'пользователей': ['пользователя', 'пользователей', 'пользователей'],
  'устройств': ['устройство', 'устройства', 'устройств'],
};

/**
 * Единица в именительном падеже — для строки «Расчётная единица» и для
 * маркеров цены. Формы из UNIT_FORMS здесь не годятся: у них винительный
 * падеж, и «лицензию» в параметрах читается как обрывок фразы.
 */
export const UNIT_SINGULAR: Record<string, string> = {
  'лицензий': 'Лицензия',
  'мест': 'Рабочее место',
  'пользователей': 'Пользователь',
  'устройств': 'Устройство',
};

/** «Рабочее место», «Лицензия» — единица расчёта как отдельное слово. */
export function unitNoun(qtyLabel: string): string {
  const key = qtyLabel.trim().toLowerCase();
  return UNIT_SINGULAR[key] || qtyLabel.trim();
}

/** «5 мест», «1 лицензию» — число со склонённой единицей. */
export function unitPhrase(n: number, qtyLabel: string): string {
  const forms = UNIT_FORMS[qtyLabel.trim().toLowerCase()];
  return forms ? `${n} ${pluralForm(n, forms)}` : `${n} ${qtyLabel.trim().toLowerCase()}`;
}

export function commerceState(input: {
  price: number;
  priceFrom?: boolean | null;
  availability?: string | null;
  minQty?: number | null;
  qtyLabel?: string | null;
  check?: string | null;
}): CommerceState {
  const unitPrice = Number.isFinite(input.price) && input.price > 0 ? input.price : 0;
  const minQty = Math.max(1, Math.floor(Number(input.minQty) || 1));
  const availability: CommercialAvailability = input.availability === 'out_of_stock'
    ? 'out_of_stock'
    : input.availability === 'limited' ? 'limited' : 'available';
  return {
    minQty,
    qtyLabel: input.qtyLabel?.trim() || 'Лицензий',
    check: input.check?.trim() || '',
    pricing: unitPrice > 0 ? 'per_unit' : 'quote_only',
    availability,
    unitPrice,
    purchasePrice: unitPrice * minQty,
    priceFrom: Boolean(input.priceFrom) || minQty > 1,
  };
}

/**
 * Подпись главного призыва: она обязана называть то, что произойдёт.
 * «В расчёт» на кнопке, которая кладёт позицию в подборку, покупателю,
 * пришедшему за ценой, не говорит ничего.
 */
export function quoteCtaLabel(s: CommerceState, qty: number): string {
  if (s.availability === 'out_of_stock') return 'Подобрать аналог';
  if (s.pricing === 'quote_only') return 'Получить расчёт';
  return `Получить КП на ${unitPhrase(Math.max(Math.floor(qty) || s.minQty, s.minQty), s.qtyLabel)}`;
}

/** Подпись позиции для заявки: что именно уходит менеджеру. */
export function quoteProductRef(name: string, sku: string, s: CommerceState, qty: number): string {
  const n = Math.max(Math.floor(qty) || s.minQty, s.minQty);
  const base = sku ? `${name} (${sku})` : name;
  return s.pricing === 'quote_only' ? base : `${base} — ${unitPhrase(n, s.qtyLabel)}`;
}
