# Каталог и привязки

- Directus — единственный источник товаров; вендор товара — точное значение
  поля `vendor` (сверять с `src/data/vendors.ts`, поле `vendor` записи).
- На bespoke-страницах (`vendors/openai|figma|zoom|jetbrains.astro`) НЕ
  фильтровать товары по префиксу sku: часть товаров живёт под
  «интеграционными» sku (OPAI-LIC-CHATGPTBUS-TEAM-1Y-USER-STD, FIGM-LIC-ORGANIZATION-TEAM-1Y-USER). Ключи меты и
  порядка карточек — slug ИЛИ sku.
- Живую выгрузку каталога (vendor/name/slug/sku/price) даёт workflow
  `ops-export-products` (комментарий в issue #22).
- `lastmod` товара в sitemap — поле `content_updated_at` (дата содержательного
  изменения), а не `date_updated`: последний Directus сдвигает при любом
  PATCH, и ежедневная переоценка по курсу ЦБ ставила всему каталогу одну
  дату (разбор 03.09.2026). Штамп ставит слой `src/lib/directus.ts`
  (`withContentStamp`: цены, наценки, закупка и `sort` — нейтральны, всё
  остальное — содержательно) и workflow мета-правок; переоценка и
  `ops-annual-reprice` его не трогают. Без штампа `lastmod` у товара не
  отдаётся. Поле заводит `ops-directus-schema` (schema-only).
- Одна и та же позиция, заведённая дважды (разные sku и слаги), склеивается
  штатно: `ops-merge-product` (вход `keep`/`drop`, сначала `apply=false` —
  план). Остающаяся карточка получает слаг снятой в `old_slugs` — страница
  начинает отдавать 301 (`src/pages/product/[slug].astro`), снятая уходит с
  витрины сменой статуса на `draft` и в базе сохраняется. Какую из пары
  оставить — решение руководителя; удалять карточки нельзя.
