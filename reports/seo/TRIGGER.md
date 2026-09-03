# Ежедневный запуск отчётности Growth Intelligence

С 03.09.2026 ежедневное письмо V4 собирает workflow
`.github/workflows/seo-daily-report.yml` (09:00 МСК, контрольный слот
09:35 МСК), еженедельное письмо комитета — `seo-committee-build.yml`
(понедельник 09:10 и 09:50 МСК). Routine на сессии Claude «BIZSoft Growth
Intelligence» упразднена решением руководителя (разбор расхода токенов);
правило и устройство прогонов — `docs/rules/operational-runs.md`.

Восстанавливать нечего: расписание живёт в workflow и приезжает с `main`.
Ручной пересбор за сегодня — запуск `seo-daily-report` с `force=yes`
(только с ветки main).

Прежний текст промпта Routine — в истории git этого файла до 03.09.2026.
