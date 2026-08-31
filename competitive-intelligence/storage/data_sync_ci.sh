#!/usr/bin/env bash
# Обмен данными контура конкурентной разведки с веткой-хранилищем competitive-data.
#
# Код живёт в main, машинные данные — в orphan-ветке competitive-data (нет
# общего предка с main, случайное слияние невозможно). Скрипты контура читают
# и пишут привычные пути data/competitive/* и reports/competitive/*, а этот
# помощник накатывает данные в рабочую копию и отправляет результаты обратно.
#
#   data_sync_ci.sh pull                       — данные из origin/competitive-data
#   data_sync_ci.sh push "<сообщение>" [каталоги] — результаты обратно;
#       третий аргумент (список каталогов через пробел) ограничивает push
#       владениями конкретного прогона.
#
# Устройство повторяет проверенный scripts/seo/data_sync.sh с его выученными
# уроками: push — полная замена каталога (удалённый файл должен исчезнуть и в
# хранилище, иначе оно только растёт), ограничение каталогами предотвращает
# затирание чужих свежих файлов параллельным прогоном, rebase -X theirs и три
# попытки переживают гонку.
set -euo pipefail

BRANCH=competitive-data
DIRS=(data/competitive reports/competitive)

cmd=${1:?использование: data_sync_ci.sh pull | push "сообщение"}

git fetch origin "$BRANCH" --quiet 2>/dev/null || {
  echo "ветка $BRANCH ещё не создана — нечего накатывать" >&2
  [ "$cmd" = "pull" ] && exit 0 || true
}

case "$cmd" in
  pull)
    for d in "${DIRS[@]}"; do
      if git cat-file -e "origin/$BRANCH:$d" 2>/dev/null; then
        git restore --source "origin/$BRANCH" --worktree -- "$d"
      fi
    done
    echo "данные накатаны из origin/$BRANCH"
    ;;

  push)
    msg=${2:?push требует сообщение коммита}
    if [ -n "${3:-}" ]; then
      # shellcheck disable=SC2206 — третий аргумент и есть список путей
      scoped=($3)
      for d in "${scoped[@]}"; do
        case " ${DIRS[*]} " in
          *" $d "*) ;;
          *) echo "каталог вне списка хранилища: $d" >&2; exit 2 ;;
        esac
      done
      DIRS=("${scoped[@]}")
    fi
    tmp=$(mktemp -d)
    trap 'git worktree remove --force "$tmp" 2>/dev/null || true' EXIT
    git worktree add --quiet --detach "$tmp" "origin/$BRANCH"

    for d in "${DIRS[@]}"; do
      [ -d "$d" ] || continue
      rm -rf "${tmp:?}/$d"
      mkdir -p "$(dirname "$tmp/$d")"
      cp -a "$d" "$tmp/$d"
    done

    # Маркер отправленного письма пишет только почтовый workflow. Копия в
    # рабочей копии прогона могла устареть за время прогона, и её возврат
    # заставил бы сторож отправить письмо повторно (урок issue #230 базового
    # контура) — маркеры всегда остаются версии хранилища.
    for f in reports/competitive/last-mailed.txt \
             reports/competitive/last-notice.txt; do
      if git cat-file -e "origin/$BRANCH:$f" 2>/dev/null; then
        git -C "$tmp" checkout -- "$f" 2>/dev/null || true
      fi
    done

    cd "$tmp"
    git add -A
    if git diff --cached --quiet; then
      echo "изменений нет — отправлять нечего"
      exit 0
    fi
    git -c user.name="Claude" -c user.email="noreply@anthropic.com" \
      commit -q -m "$msg"
    for attempt in 1 2 3; do
      git fetch origin "$BRANCH" --quiet
      if git -c user.name="Claude" -c user.email="noreply@anthropic.com" \
           rebase -X theirs "origin/$BRANCH" >/dev/null 2>&1; then
        if git push origin "HEAD:refs/heads/$BRANCH" 2>/dev/null; then
          echo "отправлено в $BRANCH с попытки $attempt"
          exit 0
        fi
      else
        git rebase --abort 2>/dev/null || true
      fi
      sleep $((attempt * 5))
    done
    echo "не удалось отправить в $BRANCH за три попытки" >&2
    exit 1
    ;;

  *)
    echo "неизвестная команда: $cmd (ожидается pull или push)" >&2
    exit 2
    ;;
esac
