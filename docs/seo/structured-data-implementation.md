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

## 10. Инцидент 08.09.2026: «Поле "brand" дублируется»

Что сообщил Google. Search Console, отчёт «Данные о товарах продавца»:
`/product/mj-standard` — один проверенный элемент «Midjourney Standard»,
одна критичная проблема «Поле "brand" дублируется» и три незначительные
(в том числе «Поле "sku" дублируется»). Дата выявления 01.09.2026,
сканирование 01.09.2026 01:48:46.

Разбор. Карточка выводит товар двумя сериализациями — JSON-LD и microdata,
и обе несли общий идентификатор узла `<canonical>#product` (`@id` у JSON-LD,
`itemid` у microdata). Google связывает узлы разных синтаксисов по общему
идентификатору и сливает их в одну сущность — поэтому в отчёте один элемент,
а не два, и поэтому каждое общее поле пришло дважды. Значения слоёв
совпадают (это закреплено смоуком), дефект — исключительно в имени узла.

Масштаб. Проверка собранного сайта по всем 224 адресам sitemap нашла тот же
дефект на каждой карточке товара с ценой (включая подарочные карты — там
Product+AggregateOffer) и, в другом виде, на главной и в «Контактах»: там
рядом с узлом организации из BaseLayout выводился второй узел с тем же
`@id` (`localBusinessSchema`), повторявший `name`, `url`, `email`,
`telephone`, `address`.

Исправление:

- `src/pages/product/[slug].astro` — microdata-слой больше не несёт `itemid`;
  слои остаются двумя независимыми сериализациями одного товара;
- `src/lib/seo.ts` — `localBusinessSchema()` стал надмножеством
  `organizationSchema()` (тот же узел, плюс график работы, ценовой диапазон,
  картинка), а `BaseLayout` получил проп `localBusiness` и выводит узел
  организации ровно один раз; главная и «Контакты» второй узел больше не
  выводят (и заодно получили `legalName`, `taxID`, `logo`, `contactPoint`,
  которых у локального узла раньше не было);
- проверки: три смоук-проверки и правило «повтор идентификатора узла» в
  `scripts/seo/check-structured-data.mjs` (работает и на проде через
  `ops-schema-check`), тест инварианта в `tests/structured-data.test.ts`.

Влияние на другие системы. Яндекс: microdata карточки не изменилась по
составу полей — `itemid` в товарной разметке Яндекс не использует, и других
потребителей у этого атрибута в проекте нет (проверено поиском по коду);
узел организации стал полнее. Товарные фиды, WebMCP, canonical, sitemap,
видимая вёрстка и аналитика не затронуты.

После деплоя: в Search Console по отчёту «Данные о товарах продавца» нажать
«ПРОВЕРИТЬ ИСПРАВЛЕНИЕ» (валидация занимает до двух недель) — API для этого
нет; переобход карточек Яндексом — `ops-yandex-recrawl`, оповещение
IndexNow — `ops-indexnow`.

### 10.1. Догон: рекомендованные поля Offer в microdata

Проверка опубликованной версии `/product/mj-standard` в Search Console
08.09.2026, 16:11 подтвердила исправление: «Обнаружено 2 элемента без ошибок»
— то есть слои снова читаются как две независимые записи одного товара, а не
как один узел с задвоенными полями.

У microdata-элемента остались два жёлтых предупреждения: «Отсутствует поле
"hasMerchantReturnPolicy" (необязательно)» и «Отсутствует поле
"shippingDetails" (необязательно)». Это не следствие правки: у JSON-LD оба
поля были всегда (`offerLogistics`), а у microdata их не было никогда —
просто пока слои сливались в один узел, поля приходили из JSON-LD и
предупреждения не было.

Решение руководителя: дополнить microdata теми же фактическими значениями
(возврат активированной лицензии не предусмотрен; доставка электронная —
0 ₽, 0–1 день, Россия). Добавлен компонент
`src/components/OfferLogisticsMicrodata.astro`, который читает ту же функцию
`offerLogistics()`, что и JSON-LD, — источник у слоёв один, разойтись им не с
чего. Компонент подключён к обычному Offer и к AggregateOffer подарочной
карты; на «цене по запросу» Offer нет вовсе, поэтому нет и этих полей.
Видимая вёрстка не меняется: только `meta`/`link` в обёртках с `hidden`,
около 0,6 КБ на карточку.

Закреплено тремя смоук-проверками: совпадение значений слоёв, наличие полей у
подарочной карты, их отсутствие на «цене по запросу».

### 10.2. Проверяльщик научился подарочным картам

Прогон `ops-schema-check` 08.09.2026 после выкатки §10.1 покраснел на
`/product/app-store-itunes-gift-card`: «Offer.price: undefined; видимая цена
35911 ≠ разметке undefined». Разметка карты при этом верна — у неё
`AggregateOffer` (lowPrice 1895, highPrice 11275, offerCount 3), цены у карты
нет вовсе. Ошибка была в проверке: она знала только обычный Offer, а
подарочные карты в контрольную выборку раньше не входили — то есть их
разметку на проде не проверял никто.

`scripts/seo/check-structured-data.mjs` получил ветку для `AggregateOffer`:
lowPrice > 0, highPrice ≥ lowPrice, offerCount ≥ 1, совпадение lowPrice и
highPrice с microdata и попадание всех видимых цен номиналов (`data-price`) в
объявленный диапазон. Заодно добавлена проверка, что `hasMerchantReturnPolicy`
и `shippingDetails` есть в обоих слоях, а подарочная карта включена в
контрольную выборку — и в скрипте, и в списке workflow.

## 11. Письма Search Console 15.09.2026 и недельный сторож

Что сообщил Google. Два письма в один день по ресурсу biz-soft.pro:

- «Данные о товарах продавца» — три незначительные проблемы: отсутствует
  `hasMerchantReturnPolicy` (в offers), отсутствует `shippingDetails`
  (в offers), поле `sku` дублируется;
- «Описания товара» — две незначительные: отсутствует `aggregateRating`,
  отсутствует `review`.

Что показал прод. Проба `ops-probe` (прогон #260, `/product/chatgpt-business`,
15.09.2026 15:53 МСК, HTTP 200): `hasMerchantReturnPolicy` — 2 вхождения,
`shippingDetails` — 2 (по разу в JSON-LD и в microdata), `sku` — 2 (`"sku":`
в JSON-LD и `itemprop="sku"` в microdata), `aggregateRating` и `review` — 0.

Чтение. Первые два пункта письма на живой странице закрыты: поля появились
с выкаткой §10.1 и на проде с 13.09.2026 — письмо описывает состояние
индекса до неё. Третий пункт того же письма относится к тому же состоянию:
дубль `sku` на странице возможен только как следствие двух сериализаций
одного товара (других источников артикула в разметке нет), а живой тест
Google 08.09.2026 после снятия общего идентификатора узла показал «2 элемента
без ошибок» — без дублей. Второе письмо — ожидаемое предупреждение из §6:
отзывов о товарах у проекта нет ни одного.

Решения руководителя 15.09.2026:

1. **Разметку не трогать**, дождаться переобхода; в Search Console нажать
   «ПРОВЕРИТЬ ИСПРАВЛЕНИЕ» по обоим отчётам (программного API нет).
   Контрольная точка — тикет `reports/seo/tasks/SD-001-merchant-listings-revalidate.md`
   (созревает 29.09.2026). Если дубль `sku` переживёт переобход, отложенный
   шаг известен: снять `meta itemprop="sku"` из microdata-слоя — Яндексу
   артикул в товарной микроразметке не нужен, в JSON-LD и в видимых
   параметрах карточки он останется.
2. **`aggregateRating` и `review` не заводить.** Фиктивные рейтинги запрещены
   правилом; сбор реальных отзывов покупателей — отдельный проект, а отзывы о
   компании Google как отзывы о товаре не принимает.
3. **Завести недельный сторож.** `ops-schema-check` получил два cron-слота
   (понедельник, 06:41 и 07:29 МСК), очередь и идемпотентность по дню:
   контрольный слот спрашивает у API, был ли сегодня успешный прогон по
   расписанию, и при успехе не делает ничего. Тишина по правилу операционных
   прогонов: при успехе прогон молчит, при сбое — одна запись в журнал-issue
   #22 со ссылкой на прогон; ручной запуск отчитывается всегда.

Повод для сторожа. Оба раза о состоянии разметки мы узнавали письмом Google —
01.09 (дубль идентификатора узла) и 15.09, — хотя проверка с нужными
инвариантами написана с 29.08 и запускалась только руками. Между выкаткой и
письмом проходит неделя и больше, и всё это время расхождение живёт в проде
незамеченным.
