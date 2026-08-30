# Структурированные данные Schema.org — отчёт о реализации

Дата: 29.08.2026. Ветка: `claude/bizsoft-schema-org-audit-o755rr`.
Отчёт «до изменений»: `docs/seo/structured-data-audit.md`.

## 1. Изменённые файлы

| Файл | Что изменено |
| --- | --- |
| `src/lib/seo.ts` | productSchema: @id/url, null при «цене по запросу», brand без фолбэка; LocalBusiness слит с Organization по @id; logo у Organization; единый postalAddress(); itemListSchema: url + isPartOf |
| `src/config/site.ts` | `sellerAddress` — единственный источник публичного адреса для разметки |
| `src/pages/product/[slug].astro` | условный вывод Product JSON-LD; microdata-слой (атрибуты + meta/link, вёрстка не меняется) |
| `src/pages/catalog/index.astro`, `vendors/{index,figma,openai}.astro`, `vendors/zoho/[group].astro`, `vendors/zoho/[group]/[family].astro`, `compare/[slug].astro`, `catalog/ai/[sub].astro`, `catalog/[segment].astro`, `blog/[slug].astro` | дедупликация BreadcrumbList/FAQPage; publisher → @id; url категории в CollectionPage |
| `src/components/{VendorLanding,VendorGenericLanding,ZohoHub}.astro` | дедупликация: FAQPage — только компонент FAQ, BreadcrumbList — только Breadcrumbs |
| `tests/structured-data.test.ts` | 14 инвариантов слоя разметки (новый файл) |
| `scripts/ci/smoke.mjs`, `scripts/ci/stub-directus.mjs` | 8 смоук-проверок разметки; фикстуры «акция» и «цена по запросу» |
| `scripts/seo/check-structured-data.mjs` | проверка выборки страниц (локально и на проде) — новый |
| `.github/workflows/ops-schema-check.yml` | прод-QA разметки с раннера, отчёт в issue #22 — новый |
| `CLAUDE.md`, `docs/vendors-expansion-prompt.md` | регулярное правило: микроразметка при добавлении вендоров/товаров |

## 2. Архитектура

Один источник данных → две сериализации, согласованность закреплена тестами:

```
Directus → effectivePrice() → UI (PriceTag, data-price)
                            ↘ lib/seo.productSchema → JSON-LD
                            ↘ microdata-атрибуты карточки (только атрибуты и meta/link)
```

@id-граф: `#organization` (Organization; на главной и /contacts тот же узел
расширяется типом LocalBusiness) ← publisher WebSite, seller Offer,
publisher BlogPosting; `#website` ← isPartOf CollectionPage;
Product `@id = <canonical>#product`. BreadcrumbList — только из компонента
`Breadcrumbs` (совпадает с видимой цепочкой), FAQPage — только из `FAQ`.

## 3. Типы страниц и разметка

| Класс | Schema.org | Источник полей |
| --- | --- | --- |
| Главная | Organization+LocalBusiness (один узел), WebSite, ItemList | config/site.ts, data/vendors.ts |
| Каталог/категории | CollectionPage+ItemList, BreadcrumbList, FAQPage | Directus (categories, products) |
| Вендорные лендинги | CollectionPage+ItemList, BreadcrumbList, FAQPage | Directus + data/vendors.ts |
| Карточка товара | Product+Offer (JSON-LD и microdata), BreadcrumbList, FAQPage (при faq) | Directus, effectivePrice() |
| Товар «цена по запросу» | без Product/Offer (оба слоя); BreadcrumbList/FAQPage остаются | — |
| Блог | BlogPosting (publisher → @id), BreadcrumbList | контент-коллекция |
| Сравнения | FAQPage, BreadcrumbList (по одному) | data/comparisons.ts |
| Контакты | Organization+LocalBusiness (@id = #organization), BreadcrumbList | config/site.ts |

Ключевые поля Offer: price (= видимой цене), priceCurrency RUB,
availability InStock (цифровой товар доступен к заказу — как в фидах),
url = canonical, seller → @id, shippingDetails/hasMerchantReturnPolicy
(фактические значения цифровой поставки), priceValidUntil при акции.

Решения «не размечать»: SoftwareApplication (Яндекс не поддерживает,
Google требует aggregateRating — реальных отзывов нет), OfferCatalog
(отложен до решения руководителя по товарным фидам — обоснование в
аудите, §5), Review/AggregateRating (запрещены до появления реального
источника отзывов).

## 4. Результаты тестов

- `pnpm test` — 409/409 (37 файлов, из них 14 новых проверок разметки);
- `astro check` — 0 ошибок, 0 предупреждений;
- `pnpm smoke` — 29/29, включая 8 новых: валидность JSON-LD, ровно один
  Product/BreadcrumbList/FAQPage, цена/URL разметки = витрине и canonical,
  microdata = JSON-LD, «цена по запросу» без Product в обоих слоях,
  промо-цена с priceValidUntil, единый @id организации;
- `pnpm check:artifacts` — 5/5;
- контрольная выборка: `scripts/seo/check-structured-data.mjs` локально
  против собранного сайта — **32/32 страниц без нарушений** (все классы:
  главная, каталог, 2 категории, AI-подкатегория, 4 товара — обычный,
  второй вендор, акция, «по запросу», — 9 вендорных лендингов включая
  bespoke и Zoho-хаб, 2 сравнения, блог+2 статьи, 7 информационных).

## 5. Производительность (до → после, HTML без сжатия, локальная сборка)

| Страница | До | После | Δ |
| --- | --- | --- | --- |
| /product/chatgpt-business | 67 421 | 68 370 | +949 Б (microdata) |
| /vendors/adobe | 120 219 | 119 841 | −378 Б (снят дубль) |
| /catalog | 132 353 | 130 382 | −1 971 Б (снят дубль FAQPage) |
| / | 188 928 | 188 996 | +68 Б (logo, @id) |

Видимый DOM не изменился: добавлены только атрибуты и непечатаемые
meta/link/span[hidden]; CLS/LCP/INP не затрагиваются (нет новых видимых
узлов, стилей и скриптов). Время сборки не изменилось. Массовой разметки
списков (сотни Offer) не добавлялось.

## 6. Валидация Яндекса и Google

Из сессии валидаторы недоступны (egress закрыт), поэтому:

- синтаксис и инварианты проверены собственными тестами (см. §4);
- после мержа и деплоя запустить `ops-schema-check` (с main) — проверит
  контрольную выборку прод-URL и отчитается в issue #22;
- вручную прогнать представителей классов через
  [валидатор Вебмастера](https://webmaster.yandex.ru/tools/microtest/) —
  microdata карточки там видна (JSON-LD валидатор показывает не для всех
  типов) — и [Rich Results Test](https://search.google.com/test/rich-results).

Ожидаемые предупреждения (не ошибки):

- Google Merchant listings: нет aggregateRating/review — намеренно (нет
  реального источника отзывов, §20 задания);
- Google может отметить две записи Product (JSON-LD + microdata) — это
  одна и та же сущность из одного источника, согласованность закреплена
  смоуком; не invalid;
- FAQPage: rich result в Google отключён с мая 2026 — разметка оставлена
  для Яндекса и AI-краулеров, дубли сняты.

## 7. Rollback

`git revert` коммитов ветки в main → deploy.yml выкатит прежнюю разметку;
частичный откат возможен пофайлово (правки независимы). Данные, Directus,
фиды, аналитика не затронуты. Feature-flag не требуется: изменения — чистые
шаблоны без состояния.

## 8. Переобход после деплоя

Яндекс (ops-yandex-recrawl, квота 150/сутки) — 30 ключевых URL:

```
https://biz-soft.pro/,https://biz-soft.pro/catalog,https://biz-soft.pro/catalog/ai,https://biz-soft.pro/catalog/design,https://biz-soft.pro/vendors,https://biz-soft.pro/vendors/openai,https://biz-soft.pro/vendors/jetbrains,https://biz-soft.pro/vendors/figma,https://biz-soft.pro/vendors/zoom,https://biz-soft.pro/vendors/maxon,https://biz-soft.pro/vendors/adobe,https://biz-soft.pro/vendors/anthropic,https://biz-soft.pro/vendors/zoho,https://biz-soft.pro/vendors/canva,https://biz-soft.pro/vendors/miro,https://biz-soft.pro/product/chatgpt-business,https://biz-soft.pro/product/anthropic-team,https://biz-soft.pro/product/ableton-live-suite,https://biz-soft.pro/product/cubase-pro,https://biz-soft.pro/product/deepl-advanced,https://biz-soft.pro/product/fl-studio-producer,https://biz-soft.pro/product/lovable-pro,https://biz-soft.pro/product/lumion-pro,https://biz-soft.pro/how-we-work,https://biz-soft.pro/pricing,https://biz-soft.pro/contacts,https://biz-soft.pro/faq,https://biz-soft.pro/blog,https://biz-soft.pro/compare/chatgpt-vs-claude,https://biz-soft.pro/solutions
```

Google — Request Indexing вручную в Search Console (программного API для
обычных страниц у Google нет; Indexing API принимает только вакансии и
трансляции), ~20 URL:

```
/, /catalog, /catalog/ai, /vendors, /vendors/openai, /vendors/jetbrains,
/vendors/figma, /vendors/zoom, /vendors/adobe, /vendors/anthropic,
/product/chatgpt-business, /product/anthropic-team, /product/ableton-live-suite,
/product/cubase-pro, /product/deepl-advanced, /product/lumion-pro,
/how-we-work, /pricing, /blog, /compare/chatgpt-vs-claude
```

Sitemap менять не требуется (URL не менялись); canonical, robots, OG,
title/description, фиды и аналитика не затронуты (закреплено смоуком).

## 9. Мониторинг

Контрольные точки 24 ч / 72 ч / 7 д / 14 д / 30 д после деплоя:
Вебмастер — диагностика, сниппеты, индексирование; Search Console —
Product snippets, Merchant listings, Breadcrumb, invalid items,
показы/CTR. Отсутствие rich-сниппета само по себе ошибкой не считается.
