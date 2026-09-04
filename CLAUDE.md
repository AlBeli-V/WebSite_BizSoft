# Правила проекта biz-soft.pro

Короткий свод. Полный текст каждого правила, история и разборы инцидентов —
в `docs/rules/` (файл указан у каждого пункта); карта проекта — `docs/INDEX.md`.
Свод читается в каждой сессии, поэтому новое правило заводится здесь одной
строкой-двумя, а обоснование — отдельным файлом в `docs/rules/`.

## Как работать

- **Проверка подхода до начала работы** (`docs/rules/approach-check.md`).
  Открывая ветку или задачу, проверить: механизм (детерминированная работа —
  скрипт или GitHub Actions, сессия только там, где нужна оценка или текст),
  объём (правки одного контура за день — одна ветка и одна сессия, не серия
  микро-PR), модель (операции и правки по шаблону — Sonnet; проектирование,
  аудиты, разбор инцидентов — Opus/Fable), чтение (генерируемые данные не
  читать целиком, документы — по нужному разделу), готовое (искать
  существующий workflow или скрипт). Расхождение — сказать до начала работы
  и предложить путь с обоснованием из трёх частей.
- **Язык** (`docs/rules/language.md`). Всё для руководителя — по-русски:
  ответы, вопросы, коммиты, PR, комментарии в коде, письма, отчёты.
  Внутренние рассуждения модели — на любом языке. Английский в результате —
  только технические идентификаторы, команды, цитаты внешних сервисов.
- **Решения — кнопками с визой** (`docs/rules/decisions-buttons.md`). Любой
  запрос решения руководителя — AskUserQuestion: 2–4 взаимоисключающих
  варианта, у каждого виза «РЕКОМЕНДУЮ» / «НЕ РЕКОМЕНДУЮ» и обоснование (чем
  подтверждается, что даёт, чем рискуем); рекомендуемый — первым, виза в
  описании варианта; кнопки «Другое» нет. Всё, что не зависит от ответа,
  делается до вопроса. Текстом без кнопок — только доклады.
- **Время — московское** (`docs/rules/timezone.md`). Время без пояса —
  МСК (UTC+3, без перехода). В cron и расписаниях — UTC с комментарием МСК.
- **Письма руководителю — на avbelyaev@biz-soft.pro** (`docs/rules/mail-recipient.md`)
  через workflow `ops-send-mail` (только с main). Почта профиля сессии —
  только для авторства коммитов.

## Прод и операции

- **Доступ к проду** (`docs/rules/prod-access.md`). Сетевой доступ из сессии
  закрыт: проверки и операции — через ops-* workflows, результаты — в
  issue #22. Деплой — только deploy.yml при пуше в main.
- **Production-workflow — только с main** (`docs/rules/production-workflow-main-only.md`).
  Ручной запуск workflow, который деплоит, ходит по SSH, пишет в Directus,
  меняет аналитику или шлёт письма, — только с ветки main; Guard не
  обходить. В ops-fetch-assets и ops-me-crawl ветка назначения — рабочая.
- **Операционные прогоны — только GitHub Actions** (`docs/rules/operational-runs.md`).
  Ежедневные и еженедельные прогоны с детерминированными шагами — workflow с
  двумя cron-слотами, идемпотентностью по артефакту дня, очередью и явным
  вызовом почтовых workflow (`scripts/ops/gh_dispatch_wait.sh`). Routine на
  сессиях Claude для них не заводятся. Контуры: `seo-daily-report`,
  `seo-committee-build`, `competitive-intelligence-daily`, `seo-serp-watch`,
  `seo-wordstat`. Статусы `intelligence/actions.json` обновляет PR,
  внедряющий действие. Тишина: при успехе ничего, при сбое — запись в issue #22.
- **Достоверность отчётов** (`docs/rules/report-integrity.md`). В тексте
  отчётов, промптов и журнала нет литералов без срока годности (даты,
  обещания, суммы, квоты) — `test_report_literals`, исключения с
  `valid_until`. Недоступный блок письма — только `passport.unavailable`;
  ложь о дате или причине блокирует выпуск. Запись в issue #22 — только
  `journal-post` с `outcome`; `|| true` вокруг основного скрипта запрещён.
  Секреты — в `ops/secrets/registry.json`; одноразовые workflow с
  `# expires:`. Периодные сравнения — только по полным окнам.
- **Товарные фиды закрыты** (`docs/rules/product-feeds.md`, `docs/yandex-feeds.md`).
  По умолчанию 404 (`X-Feed-Status: disabled`). Включать
  `YANDEX_FEEDS_ENABLED`, добавлять фиды в кабинеты, писать в поддержку
  площадок — только по прямой команде руководителя.

## Каталог, страницы, SEO

- **Поля форм с ПДн — класс `ym-disable-keys`** (`docs/rules/webvisor-masking.md`).
  Любое поле ввода персональных данных на публичной странице (ФИО, e-mail,
  телефон, компания, ИНН, текст обращения) несёт класс `ym-disable-keys`:
  Вебвизор не записывает ввод в нём. Проверка — `tests/webvisor-masking.test.ts`;
  настройки кабинета — `docs/marketing/webvisor.md`.
- **Каталог** (`docs/rules/catalog.md`). Directus — единственный источник
  товаров; вендор — точное поле `vendor` (сверять с `src/data/vendors.ts`).
  На bespoke-страницах вендоров не фильтровать по префиксу sku; ключи —
  slug или sku. Выгрузка каталога — `ops-export-products`. `lastmod` —
  `content_updated_at`. Задвоенные позиции склеивать `ops-merge-product`
  (сначала `apply=false`; 301 через `old_slugs`, снятая — `draft`);
  карточки не удалять.
- **Новые страницы → sitemap → индексация** (`docs/rules/sitemap-indexing.md`).
  Проверить `/sitemap.xml` (bespoke-страницы — руками в `STATIC_ROUTES`;
  `noindex` и `productNoindex()` не попадают), затем переобход через
  `ops-yandex-recrawl` (квота 150 URL/сутки), отчёт — в issue #22.
- **Микроразметка** (`docs/rules/structured-data.md`). Только штатный слой
  (`src/lib/seo.ts`, Breadcrumbs/FAQ/JsonLd, microdata карточки); один тип —
  один раз на страницу; «цена по запросу» — без Product/Offer; фиктивные
  цены и рейтинги запрещены; цена — из `effectivePrice()`. Приёмка —
  `pnpm verify`.
- **WebMCP** (`docs/rules/webmcp.md`, `docs/webmcp/`). Новые товары и вендоры
  видны generic-инструментам автоматически; product-specific инструменты,
  параллельная база цен и write-инструменты запрещены; вызовы не шлют цели
  Метрики/GA4; `/api/agent/*` — noindex и вне sitemap. Изменил слой —
  `pnpm verify` и `pnpm test:webmcp-browser`.
- **Уникальные title и description** (`docs/rules/unique-meta.md`).
  `meta_title` ≤ 60 и `meta_description` ≤ 160 уникальны; различитель
  (период, объём, редакция, модель лицензии) — в `name` и заголовке.
  Правка меты в проде — только `data/seo/product-descriptions.json` +
  `ops-apply-descriptions` (`apply=false`, потом `apply=true`), затем
  переобход. Общий `short_description` разводится
  `scripts/seo/dedupe-descriptions.mjs`. Проверки: `pnpm test`
  (catalog-uniqueness), `pnpm smoke`, `ops-content-audit`.
- **Сниппет-эксперименты — только на страницах с показами**
  (`docs/rules/snippet-experiments.md`). Целевые фразы — из запросов
  Вебмастера; в реестре обязательны `page_markers`, `query_intent_any`,
  `query_exclude`, `title_marker`, `baseline`; статус `planned`, `start`
  ставит `seo-site-check`; одно изменение на эксперимент; после деплоя —
  переобход. Новый эксперимент любого типа — только на кластере с
  экспозицией выше 3,6 показа в день (100 за 28 дней): проверка
  `experiment_windows.py validate` перед отправкой реестра.
- **SERP: один сбор — все потребители** (`docs/rules/serp-single-source.md`).
  Выдачу собирает только `seo-serp-watch` (Яндекс ежедневно, Google RU через
  xmlriver еженедельно) в `reports/seo/serp` ветки `seo-data`; параллельные
  сборщики и прямые вызовы из потребителей запрещены; без свежего среза —
  «нет данных». Потолки и расписание — `data/seo/xmlriver.json` через PR.
- **Решение по кандидату — в машинный реестр** (`docs/rules/vendor-decisions-registry.md`).
  Отказ или одобрение вендора действует только записью в
  `reports/seo/wordstat/decisions.json` и
  `reports/seo/intelligence/vendor-decisions.json` (ветка `seo-data`; поля
  `brand`, `decided_on`, `reason`, `by`).
