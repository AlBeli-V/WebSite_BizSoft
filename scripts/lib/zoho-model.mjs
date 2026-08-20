// Общая модель раздела Zoho ManageEngine.
//
// Здесь живут артикулы позиций и правило отбора карточек. Оба нужны и витрине
// (scripts/build-zoho-hierarchy.mjs), и импорту (scripts/build-zoho-catalog.mjs);
// разойдись они — на странице появилась бы кнопка «в корзину» для товара,
// которого в каталоге нет.

/**
 * Артикул и адрес позиции. Собираются здесь, чтобы витрина и импорт брали их
 * из одного места: разойдись они — на странице появилась бы кнопка «в
 * корзину» для несуществующего товара.
 *
 * Две позиции ServiceDesk Plus уже опубликованы и проиндексированы. Их
 * артикулы и адреса закреплены: смена слага дала бы 404 на живой странице.
 */
const PINNED = {
  'servicedesk-plus|servicedesk-plus-standard-edition-annual-subscription|10 Technicians':
    'MANAGEENGINE-SERVICEDESK-STANDARD-10',
  'servicedesk-plus|servicedesk-plus-professional-edition-annual-subscription|5 Technicians (500 IT Assets)':
    'MANAGEENGINE-SERVICEDESK-PROFESSIONAL-5',
};

export const token = (text) => (text || '')
  .toUpperCase()
  .replace(/[^A-Z0-9]+/g, '-')
  .replace(/^-+|-+$/g, '');

export const usedSkus = new Set();

export function makeSku(familySlug, offer, variant) {
  const pinned = PINNED[`${familySlug}|${offer.offer_slug}|${variant.variant_name}`];
  if (pinned) { usedSkus.add(pinned); return pinned; }

  // Различающая часть предложения: редакция плюс то, что вендор дописал к
  // ней сверх названия семейства. Одной редакции мало: «PAM360 Enterprise
  // Edition» и «PAM360 Enterprise Edition Multi-Language» — разные прайсы.
  const familyRe = new RegExp(familySlug.replace(/-/g, '[ -]'), 'ig');
  const noiseRe = /\b(annual|subscription|perpetual|edition|add-?ons?|model|store|pricing)\b/ig;
  const rest = offer.offer_name
    .replace(/\([^)]*\)/g, ' ')
    .replace(familyRe, ' ')
    .replace(offer.edition ? new RegExp(`\\b${offer.edition.replace(/[()]/g, '')}\\b`, 'ig') : /$^/, ' ')
    .replace(noiseRe, ' ');
  const offerPart = [token(offer.edition), token(rest).slice(0, 26)]
    .filter(Boolean).join('-');
  // Название позиции целиком, без скобочных уточнений: по одной лишь метрике
  // «1 Domain» четыре разные строки прайса ADManager Plus дали бы один и тот
  // же артикул с безликими хвостами -2, -3, -4.
  const variantPart = token(variant.variant_name.replace(/\([^)]*\)/g, ' ')).slice(0, 44);
  const model = offer.license_model === 'perpetual' ? '-PERP' : '';

  const base = ['ME', token(familySlug), offerPart, variantPart]
    .filter(Boolean).join('-').replace(/-{2,}/g, '-').slice(0, 96) + model;
  let sku = base;
  let n = 2;
  while (usedSkus.has(sku)) { sku = `${base}-${n}`; n += 1; }
  usedSkus.add(sku);
  return sku;
}

/**
 * Какие позиции выносим карточками в каталог, а какие оставляем расчётом.
 *
 * Берём входную позицию каждой редакции: именно с неё начинают, и по ней
 * ищут в поиске («ServiceDesk Plus Standard»). Остальные объёмы, дополнения
 * и работы вендора карточками не заводим — их собирает конфигуратор и
 * считает КП.
 *
 * Причина не только в трудоёмкости. У сайта сейчас 160 страниц исключено из
 * Яндекса как малополезные: одинаковые описания карточек. Девять сотен
 * позиций прайса, отличающихся одним числом, повторили бы эту историю в
 * большем масштабе.
 */
export function pickCards(manifest) {
  const cards = [];
  for (const family of manifest.families) {
    for (const dp of family.deployment_products) {
      for (const offer of dp.offers) {
        if (offer.kind !== 'base') continue;
        // Внутри таблицы базовой лицензии вендор держит и строки-надстройки:
        // «Additional 100 IT Assets», «One-time Server & Data Migration»,
        // «Governance, Risk and Compliance add-on». Они дешевле любой
        // лицензии, и «самая дешёвая строка» без этого фильтра дала бы
        // карточку «ServiceDesk Plus Professional» с ценой дополнительных
        // активов.
        // «Secure Gateway Server» и подобные — инфраструктурные компоненты
        // внутри той же таблицы: покупаются в дополнение к лицензии, а не
        // вместо неё.
        const EXTRA = /^additional\b|add-?on\b|\bmigration\b|\btraining\b|\bonboarding\b|\bimplementation\b|multi[- ]?language pack|failover|pack license|gateway|\bsummary server\b/i;
        const priced = offer.variants.filter(
          (v) => v.price_status === 'listed' && v.amount_usd > 0 && !EXTRA.test(v.variant_name));
        if (!priced.length) continue;
        // Входная позиция редакции — самая дешёвая из опубликованных лицензий.
        const entry = priced.reduce((a, b) => (b.amount_usd < a.amount_usd ? b : a));
        cards.push({
          sku: makeSku(family.family_slug, offer, entry),
          familySlug: family.family_slug,
          familyName: family.family_name,
          offerSlug: offer.offer_slug,
          offerName: offer.offer_name,
          edition: offer.edition,
          deployment: dp.deployment,
          licenseModel: dp.license_model,
          variantName: entry.variant_name,
          metric: entry.metric,
          amountUsd: entry.amount_usd,
          maintenance: entry.maintenance,
          otherVolumes: priced.filter((v) => v !== entry).map((v) => v.variant_name),
          sourceUrl: family.source_url,
          sourceSnapshotId: offer.source_snapshot_id || family.source_snapshot_id,
          sourceCheckedAt: family.source_checked_at,
        });
      }
    }
  }
  return cards;
}
