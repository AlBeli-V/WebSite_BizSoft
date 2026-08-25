# Карта процессов маркетинговой/аналитической подсистемы — AS-IS (25.08.2026)

Техническая схема: кто, когда и чем запускается, какие скрипты и API
задействованы, куда пишутся результаты. Только фиксация фактов; изменения не
предлагаются. Основной отчёт: `marketing-system-audit-as-is.md`.

---

## 1. Три исполнителя

Система исполняется тремя разными механизмами — это главный структурный факт:

1. **GitHub Actions (cron/push)** — сбор данных, Wordstat, доставка письма,
   публикация веб-отчёта, приёмка целей.
2. **Routine-сессия Claude Code** «BIZSoft Growth Intelligence» (cron
   `0 6 * * *` UTC = 09:00 МСК, триггер `trig_013uQS6iK8LGVQETEaKDWFxY`,
   постоянная сессия; текст промпта зафиксирован в `reports/seo/TRIGGER.md`) —
   **весь конвейер формирования отчёта**: snapshot → quality → report_v4 →
   webreport → проверки → push. Ни один workflow эти скрипты не вызывает
   (проверено grep по `.github/workflows/*.yml`).
3. **Человек (workflow_dispatch)** — разовые операции: goals-sync, ga4-admin,
   recrawl, indexnow, экспорт каталога и т.п.

## 2. Ветки: где код, где данные

```
main                     — единственный источник кода (scripts/, workflows, src/)
seo-data (orphan)        — единственное живое хранилище машинных данных:
                           reports/seo/{data,wordstat,intelligence,public}
                           26 коммитов с 23.08.2026, все от «Claude», 7–11/сутки
archive/rating-tracking-5rf03g — замороженный предшественник (23.08),
                           уникального кода нет, защищён от удаления
claude/me-sources        — второе хранилище данных: краулы ManageEngine
                           (data/sources/, пишет ops-me-crawl force-with-lease)
claude/assets-incoming   — приёмник ops-fetch-assets
```

Обмен main ↔ seo-data — только `scripts/seo/data_sync.sh`:
`pull` накатывает 4 каталога из `origin/seo-data` в рабочую копию;
`push` полностью заменяет эти каталоги во временном worktree, коммитит и
пушит с тремя попытками `rebase -X theirs`.

**FACT.** В `seo-data` лежат копии двух workflow (`seo-report-email.yml`,
`seo-publish-web.yml`): push-триггер GitHub срабатывает только если файл
workflow существует в пушенной ветке. Копии синхронизируются вручную
(diff с main — только заголовок «КОПИЯ ИЗ MAIN»).

## 3. Реестр workflow подсистемы

| Workflow | Триггер | Скрипты | API/секреты | Пишет |
|---|---|---|---|---|
| `seo-data-collect` | cron 02:40 UTC (05:40 МСК); push main (сам файл/collect.py); dispatch | `collect.py` | GSC (`GSC_SERVICE_ACCOUNT_JSON`), Вебмастер (`YANDEX_WEBMASTER_TOKEN`), Метрика (`YANDEX_METRIKA_TOKEN`, `..._COUNTER_ID`), GA4 (`GA4_PROPERTY_ID`) | `reports/seo/data/<источник>-<дата>.json` → push `seo-data` (`if: always()`) |
| `seo-wordstat` | cron 01:20 UTC full + `*/6` добор; push main (код wordstat → dry-run); dispatch (7 режимов) | `wordstat/run.py`, `report.py`, `payment_check.py`, `benchmark.py`, `probe_dynamics.py` | Yandex Cloud Search API v2 (`WORDSTAT_API_KEY`) | `reports/seo/wordstat/**` → push `seo-data`; concurrency-группа на квоту |
| `seo-site-check` | dispatch; push main (сам файл); запускается Routine ежедневно | inline-python | curl на прод biz-soft.pro | `intelligence/tags-check.json`, `site-check-<дата>.json` → push `seo-data`; **exit 1 при чужом/отсутствующем счётчике** |
| `seo-report-email` | **push в `seo-data`** (файлы письма); dispatch | inline-python (SMTP) | SMTP reg.ru 465/SSL (fallback 587/STARTTLS), `SMTP_PASS`; получатель avbelyaev@biz-soft.pro | письмо + маркер `intelligence/last-mailed.txt` обратно в `seo-data` (одно письмо на дату) |
| `seo-publish-web` | **push в `seo-data`** (`reports/seo/public/**`); dispatch | rsync | SSH на прод (`SSH_KEY/HOST/USER`) | `/opt/bizsoft/seo-reports/` (nginx, непубличный путь); `--delete` — зеркало без архива |
| `seo-analytics-check` | cron 04:05 UTC (07:05 МСК) | `goals_health.py` | Метрика API + SMTP | письмо-приёмка целей (только 7 дней после границы измерения из `measurement-limits.json`) |
| `seo-goals-sync` | dispatch (только main, guard) | `goals_sync.py` | Метрика management API, GA4 Admin API | цели в кабинетах; отчёт комментарием в issue #22; ничего не удаляет |
| `seo-ga4-admin` | dispatch; push main (сам файл) | inline-python | GA4 Admin API | key events `form_submit`/`generate_lead` (разовая утилита) |
| `git-sync-branches` | cron ежечасно :15 | `scripts/git/sync_branches.py` | git | main → ветки `claude/*` (односторонне); `seo-data`/`archive/*` не трогает; отчёт в issue #22 |
| `ops-yandex-recrawl` | dispatch | inline | API Вебмастера recrawl/queue (квота 150 URL/сутки) | комментарий в issue #22 |
| `ops-indexnow` | dispatch | ssh inline | IndexNow (Яндекс+Bing), URL из живого sitemap | пинги; лог |
| `ops-me-crawl` | dispatch | `scripts/sources/me-*.mjs` (Playwright) | store.manageengine.com | `data/sources/manageengine/<дата>/` → force-push в рабочую ветку (main запрещён) |
| `ops-send-mail` / `ops-mail` | dispatch | ssh inline | SMTP прод-сервера | письма; журнал в issue #22 |
| `ops-export-products` | dispatch | ssh inline | прод-Directus | выгрузка каталога комментарием в issue #22 |

Смежные по расписанию, но вне маркетингового контура: `ops-currency-refresh`
(04:10 UTC), `ops-zoho-audit` (04:40 UTC), `deploy` (push main),
`ci` (push/PR; блокирующий job `verify`, в т.ч. 233 unit-теста конвейера).

## 4. Суточный цикл (время МСК = UTC+3)

```
04:20  seo-wordstat, режим full        план → вызовы API (сколько нужно;
       │                              с 23.08 фактически 0 — всё из кэша)
       └─ report.py → push seo-data   (аналитика спроса пересобрана)

04:25 / 10:25 / 16:25 / 22:25         seo-wordstat, режим daily (добор ≤70)

05:40  seo-data-collect               GSC + Вебмастер + Метрика + GA4
       └─ collect.py → push seo-data  (4 файла <источник>-<дата>.json)

07:05  seo-analytics-check            goals_health.py: цели пошли? письмо
                                      (только первую неделю после границы)

09:00  Routine «BIZSoft Growth Intelligence» (сессия Claude):
       0. git pull, data_sync pull; запуск seo-data-collect и seo-site-check
          через API GitHub, ожидание, повторный pull
       1. snapshot.py → quality.py → report_v4.py → webreport.py →
          emailcheck.mjs → uxlint_v4.py → contentcheck.py → previews_v4.py →
          unittest (все гейты обязаны быть зелёными)
       2. актуализация intelligence/actions.json (вручную агентом)
       5. data_sync push «Отчёт за <дата>»  ──────────────┐
                                                          ▼
       (push в seo-data автоматически запускает)   seo-report-email
                                                   → письмо руководителю
                                                   seo-publish-web
                                                   → rsync веб-отчёта на прод
       6. превью письма руководителю через SendUserFile
       7. при полном замере спроса — PR с правками карточек (мерж — только
          руководитель; полномочие самостоятельного мержа отозвано)

каждый час :15  git-sync-branches     main → claude/* (защита от расхождения)

Понедельник — недельный отчёт (weekly/), 1-е число — месячный (monthly/).
30.08 10:00 UTC — одноразовый Routine: контроль недели после переезда данных
в seo-data и подготовка чистки копий из main.
```

**FACT (проверено по фактическим запускам 25.08.2026):** вся цепочка
наблюдаема в GitHub Actions: schedule-прогоны seo-wordstat (07:13 UTC),
seo-analytics-check (04:42 UTC), dispatch-прогоны seo-data-collect и
seo-site-check в 06:25 UTC (инициированы Routine), push в `seo-data` в
06:29 UTC → seo-publish-web. Письмо 25.08 задержано гейтом uxlint —
см. §6.

## 5. Цепочка данных (полный конвейер)

```
ИСТОЧНИКИ              СБОР (Actions)         КАНОНИЗАЦИЯ (Routine)      ОТЧЁТ (Routine)         ДОСТАВКА (Actions)
─────────              ──────────────         ─────────────────────      ───────────────         ──────────────────
GSC ───────────┐
Яндекс.Вебмастер├─ collect.py ─→ data/*.json ─→ snapshot.py ─→ snapshots/<дата>.json
Яндекс.Метрика │                                  │                        │
GA4 ───────────┘                                  ├─ quality.py ─→ data-quality/<дата>.json
                                                  │   (19 проверок, publication_rules)
Wordstat API ── wordstat/run.py ─→ cache/ + ledger/ + semantic-universe.jsonl
                wordstat/report.py ─→ intelligence-state.json ────────────┤
прод-сайт ──── seo-site-check ─→ site-check-<дата>.json ─────────────────┤
actions.json (ведёт агент) ──────────────────────────────────────────────┤
                                                                          ▼
                                                              report_v4.py → письмо V4
                                                              webreport.py → public/daily/<дата>/
                                                                          │
                                                   гейты: emailcheck, uxlint_v4 (25),
                                                   contentcheck (10), previews, unittest
                                                                          │
                                                              data_sync push → seo-data
                                                                          ├─→ seo-report-email → почта
                                                                          └─→ seo-publish-web → nginx
```

## 6. Анализ отказов (фактическое поведение)

| Сбой | Что останавливается | Что продолжает работать | Потеря данных | Что видит руководитель |
|---|---|---|---|---|
| Недоступен один из GSC/Вебмастер/Метрика/GA4 | ничего сразу: `collect.py` пишет `error` в JSON источника, exit 1; push всё равно (`if: always()`) | остальные источники собраны | данных источника за день нет | `quality.py` даёт critical `API_ERROR_AS_ZERO`/`degraded`; но `report_v4.py` при отсутствии `totals` падает с KeyError → **письма нет вовсе**; алерт — только если агент заведёт issue |
| Wordstat недоступен / 429 | текущий прогон добора | кэш обслуживает большинство запросов (hit rate 0,85); следующий cron-прогон продолжит | невыполненные вызовы переносятся (план возобновляемый) | ничего — в письме строка свежести спроса |
| Routine не запустилась / сессия умерла | **весь отчёт дня**: snapshot, письмо, веб-отчёт, actions | сбор данных (Actions) продолжает наполнять seo-data | нет — данные копятся | **ничего: ни письма, ни алерта.** Ни один workflow не упадёт. Единственный след — отсутствие письма |
| Красный гейт (uxlint/contentcheck/тесты) | отправка письма (по регламенту прогона) | данные и веб-отчёт пушатся | нет | письма нет; issue с меткой `alert` (реальный случай 25.08: ложное срабатывание `google_claim_has_page_evidence`, issue #148, исправлено PR #149) |
| SMTP не отвечает | письмо | fallback 465→587; маркер last-mailed не пишется → при следующем push письмо уйдёт повторно-корректно | нет | письма нет/придёт позже |
| Гонка двух прогонов, пишущих в seo-data | нет | `rebase -X theirs`, 3 попытки | **возможна тихая потеря результата проигравшего прогона** (осознанный компромисс, задокументирован в data_sync.sh) | ничего |
| Сломан счётчик на проде | seo-site-check красный (exit 1) | сбор из API источников | накопление визитов | красный workflow; до 21.08 поломка была видна только по исчезновению трафика через дни |
| Просроченный токен (Метрика/Вебмастер) | сбор этого источника | остальное | данные источника | как в первой строке |

## 7. Наблюдаемость

Руководитель без GitHub видит: письмо (строка свежести данных в нём),
веб-отчёт (журнал, качество данных, методика), превью от агента.
Требуют GitHub: статус конкретных workflow, журнал issue #22, alert-issues.
**Слепая зона: остановка самой Routine не детектируется ничем** (нет
«письма о том, что письма не будет»).
