# Пилот · content_modules (cm-1.0) · семейства MAXN-REDGIANT, ZOHO-OPMANAGER, ACRN-CP, ADBE-CC

Пакет этапов 1–4 постановки `product-card-content-system.md`. Куда класть в репозиторий:

| Файл здесь | Путь в репо |
|---|---|
| `prompts/1-vendor-profile.md`, `2-family-generation.md`, `3-validate-and-review.md` | `docs/tasks/product-card-content-system/prompts/` |
| `vendors/maxon.md`, `vendors/manageengine.md`, `vendors/acronis.md`, `vendors/adobe.md` | `data/content/vendors/` |
| `families/MAXN-REDGIANT.json`, `families/ZOHO-OPMANAGER.json`, `families/ACRN-CP.json`, `families/ADBE-CC.json` | `data/content/families/` |
| `scripts/validate-family.mjs` | `scripts/content/validate-family.mjs` (запуск: `node scripts/content/validate-family.mjs data/content/families/MAXN-REDGIANT.json --published <список slug>`) |
| `mockup-pilot.html` | не в репо — артефакт для Design Approval Gate |

**Design Approval Gate: макет Red Giant и OpManager одобрен руководителем 13.09.2026** — разрешение на шаги 1–3 (схема, рендер `content_modules`, `ops-apply-content`). Статус: валидатор зелёный по четырём семействам (25 позиций, 0 ошибок): Red Giant (2), OpManager (3), Acronis Cyber Protect — вся линейка (16), Adobe Creative Cloud (4). Порог предупреждения об объёме модуля откалиброван до 140 знаков. Правило валидатора уточнено: `volume_tier` требует `PLAN_COMPARE` или `BEFORE_ORDER` (когда на витрине один объём). Макет опубликован, ждёт замечаний и одобрения руководителя.

Что нужно сделать в репо до применения (DATA GAP, п. 4 постановки): поля `product_nature`, `packaging`, `family_key`, `unit_label`, `content_modules`, `content_version` в Directus (`ops-directus-schema`); ветка рендера `content_modules` в `src/pages/product/[slug].astro`; workflow `ops-apply-content` по образцу `ops-apply-descriptions`. Легаси-поля семейства (`features`, `description`, `faq`) после применения опустошаются — см. `legacy_disposition` в JSON.

Замечания по классификации из семейства OpManager (для этапа 0):
- реестр артикулов ставит план `TEAM` продуктам без индивидуальной альтернативы — по постановке это `universal`;
- `volume_tier`: единица товара — пакет, счётчик количества неверен, нужен выбор объёма (DATA GAP в шаблоне);
- вендор `Zoho` у карточек ManageEngine — решение п. 7 постановки, в макете показан как «Zoho Corporation (ManageEngine)».

Находки семейства Acronis (исправить данные вместе с применением):
- пять карточек Standard несли дословно один текст; на Standard Server заявлен бэкап SAP HANA — по вендору он есть только в Backup Advanced;
- «Расчётная единица: Рабочее место» у серверных, хостовых и облачных лицензий → `unit_label` по нагрузке;
- макеты Acronis (16) и Adobe CC (4) одобрения ещё не проходили (одобрены Red Giant и OpManager);
- legacy Acronis Advanced/Backup Advanced: SAP HANA у Advanced, «дедупликация» у Advanced, «без модуля антивируса» у Backup Advanced — исправлены по вендору.

Находки Adobe: реестр ставит CC Standard `UNI` — у Adobe это индивидуальный план; Single App для команд — `mono`, а не `suite`; 10 одиночных приложений — отдельное семейство ADBE-APPS (следующее).
