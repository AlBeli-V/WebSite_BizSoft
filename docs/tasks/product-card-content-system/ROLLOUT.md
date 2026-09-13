# Массовый перевод карточек на content_modules — план прогона

Решение руководителя 13.09.2026: макеты Red Giant, OpManager, Acronis (16) и
Adobe Creative Cloud (4) одобрены; массовое изменение всех карточек разрешено.
Design Approval Gate для шаблона пройден; дальнейшие семейства макетом не
согласуются — приёмка идёт валидатором и выборочной проверкой
`ops-card-shot` по одной позиции каждого класса в волне.

## Разделение труда
- **Claude Code (репо, ветка `feat/product-card-modules` → PR в `main`):** шаги 1–3 постановки — поля схемы (`ops-directus-schema`), ветка рендера `content_modules` в `[slug].astro` (legacy при пустом поле), workflow `ops-apply-content`; затем применение семейств по волнам.
- **Контент-сессии (Opus/Fable):** профиль вендора → семейство → `validate-family.mjs` зелёный → файл в `data/content/families/`. Готовые: `MAXN-REDGIANT`, `ZOHO-OPMANAGER`, `ACRN-CP`, `ADBE-CC`, `ADBE-APPS`.
- **Руководитель:** только решения из п. 7 постановки и письмо `ops-catalog-watch` в день волны.

## Волны (по массе витрины, очередь — `rollout-queue.csv`, 489 карточек)
| Волна | Семейства | Карточек | Профиль вендора |
|---|---|---|---|
| 0 (применяется) | Red Giant, OpManager, Acronis CP, Adobe CC | 25 | maxon, manageengine, acronis, adobe |
| 1а (готово, патч 2) | Adobe Apps (11), JetBrains IDE/Pack/dotUltimate/ReSharper (13) | 24 | adobe, jetbrains |
| 1б (готово, патч 3) | Maxon One, Cinema 4D, Redshift, ZBrush, Universe | 7 | maxon |
| 1в (готово, патч 4) | ManageEngine ServiceDesk Plus + MSP (11), Endpoint Central + MSP + DLP Plus (6) | 17 | manageengine (разделы SDP, EC) |
| 1 (готово, ветка claude/friendly-hopper-rpidvh) | остальные ManageEngine: 40 семейств — Password Manager Pro, PAM360, Key Manager Plus, Access Manager Plus, ADManager Plus, ADAudit Plus, M365 Manager/Security Plus, Exchange Reporter Plus, SharePoint Manager Plus, SupportCenter Plus, AssetExplorer, Analytics Plus, AppCreator, RMM Central, Remote Access Plus, DataSecurity Plus, FileAnalysis, Patch Manager Plus, Patch Connect Plus, Vulnerability Manager Plus, OS Deployer, MDM Plus, Application/Browser/Device Control, Malware/Ransomware Protection, Cloud Security Plus, Firewall Analyzer, NetFlow Analyzer, NCM, OpUtils, DDI Central, Applications Manager; плюс OpManager MSP/Nexus/интерфейсы (в ZOHO-OPMANAGER) и английская SDP Standard (в ZOHO-SDP) | 82 | manageengine — разделы по каждому продукту; 8 позиций needs_operator (название витрины расходится с артикулом) |
| 2 | JetBrains AI/Qodana/TeamCity/YouTrack/Datalore (quote-only, JB-TOOLS); Microsoft; SolidWorks | ~25 | jetbrains (готов), microsoft, dassault |
| 3 | Adobe Acrobat / Express / Substance / Firefly / Stock; Maxon One / C4D / Redshift / ZBrush / Universe; Figma; Parallels | ~30 | adobe, maxon (готов), figma, parallels |
| 4 | AI-сервисы (OpenAI, Anthropic, Midjourney, Runway, ElevenLabs, Kling, Hailuo, Recraft…) — классы `credit` и `edition_tier` | ~60 | по вендору |
| 5 | Длинный хвост: вендоры с 1–3 карточками | ~230 | по вендору, профиль короткий |

Порядок внутри волны — по убыванию числа карточек. Семейство считается
готовым, когда `node scripts/content/validate-family.mjs <file> --published
<slugs>` возвращает 0 ошибок.

## Применение (одна волна)
1. `ops-apply-content apply=false` по семействам волны — план и счётчик изменений в issue #22.
2. `apply=true`; legacy-поля (`features`, `description`, `for_whom`, `use_cases`, `seo_text`) опустошаются по `legacy_disposition`; `faq` заменяется; `related_products` записывается; `content_version = cm-1.0`; штамп `content_updated_at`.
3. `ops-card-shot` — одна позиция каждого класса волны (`suite/team`, `individual`, `edition_tier`, `volume_tier`, `addon`, `credit`, `perpetual`).
4. `ops-indexnow` адресно по всем URL волны сразу после записи (10 000 URL/сутки, Яндекс + Bing). Переобход Вебмастера `ops-yandex-recrawl` — отдельный ночной поток партиями по семействам в окно 00:30–00:40 МСК (квота 150, до `seo-recrawl-sweep`); волну он не задерживает, график в issue #22.
5. `ops-catalog-watch` — письмо о массовом событии ожидаемо; после последней волны `baseline=true`.
6. Наблюдение 28 дней через `seo-daily-report`; сниппет-эксперименты на затронутых кластерах не заводятся (`snippet-experiments.md`).

## Гейты, которые не отменяются массовым разрешением
- Позиция без `family_key` или с `needs_operator=true` — не применяется, уходит в список руководителю кнопками.
- Цена, минимум, единица в тексте расходятся с данными → валидатор красный, применение блокируется.
- `quote_only` и `gift_card`: композиция по `bizsoft-product-nonstandard-cards`; контент — модули `WHAT_YOU_BUY`-логика (`credit`/`BEFORE_ORDER`), без счётчика.
- Плагины JetBrains — отдельное задание (снятие + 301), в очередь не входят.
- Меты: `catalog-uniqueness` в `pnpm test` остаётся гейтом PR.

## Откат
`content_modules = null` по семейству → шаблон возвращает legacy-ветку; legacy-поля восстанавливаются из `ops-backup` снимка дня применения (снимок делать перед каждой волной).
