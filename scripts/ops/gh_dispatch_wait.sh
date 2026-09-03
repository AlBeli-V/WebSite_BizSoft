#!/usr/bin/env bash
# Запуск workflow по имени файла и ожидание его завершения (gh CLI раннера).
#
# Зачем. Push из Actions под GITHUB_TOKEN не порождает событий push для
# других workflow: почтовые и публикационные контуры (seo-report-email,
# seo-publish-web, seo-committee-email, competitive-intelligence-mail,
# ci-publish-report) после пуша данных из прогона Actions сами не стартуют.
# Явный workflow_dispatch через API под тем же токеном срабатывает — это
# документированное исключение GitHub. Отсюда общий помощник: запустить,
# найти прогон, дождаться, вернуть его код завершения.
#
#   gh_dispatch_wait.sh <файл workflow> [--ref main] [--no-wait]
#                       [--timeout <секунды>] [-f ключ=значение ...]
#
# Нужны: GH_TOKEN (github.token) с правом actions: write, GITHUB_REPOSITORY.
set -euo pipefail

wf=${1:?укажите файл workflow}; shift
ref=main; wait=1; timeout=3600; fields=()
while [ $# -gt 0 ]; do
  case $1 in
    --ref) ref=$2; shift 2 ;;
    --no-wait) wait=0; shift ;;
    --timeout) timeout=$2; shift 2 ;;
    -f) fields+=(-f "$2"); shift 2 ;;
    *) echo "неизвестный аргумент: $1" >&2; exit 2 ;;
  esac
done

since=$(date -u +%Y-%m-%dT%H:%M:%SZ)
gh workflow run "$wf" --ref "$ref" ${fields[@]+"${fields[@]}"}
echo "запущен $wf (ref $ref)"
[ "$wait" = 1 ] || exit 0

# Идентификатор прогона появляется не мгновенно: опрос до двух минут.
run_id=""
for _ in $(seq 1 24); do
  sleep 5
  run_id=$(gh run list --workflow "$wf" --event workflow_dispatch --limit 10 \
      --json databaseId,createdAt \
      --jq "map(select(.createdAt >= \"$since\")) | sort_by(.createdAt) | .[0].databaseId // empty")
  [ -n "$run_id" ] && break
done
if [ -z "$run_id" ]; then
  echo "::error::прогон $wf не появился в списке за две минуты"
  exit 1
fi
url="https://github.com/$GITHUB_REPOSITORY/actions/runs/$run_id"
echo "прогон $wf: $url"

# Ожидание с общим потолком: у gh run watch своего потолка нет.
if ! timeout "$timeout" gh run watch "$run_id" --exit-status --interval 30 >/dev/null; then
  echo "::error::прогон $wf завершился неуспешно или не уложился в $timeout с: $url"
  exit 1
fi
echo "прогон $wf завершён успешно"
