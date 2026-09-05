# Подарочные карты (product_type = gift_card)

Заведено 05.09.2026 по заданию руководителя: первый товар — Apple App Store &
iTunes Gift Card для трёх регионов (Россия, Казахстан, Турция). Механика
общая: любая цифровая карта с регионом и номиналом ложится в ту же модель
без новой архитектуры цен и интерфейса.

## Модель

- **Родитель** — обычная карточка Directus со страницей `/product/<slug>`
  (`product_type = gift_card`, `parent_sku` пуст). Несёт описание, мету,
  цену «от» (`price_from = true`; закупка родителя = минимальная закупка
  варианта, чтобы «от» переоценивалось вместе с вариантами).
- **Варианты** — по строке Directus на каждый номинал каждого региона:
  `parent_sku` = артикул родителя, `region_code` (RU/KZ/TR), `region_name`,
  `denomination`, `denomination_currency` (RUB/KZT/TRY), `availability`
  (`in_stock` | `limited` | `out_of_stock`), закупка в `base_price_usd`
  (это и есть cost_usd задания), `markup_coeff = 3.0`.
- Вариант без денежного номинала (подписка Discord: тариф и срок) несёт
  `variant_label` — подпись на витрине; `denomination` тогда — срок в месяцах
  для сортировки, `denomination_currency = MONTH`.
- Регион `GLOBAL` — код без привязки к стране; порядок регионов на витрине —
  `REGION_ORDER` (RU, KZ, TR), остальные после них по алфавиту.
- Артикулы: родитель `…-GIFT-CARD`, вариант `…-GIFT-CARD-<регион>-<номинал|код>`
  (`APP-STORE-ITUNES-GIFT-CARD-RU-1000`, `DISCORD-NITRO-GIFT-CARD-GLOBAL-NITRO-12M`).
  По этому шаблону `productNoindex()`
  закрывает варианты от индексации: в sitemap, фиды и поиск идёт только
  родитель. Страница варианта (`/product/<slug варианта>`) отдаёт 301 на
  родителя с `?sku=<вариант>` — страница открывается с выбранным номиналом,
  canonical без параметров.
- Списки витрины (каталог, лендинг вендора, поиск на сайте) варианты не
  показывают — `listingProducts()`; корзина, КП и WebMCP работают с
  вариантом как с обычной позицией (у него свой артикул и цена).

## Цена

Стратегия одна формула с другим коэффициентом: `price = base_price_usd ×
курс USD ЦБ × 3.00` (`GIFT_CARD_MARKUP_COEFF`, ровно ×3, не «+300 %»).
Номинал в расчёте не участвует. Переоценивает тот же `ops-currency-refresh`
(коэффициент хранится в строке варианта — импорт ставит его из пакета).
Округление `to1`, НДС включён в цену (5 %), формат `formatRub`. Закупка не
попадает в HTML, WebMCP и фиды (проверки: `tests/gift-cards.test.ts`,
смоук «закупка попала в HTML»).

## Страница

`src/pages/product/[slug].astro` при `product_type = gift_card` отдаёт
селектор `GiftCardSelector.astro` (шаг 1 — регион, шаг 2 — номиналы по
убыванию, у каждого — цена BIZSoft в рублях) и редакторские разделы из
`src/data/gift-cards.ts` (регионы, «Что такое…», активация, FAQ). Порядок
номиналов задаёт `src/lib/gift-cards.ts` (`denomination DESC`), не база.
Разметка — один Product с AggregateOffer (`giftCardProductSchema`) в JSON-LD
и microdata; FAQPage — компонент FAQ.

Наличие: `out_of_stock` показан, но не выбирается; `limited` — с пометкой.
Автоматического подбора комбинации кодов нет: учёта остатков в архитектуре
нет, заказ на отсутствующий номинал исполняется менеджером несколькими
кодами региона (текст об этом — на странице и в описании варианта).

## Как заводить новую карту

1. Запись вендора в таблице `scripts/build-gift-card-package.mjs` (родители,
   регионы, `[номинал, закупка USD]` или `[срок, закупка, { code, label }]`
   для подписок) и `node scripts/build-gift-card-package.mjs` — пакет
   `scripts/catalog/<vendor>.json` собирается из неё (изменились закупки —
   правится таблица, пересобирается пакет, дальше штатный импорт). Заведены:
   Apple (RU/KZ/TR), Airalo, Binance (три карты по активу), Discord.
2. Запись в `VENDORS` (`catSeg: 'gift-cards'`, `domain: 'gift'`),
   `VENDOR_LEGAL`, контент лендинга `scripts/content/<slug>.json`, иконка
   вендора (skill `add-logo-and-icons`).
3. Редакторский контент страницы — запись в `src/data/gift-cards.ts` по
   слагу родителя.
4. Мета родителя — `data/seo/product-descriptions.json` → `ops-apply-descriptions`.

## Порядок на проде (все workflow — только с main)

1. `ops-directus-schema` (schema-only) — поля `product_type`, `parent_sku`,
   `region_code`, `region_name`, `denomination`, `denomination_currency`,
   `availability`, `variant_label`. Процесс сайта, стартовавший до миграции,
   запоминает «полей нет» до перезапуска — после схемы нужен редеплой
   (`deploy` с main вручную). До прогона сайт работает: слой `directus.ts` запрашивает
   их с откатом.
2. `ops-categories` (`apply=false`, затем `true`) — раздел `gift-cards`.
3. `ops-import-vendors` (`apply=false`, затем `true`) — 1 родитель + 28
   вариантов; курс ЦБ подтягивается перед импортом, цены считаются сразу.
4. `ops-apply-descriptions` (`only=app-store-itunes-gift-card`) — мета.
5. Проверить `/sitemap.xml` (родитель есть, вариантов нет, `/vendors/apple`,
   `/catalog/gift-cards`), затем `ops-yandex-recrawl`.

## Кластер материалов Apple (05.09.2026)

Заведён вне очереди по поручению руководителя после замера спроса
(`ops-sam-demand`, набор `data/seo/apple-gift-card-probe.json`, отчёт
`reports/seo/wordstat/apple-gift-card-demand-2026-09-05.*` в `seo-data`).
Разбор спроса, конкурентов и план — `docs/marketing/apple-gift-card-plan-2026-09.md`.

- Карточка `/product/app-store-itunes-gift-card`: секции «Почему после
  1 апреля 2026 года нужна именно Gift Card», «Для компании: три сценария»,
  «Сколько кодов нужно на год подписок» и пять FAQ (`src/data/gift-cards.ts`);
  мета переписана под спрос («подарочная карта apple» ≫ «apple gift card») в
  `data/seo/product-descriptions.json` — в прод через `ops-apply-descriptions`.
- Лендинг `/vendors/apple` (`scripts/content/apple.json`): summary, сценарий
  «Продление подписок после 1 апреля 2026 года», два FAQ.
- Статьи (тег «подарочные карты» открывает страницу тега при трёх и более
  материалах): `kak-popolnit-app-store-v-rossii` (обновлена),
  `apple-prekratila-priem-platezhey-v-rossii-kak-prodlit-podpiski`,
  `apple-gift-card-sotrudnikam-podarok-ot-kompanii`,
  `apple-gift-card-turciya-kazahstan-dlya-kompanii`. Обложки —
  `scripts/marketing/build-blog-covers.mjs`.
- Решение `/solutions/podarochnye-karty-sotrudnikam` (`src/data/solutions.ts`),
  плитки вендоров Apple, Airalo, Discord — `src/data/vendor-solutions.ts`.
- Директ: отдельная кампания `bs-apple-gift-2026-09` по спецификации
  `reports/seo/ppc/round3-spec.json` (ветка `seo-data`), расписание из
  спецификации (`campaign.time_targeting`, ежедневно 9–21 МСК).
