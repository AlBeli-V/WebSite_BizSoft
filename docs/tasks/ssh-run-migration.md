# Перевод операционных workflow на обёртку ssh-run

Решение руководителя 14.09.2026 (кнопками): перевод идёт **отдельной задачей
с постановкой**, а не одним механическим PR по 43 файлам. Находка — при
выкате волны 4 контента карточек: шаг записи в прод-Directus
(`ops-apply-content`) ходил по SSH напрямую, мимо обёртки. Он переведён
отдельно; здесь — про остальные.

## Что не так

`appleboy/ssh-action` с `capture_stdout: true` пишет вывод в `GITHUB_OUTPUT`
блоком `stdout<<EOF … EOF`, а его entrypoint работает под `bash -e -o pipefail`:
ненулевой код удалённого скрипта обрывает entrypoint до закрывающей строки,
раннер отбрасывает **весь** блок («Matching delimiter not found 'EOF'»), и
`journal-post` публикует «(нет вывода)».

Вывод теряется ровно в том прогоне, ради которого журнал заведён. Разбор —
issue #542, 13.09.2026: `ops-yandex-recrawl` с HTTP 429 по каждому URL дал в
issue #22 запись ✗ без причины. Правило — `docs/rules/report-integrity.md`.

Обёртка `./.github/actions/ssh-run` выполняет скрипт в подоболочке, печатает
её код маркером `__OPS_RC=<n>` и завершает сеанс SSH нулём — вывод доезжает
целиком и при сбое. Образец обкатан на `ops-backup`, `ops-indexnow`,
`ops-yandex-recrawl` и `ops-apply-content`.

## Объём

Прямой вызов `appleboy/ssh-action` — в 48 файлах; правило нарушают 43 из них:
`capture_stdout: true` плюс запись в журнал.

**Сначала — пять по расписанию** (сбой приходит ночью, читать его будут по
журналу, а не по логу прогона):

`ops-currency-refresh`, `ops-catalog-watch`, `ops-lead-source-mail`,
`ops-content-audit`, `ops-zoho-audit`.

**Затем 38 ручных**, по группам:

| Группа | Файлы |
|---|---|
| Почта и заявки | `ops-send-mail`, `ops-form-test`, `ops-crm-backfill`, `ops-crm-cleanup-test` |
| Каталог и цены | `ops-annual-reprice`, `ops-merge-product`, `ops-rename-product`, `ops-patch-product`, `ops-archive-products`, `ops-recategorize`, `ops-categories`, `ops-set-noindex`, `ops-price-audit`, `ops-import-vendors`, `ops-import-ai-cards`, `ops-sku-migrate`, `ops-apply-descriptions`, `ops-fix-meta`, `ops-export-products`, `ops-export-content`, `ops-export-catalog-map`, `ops-vendors-audit`, `ops-index-drop-audit` |
| Сервер и nginx | `ops-server-config`, `ops-server-stats`, `ops-disk-cleanup`, `ops-fail2ban`, `ops-perf`, `ops-nginx-reports`, `ops-nginx-ci-reports`, `ops-nginx-ratelimit`, `ops-nginx-metrika-cache`, `ops-nginx-canonical-host` |
| Directus и доступы | `ops-directus-schema`, `ops-directus-token-sync`, `ops-admin-token`, `ops-zoho-rollback`, `ops-yandex-feeds-toggle` |

**Вне объёма, но проверить глазами:** `ops-leads-collect` (`capture_stdout`
есть, журнала нет — либо завести журнал, либо объяснить в шапке, почему его
нет) и четыре файла без `capture_stdout`, где вывод шага в журнал не идёт
вовсе: `deploy`, `ai-catalog-migrate`, `ops-dadata-setup`, `ops-mail`.

## Форма правки

Одинаковая для всех, образец — `ops-apply-content` (PR #556):

1. `uses: appleboy/ssh-action@v1` → `uses: ./.github/actions/ssh-run`;
   строка `capture_stdout: true` снимается, `host`/`username`/`key`/`envs`/
   `script` остаются как есть.
2. `journal-post`: `outcome: ${{ steps.<id>.outputs.outcome }}` и
   `body-file: ${{ steps.<id>.outputs.body-file }}` вместо
   `outcome: ${{ steps.<id>.outcome }}` и `body: ${{ steps.<id>.outputs.stdout }}`.
3. В шапку — строка о причине со ссылкой на issue #542.

Две ловушки, которые видны только при чтении файла:

- **Шаг перестаёт падать сам.** Обёртка завершает шаг нулём, красный статус
  прогона ставит `journal-post` по `outcome` с `fail-on-error`. Поэтому любое
  условие вида `steps.<id>.outcome` после шага по SSH надо переписать на
  `steps.<id>.outputs.outcome` — иначе после сбоя оно прочтётся как успех.
  Живой пример: в `ops-catalog-watch` от `steps.check.outcome` зависят и
  разбор находок, и решение слать ли письмо; механическая замена только
  строки `uses:` сделает так, что при упавшем осмотре сторож промолчит.
- **`checkout` обязан стоять выше** шага `ssh-run` (локальный action — файлы
  репозитория), а перед `journal-post` с `if: always()` — checkout тоже с
  `if: always()`, если он не первый шаг job. Сторож —
  `scripts/ci/check-workflow-journal.py`.

## Приёмка

- `python3 scripts/ci/check-workflow-journal.py` — 0 замечаний.
- Разбор YAML всех изменённых файлов.
- Поиск по изменённым файлам: не осталось `steps.<id>.outcome` в условиях и
  в `journal-post`.
- Холостой прогон каждого переведённого workflow в безопасном режиме, где он
  есть (`apply=false`, `mode=check`, `dry-run`); где холостого режима нет —
  прогон на следующем штатном вызове с чтением записи в issue #22.

Прогон вслепую по всем 43 файлам разом в приёмку не годится: среди них почта,
ежедневная переоценка и сторож каталога, а сетевого доступа к проду из сессии
нет — ошибка в одном выяснится на боевом прогоне.
