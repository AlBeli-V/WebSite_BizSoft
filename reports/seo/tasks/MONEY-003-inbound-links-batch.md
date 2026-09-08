# MONEY-003 — Входящие ссылки на страницы партии MONEY-A1

**Приоритет:** P2 · **Статус:** queued · **Заведено:** 2026-09-08 · **Созревает:** 2026-10-06 · **Ждёт:** MONEY-A1

## Проблема

У `/vendors/capture-one` и `/vendors/freepik` на весь сайт **ноль входящих
внутренних ссылок** (проверено по `src/`). Кластер Capture One при этом растёт
в каждой выгрузке с 31.08 и уже даёт 211 показов за 12 дней.

## Почему не сейчас

Перелинковка — фактор ранжирования. Заведи её вместе со сниппетом, и вывод
партии MONEY-A1 станет неотделим от вывода о ссылках. Записи в
`SEO_EXPERIMENT_LINKS` для этих страниц сознательно не заведены, тест
`tests/seo-experiments.test.ts` это фиксирует с объяснением.

## Что сделать после 06.10

| Откуда | Куда | Анкор |
|---|---|---|
| `/catalog/design` | `/vendors/capture-one` | Capture One — оплата и продление для студии |
| `/blog/kak-kupit-zarubezhnoe-po-dlya-yurlica` | `/vendors/capture-one` | оплата Capture One юридическим лицом |
| `/vendors/adobe` | `/vendors/capture-one` | RAW-конвертер Capture One |
| `/catalog/design` | `/vendors/freepik` | Magnific и Freepik — подписка на компанию |
| `/vendors/midjourney`, `/vendors/recraft` | `/vendors/freepik` | Magnific — апскейл генераций |
| `/` и `/catalog` (`SEO_EXPERIMENT_LINKS`) | обе | по формуле реестра |

Завести отдельной записью эксперимента программы B со своей датой: один
эксперимент — одно изменение.
