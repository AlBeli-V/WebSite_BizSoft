# Схемы данных и карта взаимосвязей

Что где лежит, что от чего зависит и что проверяется автоматически.

---

## Ключи связи

| Сущность | Ключ | Кто на него завязан |
|---|---|---|
| Вендор | `slug` | лендинг `/vendors/<slug>`, логотипы, иконки, контент, перелинковка |
| Вендор | `vendor` — точная строка | **выборка товаров из Directus**, `vendorSlug()` |
| Товар | `sku` | upsert при импорте |
| Товар | `slug` = `sku.toLowerCase()` | URL карточки, иконки товара, сравнения, `related_products` |
| Раздел | `category.slug` | плитка `/catalog`, фильтры, sitemap |

Как имя вендора превращается в слаг (`src/lib/vendor-links.ts`, `vendorSlug()`):

1. точное совпадение (в нижнем регистре) с `VENDORS[].vendor` или `VENDORS[].title`;
2. совпадение с `vendorLandings[].name` из `src/config/site.ts`;
3. ручная карта `AI_SLUGS`;
4. `slugifyVendor()` — нижний регистр, всё не `[a-z0-9]` в дефис, обрезка по краям.

Отсюда главное правило: **`products.vendor` в Directus обязан побуквенно совпадать
с `VENDORS[].vendor`.** Расхождение в символе — и лендинг пуст, а логотип падает
в монограмму. Ошибки при этом нет ни одной.

---

## `src/data/vendors.ts` — запись производителя

```ts
{
  slug: 'postman',
  vendor: 'Postman',          // точно как в Directus
  title: 'Postman',           // необязательно; по умолчанию = vendor
  legalName: 'Postman, Inc.',
  brandColor: '#FF6C37',
  site: 'https://www.postman.com',
  catSeg: 'development',      // существующий раздел каталога
  catLabel: 'Разработка',     // подпись для хлебных крошек
  domain: 'it',               // design | games | video | ai | it
  tagline: '…',               // одна фраза для плитки и meta
  about: '…',                 // абзац для лендинга
}
```

`catSeg` ведёт в хлебные крошки и в ссылку «Все товары раздела» на лендинге. Если
товары вендора расходятся по нескольким разделам, ставь тот, где лежит основная масса
и где ссылка не окажется пустой.

---

## `scripts/catalog/<slug>.json` — пакет товаров

```json
{
  "vendor_entry": { "…те же поля, что в VENDORS…" },
  "products": [
    {
      "sku": "POSTMAN-PROFESSIONAL",
      "slug": "postman-professional",
      "name": "Postman Professional",
      "official_name": "Postman Professional (Annual)",
      "category": "development",
      "license_type": "org",
      "short_description": "…",
      "description": "…",
      "keywords": "…",
      "features": ["…", "…", "…"],
      "base_price_usd": 348,
      "billing": "за пользователя в год",
      "min_quantity": 3,
      "price_confidence": "vendor-page",
      "source_url": "https://www.postman.com/pricing/",
      "checkout_url": "https://www.postman.com/pricing/",
      "checked_at": "2026-08-24",
      "notes": "…",
      "status": "published",
      "markup_coeff": null,
      "sort": null
    }
  ]
}
```

Что требует контракт (`tests/vendor-catalog.test.ts`):

- слаги товаров уникальны **по всем пакетам сразу**, не только внутри своего;
- `category` — из списка `ALLOWED_CATEGORIES`;
- `status` — только `published` или `draft`;
- у `published` непустые `name`, `short_description`, `description`, `keywords`,
  `billing` и `features` длиной не меньше трёх;
- у `draft` непустые `name`, `short_description`, `billing` — скрытая позиция страницы
  не имеет, но её название уходит в КП покупателю, поэтому должно быть человеческим;
- `base_price_usd`, если задана, строго больше нуля;
- цена у позиции со статусом не `published` допустима только при `status: draft`
  и пометкой про конфигуратор в `notes`;
- в названии нет слова `enterprise` — кроме позиций пайплайна Zoho (`me-`,
  `manageengine-`), где послабление подтверждено владельцем и требует цены со снимка.

Поля `source_url`, `checkout_url`, `checked_at`, `price_confidence` в схему Directus
не попадают — они остаются в репозитории как след аудита. Всё, чему нет места в схеме,
дублируется строкой в `reports/vendors/pricing-audit.md`.

---

## `scripts/content/<slug>.json` — контент лендинга

```json
{
  "summary": "…",
  "comparison": { "cols": ["…"], "rows": [{ "label": "…", "values": ["…"] }] },
  "decision": [{ "scenario": "…", "product": "…", "note": "…" }],
  "scenarios": [{ "title": "…", "text": "…" }],
  "faq": [{ "q": "…", "a": "…" }]
}
```

Все секции необязательны. Есть запись — `VendorLanding.astro` отрисует сравнение
тарифов, матрицу «какой выбрать», сценарии и свой FAQ; нет — покажет базовый шаблон.

Собирается командой `node scripts/build-vendor-content.mjs` в
`src/data/vendor-content.ts`. **Этот файл генерируется — руками не править.**

---

## Колонки импорта

`ops-import-vendors` собирает xlsx и шлёт в `/api/admin/import` (upsert по `sku`).
Признаёт эти колонки (`IMPORT_COLUMNS` в `src/lib/bulk-import.ts`):

```
sku, name, vendor, origin, category, license_type,
short_description, description, keywords,
base_price_usd, base_price_eur, peg_currency, markup_coeff, price_locked,
price, price_note, vat_percent, currency,
promo_price, promo_label, promo_start, promo_end,
features, status, sort
```

- `features` — через `|` или перевод строки.
- `origin` понимает и русские написания: «иностранное», «зарубежное», `foreign`.
- `license_type`: `org` / `individual` / `student`, тоже с русскими синонимами.
- `category` резолвится по слагу **или** по названию раздела. Не нашлось — строка
  получает `error` и не применяется.

Остальные SEO-поля (`for_whom`, `use_cases`, `faq`, `related_products`) заводятся
через админку Directus после импорта. Схему не расширять без согласования.

---

## Цена

Формула (`src/lib/pricing.ts`):

```
рубли = base_price_usd × курс_ЦБ × markup_coeff,  округление roundPrice('to1')
```

- `markup_coeff` по умолчанию **1.85**; у коробочных ключей Microsoft — **1.0**.
- Курс ЦБ подтягивается сам, в текстах и ценах его не хардкодить.
- Пустая `price` — штатный режим «Цена по запросу», у такой карточки нет прямой покупки.
- Скидки — только через `promo_price` / `promo_start` / `promo_end`.
- Ежедневная переоценка всех привязанных товаров — воркфлоу `ops-currency-refresh`;
  `price_locked` она не трогает.

---

## Что подхватывается само

Трогать не нужно, оно читает живые данные:

- маршрут `/vendors/<slug>` — рендерит любой слаг из `VENDORS`;
- sitemap — вендоры и товары приходят из базы;
- шапка, `/vendors`, главная, `/catalog` — живые списки;
- рублёвая цена — переоценка по курсу ЦБ;
- иконка вендора как запасная для товара без своей иконки.

## Что руками

- `src/data/vendors.ts`, `scripts/content/<slug>.json`, `src/data/vendor-solutions.ts`;
- `src/data/popular.ts` — карусель на главной, ручной список;
- `STATIC_ROUTES` в `src/pages/sitemap.xml.ts` — только для bespoke-страниц;
- `ALLOWED_CATEGORIES` в тесте — при заведении нового раздела;
- сам раздел в Directus — воркфлоу `ops-categories`.

---

## Тесты как контракт

| Файл | Что стережёт |
|---|---|
| `tests/vendor-catalog.test.ts` | состав партии: слаги, стоп-лист, категории, полнота полей, запреты |
| `tests/vendor-solutions.test.ts` | перелинковка вендор ↔ решение существует и симметрична |
| `tests/catalog-categories.test.ts` | у раздела есть текст и своя иконка, товары лежат в описанных разделах |

Вводишь новое правило — допиши его в тест **с комментарием, кто и когда решил**.
Так уже зафиксированы послабления по SOLIDWORKS, Atlassian, TeamViewer и по редакциям
Enterprise у ManageEngine. Правило без объяснения через месяц выглядит произволом,
и следующий человек снимет его «как лишнее».
