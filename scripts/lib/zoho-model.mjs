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

/**
 * Артикулы единой системы (docs/rules/sku-system.md). Прежний артикул
 * (`legacy`) остаётся адресом страницы: слаг карточки — он в нижнем
 * регистре, и смена слага дала бы 404 на проиндексированных страницах.
 * Артикул позиции (`sku`) собирается из тех же частей переводчиком
 * scripts/catalog/sku-legacy-zoho.mjs; коды продуктов — общие на прогон.
 */
/** Автокоды продуктов, выданные за прогон (голова → код): генератор расстановки закрепляет их в реестре. */
export const skuCodes = new Map();
const usedSystemSkus = new Set();
function systemSku(parts) {
  return zohoSystemSku(parts, skuCodes, usedSystemSkus);
}

export const token = (text) => (text || '')
  .toUpperCase()
  .replace(/[^A-Z0-9]+/g, '-')
  .replace(/^-+|-+$/g, '');

export const usedSkus = new Set();
import { zohoSystemSku, ZOHO_RULES } from '../catalog/sku-legacy-zoho.mjs';

export function makeSku(familySlug, offer, variant) {
  const pinned = PINNED[`${familySlug}|${offer.offer_slug}|${variant.variant_name}`];
  if (pinned) {
    usedSkus.add(pinned);
    const sku = ZOHO_RULES.pinned[pinned];
    usedSystemSkus.add(sku);
    return { legacy: pinned, sku, parts: null };
  }

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
  let legacy = base;
  let n = 2;
  while (usedSkus.has(legacy)) { legacy = `${base}-${n}`; n += 1; }
  usedSkus.add(legacy);
  // Части для артикула единой системы: голова — семейство и предложение
  // (как в старом артикуле до объёма), хвост — объём, дубль — та же цифра.
  const parts = {
    head: [token(familySlug), offerPart].filter(Boolean).join('-').replace(/-{2,}/g, '-'),
    tail: variantPart,
    perp: offer.license_model === 'perpetual',
    addon: offer.kind !== 'base',
    dedupe: n > 2 ? n - 1 : 0,
  };
  return { legacy, sku: systemSku(parts), parts };
}

/** Сумма сопровождения из столбца AMS: «US$297» → 297, «Included» → null. */
export function amsAmount(text) {
  const m = String(text || '').trim().match(/^(?:US\$|\$)\s?([\d][\d,]*)(?:\.(\d{2}))?$/);
  if (!m) return null;
  const value = Number(m[1].replace(/,/g, '') + (m[2] ? '.' + m[2] : ''));
  return Number.isFinite(value) && value > 0 ? value : null;
}

/**
 * Позиции, которые выносим карточками в каталог: они получают страницу,
 * SEO-текст и место в поиске.
 *
 * Берём входную позицию каждой редакции — с неё начинают, и по ней ищут
 * («ServiceDesk Plus Standard»). Остальные объёмы страниц не получают: они
 * живут в конфигураторе и попадают в КП. Причина не в трудоёмкости — у сайта
 * 160 страниц исключено из Яндекса как малополезные из-за одинаковых
 * описаний, и три с половиной тысячи страниц, отличающихся одним числом,
 * повторили бы это в большем масштабе.
 */
function isCardVariant(offer, variant, entry) {
  return offer.kind === 'base' && variant === entry;
}

/** Строки прайса, которые не являются самостоятельной лицензией. */
const EXTRA = /^additional\b|add[- ]?ons?\b|\bmigration\b|\btraining\b|\bonboarding\b|\bimplementation\b|multi[- ]?language pack|failover|pack license|gateway|\bsummary server\b/i;

/**
 * Все позиции раздела: и те, что станут карточками, и те, что живут только в
 * конфигураторе. У каждой — артикул, цена источника и роль.
 *
 * Вечная лицензия и её сопровождение (AMS) продаются вендором только парой:
 * в прайсе у такой строки два денежных столбца — цена лицензии и цена
 * сопровождения на тот же объём. Поэтому вечная позиция порождает две:
 * саму лицензию и контракт сопровождения со своим артикулом. У подписки
 * сопровождение входит в цену, и пары не возникает.
 */
export function buildPositions(manifest) {
  const positions = [];

  for (const family of manifest.families) {
    // Обучение и сертификация — работы вендора, а не лицензии.
    if (/^(training|certification|onboarding)/i.test(family.family_name)) continue;

    for (const dp of family.deployment_products) {
      for (const offer of dp.offers) {
        const priced = offer.variants.filter(
          (v) => v.price_status === 'listed' && v.amount_usd > 0);
        // Входная позиция редакции — самая дешёвая настоящая лицензия.
        const licences = priced.filter((v) => !EXTRA.test(v.variant_name));
        const entry = offer.kind === 'base' && licences.length
          ? licences.reduce((a, b) => (b.amount_usd < a.amount_usd ? b : a))
          : null;

        for (const variant of priced) {
          const { legacy, sku, parts } = makeSku(family.family_slug, offer, variant);
          const base = {
            sku,
            legacySku: legacy,
            familySlug: family.family_slug,
            familyName: family.family_name,
            offerSlug: offer.offer_slug,
            offerName: offer.offer_name,
            edition: offer.edition,
            kind: offer.kind,
            deployment: dp.deployment,
            licenseModel: dp.license_model,
            variantName: variant.variant_name,
            metric: variant.metric,
            amountUsd: variant.amount_usd,
            sourceUrl: family.source_url,
            sourceSnapshotId: offer.source_snapshot_id || family.source_snapshot_id,
            sourceCheckedAt: family.source_checked_at,
          };

          const ams = dp.license_model === 'perpetual' ? amsAmount(variant.maintenance) : null;
          // Контракт сопровождения — услуга (SVC) к вечной лицензии того же объёма.
          const amsSku = ams ? (parts ? systemSku({ ...parts, ams: true }) : `${sku}-AMS`) : null;
          positions.push({
            ...base,
            role: isCardVariant(offer, variant, entry) ? 'card' : 'hidden',
            otherVolumes: entry
              ? licences.filter((v) => v !== entry).map((v) => v.variant_name)
              : [],
            // Артикул парного контракта сопровождения, если он есть.
            amsSku,
          });

          if (ams) {
            positions.push({
              ...base,
              sku: amsSku,
              legacySku: `${legacy}-AMS`,
              role: 'hidden',
              isAms: true,
              // Сопровождение всегда идёт к своей лицензии и отдельно не продаётся.
              pairOf: sku,
              amountUsd: ams,
              otherVolumes: [],
              amsSku: null,
            });
          }
        }
      }
    }
  }
  return positions;
}

/** Только карточные позиции — для сборки пакета каталога и витрины. */
export function pickCards(manifest) {
  return buildPositions(manifest).filter((p) => p.role === 'card');
}
