# Прайс-лист для Яндекс Бизнеса

Каталог biz-soft.pro отдаётся в Яндекс Бизнес прайс-листом YML по шаблону
Яндекса (`yml_catalog → shop → categories + offers`).

## Ссылка на фид

```
https://biz-soft.pro/yandex-business.xml          # продвигаемый каталог (по умолчанию)
https://biz-soft.pro/yandex-business.xml?all=1    # + скрытые от индексации позиции
```

Маршрут — SSR (`src/pages/yandex-business.xml.ts`), данные берутся из Directus
на каждый запрос (кэш каталога 60 c, HTTP-кэш 1 ч). Отдельный файл держать и
перезаливать не нужно: цены и состав каталога в Яндексе обновляются сами.

**Как подключить.** Яндекс Бизнес → карточка организации → «Товары и услуги» →
загрузка прайс-листа **по ссылке** → указать URL выше. Если интерфейс просит
именно файл — скачать этот URL и загрузить как `.xml`.

## Что попадает в фид

Правила — в `src/lib/yml-feed.ts` (чистая логика, тесты `tests/yml-feed.test.ts`):

| Условие | Поведение |
|---|---|
| `status != published` | не попадает |
| `origin = domestic` | не попадает (отечественное ПО снято с сайта) |
| `noindex`, `JB-PLG-*`, `JB-*-IND` | не попадает (кроме `?all=1`) |
| цена 0 / «по запросу» | не попадает — Яндексу нужна цена |
| активная акция | в `price` уходит акционная цена |

## Соответствие полей

| YML | Источник |
|---|---|
| `offer id` | `products.id` (целое, стабильное) |
| `name` | название карточки; бренд подставляется в начало, если его нет в названии |
| `vendor` | `products.vendor` |
| `price` | эффективная цена в ₽ (с учётом акции), округлённая |
| `currencyId` | `RUR` |
| `categoryId` | `products.category.id`; без категории → `999` «Прочее ПО» |
| `picture` | `/og/product/<slug>.png` — генерируемая обложка 1200×630 |
| `description` | `description` (markdown → плоский текст), фолбэк `seo_text`, до 3000 символов |
| `shortDescription` | `short_description`, фолбэк `meta_description`, до 250 символов |
| `url` | `/product/<slug>` |

Картинки берём из OG-обложек, а не из медиатеки Directus: Directus доступен
только во внутренней docker-сети, его `/assets/*` наружу не отдаются.

## Готовый файл (снимок)

`data/yandex-business-2026-08-19.xml` — выгрузка на 19.08.2026: 279 офферов,
19 категорий. Пригодится, если Яндекс Бизнес просит файл, а не ссылку.
Снимок не обновляется сам — для актуальных цен берите ссылку выше.

## Снимок каталога без доступа к проду

`data/catalog-snapshot.json` — машиночитаемая выгрузка товаров и категорий
(обновляется workflow `ops-export-products`, коммитится в ветку запуска).
Нужен, чтобы собрать файл прайс-листа офлайн — тем же кодом, что и маршрут:

```js
import { buildYmlCatalog } from './src/lib/yml-feed';
const { products, categories } = JSON.parse(fs.readFileSync('data/catalog-snapshot.json', 'utf8'));
fs.writeFileSync('out/yandex-business.xml', buildYmlCatalog(products, categories, { siteUrl: 'https://biz-soft.pro' }));
```
