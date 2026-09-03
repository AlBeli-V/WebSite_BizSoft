# Ежедневный прогон конкурентной разведки

С 03.09.2026 прогон выполняет workflow
`.github/workflows/competitive-intelligence-daily.yml` (09:20 МСК,
контрольный слот 10:05 МСК): pull ветки `competitive-data`, `run_daily.py`,
тесты, push, публикация deep report и запуск почтового workflow
`competitive-intelligence-mail` с проверкой маркера `last-mailed.txt`.
Сторож почтового workflow в 10:40 МСК по-прежнему шлёт уведомление о сбое,
если письма за сегодня нет.

Routine «BIZSoft Конкурентная разведка» и «Сторож письма конкурентной
разведки» на сессиях Claude упразднены решением руководителя (разбор
расхода токенов); правило и устройство прогонов —
`docs/rules/operational-runs.md`. Прежний текст промпта — в истории git
этого файла до 03.09.2026.
