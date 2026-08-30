# WebMCP в BIZSoft: архитектура

Дата внедрения: 30.08.2026.

## Версия спецификации

Реализация выполнена по **WebMCP (Web Model Context API)** — CG-Draft
W3C Web Machine Learning Community Group, редакция **августа 2026**
(последние учтённые правки спецификации — 26.08.2026):

- спецификация: <https://webmachinelearning.github.io/webmcp/>
  (репозиторий <https://github.com/webmachinelearning/webmcp>);
- актуальная точка входа — **`document.modelContext`**
  (`navigator.modelContext` — устаревший алиас ранних сборок Chrome,
  поддержан у нас как фолбэк);
- `registerTool({ name, title, description, inputSchema, annotations, execute })`,
  `inputSchema` — объект JSON Schema, ответ `execute` —
  `{ content: [{ type: 'text', text }] }`;
- аннотации: `readOnlyHint` (у всех наших инструментов — `true`);
- поддержка браузеров на дату внедрения: Chrome 149+/Edge 150+ за
  **origin trial** (либо флаг `chrome://flags/#enable-webmcp-testing`);
  Firefox/Safari — только обсуждение позиции. Headless-режима у стандарта
  нет: API существует только в окне с документом.

Стандарт экспериментальный и меняется (переезды API уже были:
`window.agent` → `navigator.modelContext.provideContext` →
`document.modelContext.registerTool`). Поэтому слой изолирован так, чтобы
его можно было переписать или удалить, не трогая сайт (см. ниже).

## Принцип: progressive enhancement

WebMCP — дополнительный agent-facing слой над существующим сайтом,
НЕ новая архитектура:

```
                Человек
                   ↓
                Web UI
                   ↓
Directus → доменная логика (lib/directus, lib/pricing, lib/catalog)
                   ↓
      ┌────────────┼─────────────────┐
      ↓            ↓                 ↓
     UI      Structured Data      WebMCP
  (страницы)  (JSON-LD+microdata)   ↓
                                 AI-агент
```

Правила, которые нельзя нарушать:

1. **Один источник данных.** Инструменты читают тот же Directus теми же
   функциями (`getProducts`, `getProductBySlug`, `getVendors`), цена —
   только `effectivePrice()`. Отдельной «базы для агентов» не существует.
2. **Отказ слоя не трогает сайт.** Нет браузерного API — регистратор
   молча выходит; упал Directus — API отвечает 503 (как страницы);
   выключен рубильник — сайт работает как до внедрения.
3. **Read-only.** v1 не пишет ничего: ни заявок, ни КП, ни аналитики
   (см. security.md, раздел «Side effects»).

## Состав слоя

| Файл | Роль |
|---|---|
| `src/webmcp/definitions.ts` | Определения инструментов (имя/описание/JSON Schema). Изоморфный, без серверных импортов |
| `src/webmcp/validate.ts` | Серверная валидация недоверенного входа по схеме |
| `src/webmcp/adapters.ts` | Нормализация доменной модели в ответ агенту (белый список полей) |
| `src/webmcp/handlers.ts` | Серверные обработчики: схема → бизнес-проверки → каталог → адаптер |
| `src/webmcp/flag.ts` | Рубильник `PUBLIC_WEBMCP` |
| `src/webmcp/client.ts` | Браузерный регистратор: feature detection + `registerTool`, исполнение через fetch |
| `src/pages/api/agent/[tool].ts` | Единственный HTTP-эндпоинт: `GET /api/agent/<tool>?...` (JSON, noindex) |
| `src/components/WebMCP.astro` | Подключение клиентского чанка из BaseLayout |
| `src/lib/product-search.ts` | Общий поиск каталога — один и тот же для страницы `/catalog?q=` и `search_products` |

Цепочка вызова инструмента:

```
агент в браузере
  → document.modelContext → execute()          (client.ts)
  → GET /api/agent/<tool>?args                 ([tool].ts)
  → validateInput(схема)                       (validate.ts)
  → обработчик → getProducts()/getVendors()    (handlers.ts → lib/directus)
  → адаптер (белый список полей, effectivePrice) (adapters.ts)
  → { ok, data } → { content: [{type:'text'}] }
```

Исполнение — на сервере: в браузере нет ни данных, ни цен, ни логики.
Прямой запрос к `/api/agent/*` проходит те же проверки, что вызов агента.

## Imperative vs Declarative

- **Imperative API** — используется для всего v1 (поиск, карточки,
  вендоры): это программные операции чтения, форм у них нет.
- **Declarative API** (атрибуты `toolname`/`tooldescription` на формах) —
  **не используется**. Причины: (1) это отдельный explainer с TBD-частями
  (алгоритм синтеза схем, механизм ответа); (2) формы BIZSoft отправляются
  JS-фетчем на `/api/lead` (не классический submit), декларативная
  разметка потребовала бы их переделки; (3) отправка заявки — write-действие,
  запрещённое в v1 политикой side effects. Вернуться к вопросу при
  стабилизации explainer'а — см. security.md.

## Kill switch

`PUBLIC_WEBMCP=0` (astro.env на сервере + пересборка) гасит слой целиком:

- BaseLayout перестаёт рендерить `<WebMCP />` — скрипт исчезает со всех
  страниц ещё на сборке;
- `/api/agent/*` отвечает `404` + `X-Agent-Api: disabled` (по образцу
  закрытых товарных фидов); серверная сторона читает и рантайм-окружение,
  так что API можно погасить и без пересборки (рестарт контейнера).

Рубильник сделан по образцу `PUBLIC_ZOHO_HUB` («выключается значением»,
а не «включается наличием») — прод-сборка без переменной работает
со включённым слоем, ловушка BLD-002 не срабатывает.

## Покрытие типов страниц

| Тип страницы | Ценность для агента | WebMCP | Механизм |
|---|---|---|---|
| Карточка товара `/product/*` | высокая | да | generic `get_product` (+ `search_products`) |
| Вендор `/vendors/*` (bespoke и шаблонные) | высокая | да | `get_vendor`, `list_vendor_products` |
| Каталог/поиск `/catalog` | высокая | да | `search_products` (общая логика с `?q=`) |
| Список вендоров `/vendors` | средняя | да | `list_vendors` |
| Сравнения `/compare/*` | средняя | нет отдельного tool | агент вызывает `get_product` дважды |
| Корзина/КП `/cart`, формы | write | **нет в v1** | политика side effects (security.md) |
| Блог, solutions, справочные | низкая | нет | контент читается как обычный HTML |
| Служебные (admin, api, og) | нулевая | нет | не экспонируются |

Инструменты зарегистрированы на **всех** страницах (один общий слой в
BaseLayout): агент, попавший на любую страницу, может искать по каталогу.
Инструментов «на каждый URL» и «под конкретный продукт» не существует —
новые товары и вендоры Directus видны generic-инструментам автоматически.

## Производительность

- Клиентский чанк ~2.5 КБ до сжатия (definitions + регистратор), модульный
  (`<script type="module">`, не inline) — грузится отложенно, ничего не
  исполняет в браузерах без WebMCP, hydration и CWV не затрагивает.
- Серверный эндпоинт ходит в тот же кэш каталога (60 с TTL + SWR), что и
  страницы; успешные ответы дополнительно кэшируются `max-age=60`.

## SEO и аналитика

- `/api/agent/*` — служебный: `X-Robots-Tag: noindex, nofollow`, в sitemap
  не попадает (смоук это сверяет). Новых индексируемых URL нет.
- Разметка Schema.org, canonical, sitemap, robots не менялись; смоук
  сверяет четыре слоя цены: UI ↔ JSON-LD ↔ microdata ↔ WebMCP.
- Вызовы инструментов НЕ отправляют целей Метрики/GA4 и не создают
  pageview — конверсии людей не разбавляются агентским трафиком.
  Серверный след — обычный access-лог nginx по `/api/agent/*`
  (при надобности по нему же строится отдельная статистика).
