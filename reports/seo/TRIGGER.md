# Восстановление ежедневного триггера отчётности (V3)

Система запускается Routine-триггером Claude Code (среда CCR, сессия «BIZSoft Growth Intelligence»). Если триггер или сессия утеряны — создать заново из любой сессии Claude Code этого репозитория:

- **Расписание:** cron `3 3 * * *` UTC (09:03 Бишкек, ежедневно).
- **Текущий триггер:** `trig_013uQS6iK8LGVQETEaKDWFxY` («BIZSoft Search Performance Brief»), сессия `session_01JoQwrqUDpG5fpgeEWaNzKx`.
- **Промпт триггера** (актуальная редакция от 19.08.2026, письмо V3):

> Ежедневный прогон отчётности BIZSoft Search Performance (V3). Методика — reports/seo/README.md и docs/seo/reporting-methodology.md, ветка claude/biz-soft-rating-tracking-5rf03g. 0) git pull; git fetch origin main; синхронизируй reports/seo/intelligence/seo-experiments.json с main и проверь коммиты main за сутки; запусти воркфлоу seo-data-collect.yml и seo-site-check.yml, дождись коммита данных, git pull. 1) Конвейер: python3 scripts/seo/snapshot.py <дата>; python3 scripts/seo/quality.py <дата>; python3 scripts/seo/report_v3.py <дата>; python3 scripts/seo/uxlint.py <дата>; скриншоты node scripts/seo/render.mjs с манифестом на 375 и 680 px в reports/seo/intelligence/previews/; python3 -m unittest discover -s scripts/seo/tests. Рыночный спрос подтягивается из reports/seo/semantics/brief-*.json автоматически: если замера нет или он собран до включения фильтра релевантности, письмо честно пишет «рыночный спрос ещё не измерен». UX lint и тесты обязаны быть зелёными — иначе письмо не отправляется, а причина фиксируется в отчёте. 2) Актуализируй reports/seo/intelligence/actions.json: статусы, сроки и владельцы из карты ролей (Data Auditor, SEO Lead, PPC Lead). GREEN и YELLOW агенты ведут сами — они попадают в блок «Система уже делает»; RED (бюджет, юридические обязательства, цены, домены, необратимые изменения) — в блок «От вас»; если RED, ожидающих решения, нет — письмо показывает «действий не требуется». 3) Проверь письмо: 450–650 видимых слов, ≤4 показателя, ≤3 изменения, ≤3 действия, ≤2 PNG-изображения, без inline SVG, без технических терминов (SOURCE_RECONCILIATION, guardrails, snapshot, ym:s:visits, popular queries, rollback, stop-condition, key events) и без локальных путей; ссылки — кликабельные URL на приложение, журнал работ, проверки качества и PR. Составной статус: Яндекс, Google, общий вывод. Нулевая дельта — «не изменилось», слова роста и падения запрещены. Совместное внедрение — один эксперимент. Воронка не показывается до завершения сверки: вместо неё карта измерения. 4) Обнови приложение <дата>-appendix.md: полная таблица свежести, все предупреждения, таблицы запросов и страниц, роли и зоны, словарь терминов, тикеты, графики. 5) git pull --rebase, коммит, push — seo-report-email отправит письмо с PNG-вложениями на avbelyaev@biz-soft.pro (проверь статус run). 6) SendUserFile: preview письма (<дата>-executive.html, display render, status proactive), скриншоты previews/ и приложение; в caption — итог дня одним предложением и что требуется от руководителя. Понедельник — недельный отчёт (weekly/), 1-е число — месячный (monthly/). Ограничения: деплой не выполнять, main не менять, сайт и рекламные кабинеты не трогать.

При изменении промпта триггера — обновлять и этот файл (единая точка восстановления).

## Зависимости системы (что должно быть живо)

- Секреты репозитория: `SMTP_PASS`, `GSC_SERVICE_ACCOUNT_JSON`, `YANDEX_WEBMASTER_TOKEN`,
  `YANDEX_METRIKA_TOKEN`, `YANDEX_METRIKA_COUNTER_ID`, `GA4_PROPERTY_ID`.
- Воркфлоу: `seo-data-collect.yml` (сбор), `seo-report-email.yml` (почта, отправляет
  `intelligence/<дата>-executive-email.html` с PNG-вложениями), `seo-site-check.yml` и `seo-ga4-admin.yml` (утилиты).
- Скрипты: `scripts/seo/{snapshot,quality,charts,charts_png,report_v2,report_v3,uxlint}.py`,
  рендер `scripts/seo/render.mjs` (Playwright + Chromium из /opt/pw-browsers), тесты `scripts/seo/tests/`.
- Карта ролей и действий: `reports/seo/intelligence/actions.json` (поле `demand_clusters`
  связывает действие с кластерами спроса — из него берётся строка «Зачем» в письме).
- Рыночный спрос: `seo-wordstat.yml` (расписание живёт в main), скрипты
  `scripts/seo/{build_clusters,collect_wordstat,semantics}.py`, артефакты в
  `reports/seo/semantics/`. Лимит сервиса — 100 запросов в час, сбор возобновляемый.
- Токен Яндекса живёт ~1 год — при истечении перевыпустить и обновить секреты.
