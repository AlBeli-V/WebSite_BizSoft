// Сборка пакета карточек Zoho ManageEngine для штатного импорта.
//
// Вход:
//   data/sources/manageengine/<дата>/manifest.json — прайс со снимков вендора
//   scripts/content/zoho-cards.json — редакторский текст по семействам
//
// Выход:
//   scripts/catalog/zoho.json          — пакет для ops-import-vendors
//   data/catalog/zoho-rollback.json    — те же артикулы со снятием с витрины
//
// В каталог попадают ВСЕ позиции прайса, но по-разному:
//
//   status: published — карточка с SEO-текстом, страницей и местом в поиске;
//   status: draft     — позиция с ценой, но без страницы: живёт только в
//                       конфигураторе и в КП.
//
// Черновик не отдаётся ни каталогом, ни sitemap, а /product/<slug> для него
// возвращает 404 — все запросы к базе на витрине фильтруют по published.
// Цену черновику пересчитывает та же ежедневная переоценка по курсу ЦБ:
// getAllProductsAdmin статус не фильтрует.
//
// Карточкой позиция становится только при наличии редакторского текста
// семейства: у сайта 160 страниц исключено из Яндекса как малополезные, и
// добивать это шаблонными заглушками нельзя.
//
// Запуск: node scripts/build-zoho-catalog.mjs [дата]
import { readFileSync, writeFileSync, mkdirSync, readdirSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { buildPositions } from './lib/zoho-model.mjs';

const __dir = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dir, '..');
const SRC = resolve(ROOT, 'data/sources/manageengine');
const OUT_PKG = resolve(ROOT, 'scripts/catalog/zoho.json');
const OUT_ROLLBACK = resolve(ROOT, 'data/catalog/zoho-rollback.json');

function pickDay(arg) {
  if (arg) return arg;
  const days = readdirSync(SRC).filter((d) => /^\d{4}-\d{2}-\d{2}$/.test(d)).sort();
  if (!days.length) throw new Error(`нет снимков в ${SRC}`);
  return days[days.length - 1];
}

const day = pickDay(process.argv[2]);
const manifest = JSON.parse(readFileSync(resolve(SRC, day, 'manifest.json'), 'utf8'));
const copy = JSON.parse(readFileSync(resolve(__dir, 'content/zoho-cards.json'), 'utf8'));
const existing = JSON.parse(readFileSync(OUT_PKG, 'utf8'));

/** Русское название модели лицензии для подписи к цене. */
const MODEL_NOTE = {
  subscription: 'в год',
  perpetual: 'разово за вечную лицензию',
  unspecified: 'за пакет',
};

/** Русское склонение по количеству: 1 сервер, 2 сервера, 10 серверов. */
function plural(n, forms) {
  const [one, few, many] = forms;
  if (n % 10 === 1 && n % 100 !== 11) return one;
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return few;
  return many;
}

/** Человеческое описание объёма из названия позиции вендора. */
function volumeRu(card, fam) {
  const forms = card.metric && fam.units ? fam.units[card.metric.unit] : null;
  if (forms) return `${card.metric.quantity} ${plural(card.metric.quantity, forms)}`;
  return fam.volumeFallback || 'входной пакет вендора';
}

/** Заглавная буква в начале предложения. */
const cap = (text) => (text ? text[0].toUpperCase() + text.slice(1) : text);

/**
 * Скрытая позиция: цена в базе есть, страницы нет.
 *
 * Тексты у неё служебные и короткие — их никто не читает: позиция не
 * индексируется и показывается только в конфигураторе и в спецификации КП.
 * Название при этом должно быть человеческим: именно оно уйдёт в КП
 * покупателю.
 */
function hiddenProduct(pos, fam) {
  const nameRu = fam?.nameRu || pos.familyName;
  const editionRu = pos.edition ? ` ${pos.edition}` : '';
  const modelRu = pos.licenseModel === 'perpetual' ? 'вечная лицензия' : 'годовая подписка';
  const name = pos.isAms
    ? `ManageEngine ${nameRu}${editionRu} — сопровождение вендора на год, ${pos.variantName}`
    : `ManageEngine ${nameRu}${editionRu}, ${pos.variantName}${pos.licenseModel === 'perpetual' ? ', вечная лицензия' : ''}`;
  const short = pos.isAms
    ? 'Годовое сопровождение вендора: обновления и техподдержка к вечной лицензии того же объёма.'
    : `${nameRu}${editionRu}: ${modelRu}, объём по прайсу вендора — ${pos.variantName}.`;
  return {
    sku: pos.sku,
    slug: pos.sku.toLowerCase(),
    name,
    official_name: `ManageEngine ${pos.familyName}${pos.edition ? ` ${pos.edition} Edition` : ''}, ${pos.variantName}`
      + (pos.isAms ? ' (Annual Maintenance & Support)' : pos.licenseModel === 'perpetual' ? ' (Perpetual License)' : ''),
    category: 'system',
    license_type: 'org',
    short_description: short,
    description: short,
    keywords: '',
    features: [],
    base_price_usd: pos.amountUsd,
    billing: pos.isAms ? 'за год сопровождения' : `за пакет: ${pos.variantName}`,
    min_quantity: 1,
    price_confidence: 'vendor-page',
    source_url: pos.sourceUrl,
    checkout_url: pos.sourceUrl,
    checked_at: (pos.sourceCheckedAt || '').slice(0, 10) || day,
    notes: `Позиция конфигуратора, страницы не имеет. Цена снята ${day} `
      + `(снимок ${pos.sourceSnapshotId}): «${pos.offerName}», строка «${pos.variantName}»`
      + (pos.isAms ? ', столбец сопровождения (AMS).' : '.'),
    // Скрытая позиция: в каталоге, поиске и sitemap не показывается.
    status: 'draft',
    markup_coeff: null,
    sort: null,
  };
}

const positions = buildPositions(manifest);
const products = [];
const skipped = [];

for (const card of positions) {
  const fam = copy.families[card.familySlug];
  const editionNote = card.edition ? fam?.editions?.[card.edition] : fam?.editions?.['—'];

  // Роль позиции: страница с текстом или скрытая строка конфигуратора.
  // Позиция без редакторского текста семейства карточкой стать не может —
  // она уходит в скрытые, а не выпадает из каталога совсем.
  const isCard = card.role === 'card' && fam && (!card.edition || editionNote);
  if (card.role === 'card' && !isCard) {
    skipped.push(`${card.familyName}${card.edition ? ' ' + card.edition : ''} (нет текста — уходит в скрытые)`);
  }
  if (!fam) { products.push(hiddenProduct(card, null)); continue; }
  if (!isCard) { products.push(hiddenProduct(card, fam)); continue; }

  const volume = volumeRu(card, fam);
  const model = card.licenseModel || 'unspecified';
  const modelRu = model === 'perpetual' ? 'вечная лицензия' : 'годовая подписка';
  const editionRu = card.edition ? ` ${card.edition}` : '';
  const multi = /multi[- ]?language/i.test(card.offerName) ? ', многоязычная версия' : '';

  // Подписка и вечная лицензия на один и тот же объём — разные товары.
  // Без пометки в названии в каталоге стояли бы две одинаковые карточки.
  const modelSuffix = model === 'perpetual' ? ', вечная лицензия' : '';
  const name = `ManageEngine ${fam.nameRu}${editionRu}${multi}, ${volume}${modelSuffix}`;
  const officialName = `ManageEngine ${card.familyName}${card.edition ? ` ${card.edition} Edition` : ''}, ${card.variantName}`
    + (model === 'perpetual' ? ' (Perpetual License)' : model === 'subscription' ? ' (Annual Subscription)' : '');

  // Описание собирается из блоков семейства и редакции — той же структурой,
  // что и остальные карточки сайта: сценарий, состав, отличие от соседнего
  // тарифа, ограничения, кому подходит.
  const description = [
    `${fam.nameRu}${editionRu} — ${fam.purpose}`,
    `Типичный сценарий: ${fam.scenario}`,
    editionNote ? `Чем отличается от соседней редакции: ${editionNote}` : null,
    `Ограничения: пакет рассчитан на ${volume}; ${
      card.otherVolumes.length
        ? `у вендора есть и другие объёмы (${card.otherVolumes.length} шт.) — посчитаем под ваше количество`
        : 'больший объём считаем под запрос'
    }. Лицензия считается ${fam.metricNote}.`,
    `Кому подходит: ${fam.audience}`,
    model === 'perpetual'
      ? 'Вечная лицензия: право пользования бессрочное, обновления и поддержка вендора оплачиваются отдельно ежегодно.'
      : 'Годовая подписка: в стоимость входит сопровождение вендора на весь срок.',
    'Оформим на вашу компанию: договор, счёт в рублях, закрывающие документы через ЭДО, доступ за 1–3 рабочих дня.',
  ].filter(Boolean).join('\n\n');

  const shortDescription = `${fam.short} ${cap(modelRu)} на ${volume}.`;

  products.push({
    sku: card.sku,
    slug: card.sku.toLowerCase(),
    name,
    official_name: officialName,
    category: 'system',
    license_type: 'org',
    short_description: shortDescription,
    description,
    keywords: (fam.keywords || []).join(', '),
    features: [...(fam.features || []), `${cap(modelRu)}, ${volume}`],
    base_price_usd: card.amountUsd,
    billing: `за пакет на ${volume} ${MODEL_NOTE[model]}`,
    min_quantity: 1,
    price_confidence: 'vendor-page',
    source_url: card.sourceUrl,
    checkout_url: card.sourceUrl,
    checked_at: (card.sourceCheckedAt || '').slice(0, 10) || day,
    notes: `Цена снята со страницы магазина вендора ${day} (ops-me-crawl, снимок ${card.sourceSnapshotId}): `
      + `«${card.offerName}», строка «${card.variantName}».`,
    status: 'published',
    markup_coeff: null,
    sort: null,
  });
}

// Пакет сохраняет прежнюю запись производителя: она уже опубликована.
const pkg = { vendor_entry: existing.vendor_entry, products };
writeFileSync(OUT_PKG, JSON.stringify(pkg, null, 1) + '\n');

// Откат: те же артикулы со снятием с витрины. Штатный импорт понимает
// стаб {sku, archive: true} — товар переводится в archived, а не удаляется,
// поэтому откат обратим и ничего не теряет.
mkdirSync(dirname(OUT_ROLLBACK), { recursive: true });
const pinned = new Set(['MANAGEENGINE-SERVICEDESK-STANDARD-10', 'MANAGEENGINE-SERVICEDESK-PROFESSIONAL-5']);
const rollback = {
  vendor_entry: existing.vendor_entry,
  // Две ранее опубликованные позиции откат не трогает: они были на витрине
  // до этой работы и должны остаться после отката.
  products: products.filter((p) => !pinned.has(p.sku)).map((p) => ({ sku: p.sku, archive: true })),
};
writeFileSync(OUT_ROLLBACK, JSON.stringify(rollback, null, 1) + '\n');

console.log(`✓ scripts/catalog/zoho.json: ${products.length} карточек`);
console.log(`✓ data/catalog/zoho-rollback.json: ${rollback.products.length} стабов снятия`);
if (skipped.length) {
  const uniq = [...new Set(skipped)];
  console.log(`  не публикуем без текста: ${uniq.length} позиций`);
  for (const line of uniq.slice(0, 30)) console.log(`    ${line}`);
}
if (!existsSync(resolve(ROOT, 'scripts/catalog/zoho.json'))) process.exit(1);
