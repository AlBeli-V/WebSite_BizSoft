# Нижняя часть карточки — модули по классу товара

Решение руководителя 13.09.2026 (постановка —
`docs/tasks/product-card-content-system/README.md`, план прогона — `ROLLOUT.md`).

- Нижняя часть карточки (от hero-описания до FAQ) собирается из поля
  `content_modules` (JSON) по классу товара: оси `product_nature`,
  `packaging`, план из артикула, срок, единица `unit_label`. Пустое поле —
  legacy-рендер (`features`, `description`, `seo_text`) без изменений.
- Контент пишется **семействами** (`family_key`), не карточками: у семейства
  есть носитель, соседи несут дельту и ссылки. Источник фактов — профиль
  вендора `data/content/vendors/<vendor>.md` по официальным источникам.
- Файл семейства `data/content/families/<FAMILY>.json` проходит
  `node scripts/content/validate-family.mjs <file>` (модули по матрице,
  лимиты, запрещённые фразы, повторы внутри страницы и между соседями,
  меты). Красный — не применяется.
- Запись в прод — только `ops-apply-content` (`apply=false` → `true`),
  с `main`; legacy-поля семейства при этом опустошаются; откат —
  `content_modules = null` + `ops-backup` дня прогона.
- FAQ карточки — только вопросы, зависящие от вендора; про оплату, договор,
  ЭДО и доступ — `policies.ts` и `/faq`.
