# Восстановление ежедневного триггера отчётности (v2)

Система запускается Routine-триггером Claude Code (среда CCR, сессия «BIZSoft Growth Intelligence»). Если триггер или сессия утеряны — создать заново из любой сессии Claude Code этого репозитория:

- **Расписание:** cron `3 3 * * *` UTC (09:03 Бишкек, ежедневно).
- **Текущий триггер:** `trig_013uQS6iK8LGVQETEaKDWFxY` («BIZSoft Search Performance Brief»), сессия `session_01JoQwrqUDpG5fpgeEWaNzKx`.
- **Промпт триггера** (актуальная редакция от 19.08.2026, отчётность v2):

> Ежедневный прогон отчётности BIZSoft Search Performance (v2). Источник истины по методике — reports/seo/README.md и docs/seo/reporting-methodology.md в репозитории WebSite_BizSoft, ветка claude/biz-soft-rating-tracking-5rf03g. Порядок: 0) git pull; git fetch origin main; синхронизируй reports/seo/intelligence/seo-experiments.json с main (main первичен) и проверь коммиты main за сутки — что внедрено; запусти воркфлоу seo-data-collect.yml и seo-site-check.yml (GitHub MCP actions_run_trigger, ref ветки), дождись коммита данных, git pull. 1) Прогони конвейер: python3 scripts/seo/snapshot.py <дата>; python3 scripts/seo/quality.py <дата>; python3 scripts/seo/report_v2.py <дата> (графики строятся внутри); затем python3 -m unittest discover -s scripts/seo/tests — все тесты обязаны проходить. 2) Прочитай snapshot и data-quality JSON и проверь сгенерированный executive brief: объём ≤900 слов, ≤3 решения, нет противоречий между блоками, каждый KPI с источником и периодом, при critical-находке общий статус не зелёный и зависящие выводы подавлены. 3) Дополни решения и статусы содержательно, только на основании snapshot: не выдумывай значения, причины, бюджеты и рыночные бенчмарки; отсутствующее — «нет данных»; показы называть видимостью страниц, а не спросом; цели Метрики — целевыми событиями, а не заявками; низкую выборку маркировать; формулировки типа «Яндекс наращивает доверие», «уже в топ-5», «лучший день» запрещены. 4) Проверь активные эксперименты по их primary metric и guardrails; вердикт объявляй только при достаточном объёме наблюдений (не по фиксированным 7 дням); статусы задач бери из main и seo-site-check, не из вчерашнего отчёта; технические задачи веди тикетами reports/seo/tasks/, промты в письмо не вставляй. 5) Обнови приложение (reports/seo/intelligence/<дата>-appendix.md) — полные таблицы, расхождения источников, реестр экспериментов, риски, тикеты, графики. 6) git pull --rebase, коммит, push — воркфлоу seo-report-email отправит executive brief на avbelyaev@biz-soft.pro (проверь статус run). 7) SendUserFile: executive.html (display render, status proactive) и appendix.md; в caption — общий статус одним предложением и главное изменение. Понедельник — недельный отчёт (reports/seo/weekly/), 1-е число — месячный (monthly/). Ограничения: деплой не выполнять, main не менять, biz-soft.pro и рекламные кабинеты недоступны из среды напрямую — только через воркфлоу.

При изменении промпта триггера — обновлять и этот файл (единая точка восстановления).

## Зависимости системы (что должно быть живо)

- Секреты репозитория: `SMTP_PASS`, `GSC_SERVICE_ACCOUNT_JSON`, `YANDEX_WEBMASTER_TOKEN`,
  `YANDEX_METRIKA_TOKEN`, `YANDEX_METRIKA_COUNTER_ID`, `GA4_PROPERTY_ID`.
- Воркфлоу: `seo-data-collect.yml` (сбор), `seo-report-email.yml` (почта, отправляет
  `intelligence/<дата>-executive.html`), `seo-site-check.yml` и `seo-ga4-admin.yml` (утилиты).
- Скрипты v2: `scripts/seo/{snapshot,quality,charts,report_v2}.py`, тесты `scripts/seo/tests/`.
- Токен Яндекса живёт ~1 год — при истечении перевыпустить и обновить секреты.
