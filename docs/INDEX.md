# Карта проекта biz-soft.pro

Маркетинговый B2B-сайт ИП Беляев А.В.: подписки на зарубежное ПО для
российских юрлиц (договор, счёт, ЭДО). Вокруг сайта — контуры SEO-аналитики,
конкурентной разведки и рекламы, каждый со своей веткой-хранилищем и
workflow-конвейером; сессия модели их не запускает вручную, только правит
код в `main` и читает результаты в issue #22 или письмах.

Стек: **Astro 5** (SSR, Node-адаптер) · **Directus + PostgreSQL** · **Tailwind v4** ·
TypeScript strict · Vitest · Python 3 (контуры SEO/разведки/рекламы).

Эта карта — единственная точка входа для новой сессии. Прежде чем читать
что-то ещё, посмотри нужный раздел ниже.

## Контуры

| Контур | Код | Данные (ветка) | Workflow | Документ | Тесты |
|---|---|---|---|---|---|
| Сайт (Astro/Directus) | `src/` (pages, components, lib, data) | Directus/Postgres на проде, вне git | `deploy.yml`, `ci.yml` | `README.md`, `docs/OPERATIONS.md`, `docs/ADMIN-GUIDE.md` | `pnpm test`, `pnpm typecheck`, `pnpm smoke` |
| Каталог и импорт | `scripts/catalog/*.json`, `scripts/ai-catalog-cards.json`, `scripts/import-vendors.mjs`, `scripts/import-cards.mjs`, `src/data/vendors.ts` | Directus прод; исходники вендоров — `main` | `ops-import-vendors`, `ops-import-ai-cards`, `ops-export-products`, `ops-merge-product`, `ops-patch-product`, `ops-rename-product`, `ops-recategorize`, `ops-categories` | `docs/vendors-expansion-prompt.md`, `docs/ai-catalog-import.md` | `tests/catalog-uniqueness.test.ts`, `tests/bulk-import.test.ts` |
| SEO Growth Intelligence | `scripts/seo/*.py` (collect, snapshot, quality, report_v4, webreport, allocator, loop_health, money_queries) | ветка `seo-data` → `reports/seo/*` | `seo-data-collect`, `seo-daily-report`, `seo-report-email`, `seo-period-report`, `seo-site-check`, `seo-analytics-check`, `seo-goals-sync`, `seo-publish-web` | `reports/seo/README.md`, `docs/seo/reporting-methodology.md` (721 стр. — по разделу), `docs/seo/goals.md`, `docs/seo/pagespeed-monitor.md` | `python3 -m unittest discover -s scripts/seo/tests` (94 проверки) |
| Wordstat | `scripts/seo/wordstat/*.py` (run, report, audience) | ветка `seo-data` → `reports/seo/wordstat/` | `seo-wordstat` | `reports/seo/README.md` (раздел 11), `reports/seo/wordstat/decisions.json` — реестр решений по кандидатам | `scripts/seo/tests` (общий набор) |
| SERP (Яндекс + Google xmlriver) | `scripts/seo/serp_watch.py`, `serp_google.py`, `xmlriver.py`, `serp_analysis.py` | ветка `seo-data` → `reports/seo/serp/` | `seo-serp-watch` — единственный сборщик («один сбор — все потребители») | `docs/seo/serp-google-xmlriver.md` | `scripts/seo/tests` |
| Конкурентная разведка | `competitive-intelligence/` (discovery, scoring, decision_engine, mailer, `run_daily.py`) | orphan-ветка `competitive-data` | `competitive-intelligence-daily`, `competitive-intelligence-mail` | `docs/competitive/methodology.md` (1313 стр. — по разделу), `docs/competitive/TRIGGER.md` | `python3 -m unittest discover -s competitive-intelligence/tests` |
| Директ (реклама) | `scripts/ppc/direct_*.py` | аккаунт Яндекс.Директа, вне git; результат — issue #22 | `ops-direct` (единый, вход `action`: apply/check/expand/improve/negatives/refine/sitelinks/stats/tighten) | заголовок `ops-direct.yml` | — |
| WebMCP | `src/webmcp/*`, `src/pages/api/agent/*`, `src/data/policies.ts`, `src/lib/policy-search.ts` | тот же Directus, отдельной базы нет | входит в `ci.yml` | `docs/webmcp/architecture.md`, `security.md`, `tools.md`, `testing.md`, `shopping-agent-review.md` | `pnpm test:webmcp-browser` |
| Логотипы/иконки | `scripts/build-logos.mjs`, `src/components/VendorLogo.astro`, `VendorIcon/ProductIcon/CategoryIcon.astro` | `docs/*icons-manifest.json`, `docs/*icon-map.json` | `ops-fetch-assets` (приём архивов) | skill `add-logo-and-icons` | `pnpm check:artifacts` |
| Фиды | `src/lib/feeds/*` (yml, registry, select) | — (SSR из Directus на лету) | `ops-yandex-feeds-toggle`, `ops-yandex-feeds` | `docs/yandex-feeds.md` | `pnpm smoke` (закрыты по умолчанию) |
| Визуальный слой отчётов (KPI-kit) | `scripts/viz/kpi_kit.py` (плитки, светофор, линии, теплокарта, малые кратные, таблицы-дашборды; email-варианты) | — | входит в `seo-daily-report`, `competitive-intelligence-daily` | `docs/rules/kpi-kit.md`, витрина `docs/design/kpi-dashboards/` | `scripts/seo/tests/test_kpi_kit.py` |
| Письма | `scripts/seo/report_v4.py`, `committee.py`; `competitive-intelligence/mailer/*` | ветки `seo-data` / `competitive-data` | `seo-report-email`, `seo-committee-build`+`seo-committee-email`, `competitive-intelligence-mail`, `ops-send-mail`, `ops-mail` | `reports/seo/README.md` | `uxlint_v4.py`, `contentcheck.py` (в конвейере отчёта) |
| Бэкапы/DR | `scripts/ops/backup.sh` | снапшоты на сервере `/opt/bizsoft` | `ops-backup` | `docs/DR-RUNBOOK.md`, `docs/OPERATIONS.md` | — |
| Операционные прогоны | — (детерминированные workflow, без сессий Claude/Routine) | — | `seo-daily-report`, `competitive-intelligence-daily`, `seo-committee-build`, `seo-tasks-due`; кросс-запуск между workflow — `scripts/ops/gh_dispatch_wait.sh` | заголовки этих workflow объясняют, какую Routine они заменили | — |

## Где что искать

- **Новый вендор/товар** — `src/data/vendors.ts`, `scripts/catalog/<slug>.json`;
  чеклист и обязательные шаги (sitemap, микроразметка, WebMCP, уникальность
  meta) — `docs/vendors-expansion-prompt.md`, раздел 11/11а, и правила в
  `CLAUDE.md`.
- **Карточка AI-каталога и пара «базовое место + Premium»** —
  реестр `scripts/ai-catalog-cards.json`, заливка воркфлоу `ops-import-ai-cards`,
  правила против каннибализации пары тарифов: `docs/ai-catalog-import.md`,
  раздел «Заведение отдельной карточки AI-каталога».
- **Подарочная карта (тип gift_card)** — модель, цена ×3, порядок на проде:
  `docs/gift-cards.md`; пакет Apple собирает `scripts/build-gift-card-package.mjs`,
  контент страницы — `src/data/gift-cards.ts`, логика — `src/lib/gift-cards.ts`.
- **Новая статья** — `src/content/blog/<slug>.md`; редполитика — skill
  `bizsoft-content`; формат frontmatter — `README.md`, раздел «Контент по
  календарю».
- **Отбор кластеров под правку сниппета или контента** — модель
  `scripts/seo/money_queries.py`: считает недобор переходов, интент, ценность,
  релевантность посадочной и риск, проверяет форму спроса (всплеск / затухание) и
  занятость кластера идущими экспериментами — и по реестру `seo-data`, и по
  выкаченным сниппетам в `src/data/seo-experiments.ts`. Результат — бэклог
  `reports/seo/yandex-money-backlog.json`, разбор —
  `reports/seo/yandex-money-growth-plan.md`.
- **Новый SEO-эксперимент** — запись кладётся в
  `data/seo/experiments-pending/*.json` (ветка main, обычный код-ревью), в
  реестр `seo-data` её переносит `scripts/seo/experiments_sync.py` шагом
  `seo-site-check` до активации. Руками реестр не редактировать: запись с
  существующим id перенос не трогает, потому что её ведут другие прогоны.
- **Очередь работ и сроки** — тикеты `reports/seo/tasks/*.md`. У тикета,
  который нельзя делать сразу, в заголовке стоит `**Созревает:** ГГГГ-ММ-ДД`;
  `scripts/seo/tasks_due.py` находит созревшие, workflow `seo-tasks-due`
  ежедневно пишет их в issue #22 и молчит, когда не созрело ничего. Тикет без
  срока слой не показывает никогда — поэтому `tasks_due.py --unmanaged`
  называет открытые тикеты без даты, и понедельничный слот того же workflow
  пишет их в журнал раз в неделю.
- **«Первое место, а переходов нет»** — замер первого экрана выдачи:
  протокол `data/seo/serp-fold-probe.json` (заполняется руками — Search API
  отдаёт только органику и о рекламе над ней не знает, а сессия в выдачу не
  ходит), вывод по заранее записанному правилу — `scripts/seo/serp_fold.py`.
- **Правка меты карточки** — только через `data/seo/product-descriptions.json`
  + workflow `ops-apply-descriptions` (правило CLAUDE.md «уникальные title и
  description»), руками в Directus не редактировать.
- **Новая страница** (лендинг/продукт) — `src/pages/vendors/*`,
  `src/pages/product/[slug].astro`; добавить в `STATIC_ROUTES`
  (`src/pages/sitemap.xml.ts`), если страница bespoke.
- **Правка письма отчёта** — блоки письма в `scripts/seo/report_v4.py`
  (Growth Intelligence) или `scripts/seo/committee.py` (Growth Committee);
  методика — `docs/seo/reporting-methodology.md`, открывать нужный раздел,
  не файл целиком.
- **Правка условий работы** (договор, счёт, ЭДО, сроки, порядок сделки) —
  только `src/data/policies.ts`: из него рендерятся `/faq`, `/how-we-work`,
  `/pricing` и отвечает WebMCP-инструмент `search_policies`. Массив
  `{ q, a }` прямо в `.astro` запрещён тестом `tests/policies.test.ts`.
- **Что публиковать: темы, запросы ядра, целевые страницы** —
  `docs/marketing/external/publication-plan.md`.
- **Где регистрироваться и что публиковать** — `docs/marketing/external/platform-registry.md`
  (очерёдность площадок, единые данные профилей, инструкция по регистрации,
  разбор Дзена, механика Pressfeed); состояние регистраций —
  `data/marketing/platform-accounts.json`, оттуда подтверждённые профили
  идут в `sameAs`. Реестр еженедельно сверяет сторож `ops-registrations-watch`
  (`scripts/ops/registrations_watch.py`): записанные профили дёргает живым
  запросом, о незаведённых напоминает письмом.
- **Можно ли публиковать машиной** (Яндекс Бизнес, Дзен) —
  `docs/marketing/external/auto-publishing.md`: товарные карточки уже идут
  фидом, посты и статьи публичным API не пишутся, RSS-экспорт Дзена разобран
  с доводами против подключения сейчас.
- **Авторитет в Google** (почему Яндекс держит топ, а Google нет) —
  `reports/seo/google-authority-strategy.md`; карта контента и разрыв —
  `google-content-map.json`, `google-link-gap.csv`, `google-entity-gap.md`;
  дропы — `drop-domain-strategy.md` и приложения; замена источников после
  блокировки регистратора — `drop-domain-data-sources.md`, схема сервиса на
  ключах пользователей — `docs/drop-service/byo-account-architecture.md`,
  спецификация расширения браузера — `docs/drop-service/extension-spec.md`. Разбор строит
  `scripts/seo/google_authority.py` из срезов SERP и сенсора покрытия
  индекса (шаг `Google authority analysis` в `seo-serp-watch`), руками цифры
  не правятся. Очередь работ и очередь на обход — общие с контуром
  восстановления обхода: `google-recovery-backlog.json` и
  `google-url-priority.csv` (GIPS); вторых списков в проекте нет.
- **Новый workflow** — `.github/workflows/*.yml`; production-workflow
  запускается только с `main` (правило CLAUDE.md); для запуска одного
  workflow из другого — `scripts/ops/gh_dispatch_wait.sh`.

## Проверка

- `pnpm test` — Vitest, вся `tests/`.
- `pnpm verify` — тест + typecheck + build + check:artifacts + smoke, полный
  прогон перед мержем.
- `python3 -m unittest discover -s scripts/seo/tests` — контур SEO/Growth
  Intelligence.
- `python3 -m unittest discover -s competitive-intelligence/tests` — контур
  конкурентной разведки.

## Правила чтения

Не открывать целиком (это же закрыто в `.claude/settings.json` →
`permissions.deny`, при необходимости — `grep` с ограничением вывода):

- `src/data/zoho-hierarchy.ts` (2,4 МБ) — генерируется, читать точечным grep;
- `scripts/catalog/*.json` (`zoho.json` — 7,8 МБ, и другие) — сырые данные
  вендоров;
- `scripts/content/zoho-rules.json`, `scripts/content/zoho-cards.json` —
  сгенерированные карточки;
- `scripts/seo/tests/fixtures/**` — тестовые фикстуры;
- `pnpm-lock.yaml` — лок-файл зависимостей.

Открывать только нужный раздел, не весь файл:

- `docs/competitive/methodology.md` — 1313 строк;
- `docs/seo/reporting-methodology.md` — 721 строка;
- `TECHNICAL_AUDIT_REPORT.md` — 1312 строк.

## Правила проекта

Регулярные правила (sitemap, микроразметка, WebMCP, уникальность meta,
кнопки с визой, часовой пояс, доступ к серверу и т.д.) здесь не
дублируются — источник истины: `CLAUDE.md` в корне репозитория и
`docs/rules/` (полные тексты по темам).
