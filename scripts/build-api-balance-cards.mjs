// Разворачивает реестр пополнений баланса API (scripts/api-balance.json) в
// реестр карточек того же формата, что scripts/ai-catalog-cards.json →
// scripts/api-balance-cards.json. Дальше карточки идут штатным путём:
// build-vendor-cards.mjs собирает xlsx, ops-import-ai-cards заливает upsert'ом
// по sku (вход registry=scripts/api-balance-cards.json).
//
// Использование: node scripts/build-api-balance-cards.mjs [--check]
//   --check — не писать файл, а сверить, что на диске лежит актуальный результат
//             (используется тестом: реестр и сгенерированные карточки не должны
//             разъезжаться незаметно).
//
// Почему генератор, а не руками: номиналов у одного вендора десяток, и
// отличаются карточки одним числом. Руками это десять мест, где можно
// ошибиться в себестоимости, и ноль гарантий, что у второго вендора линейка
// устроена так же. Вендор добавляется одной записью в scripts/api-balance.json.
//
// Цена. Себестоимость = номинал × vat_coeff: при закупке на номинал начисляется
// НДС поставщика, и на баланс мы кладём номинал, а платим больше. Витринная
// цена считается штатно — себестоимость × markup_coeff × курс ЦБ, — поэтому
// пополнения переоцениваются тем же ежедневным механизмом, что и подписки.
import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { buildSku } from '../src/lib/sku.ts';

const REGISTRY = 'scripts/api-balance.json';
const OUT = 'scripts/api-balance-cards.json';

const round2 = (n) => Math.round(Number(n) * 100) / 100;
/** Сумма прописью для названия карточки: «50 $», «10 000 $». */
const money = (n) => `${n.toLocaleString('ru-RU')} $`;

export function buildCards(reg) {
  const d = reg.defaults;
  const vendors = reg.vendors.map((v) => {
    const t = v.texts || {};
    const products = [];

    // Родительская карточка: сумма вне ряда номиналов и любой нестандартный
    // случай. Она же держит поисковый интент «пополнить баланс <вендор>» —
    // номиналы из поиска закрыты индексной матрицей (CRD с вариантом).
    // Артикулы — по единой системе (docs/rules/sku-system.md): родитель
    // <вендор>-CRD-<продукт>-UNI-BAL-NOM, номинал — тот же с вариантом-суммой.
    const skuOf = (variant) => buildSku({ vendor: v.sku_vendor, kind: 'CRD', product: v.sku_product, plan: 'UNI', term: 'BAL', unit: 'NOM', variant });
    if (skuOf(null) !== v.parent_sku) throw new Error(`${v.vendor}: parent_sku «${v.parent_sku}» не совпадает с артикулом по сегментам «${skuOf(null)}»`);
    products.push({
      sku: v.parent_sku,
      key: 'API-BALANCE',
      name: v.parent_name,
      license_type: d.license_type,
      price_on_request: true,
      sort: v.sort_base,
      short_desc_ru: `Пополнение баланса ${v.api_name} на согласованную сумму: оплата идёт по фактическому потреблению моделей, подписка за место не нужна.`,
      description_ru: [
        `Пополнение баланса ${v.api_name} — разовая услуга для команд разработки: вносим согласованную сумму ${t.where}, с которой списывается фактическое потребление ${t.models}.`,
        `Модель оплаты отличается от подписки: фиксированной цены за пользователя нет, расход зависит от числа запросов и выбранных моделей. Типичный случай — ${t.intent}.`,
        `Эта карточка — для суммы вне готового ряда номиналов: назовите нужную, и мы посчитаем её в КП. Готовые номиналы с ценой на витрине — отдельными карточками.`,
        `Оформим на вашу компанию: договор, счёт в рублях, закрывающие документы через ЭДО.`,
      ].join('\n\n'),
      features_ru: [
        `Любая сумма пополнения по согласованию`,
        `Зачисление ${t.where}`,
        `Списание по фактическому потреблению`,
        `Договор, счёт в рублях, закрывающие через ЭДО`,
      ],
    });

    v.denominations.forEach((nominal, i) => {
      products.push({
        sku: skuOf(String(nominal)),
        key: `CREDITS-${nominal}`,
        name: `${v.api_name} — пополнение баланса на ${money(nominal)}`,
        license_type: d.license_type,
        base_price: round2(nominal * d.vat_coeff),
        currency: d.currency,
        vat_included: d.vat_included,
        markup_coeff: d.markup_coeff,
        billing_note_ru: d.billing_note_ru,
        price_on_request: false,
        sort: v.sort_base + 10 * (i + 1),
        short_desc_ru: `Разовое пополнение баланса ${v.api_name} на ${money(nominal)}: списание идёт по фактическому потреблению моделей, подписка за место не нужна.`,
        description_ru: [
          `Номинал ${money(nominal)} на баланс ${v.api_name}: сумма зачисляется ${t.where} и расходуется по мере работы — платите за фактические запросы к моделям, а не за место сотрудника.`,
          `Расход зависит от объёма и выбранных моделей (${t.models}), поэтому номинал подбирают под ожидаемую нагрузку: меньший — на пилот и замер собственной экономики запроса, больший — на постоянную работу продукта.`,
          `Нужна сумма вне этого ряда — посчитаем по запросу отдельной строкой в КП.`,
          `Оформим на вашу компанию: договор, счёт в рублях, закрывающие документы через ЭДО.`,
        ].join('\n\n'),
        features_ru: [
          `Номинал ${money(nominal)} на баланс аккаунта`,
          `Списание по фактическому потреблению (токены)`,
          `Доступны ${t.models}`,
          `Разовая покупка, без подписки за место`,
          `Договор, счёт в рублях, закрывающие через ЭДО`,
        ],
      });
    });

    return { vendor: v.vendor, prefix: v.prefix, category: v.category, products };
  });

  return {
    _generated: `Собрано scripts/build-api-balance-cards.mjs из ${REGISTRY}. Руками не править: правки делаются в реестре, файл пересобирается.`,
    block: 'ai',
    sortBase: Math.min(...reg.vendors.map((v) => v.sort_base)),
    vendors,
  };
}

/** Текст файла карточек по реестру на диске — им же пользуется тест. */
export function renderCards() {
  return `${JSON.stringify(buildCards(JSON.parse(readFileSync(REGISTRY, 'utf8'))), null, 2)}\n`;
}

// Файл и импортируется тестом, и запускается руками: сборка ниже выполняется
// только при прямом запуске, иначе `pnpm test` переписывал бы реестр карточек.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const text = renderCards();
  if (process.argv.includes('--check')) {
    if (readFileSync(OUT, 'utf8') !== text) {
      console.error(`${OUT} разошёлся с ${REGISTRY}: пересоберите — node scripts/build-api-balance-cards.mjs`);
      process.exit(1);
    }
    console.log(`${OUT} совпадает с реестром`);
  } else {
    writeFileSync(OUT, text);
    const n = JSON.parse(text).vendors.reduce((a, v) => a + v.products.length, 0);
    console.log(`${OUT}: ${JSON.parse(text).vendors.length} вендор(ов), ${n} карточек`);
  }
}
