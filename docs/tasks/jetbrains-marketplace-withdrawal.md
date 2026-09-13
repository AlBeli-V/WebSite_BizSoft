# Снятие плагинов JetBrains Marketplace с витрины

Решение руководителя 13.09.2026 (снятие; 301 на позицию «по запросу» — подтверждено тем же днём). Основание: 867 позиций `JB-PLG-*` (55 % реестра
артикулов) не индексируются (`productNoindex`), не приносят выручки, требуют
по-плагинной проверки модели лицензирования у сторонних разработчиков
(сейчас все ошибочно закодированы `1Y`), шумят в `ops-catalog-watch` и
реестрах, а вендор у них проставлен неверно (JetBrains вместо автора).

## Что сделать

1. **Снять с витрины, не удалять** (`docs/rules/catalog.md`): всем позициям с
   артикулом `JB-PLG-*` (и их новым артикулам `JB-ADD-*` из
   `sku-assignment.json`) выставить `status = draft`. Механизм —
   детерминированный: новый одноразовый workflow `ops-withdraw-jb-plugins`
   по образцу `ops-apply-descriptions` (`apply=false` → план и счётчик →
   `apply=true`), с `# expires:` (`report-integrity.md`); ручной правки в
   Directus нет.
2. **Одна договорная позиция** «Плагин JetBrains Marketplace — по запросу»:
   `price = 0` (композиция `quote_only`), вендор JetBrains, категория —
   основная категория вендора, `content_modules`: `ADDON_SCOPE` (что такое
   платный плагин Marketplace, что модель лицензирования — месяц/год/
   бессрочно/с fallback — задаёт автор, лицензия лежит в JetBrains Account
   отдельно от IDE), `DEPENDENCIES` (совместимая IDE, версия, редакция,
   число Plugin Users), `BEFORE_ORDER` (назвать плагин, IDE и число
   пользователей; co-terming со сроком IDE — по желанию). CTA — «Запросить
   КП», форма с полем «Плагин».
3. **Страница вендора JetBrains** (`vendor-page-rebuild`): абзац
   «Плагины Marketplace оформляем по запросу» со ссылкой на позицию п. 2.
4. **Sitemap и индекс** — решение руководителя 13.09.2026: снятые URL
   отдают **301 на позицию п. 2**. Механизм — `old_slugs` у позиции п. 2
   (штатный редирект `catalog.md`, без правки nginx); 867 слагов заносятся
   тем же workflow п. 1. Плагины и так вне sitemap; после выката —
   `ops-index-validate`, отчёт в issue #22.
5. **Реестры**: перегенерировать `sku-assignment.json`
   (`scripts/catalog/sku-assign.mjs`), пересобрать базу `ops-catalog-watch`
   с `baseline=true`, записать решение в
   `reports/seo/intelligence/vendor-decisions.json` (ветка `seo-data`,
   `brand`, `decided_on`, `reason`, `by`).
6. **Возврат плагина в каталог** — только по заявке или по спросу выше
   порога экспозиции кластера (`snippet-experiments.md`, 3,6 показа/сутки),
   с заполнением полей класса `addon`
   (`addon_source = marketplace`, `license_model`, `fallback`, `requires`,
   `plugin_users`) и вендором — автором плагина.

## Проверка
`pnpm test`, `pnpm verify`, `pnpm smoke`; письмо `ops-catalog-watch` за день
снятия — ожидаемое массовое событие, после него `baseline=true`; отчёт в
issue #22.

## Что не трогать
Основные продукты JetBrains (IDE, All Products Pack, dotUltimate, AI Pro/
Ultimate, Qodana, TeamCity, YouTrack) — остаются; ManageEngine и Zoom
дополнения — класс `addon` с `addon_source = vendor`, остаются и входят в
пилот постановки `product-card-content-system.md`.
