# Аудит структурированных данных Schema.org (до изменений)

Дата: 29.08.2026. Ветка: `claude/bizsoft-schema-org-audit-o755rr`.
Задача: единый слой Schema.org с приоритетом Яндекса и максимальной
совместимостью с Google, без изменения UI, цен, canonical и бизнес-логики.

## 1. Что уже есть (инвентаризация кода)

Вся разметка сайта — **JSON-LD** (компонент `src/components/JsonLd.astro`,
построители в `src/lib/seo.ts`). Microdata и RDFa в шаблонах нет
(грep по `itemscope|itemtype|itemprop` — ноль вхождений в src).
OpenGraph/Twitter — отдельно в `SeoHead.astro`, не пересекается.

Существующие типы и где они выводятся:

| Тип | Построитель | Страницы |
| --- | --- | --- |
| Organization (`#organization`) | `organizationSchema()` | все (BaseLayout) |
| WebSite (`#website`) | `websiteSchema()` | все (BaseLayout) |
| LocalBusiness (`#localbusiness`) | `localBusinessSchema()` | главная, /contacts |
| Product + Offer | `productSchema()` | /product/[slug] |
| BreadcrumbList | `breadcrumbSchema()` | компонент Breadcrumbs (все внутренние) + ещё раз в ld-массивах ряда страниц |
| FAQPage | `faqSchema()` | компонент FAQ + ещё раз в ld-массивах ряда страниц |
| CollectionPage (+ItemList) | `collectionPageSchema()`, `itemListSchema()`, inline | каталог, категории, вендорные лендинги, /vendors |
| ItemList (сервисы) | inline | главная |
| BlogPosting | inline | /blog/[slug] |

Фактический HTML прода проверен через `ops-probe` (issue #22,
29.08.2026 10:39): главная — 2 блока `application/ld+json`, карточка
товара и лендинг вендора — по 4 блока. Совпадает с кодом: прод отдаёт
текущую разметку из main, расхождений «код ↔ прод» нет.

## 2. Найденные проблемы

### П1. Двойной BreadcrumbList на одной странице (критично)

Компонент `Breadcrumbs.astro` сам выводит `breadcrumbSchema([Главная, …])`.
Одновременно те же страницы кладут `breadcrumbSchema(crumbs)` (без «Главной»
и иногда с другим составом) в свой ld-массив. Итог — **две разные
навигационные цепочки** на странице; поисковик волен выбрать любую.

Затронуты: `vendors/index`, `vendors/figma`, `vendors/openai`,
`vendors/zoho/[group]`, `vendors/zoho/[group]/[family]`,
`compare/[slug]`, `catalog/ai/[sub]`, компоненты `VendorLanding`,
`VendorGenericLanding`, `ZohoHub`.

На `/compare/*` вдобавок ld-цепочка (`Каталог → AI-сервисы → Сравнения →
X`) не совпадает с видимой (`Главная → AI-сервисы → X`) — прямое
нарушение принципа «разметка = видимый контент».

### П2. Двойной FAQPage на одной странице (критично)

Компонент `FAQ.astro` по умолчанию выводит `faqSchema(items)`. Страницы
`catalog/index`, `vendors/figma`, `vendors/openai`, компоненты
`VendorGenericLanding`, `ZohoHub`, `compare/[slug]` кладут тот же FAQPage
ещё раз в свой ld-массив → **два одинаковых FAQPage** на странице.
Только `VendorLanding` делает правильно (`schema={false}`).

### П3. Offer без price у товаров «цена по запросу»

`productSchema()` при `price <= 0` выводит Offer с `priceCurrency`, но без
`price`. Для Google это invalid item (у Product нет ни offers.price, ни
review, ни aggregateRating), для строгой разметки Яндекса price обязателен.
В каталоге 24 такие карточки (выгрузка ops-export-products, 29.08.2026:
`price: req` — Claude Enterprise, Canva Enterprise, GitLab Premium и др.).

### П4. Разрозненные сущности организации

- `LocalBusiness` живёт под отдельным `@id` (`#localbusiness`) и не связан
  с `Organization` (`#organization`) — две независимые сущности BIZSoft
  на главной и /contacts.
- Адрес захардкожен в `seo.ts` дважды (в двух функциях) и отличается от
  `seller.address` в `config/site.ts`: в разметке есть номер офиса «378»,
  которого нет на видимой странице /contacts.
- У Organization нет `logo` (рекомендация Google), у Product.seller связь
  через `@id` есть — это хорошо.

### П5. Product без url/@id; brand-фолбэк

- У Product нет `@id` и `url` — Offer.url есть (исправлен в PR #195), но
  сама сущность Product не привязана к canonical.
- `brand` при пустом vendor подставляет BIZSoft — продавец не является
  производителем, это фиктивные данные.

### П6. Мелкое

- `itemListSchema()` (CollectionPage категорий) без `url`/`isPartOf`.
- BlogPosting: publisher — inline-объект, не связан с `#organization`.
- FAQPage продолжает выводиться повсеместно: Google с мая 2026 полностью
  убрал FAQ rich results (разметка осталась валидной и полезной для
  Яндекса — быстрые ответы на мобильной выдаче — и для AI-краулеров).
  Ошибкой не является; дубли (П2) — являются.

## 3. Карта типов страниц → целевая разметка

| Класс | Пример | Сейчас | Целевое состояние |
| --- | --- | --- | --- |
| A. Главная | `/` | Org, WebSite, LocalBusiness, ItemList | то же, LocalBusiness слит с Org через @id |
| B. Каталог | `/catalog` | Org, WebSite, CollectionPage, ItemList, FAQPage×2, Breadcrumb | дедуп FAQ; остальное без изменений |
| C. Категории | `/catalog/[segment]`, `/catalog/ai/[sub]` | CollectionPage+ItemList, Breadcrumb (на ai-sub — двойной) | дедуп Breadcrumb |
| D. Производитель | `/vendors/*` | CollectionPage+ItemList, FAQPage (иногда ×2), Breadcrumb×2 | дедуп; ItemList остаётся |
| E. Товар/SKU | `/product/[slug]` | Product+Offer, Breadcrumb, FAQPage | Product c @id/url; «цена по запросу» — без Product; + microdata-слой (см. §5) |
| F. SaaS/ПО | те же /product/* | Product | Product (SoftwareApplication не добавляем, см. §6) |
| G. Информационные | /blog/*, /compare/*, /faq, /how-we-work | BlogPosting, FAQPage (на compare ×2), Breadcrumb (×2) | дедуп; publisher → @id |
| H. Организация | /contacts, /about, /documents | LocalBusiness (contacts), Breadcrumb | LocalBusiness слит с Org |

## 4. Требования поисковиков (проверено 29.08.2026)

Ограничение сессии: `yandex.ru` и `developers.google.com` закрыты
egress-прокси; страницы справки Яндекса вдобавок рендерятся JS (проверено
ops-probe: `content-length: 0` в первом ответе). Требования собраны через
веб-поиск по официальным страницам и сверены минимум по двум источникам;
ключевые официальные страницы:

- Яндекс: [Информация о товарах](https://yandex.ru/support/webmaster/ru/supported-schemas/goods-prices),
  [Строгая микроразметка — Каталоги](https://yandex.ru/support/webmaster/ru/supported-schemas/catalogs.html),
  [JSON-LD](https://yandex.ru/support/webmaster/ru/json-ld/about.html).
- Google: [Product snippet](https://developers.google.com/search/docs/appearance/structured-data/product-snippet),
  [Merchant listing](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing),
  [Software app](https://developers.google.com/search/docs/appearance/structured-data/software-app),
  [FAQ deprecation](https://www.searchenginejournal.com/google-drops-faq-rich-results-from-search/574429/).

Выжимка:

**Яндекс.**
- Товары: схемы Product/Offer/AggregateOffer; у Product обязателен
  `offers`; у Offer — цена и валюта; изображение обязательно.
- JSON-LD официально подтверждён для навигационных цепочек (Breadcrumb)
  и вопросов-ответов; для товарной строгой разметки обработка JSON-LD
  **не гарантируется** — надёжный формат товарной разметки — microdata.
- Строгая разметка каталогов: один OfferCatalog на странице, без вложенных
  списков; все поддерживаемые поля обязательны (OfferCatalog: name,
  description, image; Offer: url, name, description, image, availability,
  price, priceCurrency).
- Валидатор Вебмастера надёжно показывает microdata; JSON-LD в нём
  отображается не для всех типов.
- Товарные данные Яндекс также берёт из YML-фидов — механизм в проекте
  готов (`src/lib/feeds/*`), открыт только фид Директа (решение
  руководителя 29.08.2026, `docs/yandex-feeds.md`).

**Google.**
- Product snippet: у Product обязателен `name` + одно из
  `offers`/`review`/`aggregateRating`; в Offer обязателен `price`
  (или priceSpecification.price).
- Merchant listing (страница, где товар можно купить): Offer с `price`>0,
  `priceCurrency`, рекомендованы availability, shippingDetails,
  hasMerchantReturnPolicy (у нас уже есть, значения фактические:
  цифровая поставка, возврата активированной лицензии нет).
- FAQ rich results полностью отключены с мая 2026 (разметка валидна,
  но сниппет не даёт); HowTo отключён ранее.
- SoftwareApplication rich result требует `aggregateRating` — у BIZSoft
  реальных отзывов нет, значит право на этот rich result не получить.
- Форматы: JSON-LD рекомендуем, microdata полностью поддерживается.

## 5. Таблица совместимости и конфликты

| Вопрос | Яндекс | Google | Решение |
| --- | --- | --- | --- |
| Формат товарной разметки | microdata гарантированно; JSON-LD не гарантирован | JSON-LD рекомендован, microdata поддерживается | Оба сериализуются из одного источника: JSON-LD (для Google и общих потребителей) + microdata-слой на карточке товара (для Яндекса). Не «две системы»: одна модель данных → две сериализации, согласованность закрепляется автотестом |
| Offer без цены | price обязателен | price обязателен | «Цена по запросу» → Product/Offer не размечаем вовсе (24 карточки) |
| availability | обязательна в строгой разметке | рекомендована | `InStock` — фактически верно: цифровой товар можно заказать сейчас (фиды уже отдают `available="true"`) |
| shippingDetails / возвраты | не используется | рекомендовано для merchant listing | оставить существующие фактические значения (цифровая поставка 0–1 день, возврат не предусмотрен) — Яндексу не мешают |
| FAQPage | поддерживает (быстрые ответы) | rich result отключён, разметка валидна | оставить, но убрать дубли |
| BreadcrumbList | поддерживает, в т.ч. JSON-LD | поддерживает | один BreadcrumbList на страницу, совпадает с видимой цепочкой |
| OfferCatalog | строгая microdata-разметка витрин | не использует | отложить (см. ниже) |
| SoftwareApplication | не поддерживает | требует aggregateRating | не внедрять (см. §6) |

Семантических конфликтов «Яндекс против Google» не обнаружено: все
требования совместимы в одном слое. Единственная развилка — формат
(microdata для Яндекса против JSON-LD для Google) — решается двойной
сериализацией одной модели на карточке товара.

**OfferCatalog (строгая разметка каталогов)** — рассмотрен и отложен:

1. Строгая схема требует у каждого Offer `description` и `image`, которых
   нет в видимой вёрстке карточек-плиток; выводить их скрытыми meta —
   расхождение с видимым контентом.
2. На vendor-страницах уже есть ItemList (ссылки на карточки), а товарные
   данные Яндекс получает из карточек товара и YML-фидов; фиды открываются
   только по команде руководителя — публикация каталожной строгой
   разметки логично идёт тем же решением, не раньше.
3. Требование «один размеченный список на странице без вложенных» на
   Zoho-хабе и сегментных страницах с несколькими блоками потребует
   перестройки списков.

Возврат к OfferCatalog — отдельным этапом после решения руководителя по
товарным фидам.

## 6. SoftwareApplication / WebApplication — решение

Не внедряем и не заменяем Product:

- Яндекс товарные сниппеты строит по Product/Offer; SoftwareApplication
  в поддерживаемых схемах Вебмастера отсутствует.
- Google для software-rich-result требует aggregateRating; реальных
  отзывов нет (см. §20 задания — рейтинги не выдумываем), т.е. право на
  rich result недостижимо, а замена Product → SoftwareApplication лишила
  бы страницы товарного сниппета.
- Вложенная модель (Product + isRelatedTo/subjectOf SoftwareApplication)
  умножает сущности без пользы для сниппетов и нарушает принцип
  «минимум типов — однозначная семантика».
- Компромисс без риска: `Product.additionalType = schema.org/SoftwareApplication`
  не добавляем — Google игнорирует, Яндексу не нужно; category у Product
  уже передаётся.

## 7. Целевая архитектура

Единый слой, один источник данных:

```
Directus (товар) → lib/pricing.effectivePrice → UI (PriceTag/карточка)
                                             ↘ lib/seo.productSchema (JSON-LD)
                                             ↘ microdata-атрибуты карточки
```

- `@id`-граф: `#organization` (Organization, сайт-wide) ← `publisher` у
  WebSite, `seller` у Offer, publisher у BlogPosting; `#website` ←
  isPartOf у CollectionPage; Product `@id = <canonical>#product`.
- LocalBusiness становится тем же узлом организации:
  `@type: ['Organization','LocalBusiness']`, `@id: #organization` —
  на главной/контактах узлы сливаются по @id, противоречий нет.
- BreadcrumbList — только из компонента `Breadcrumbs` (совпадает с
  видимой цепочкой, включая «Главная»).
- FAQPage — только из компонента `FAQ` (рядом с видимым контентом).
- Product: `@id`, `url`, name, sku, image, description, brand (только
  реальный vendor), category, offers{price, priceCurrency, availability,
  url, seller@id, shippingDetails, hasMerchantReturnPolicy,
  priceValidUntil при акции}. При `price <= 0` — Product не выводится.
- Microdata на карточке товара: атрибуты на существующих элементах
  (h1 → name, артикул → sku) + невидимые `meta`/`link` itemprop для
  price/priceCurrency/availability/url/image/description в существующем
  DOM-контейнере. Видимая вёрстка не меняется (только атрибуты и
  meta-теги, не участвующие в рендере).

## 8. Источники данных полей

| Поле | Источник | Примечание |
| --- | --- | --- |
| name, sku, description, vendor, category | Directus `products` | как в UI |
| price | `effectivePrice()` (учёт акции) | та же функция, что у PriceTag и «Итого» |
| priceCurrency | `product.currency` (RUB) | |
| availability | InStock для товаров с ценой | цифровой товар доступен к заказу |
| image | галерея товара; иначе `/og-default.png` | тот же образ, что в og:image |
| Offer.url / Product.@id | canonical `/product/<slug>` | функция `canonicalUrl` |
| Организация | `config/site.ts` (seller, workingHours) | адрес приводится к публичному виду без номера офиса |
| priceValidUntil | `promo_end` | только при активной акции |

## 9. Риски

1. **Двойная сериализация Product (JSON-LD + microdata)** — Google увидит
   две записи об одном товаре. Это допустимо (не invalid), но требует
   строгой согласованности → автотест сверяет microdata с JSON-LD и с
   видимой ценой. Откат — одним revert.
2. **Снятие Product с «цены по запросу»** (24 карточки) — потеря товарного
   сниппета у этих страниц. Альтернатива (фиктивная цена) запрещена.
3. **Слияние LocalBusiness с Organization** — изменение @id существующего
   узла; поисковики переобойдут и пересоберут граф, переходный период
   безопасен (тип/данные не противоречат прежним).
4. **Удаление дублей Breadcrumb/FAQ** — сниппеты могли строиться по любой
   из копий; остаётся копия, совпадающая с видимым контентом, риск
   минимален.
5. Рост HTML на карточке — только meta-теги микроданных, ≤ ~0,5 КБ на
   страницу; на списках ничего не добавляем.

## 10. План тестирования

1. Юнит-тесты построителей (`tests/structured-data.test.ts`): сценарии
   цен (обычная, акция, по запросу), @id/URL-инварианты, отсутствие
   фиктивного brand, абсолютность URL, RUB.
2. Расширение смоука (`scripts/ci/smoke.mjs` + фикстуры stub-directus):
   на собранном сайте парсится каждый `ld+json`, проверяется:
   валидный JSON, ровно один BreadcrumbList/FAQPage на страницу,
   `Offer.price` = данным stub'а = `data-price` кнопки, `Offer.url` =
   canonical, у «цены по запросу» нет Product, microdata-цена =
   JSON-LD-цене.
3. `pnpm verify` (tests + typecheck + build + check-artifacts + smoke).
4. Визуальная неизменность: microdata добавляет только атрибуты и
   meta/link (display:none по умолчанию не требуется — они не
   рендерятся); сравнение видимого DOM в смоуке по отсутствию новых
   видимых узлов.
5. Контрольная выборка ≥30 страниц: локально на расширенных фикстурах
   (все классы страниц), после деплоя — скрипт
   `scripts/seo/check-structured-data.mjs` по 30+ прод-URL (через
   workflow с main), плюс ручная проверка валидатором Вебмастера и
   Rich Results Test представителей классов.

## 11. План rollout

1. Этот PR: правки слоя + тесты + отчёты (ветка → ревью → merge в main).
2. Деплой штатный (deploy.yml при пуше в main).
3. Прод-QA: ops-probe/скрипт проверки по контрольным URL, валидатор
   Яндекса, Rich Results Test.
4. Переобход: ops-yandex-recrawl ~30 ключевых URL (квота 150/сутки);
   Google — Request Indexing вручную в Search Console (API для этого
   нет), список URL в отчёте о реализации.
5. Мониторинг 24 ч / 72 ч / 7 д / 14 д / 30 д: Вебмастер (диагностика,
   сниппеты), Search Console (Product snippets, Merchant listings,
   Breadcrumb, invalid items).

## 12. План rollback

Feature-flag не вводим (изменения — чистые шаблоны без состояния):
`git revert` коммита в main → deploy.yml автоматически выкатит прежнюю
разметку. Частичный откат возможен по файлам (seo.ts / отдельные
страницы) — правки независимы. Данные/Directus/фиды не затрагиваются.
