# Восстановление ежедневного триггера отчётности (V4)

Система запускается Routine-триггером Claude Code (среда CCR, сессия «BIZSoft
Growth Intelligence»). Если триггер или сессия утеряны — создать заново из
любой сессии Claude Code этого репозитория.

- **Расписание:** cron `0 6 * * *` UTC (09:00 МСК, ежедневно; время проекта —
  московское, правило CLAUDE.md).
- **Текущий триггер:** `trig_013uQS6iK8LGVQETEaKDWFxY`, сессия
  `session_01JoQwrqUDpG5fpgeEWaNzKx`.
- **Устройство:** код — в `main`, машинные данные — в orphan-ветке `seo-data`
  (см. README этой ветки); обмен — `scripts/seo/data_sync.sh`.

Промпт триггера (актуальный текст):

> Ежедневный прогон BIZSoft Growth Intelligence (письмо V4 «Executive Command
> Center»). Методика — reports/seo/README.md и docs/seo/reporting-methodology.md.
> Код — в main, машинные данные — в ветке seo-data; обмен данными — только
> через scripts/seo/data_sync.sh; в main из прогона ничего не коммитится,
> правки кода — отдельным PR.
> 0) git fetch origin main seo-data; git checkout main; git pull; bash
> scripts/seo/data_sync.sh pull. Запусти воркфлоу seo-data-collect.yml и
> seo-site-check.yml (GitHub MCP actions_run_trigger, ref main), дождись их
> успешного завершения — они пишут в seo-data — и снова bash
> scripts/seo/data_sync.sh pull. Просмотри коммиты main за сутки.
> 1) Конвейер: python3 scripts/seo/snapshot.py <дата>; python3
> scripts/seo/quality.py <дата>; python3 scripts/seo/report_v4.py <дата>;
> python3 scripts/seo/webreport.py <дата>; node scripts/seo/emailcheck.mjs
> reports/seo/intelligence/<дата>-v4.html
> reports/seo/intelligence/<дата>-v4-render.json; python3
> scripts/seo/uxlint_v4.py <дата>; python3 scripts/seo/contentcheck.py <дата>;
> python3 scripts/seo/previews_v4.py <дата>; python3 -m unittest discover -s
> scripts/seo/tests -t scripts/seo/tests. UX lint, качество содержания и тесты
> обязаны быть зелёными — иначе письмо не отправляется, а причина фиксируется
> в отчёте.
> 2) Актуализируй reports/seo/intelligence/actions.json: статусы, стадии,
> сроки, владельцев, поля status_changed_at, pr/ci/qa/deploy/rollback и
> demand_clusters. В журнал письма попадают только задачи со сменой статуса
> сегодня, блокировкой или сроком в ближайшие 7 дней. RED (бюджет, юридические
> обязательства, цены, домены, необратимые изменения) — блок «От вас»; если
> RED нет, письмо показывает «действий не требуется».
> 3) Правила письма: 800–1000 видимых слов, первый экран до 250; ≤4
> показателя, ≤3 сигнала, ≤3 возможности, ≤5 строк журнала, ≤3 изображения.
> Причина изменения либо подтверждена перечисленными страницами и запросами,
> либо не называется. Нулевая дельта — «без изменений». Если источник не
> обновился — сказать прямо и не подавать вчерашнюю дельту как новость.
> «Рыночный спрос» разрешён только при замере Вордстата. Один факт не
> повторяется больше двух раз.
> 4) Веб-отчёт reports/seo/public/daily/<дата>/index.html — полные таблицы,
> карта измерений, история экспериментов, журнал исполнения, качество данных
> и методика. Письмо ведёт туда; пока PUBLIC_REPORT_BASE_URL не задан, ссылка
> помечается как техническая копия.
> 5) bash scripts/seo/data_sync.sh push "Отчёт за <дата>" — push в seo-data
> запускает seo-report-email (письмо на avbelyaev@biz-soft.pro; одно письмо на
> дату — маркер reports/seo/intelligence/last-mailed.txt). Проверь статус run.
> 6) SendUserFile: preview письма (<дата>-v4.html, display render, status
> proactive) и веб-отчёт; в caption — итог дня одним предложением и что
> требуется от руководителя.
> 7) Если рыночный спрос собран полностью (market_demand.complete) и в нём
> есть разрывы — подготовь правки карточек товара по измеренным коммерческим
> фразам: PR в main с указанием фразы и её частотности по каждой правке,
> тесты и сборка зелёные, затем мерж (полномочие выдано руководителем
> 19.08.2026).
> Понедельник — недельный отчёт (weekly/), 1-е число — месячный (monthly/).
> Ограничения: рекламные кабинеты не трогать; цены, домены, юридические
> обязательства и бюджет — решение руководителя; изменения сайта — только
> через PR с обоснованием измеренным спросом.
