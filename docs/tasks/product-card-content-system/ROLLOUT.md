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
| 2 (готово, патч 5, партия 100) | Figma (9), Adobe Acrobat/Express/Substance/Firefly/Stock (11), Microsoft бессрочные (13), Parallels (4), ChatGPT/OpenAI/Claude (7), JetBrains tools (7), ManageEngine: ADManager (5), ADAudit (2), M365/Exchange/SharePoint (7), PAM-линия (12), SupportCenter (6), Endpoint-безопасность (16), SDP Standard (1) | 100 | figma, microsoft, parallels, openai-anthropic, adobe, jetbrains, manageengine |
| 3 (готово, патч 6, партия 68) | Zoom, TeamViewer, AnyDesk (12); Atlassian, Slack, Notion, Miro, Dropbox, Box (15); Docker, GitLab, GitHub Copilot, Postman, Sentry, BrowserStack, n8n, Cloudflare, Cursor, Windsurf (22); Canva, Grammarly, DeepL, Framer, Sketch, Zeplin, Gamma (19). ManageEngine сеть (17) и данные/MDM (16) из патча 6 отброшены — те же 33 карточки уже слиты волной 1 (#545) | 68 | краткие профили 26 SaaS-вендоров. Решения руководителя 14.09.2026 по последним четырём needs_operator: Analytics Plus (2) — текст по артикулу, название витрины исправлено; OpUtils (2) — позиции признаны дополнительными пакетами ёмкости, композиция переписана на `addon`. Решение руководителя 13.09.2026 по 4 позициям needs_operator волны 1 (NetFlow Standard 500, NCM Enterprise 250, Firewall Analyzer Enterprise 20, Applications Manager Enterprise 100): текст по артикулу, название витрины исправить `ops-rename-product` до применения |
| 4 (готово, патч 7, партия 102) | SolidWorks (8), Autodesk (5), Foundry (6), Houdini (4), Boris FX (4), SketchUp (4), Lumion (3), Unity (2), Epic (2), Toon Boom (2), Reallusion (3), Marmoset (2), Rizom (2), Spine (2), Gaea (3), Wwise (3), FMOD (3), Ableton (3), Cubase (3), FL Studio (4), NI (4), iZotope (4), Topaz (4), Telestream (4), VEGAS (3), Wondershare (3), Capture One (1), Resolve (1), Corel (3), Clip Studio (2), Procreate (2), Astute (1), think-cell (1), WinRAR (1) | 102 | краткие профили инженерных, творческих и аудио-вендоров |
| 1 (готово, ветка claude/friendly-hopper-rpidvh) | остальные ManageEngine после волны 2: OpManager MSP/Nexus/интерфейсы (в ZOHO-OPMANAGER), DataSecurity Plus (5), FileAnalysis, MDM Plus (4), Cloud Security Plus, Firewall Analyzer (3), NetFlow Analyzer (3), NCM (2), OpUtils (2), DDI Central (2), Applications Manager (2), Analytics Plus (2), AppCreator, AssetExplorer, RMM Central; 49 позиций ManageEngine ушли волной 2 | 33 | manageengine — разделы по каждому продукту (35 новых); 8 позиций needs_operator (название витрины расходится с артикулом) |
| 2 | JetBrains AI/Qodana/TeamCity/YouTrack/Datalore (quote-only, JB-TOOLS); Microsoft; SolidWorks | ~25 | jetbrains (готов), microsoft, dassault |
| 3 | Adobe Acrobat / Express / Substance / Firefly / Stock; Maxon One / C4D / Redshift / ZBrush / Universe; Figma; Parallels | ~30 | adobe, maxon (готов), figma, parallels |
| AI (следующая, решение 14.09.2026) | AI-сервисы (OpenAI, Anthropic, Midjourney, Runway, ElevenLabs, Kling, Hailuo, Recraft…) — классы `credit` и `edition_tier` | ~60 | по вендору |
| 5 | Длинный хвост: вендоры с 1–3 карточками | ~230 | по вендору, профиль короткий |

Порядок внутри волны — по убыванию числа карточек. Семейство считается
готовым, когда `node scripts/content/validate-family.mjs <file> --published
<slugs>` возвращает 0 ошибок.

## Состояние на 14.09.2026

Контент написан для 376 карточек из 490 на витрине (77 %), 95 семейств.
Позиций с непрояснённым `needs_operator` не осталось. Без контента — 114
карточек. Счёт держится по реестру `rollout-queue.csv` (489 позиций) плюс
пилотная Red Giant.

Партии 274 карточек (волны 0–3 и хвост ManageEngine) записаны в прод и
несут `content_version = cm-1.0`. Партия 102 карточек инженерных,
творческих и аудио-вендоров слита в репозиторий и применяется отдельно.

Решение руководителя 14.09.2026 о порядке дальше: следующей идёт партия
AI-сервисов (классы `credit` и `edition_tier`, ~60 карточек) — это самая
масса из оставшегося, и на ней обкатывается композиция пополнений до
длинного хвоста. За ней остаётся длинный хвост вендоров с одной-тремя
карточками.

Номера волн в таблице ниже сквозными не являются: очередь заводилась по
массе витрины, а партии шли по готовности профилей вендоров. Ориентир —
пометка «готово» и номер патча, а не номер строки.

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
