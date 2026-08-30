#!/usr/bin/env bash
# Обмен данными конвейера Growth Intelligence с веткой-хранилищем seo-data.
#
# Код живёт в main, машинные данные — в orphan-ветке seo-data (у неё нет
# общего предка с main, случайное слияние невозможно). Скрипты конвейера
# при этом читают и пишут привычные пути reports/seo/* — этот помощник
# накатывает данные в рабочую копию и отправляет результаты обратно.
#
#   data_sync.sh pull            — данные из origin/seo-data в рабочую копию
#   data_sync.sh push "<сообщение>" — результаты из рабочей копии в seo-data
#
# push устойчив к гонке с параллельными прогонами (Wordstat пишет в ту же
# ветку): rebase -X theirs и три попытки, как в прежней схеме. Машинные
# файлы конфликтуют закономерно, и свежий результат прогона всегда полнее.
set -euo pipefail

BRANCH=seo-data
DIRS=(reports/seo/data reports/seo/wordstat reports/seo/intelligence
      reports/seo/public reports/seo/ppc)

cmd=${1:?использование: data_sync.sh pull | push \"сообщение\"}

git fetch origin "$BRANCH" --quiet

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
    tmp=$(mktemp -d)
    trap 'git worktree remove --force "$tmp" 2>/dev/null || true' EXIT
    git worktree add --quiet --detach "$tmp" "origin/$BRANCH"

    for d in "${DIRS[@]}"; do
      [ -d "$d" ] || continue
      # Полная замена каталога, а не наложение: удалённый прогоном файл
      # (например, истёкший кэш) должен исчезнуть и из хранилища, иначе оно
      # только растёт. rsync не используется — его нет в контейнере сессии.
      rm -rf "${tmp:?}/$d"
      mkdir -p "$(dirname "$tmp/$d")"
      cp -a "$d" "$tmp/$d"
    done

    # Копии workflow в seo-data (push-триггер исполняет файл из пушенной
    # ветки). Обновлять их может только сессия: GITHUB_TOKEN воркфлоу не
    # имеет права писать workflow-файлы, поэтому под Actions шаг пропускается
    # (иначе устаревшая копия валила бы весь пуш данных), а отставание там
    # ловит шаг-детектор в seo-data-collect.
    if [ "${GITHUB_ACTIONS:-}" != "true" ]; then
      for f in seo-report-email.yml seo-publish-web.yml; do
        src=".github/workflows/$f"
        [ -f "$src" ] || continue
        mkdir -p "$tmp/.github/workflows"
        {
          printf '%s\n' \
            '# КОПИЯ ИЗ MAIN. Push-триггер срабатывает только если файл workflow есть' \
            '# в самой пушенной ветке, поэтому в ветке-хранилище seo-data лежит копия.' \
            '# Синхронизируется сессией при data_sync push (GITHUB_TOKEN воркфлоу не' \
            '# имеет права писать workflow-файлы — шаг в Actions только сверяет).'
          cat "$src"
        } > "$tmp/.github/workflows/$f"
      done
    fi

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
