# GIDX-002 — Подача приоритетных URL в переобход Google

**Приоритет:** P1 · **Зона:** YELLOW · **Статус:** proposed · **Владелец:** seo_lead
· **Момент запуска:** через 7 дней после деплоя GIDX-000 (сигналы обхода), не раньше

## Контекст
Из 112 URL уровней TIER 1–2 (`reports/seo/google-url-priority.csv`) Google не скачал 82.
В TIER 1 — 22 лендинга вендоров, стоящих в Яндексе на 1–3 местах и неизвестных Google
(`/vendors/anthropic`, `/vendors/atlassian`, `/vendors/capture-one`, `/vendors/cursor`,
`/vendors/google`, `/vendors/perplexity`, `/vendors/slack` и другие).

## Ограничение, которое надо назвать прямо
**Программного переобхода у Google нет.** Indexing API принимает только `JobPosting` и
`BroadcastEvent` — карточки товаров и лендинги через него не подаются. IndexNow
(`ops-indexnow` в проекте) обслуживает Яндекс и Bing, Google его не поддерживает.
Остаётся ручная инспекция URL в Search Console с квотой порядка 10–13 адресов в сутки.
Аналога `ops-yandex-recrawl` для Google построить нельзя — это не пробел реализации,
а отсутствие интерфейса у поисковика.

## Задача
1. Дождаться, что сигналы GIDX-000 (`lastmod`, ссылки, канонический хост) отработали:
   `ops-server-stats` показывает рост запросов Googlebot, `index-google-*.json` — рост
   числа скачанных URL. Подавать URL до этого бессмысленно: страница вернётся в ту же
   очередь.
2. Порядок ручной подачи — по убыванию GIPS из `google-url-priority.csv`, 10 адресов в
   сутки, начиная с TIER 1.
3. Каждый прогон — запись в журнал (issue #22) со списком поданных адресов, чтобы
   эффект можно было отделить от фонового обхода.

## Приёмка
Поданные URL переходят из `Discovered — currently not indexed` в `Submitted and indexed`
в срезе `index-google-*.json` следующих суток.

## Зависимости
GIDX-000 в проде; данные `ops-server-stats` с разрезом Googlebot (уже в коде).
