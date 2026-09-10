#!/usr/bin/env bash
# Обмен данными конвейера Growth Intelligence с веткой-хранилищем seo-data.
#
# Код живёт в main, машинные данные — в orphan-ветке seo-data (у неё нет
# общего предка с main, случайное слияние невозможно). Скрипты конвейера
# при этом читают и пишут привычные пути reports/seo/* — этот помощник
# накатывает данные в рабочую копию и отправляет результаты обратно.
#
#   data_sync.sh pull            — данные из origin/seo-data в рабочую копию
#   data_sync.sh push "<сообщение>" [каталоги] — результаты в seo-data;
#       третий аргумент (список каталогов через пробел) ограничивает push
#       каталогами-владениями прогона. Каждый workflow пушит только своё;
#       без третьего аргумента (сессия, Routine) — все каталоги.
#
# Отправляются только файлы, которые прогон действительно изменил
# (решение руководителя 04.09.2026). Прежде push был полной заменой
# каталога: в хранилище уезжала вся рабочая копия, включая файлы, снятые
# pull-ом в начале прогона и с тех пор обновлённые кем-то другим. Так
# терялись чужие правки — 30.08 три одновременных workflow затёрли друг
# другу свежие файлы, 29.08 push откатил почтовый маркер на сутки и
# сторож отправил письмо повторно (issue #230), 31.08 сборщик удалил
# свежий site-check через 26 секунд после записи, 04.09 проверка живых
# страниц затёрла реестр экспериментов через минуту после правки.
# Точечные списки исключений закрывали каждый случай по отдельности —
# теперь механизм общий: pull запоминает снятую версию хранилища
# (метка в .git), push сверяет с ней каждый файл и трогает лишь
# отличающиеся. Файл, удалённый прогоном, удаляется и в хранилище;
# файл, которого прогон не касался, остаётся версии хранилища, какой бы
# свежей она ни была.
#
# push устойчив к гонке с параллельными прогонами (Wordstat пишет в ту же
# ветку): rebase -X theirs и три попытки, как в прежней схеме. Машинные
# файлы конфликтуют закономерно, и свежий результат прогона всегда полнее.
set -euo pipefail

BRANCH=seo-data
DIRS=(reports/seo/data reports/seo/serp reports/seo/wordstat
      reports/seo/intelligence reports/seo/public reports/seo/ppc
      reports/seo/pagespeed)

# Метка версии, снятой последним pull: по ней push отличает «этот файл
# изменил прогон» от «этот файл лежал так с момента pull». Живёт в .git,
# а не в рабочей копии, чтобы не уехать в хранилище вместе с данными.
BASELINE_FILE="$(git rev-parse --git-dir)/seo-data-baseline"

cmd=${1:?использование: data_sync.sh pull | push \"сообщение\"}

git fetch origin "$BRANCH" --quiet

case "$cmd" in
  pull)
    # Учёт пересборов источника (snapshot.data_revisions) читает историю
    # выгрузок по ветке данных. actions/checkout клонирует на глубину 1, и
    # тогда в истории виден только последний коммит: два сбора одного дня
    # выглядят как один. Углубляется только мелкий клон — у полного
    # --shallow-since, наоборот, историю обрезал бы.
    if [ "$(git rev-parse --is-shallow-repository)" = "true" ]; then
      git fetch origin "$BRANCH" --shallow-since="4 days ago" --quiet 2>/dev/null \
        || echo "внимание: углубить историю $BRANCH не удалось, учёт пересборов будет неполным" >&2
    fi
    for d in "${DIRS[@]}"; do
      if git cat-file -e "origin/$BRANCH:$d" 2>/dev/null; then
        git restore --source "origin/$BRANCH" --worktree -- "$d"
      fi
    done
    git rev-parse "origin/$BRANCH" > "$BASELINE_FILE"
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
    if [ -s "$BASELINE_FILE" ] && git cat-file -e "$(cat "$BASELINE_FILE")^{commit}" 2>/dev/null; then
      base=$(cat "$BASELINE_FILE")
    else
      # Метки нет: pull в этом прогоне не делали (или .git не переживил шаг).
      # Сверять не с чем, поэтому за исходное берётся текущее состояние
      # хранилища — отправятся файлы, отличающиеся от него прямо сейчас.
      base=$(git rev-parse "origin/$BRANCH")
      echo "внимание: метки pull нет, изменения считаются от текущего $BRANCH"
    fi

    tmp=$(mktemp -d)
    trap 'git worktree remove --force "$tmp" 2>/dev/null || true' EXIT
    git worktree add --quiet --detach "$tmp" "origin/$BRANCH"

    changed=0 removed=0 kept=0
    for d in "${DIRS[@]}"; do
      # Файлы рабочей копии: отправляются новые и изменённые с момента pull.
      if [ -d "$d" ]; then
        while IFS= read -r f; do
          if git cat-file -e "$base:$f" 2>/dev/null \
             && git show "$base:$f" 2>/dev/null | cmp -s - "$f"; then
            kept=$((kept + 1))          # прогон не трогал — версия хранилища
            continue
          fi
          mkdir -p "$tmp/$(dirname "$f")"
          cp -a "$f" "$tmp/$f"
          changed=$((changed + 1))
        done < <(find "$d" -type f)
      fi
      # Файлы, удалённые прогоном: были в снятой версии, в рабочей копии нет.
      # Истёкший кэш должен исчезнуть и из хранилища, иначе оно только растёт.
      while IFS= read -r f; do
        [ -n "$f" ] || continue
        if [ ! -e "$f" ]; then
          rm -f "$tmp/$f"
          removed=$((removed + 1))
        fi
      done < <(git ls-tree -r --name-only "$base" -- "$d" 2>/dev/null)
    done
    echo "к отправке: изменено $changed, удалено $removed; оставлено версии хранилища: $kept"

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
