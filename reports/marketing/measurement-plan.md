# BIZSoft Measurement Plan

**Статус:** эталонная модель. Описывает, как измерение BIZSoft должно быть
устроено, а не как оно устроено сейчас. Фактическое состояние — в
`analytics-audit.md`, что уже исправлено — в `remediation-status.md`.
**Дата:** 21.08.2026, сверено с реестром после слияния веток.

> **Единственный реестр целей — `src/lib/analytics.ts`, константа `GOALS`.**
> Там же у каждой цели указано имя в GA4 и флаг `key` — конверсия это или
> сигнал намерения. Из этого же реестра `scripts/seo/goals_sync.py` заводит
> цели в кабинетах, а `quality.py` сверяет отправляемое с заведённым. Второй
> список целей рядом означал бы два ответа на один вопрос; таблицы ниже
> описывают смысл и уровни, но именами распоряжается реестр.

---

## 1. Принципы

1. **Конверсией считается только подтверждённое сервером действие.** Событие
   уровня `lead` отправляется исключительно после успешного ответа API
   (`res.ok`). Клик по кнопке конверсией не является никогда.
2. **Одно действие — одно имя.** Имя цели не переиспользуется для разных
   действий, разные имена не описывают одно действие.
3. **Имя цели в коде обязано существовать в счётчике.** Отправка цели,
   которой нет в Метрике, — это молчаливая потеря данных; проверяется
   автоматически (см. чеклист, проверка A-3).
4. **Персональные данные в параметры не передаются.** Ни ФИО, ни e-mail, ни
   телефон, ни ИНН, ни наименование организации. Передаётся только `sku`,
   `vendor`, `form_source`, `block_name`, `value`, `currency`.
5. **Уровень конверсии задаётся явно.** Событие всегда принадлежит ровно
   одному уровню; смешивать уровни в одном отчётном показателе запрещено.

---

## 2. Уровни конверсии

| Уровень | Определение | Считается конверсией в отчётах |
|---|---|---|
| `engagement` | посмотрел, полистал, раскрыл | нет |
| `micro` | проявил предметный интерес к товару | нет, но входит в качество трафика |
| `intent` | нажал на CTA, но заявку не отправил | нет; используется для оценки форм |
| `lead` | сервер принял заявку (HTTP 200) | **да** |
| `qualified` | менеджер подтвердил, статус в CRM ≠ `new`/`spam` | **да**, отдельной строкой |
| `sale` | статус `won`, известна сумма | **да**, основной бизнес-результат |

---

## 3. Матрица событий

Легенда: **М** — цель Яндекс.Метрики, **G** — событие GA4,
**KE** — ключевое событие GA4 (конверсия).

### Уровень `lead` — только эти два события называются заявкой

| Event | Trigger | М | G | Параметры | Уровень |
|---|---|---|---|---|---|
| `lead_sent` | `POST /api/lead` вернул 200 (`LeadForm`, `QuestionForm`) | цель JS ✓ | KE ✓ | `form_source`, `product_ref`, `vendor` | lead |
| `quote_pdf` | `POST /api/quote` вернул PDF (`/cart`) | цель JS ✓ | KE ✓ | `quote_no`, `value`, `currency:RUB`, `items_count` | lead |

`quote_pdf` — самый тёплый контакт на сайте: клиент назвал организацию, ИНН,
телефон и собрал корзину. В отчётах он выделяется отдельно от `lead_sent`, а не
складывается с ним без пометки.

### Уровень `micro`

| Event | Trigger | М | G | Параметры | Уровень |
|---|---|---|---|---|---|
| `add_to_cart` | добавление товара в подборку | цель JS ✓ | G ✓ | `sku`, `vendor`, `price`, `currency` | micro |
| `form_start` | первый `input`/`change` в форме заявки | цель JS ✓ | G ✓ | `form_source` | micro |
| `view_product` | открытие карточки `/product/[slug]` | — | G ✓ | `sku`, `vendor`, `category`, `price` | micro |
| `begin_checkout` | переход к оформлению из подборки | — | G ✓ | `items`, `total` | micro |
| `quiz_complete` | квиз подбора пройден до конца | цель JS ✓ | G ✓ | `vendor` | micro |
| `site_search` | поиск по сайту | автоцель ✓ | G ✓ | `search_term` | micro |

### Уровень `intent`

| Event | Trigger | М | G | Параметры | Уровень |
|---|---|---|---|---|---|
| `click_get_quote` | CTA «получить КП» / «запросить расчёт» | составная цель ✓ | G ✓ | `vendor`, `block_name`, `page_url` | intent |
| `click_choose_plan` | выбор тарифа | — | G ✓ | `vendor`, `plan` | intent |
| `click_clarify_price` | «уточнить цену» | — | G ✓ | `sku`, `vendor` | intent |
| `click_request_invoice` | «запросить счёт» | — | G ✓ | `vendor` | intent |
| `click_buy_org` | «купить на организацию» | — | G ✓ | `vendor` | intent |
| `click_renew` | «продлить» | — | G ✓ | `vendor` | intent |
| `click_phone`, `click_email`, `click_messenger` | клик по любой ссылке `tel:`, `mailto:` или в мессенджер — один делегированный обработчик на весь сайт (`src/lib/contact-goals.ts`) | цель JS ✓ | `contact` ✓ **конверсия** | `contact`/`channel`, `page_url` | **lead** |

Клик по телефону считается конверсией наравне с заявкой: человек снял трубку.
Обработчик один на весь сайт и ловит ссылки в шапке, подвале, карточке товара
и на лендингах — расставлять вызовы по компонентам значит гарантированно
забыть половину, а забытый клик по телефону неотличим от ушедшего посетителя.

### Уровень `engagement`

| Event | Trigger | М | G | Параметры | Уровень |
|---|---|---|---|---|---|
| `view_vendor_landing` | загрузка лендинга вендора | параметр визита | G ✓ | `vendor` | engagement |
| `view_jetbrains_landing`, `view_zoom_landing`, `view_figma_landing`, `view_openai_landing` | загрузка bespoke-лендинга | параметр визита | G ✓ | `vendor` | engagement |
| `click_plugins_catalog`, `click_pick_licenses` | CTA каталога плагинов JetBrains | — | G ✓ | `vendor` | engagement |
| `click_compare_app` | таблица сравнения попала во вьюпорт | — | G ✓ | `vendor` | engagement |
| `view_category` | открытие `/catalog/*` | — | G ✓ | `category` | engagement |
| `use_filter` | применение фильтра каталога | — | G ✓ | `filter_name`, `filter_value` | engagement |
| `click_product_card` | клик по карточке товара в листинге | — | G ✓ | `sku`, `list_name`, `position` | engagement |
| `click_related_link` | перелинковка | — | G ✓ | `target_path` | engagement |
| `open_comparison_table` | таблица сравнения попала во вьюпорт (порог 0.3) | — | G ✓ | `vendor` | engagement |
| `expand_plugins_category` | раскрытие категории плагинов | — | G ✓ | `category` | engagement |
| `quiz_step` | шаг квиза | — | G ✓ | `step` | engagement |
| `view_cart` | открытие подборки | — | G ✓ | `items`, `total` | engagement |
| `remove_from_cart` | удаление позиции из подборки | — | G ✓ | `sku` | engagement |
| `view_solution` | открытие страницы решения | — | G ✓ | `industry` | engagement |
| `company_autofill` | реквизиты подставились по ИНН | — | G ✓ | `filled` — **только признак, не сам ИНН** | engagement |

**Отдельно об `engagement` в Метрике.** Заводить 15 целей ради событий, которые
не являются конверсией, вредно: список целей перестаёт быть списком того, что
для бизнеса важно. Уровень `engagement` живёт в GA4 и в параметрах визита
Метрики (`ym(id,'params',{...})`), а целями Метрики становятся только `lead`,
`micro` и `click_get_quote`.

### Уровень ошибок — обязателен для диагностики форм

| Event | Trigger | М | G | Параметры | Уровень |
|---|---|---|---|---|---|
| `lead_error` / `quote_error` | любой сбой отправки: отказ сервера или ошибка сети. **Одно событие на все виды сбоя** — при двух (`form_error` в ветке отказа и `lead_error` в `catch`) один отказ 422 считается дважды, потому что `throw` из первой ветки попадает во вторую | — | G ✓ | `form_source`, `http_status` (0, если ответа не было), `reason` | диагностика |
| `form_validation_error` | браузерная валидация не пропустила отправку | — | G ✓ | `form_source`, `field` | диагностика |

Сейчас не отправляются: `catch`-ветки во всех трёх формах показывают текст
пользователю и не сообщают аналитике ничего. Из-за этого невозможно отличить
«никто не отправлял заявку» от «сервер отвечал 502».

---

## 4. Атрибуция

### Правила

1. **First-touch пишется один раз** и не перезаписывается 90 дней.
2. **Last-touch перезаписывается** при каждом визите с непустым источником.
3. Обе записи хранятся одновременно и не уничтожают друг друга.
4. `Direct` **никогда не перезаписывает** непустой last-touch: отсутствие
   источника не является источником.

### Хранилище (localStorage)

```
bizsoft_attr_first = {utm_source, utm_medium, utm_campaign, utm_content,
                      utm_term, yclid, gclid, referrer, landing_path, ts}
bizsoft_attr_last  = { …те же поля… }
```

### Передача в заявку

`POST /api/lead` и `POST /api/quote` получают блок:

```json
"attribution": {
  "first": { "...": "..." },
  "last":  { "...": "..." },
  "ym_client_id": "1723...",
  "ga_client_id": "1234567890.1723..."
}
```

`ym_client_id` — из `ym(110206070,'getClientID',cb)`;
`ga_client_id` — из `gtag('get','G-V9BK2D1431','client_id',cb)`.
Наличие обоих идентификаторов делает возможной обратную сверку
«заявка в CRM ↔ визит в аналитике» — без неё сквозная аналитика невозможна
в принципе.

### Поля в Directus `leads`

`utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`,
`first_touch_source`, `first_touch_ts`, `last_touch_source`, `landing_path`,
`ym_client_id`, `ga_client_id`.

Существующее поле `source` **переименовать в `form_source`**: сейчас его
значение (`pricing`, `question`, `quote`) читается как канал трафика, в том
числе в письме менеджеру («Источник: pricing»).

---

## 5. Целевая воронка BIZSoft

```
Показ в поиске            Вебмастер (все запросы) + GSC
   ↓
Клик из выдачи            Вебмастер + GSC
   ↓
Сессия                    Метрика visits + GA4 sessions      [внутренний трафик отфильтрован]
   ↓
Просмотр категории        view_category
   ↓
Просмотр товара           view_item                          [sku, vendor]
   ↓
Интерес                   add_to_cart / form_start           micro
   ↓
Намерение                 click_get_quote / contact_click    intent
   ↓
ЗАЯВКА                    lead_sent / quote_pdf              lead        ← конверсия
   ↓
Квалификация              Directus status ≠ new/spam         qualified
   ↓
Сделка                    Directus status = won, amount      sale
```

На каждом переходе обязателен разрез по `vendor` и `sku` — иначе аналитика
vendor/product (раздел 16 задания) остаётся невычислимой.

---

## 6. Custom dimensions GA4

Event-scoped, регистрируются через Admin API:

| Параметр | Dimension name | Где используется |
|---|---|---|
| `sku` | `sku` | воронка товара, отчёт vendor/product |
| `vendor` | `vendor` | приоритизация вендоров |
| `form_source` | `form_source` | эффективность форм |
| `block_name` | `block_name` | эффективность блоков лендингов |
| `channel` | `contact_channel` | доля обращений мимо форм |

Без регистрации параметр не появляется в стандартных отчётах и недоступен
Data API — передача параметра в событии этого не заменяет.

---

## 7. Что должен запрашивать сборщик после внедрения

Дополнительно к текущим запросам `collect.py`:

**Метрика:**
- `ym:s:goal<id>reaches` по каждой цели уровня `lead` отдельно (вместо
  `sumGoalReachesAny`, который складывает всё подряд);
- `ym:s:goal<id>visits` — дедупликация по визиту;
- `ym:s:goal<id>converionRate` с обязательным указанием `n`.

**GA4:**
- `eventName` × `keyEvents` — конверсии в разрезе события;
- `customEvent:vendor` × `keyEvents` — заявки по вендору;
- `customEvent:sku` × `eventCount` для `view_item` и `add_to_cart`;
- `sessionSource` с исключением `metrika.yandex.ru`, `webmaster.yandex.ru`,
  `alice.yandex.ru`.

**Directus (новый источник):**
- `leads`: количество по `status`, `first_touch_source`, `vendor`, суммы;
- `quotes`: количество и суммы.
Это закрывает запись `CRM leads — источник не подключён` в
`scripts/seo/measurement.py`.

---

## 8. Порядок внедрения

| Шаг | Что | Блокирует | Сложность |
|---|---|---|---|
| 1 | Завести цели `lead_sent`, `quote_pdf`, `add_to_cart`, `click_get_quote` в Метрике | всё измерение конверсий | часы |
| 2 | Разметить `lead_sent`, `quote_pdf` как key events GA4, снять `form_submit` | конверсии GA4 | часы |
| 3 | Фильтры внутреннего трафика (GA4 + Метрика) | достоверность органики | часы |
| 4 | Модуль атрибуции + поля в Directus | ROI, реклама, сквозная аналитика | дни |
| 5 | `form_start`, `form_error`, `contact_click`, `view_item` | диагностика форм, воронка товара | дни |
| 6 | Custom dimensions GA4 + расширение `collect_ga4` | vendor/product-аналитика | дни |
| 7 | Выгрузка Directus в снимок | уровни `qualified` и `sale` | дни |
| 8 | Автопроверки из чеклиста в CI | защита от регрессий | дни |

Шаги 1–3 закрывают три P0 и требуют настройки, а не разработки. Их следует
сделать первыми и в один день — при этом обязательно проставить дату в
`reports/seo/measurement-limits.json`: она становится границей, через которую
сравнивать конверсии нельзя.
