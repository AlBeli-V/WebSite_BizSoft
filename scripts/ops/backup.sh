#!/usr/bin/env bash
# Резервная копия biz-soft.pro. Живёт на прод-сервере как /opt/bizsoft/backup.sh
# и запускается двумя способами:
#   * ночным cron сервера — основной путь, не зависит от GitHub;
#   * workflow ops-backup (режимы check/backup) — тот же файл заливается перед
#     запуском, поэтому ручной прогон и ночной исполняют один и тот же код.
#
# Почему копию снимает сервер, а не GitHub Actions. 27.08.2026 планировщик
# GitHub не выдал ни одного запуска по расписанию в течение шести часов —
# ежечасный workflow репозитория пропустил пять слотов подряд, ночная копия
# не снялась, RPO в 24 часа оказался нарушен. События schedule в Actions не
# гарантированы: при нагрузке их откладывают, а слоты вида «ровно 00 или 30
# минут» выбрасывают первыми. Резервное копирование не может зависеть от
# очереди, у которой нет обязательств.
#
# Настройки берутся из /opt/bizsoft/backup.env (см. ops-backup install),
# реквизиты SMTP для отчёта — из /opt/bizsoft/astro.env. Ни один секрет в
# лог не печатается.
#
# Использование: backup.sh [check|backup]
#   check  — только осмотр, ничего не записывает;
#   backup — снять копию, проверить восстановлением, выгрузить, ротировать.
set -uo pipefail

BASE=${BIZSOFT_BASE:-/opt/bizsoft}
DEST="$BASE/backups"
LOGDIR="$DEST/logs"
GDIR=${GDRIVE_DIR:-BizSoft-Backups}
ENVFILE="$BASE/backup.env"

# Файл настроек читается первым, но не затирает то, что пришло из окружения:
# при запуске из workflow значения задаёт GitHub, и они должны побеждать.
# Поэтому запоминаем окружение до чтения файла и возвращаем его после.
FROM_ENV=$(export -p | grep -E ' (MODE|VERIFY|OFFSITE|KEEP_[DWM]|MAIL_ON|MAIL_TO|BACKUP_PASSPHRASE|RCLONE_CONF|RCLONE_CONF_B64)=' || true)
if [ -f "$ENVFILE" ]; then
  # shellcheck disable=SC1090
  . "$ENVFILE"
fi
eval "$FROM_ENV"

MODE=${1:-${MODE:-check}}
VERIFY=${VERIFY:-true}
OFFSITE=${OFFSITE:-true}
KEEP_D=${KEEP_D:-7}
KEEP_W=${KEEP_W:-4}
KEEP_M=${KEEP_M:-6}
BACKUP_PASSPHRASE=${BACKUP_PASSPHRASE:-}
RCLONE_CONF=${RCLONE_CONF:-$BASE/rclone.conf}
RCLONE_CONF_B64=${RCLONE_CONF_B64:-}
RUNBOOK_SRC=${RUNBOOK_SRC:-$BASE/README-RESTORE.md}
MAIL_TO=${MAIL_TO:-}
# always — письмо после каждого прогона, error — только при ошибке,
# never — не отправлять. Тишина при always означает, что cron умер:
# это отдельный сигнал, ради него режим и выбран по умолчанию.
MAIL_ON=${MAIL_ON:-always}

STAMP=$(date -u +%Y%m%d-%H%M)
FAIL=0
WARN=0
# Каталоги создаются внутри main, а убираются здесь: в них лежат дамп с
# заявками клиентов и конфиг rclone с токеном Google — они не должны
# пережить прогон ни при каком выходе, включая ранний.
WORK=""
RCTMP=""
trap 'rm -rf "$WORK" "$RCTMP" 2>/dev/null' EXIT

# ── маска: любой вывод rclone проходит через неё ──────────────────────
# Даже маловероятная утечка токена в тексте ошибки не должна попасть ни
# в лог, ни в письмо.
mask() { sed -E 's/(ya29\.|1\/\/)[A-Za-z0-9._-]+/***/g; s/("(access|refresh)_token":")[^"]*/\1***/g'; }

main() {
  echo "════ ОКРУЖЕНИЕ ════"
  echo "режим: $MODE"
  echo "пользователь: $(id -un)"
  echo "дата (UTC):    $(date -u +%FT%TZ)"
  echo "дата (сервер): $(date +'%F %T %Z %z')"
  docker info >/dev/null 2>&1 || { echo "✗ docker недоступен — без него копию снять нечем"; return 1; }

  DB_C=$(docker ps --format '{{.Names}}' | grep -Ei 'db|postgres' | head -1)
  DIR_C=$(docker ps --format '{{.Names}}' | grep -Ei 'directus' | head -1)
  echo "контейнер БД:       ${DB_C:-НЕ НАЙДЕН}"
  echo "контейнер Directus: ${DIR_C:-НЕ НАЙДЕН}"
  [ -n "$DB_C" ] || { echo "✗ контейнер PostgreSQL не найден"; return 1; }

  DB_IMAGE=$(docker inspect -f '{{.Config.Image}}' "$DB_C" 2>/dev/null)
  ENVDUMP=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$DB_C" 2>/dev/null)
  DB_USER=$(echo "$ENVDUMP" | sed -n 's/^POSTGRES_USER=//p' | head -1)
  DB_NAME=$(echo "$ENVDUMP" | sed -n 's/^POSTGRES_DB=//p' | head -1)
  DB_USER=${DB_USER:-postgres}
  DB_NAME=${DB_NAME:-$DB_USER}
  echo "образ БД: $DB_IMAGE   база: $DB_NAME   роль: $DB_USER"

  FREE_MB=$(df -Pm "$BASE" | awk 'NR==2{print $4}')
  echo "свободно на диске: ${FREE_MB} МБ"
  DB_SIZE=$(docker exec "$DB_C" psql -U "$DB_USER" -d "$DB_NAME" -tAc \
    "select pg_size_pretty(pg_database_size('$DB_NAME'))" 2>/dev/null | tr -d ' ')
  echo "размер базы: ${DB_SIZE:-неизвестен}"
  if [ -n "$DIR_C" ]; then
    UP_SIZE=$(docker exec "$DIR_C" sh -c 'du -sh /directus/uploads 2>/dev/null | cut -f1' 2>/dev/null)
    echo "медиатека Directus: ${UP_SIZE:-размер не определён}"
  fi
  echo "пароль шифрования: $([ -n "$BACKUP_PASSPHRASE" ] && echo задан || echo НЕ ЗАДАН)"
  if [ "$OFFSITE" = "true" ] && [ -z "$BACKUP_PASSPHRASE" ]; then WARN=1; fi
  echo "openssl: $(command -v openssl >/dev/null 2>&1 && openssl version || echo НЕТ)"

  # rclone ищем не только в PATH: у cron и у неинтерактивного SSH ~/.bashrc
  # и ~/.profile не читаются, поэтому ~/bin из PATH выпадает, и бинарник,
  # установленный без прав root, «пропадает».
  RCLONE_BIN=$(command -v rclone 2>/dev/null)
  if [ -z "$RCLONE_BIN" ]; then
    for c in "$HOME/bin/rclone" /home/deploy/bin/rclone "$HOME/rclone/rclone" \
             /usr/local/bin/rclone /usr/bin/rclone /opt/rclone/rclone; do
      if [ -x "$c" ]; then RCLONE_BIN="$c"; break; fi
    done
  fi
  if [ -n "$RCLONE_BIN" ]; then
    echo "rclone: $RCLONE_BIN ($("$RCLONE_BIN" version 2>/dev/null | head -1))"
  else
    echo "rclone: НЕ НАЙДЕН (искали в PATH, ~/bin, /home/deploy/bin, /usr/local/bin, /usr/bin, /opt/rclone)"
    if [ "$OFFSITE" = "true" ]; then WARN=1; fi
  fi

  echo
  echo "════ ПРАВА ПОЛЬЗОВАТЕЛЯ ════"
  echo "группы: $(id -nG)"
  if docker ps >/dev/null 2>&1; then
    echo "docker ps без sudo: ✓"
  else
    echo "docker ps без sudo: ✗ — пользователь не в группе docker"; WARN=1
  fi
  if docker exec "$DB_C" true >/dev/null 2>&1; then
    echo "docker exec в $DB_C: ✓"
  else
    echo "docker exec в $DB_C: ✗ — дамп снять не получится"; WARN=1
  fi
  CPPROBE=$(mktemp)
  if docker cp "$DB_C:/etc/hostname" "$CPPROBE" >/dev/null 2>&1 && [ -s "$CPPROBE" ]; then
    echo "docker cp из контейнера: ✓"
  else
    echo "docker cp из контейнера: ✗ — медиатеку Directus не забрать"; WARN=1
  fi
  rm -f "$CPPROBE"

  # ── конфиг rclone ───────────────────────────────────────────────────
  # Обычный путь — постоянный файл на сервере. Вариант с base64 остаётся
  # для запуска из workflow, где конфиг приезжает из секрета GitHub.
  RC=""
  RCTMP=""
  if [ -n "$RCLONE_CONF_B64" ] && [ -n "$RCLONE_BIN" ]; then
    RCTMP=$(mktemp -d); chmod 700 "$RCTMP"
    RC="$RCTMP/rclone.conf"
    if ! printf '%s' "$RCLONE_CONF_B64" | base64 -d 2>/dev/null | tr -d '\r' > "$RC" || [ ! -s "$RC" ]; then
      printf '%s' "$RCLONE_CONF_B64" | tr -d '\r' > "$RC"
    fi
    chmod 600 "$RC"
  elif [ -f "$RCLONE_CONF" ] && [ -n "$RCLONE_BIN" ]; then
    RC="$RCLONE_CONF"
  fi
  REMOTE=""
  if [ -n "$RC" ]; then
    REMOTE=$(sed -n 's/^\[\(.*\)\]$/\1/p' "$RC" | head -1)
    if [ -z "$REMOTE" ]; then
      echo "✗ в конфиге rclone нет ни одной секции [имя] — файл битый"
      echo "  ($(wc -l < "$RC") строк, $(wc -c < "$RC") байт; содержимое не печатаем — там токен Google)"
      RC=""; WARN=1
    else
      echo "хранилище rclone: $REMOTE  →  каталог $GDIR"
    fi
  elif [ "$OFFSITE" = "true" ]; then
    echo "конфиг rclone не найден ($RCLONE_CONF) — выгружать некуда"; WARN=1
  fi

  echo
  echo "════ УЖЕ СНЯТЫЕ КОПИИ ════"
  if [ -d "$DEST" ]; then
    ls -lh "$DEST" 2>/dev/null | grep -E 'bizsoft-|README' || echo "  (пусто)"
    echo "  занято копиями: $(du -sh "$DEST" 2>/dev/null | cut -f1)"
  else
    echo "  каталога $DEST ещё нет — копий не было ни разу"
  fi
  echo "── копии в Google Drive ($GDIR) ──"
  if [ -n "$RC" ]; then
    # Вывод забираем в переменную: в конвейере с head код возврата rclone
    # терялся, и недоступный Диск выглядел как пустая папка.
    GD_OUT=$("$RCLONE_BIN" --config "$RC" lsl "$REMOTE:$GDIR" 2>&1); GD_RC=$?
    if [ -n "$GD_OUT" ]; then printf '%s\n' "$GD_OUT" | mask | head -30; fi
    if [ "$GD_RC" -ne 0 ]; then
      case "$GD_OUT" in
        *"directory not found"*|*"not found"*)
          echo "  каталога $GDIR ещё нет — его создаст первая выгрузка" ;;
        *)
          echo "✗ Google Drive не ответил (код $GD_RC) — выгрузка сейчас не сработала бы"; WARN=1 ;;
      esac
    elif [ -z "$GD_OUT" ]; then
      echo "  каталог пуст"
    fi
  else
    echo "  проверить нечем: нет rclone или конфига"
  fi

  echo
  echo "════ РАСПИСАНИЕ НА СЕРВЕРЕ ════"
  # Копию снимает cron сервера, поэтому его наличие — часть осмотра:
  # пропавшая строка crontab выглядит точно так же, как исправная
  # система, ровно до первой аварии.
  CRON_LINE=$(crontab -l 2>/dev/null | grep -F 'backup.sh' | grep -v '^#' | head -1)
  if [ -n "$CRON_LINE" ]; then
    echo "  $CRON_LINE"
  else
    echo "✗ в crontab нет строки с backup.sh — ночная копия не снимается"
    WARN=1
  fi
  if [ -f "$LOGDIR/last.log" ]; then
    echo "  последний прогон: $(date -r "$LOGDIR/last.log" +'%F %T %Z' 2>/dev/null)"
    echo "  итог: $(grep -E '^(✓|✗) ИТОГ' "$LOGDIR/last.log" 2>/dev/null | tail -1)"
  fi

  if [ "$MODE" != "backup" ]; then
    echo
    if [ "$WARN" = "0" ]; then
      echo "mode=check: ничего не записывалось, замечаний нет."
      return 0
    fi
    echo "mode=check: ничего не записывалось; есть замечания — см. ✗ выше."
    return 1
  fi

  # Дамп + медиатека + конфиг занимают примерно столько же, сколько
  # исходники. 2 ГБ — запас, при котором нечем заполнить диск.
  if [ "${FREE_MB:-0}" -lt 2048 ]; then
    echo "✗ на диске меньше 2 ГБ свободного места — копия не снимается"
    return 1
  fi

  echo
  echo "════ СНЯТИЕ КОПИИ $STAMP ════"
  mkdir -p "$DEST" && chmod 700 "$DEST"
  WORK=$(mktemp -d)
  # Дамп и конфиг содержат секреты и персональные данные заявок:
  # каталог не должен быть читаем никем, кроме владельца.
  chmod 700 "$WORK"

  echo "── 1/4 дамп PostgreSQL ──"
  # -Fc: сжатый формат, восстанавливается pg_restore выборочно, по одной
  # таблице; -Z6 — компромисс размера и времени.
  if docker exec "$DB_C" pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc -Z6 > "$WORK/db.dump" 2>"$WORK/db.err"; then
    echo "  ok: $(du -h "$WORK/db.dump" | cut -f1)"
  else
    echo "  ✗ pg_dump упал:"; sed 's/^/    /' "$WORK/db.err"; FAIL=1
  fi
  # Пустой или обрезанный дамп молча складывать нельзя — это худший вид
  # «копии»: файл есть, восстановить нечего.
  if [ ! -s "$WORK/db.dump" ] || [ "$(stat -c%s "$WORK/db.dump")" -lt 10000 ]; then
    echo "  ✗ дамп подозрительно мал — считаем снятие неудачным"; FAIL=1
  fi
  # Дальше идти нельзя: архив без годного дампа занял бы место в ротации
  # и через несколько неудачных ночей вытеснил бы все рабочие копии.
  if [ "$FAIL" != "0" ]; then
    echo "✗ дамп не снят — архив не собирается, ротация не выполняется"
    return 1
  fi

  echo "── 2/4 медиатека Directus ──"
  if [ -n "$DIR_C" ]; then
    # docker cp не требует ни tar, ни du внутри образа — работает с любым
    # Directus, даже distroless.
    if docker cp "$DIR_C:/directus/uploads" "$WORK/uploads" >/dev/null 2>&1; then
      tar czf "$WORK/uploads.tgz" -C "$WORK" uploads 2>/dev/null
      rm -rf "$WORK/uploads"
      echo "  ok: $(du -h "$WORK/uploads.tgz" | cut -f1)"
    else
      echo "  ⚠ каталог /directus/uploads не скопировался (нет файлов или другой путь)"
    fi
  else
    echo "  ⚠ контейнер Directus не найден — медиатека пропущена"
  fi

  echo "── 3/4 конфигурация и секреты ──"
  CFG="$WORK/config"
  mkdir -p "$CFG"
  for f in astro.env docker-compose.yml docker-compose.override.yml deploy.sh; do
    if [ -f "$BASE/$f" ]; then
      cp -a "$BASE/$f" "$CFG/" 2>/dev/null && echo "  + $f"
    else
      echo "  ⚠ $BASE/$f не найден"
    fi
  done
  # Настройки копирования сохраняем, пароль из них вычищаем: он лежит в
  # менеджере паролей руководителя, и класть его внутрь зашифрованного
  # им же архива смысла нет.
  if [ -f "$BASE/backup.env" ]; then
    sed 's/^BACKUP_PASSPHRASE=.*/BACKUP_PASSPHRASE=<взять из менеджера паролей>/' \
      "$BASE/backup.env" > "$CFG/backup.env" && echo "  + backup.env (без пароля)"
  fi
  # docker-compose.yml сервера в репозитории отсутствует. Без него стек не
  # из чего поднимать, поэтому его пропажа — не предупреждение, а ошибка.
  if [ ! -f "$CFG/docker-compose.yml" ]; then
    echo "  ✗ docker-compose.yml сервера не попал в архив — копия неполная"; FAIL=1
  fi
  if [ ! -f "$CFG/astro.env" ]; then
    echo "  ✗ astro.env не попал в архив — копия неполная"; FAIL=1
  fi
  NGINX_CONF=$(grep -rl "server_name biz-soft.pro" /etc/nginx 2>/dev/null | grep -v '\.bak' | head -1)
  [ -n "$NGINX_CONF" ] && cp -a "$NGINX_CONF" "$CFG/nginx-biz-soft.conf" 2>/dev/null
  crontab -l > "$CFG/crontab.txt" 2>/dev/null || true
  docker compose -f "$BASE/docker-compose.yml" images > "$CFG/images.txt" 2>/dev/null || \
    docker ps --format '{{.Names}} {{.Image}}' > "$CFG/images.txt" 2>/dev/null
  tar czf "$WORK/config.tgz" -C "$WORK" config 2>/dev/null
  rm -rf "$CFG"
  echo "  ok: $(du -h "$WORK/config.tgz" | cut -f1) ($(tar tzf "$WORK/config.tgz" | wc -l) файлов)"

  echo "── 4/4 сборка архива ──"
  {
    echo "снято (UTC): $(date -u +%FT%TZ)"
    echo "сервер: $(hostname)"
    echo "образ БД: $DB_IMAGE"
    echo "база: $DB_NAME, роль: $DB_USER"
    echo "версия PostgreSQL: $(docker exec "$DB_C" psql -U "$DB_USER" -d "$DB_NAME" -tAc 'show server_version' 2>/dev/null)"
    echo "размер базы: ${DB_SIZE:-?}"
    echo "содержимое: db.dump (pg_dump -Fc), uploads.tgz (медиатека), config.tgz (конфиг + astro.env)"
    echo "восстановление: README-RESTORE.md рядом с архивом (копия docs/DR-RUNBOOK.md)"
  } > "$WORK/MANIFEST.txt"
  ARCHIVE="$DEST/bizsoft-$STAMP.tar.gz"
  tar czf "$ARCHIVE" -C "$WORK" . 2>/dev/null && chmod 600 "$ARCHIVE"
  if [ ! -s "$ARCHIVE" ]; then
    echo "  ✗ архив не собрался"; FAIL=1
  fi
  sha256sum "$ARCHIVE" | awk '{print $1}' > "$ARCHIVE.sha256"
  echo "  архив: $ARCHIVE ($(du -h "$ARCHIVE" | cut -f1))"
  echo "  sha256: $(cat "$ARCHIVE.sha256")"

  # Открытая инструкция лежит и на сервере, и (ниже) в облаке.
  if [ -f "$RUNBOOK_SRC" ] && [ "$RUNBOOK_SRC" != "$DEST/README-RESTORE.md" ]; then
    cp -a "$RUNBOOK_SRC" "$DEST/README-RESTORE.md" 2>/dev/null \
      && echo "  README-RESTORE.md обновлён ($(wc -c < "$DEST/README-RESTORE.md") байт)"
  fi

  if [ "$VERIFY" = "true" ] && [ -s "$WORK/db.dump" ]; then
    echo
    echo "════ ПРОВЕРКА ВОССТАНОВЛЕНИЯ ════"
    # Разворачиваем дамп в отдельный контейнер той же версии. Прод при
    # этом не трогается вообще: свой том, своя сеть, портов наружу нет.
    T=bizsoft-restore-check
    docker rm -f "$T" >/dev/null 2>&1
    if docker run -d --name "$T" -e POSTGRES_PASSWORD=verify \
         -e POSTGRES_DB=verify "$DB_IMAGE" >/dev/null 2>&1; then
      READY=0
      for _ in $(seq 1 30); do
        docker exec "$T" pg_isready -U postgres -q 2>/dev/null && { READY=1; break; }
        sleep 2
      done
      if [ "$READY" = "1" ]; then
        docker cp "$WORK/db.dump" "$T:/tmp/db.dump" >/dev/null 2>&1
        # --no-owner/--no-privileges: роли прода во временной базе нет,
        # без этих флагов restore ругается на каждый объект.
        docker exec "$T" pg_restore -U postgres -d verify --no-owner --no-privileges \
          /tmp/db.dump > "$WORK/restore.log" 2>&1
        RC_CODE=$?
        docker exec "$T" psql -U postgres -d verify -c 'ANALYZE' >/dev/null 2>&1
        TABLES=$(docker exec "$T" psql -U postgres -d verify -tAc \
          "select count(*) from information_schema.tables where table_schema='public'" 2>/dev/null | tr -d ' ')
        echo "код возврата pg_restore: $RC_CODE (0 — без замечаний)"
        echo "таблиц восстановлено: ${TABLES:-0}"
        echo "── строки в крупнейших таблицах ──"
        docker exec "$T" psql -U postgres -d verify -c \
          "select relname as таблица, n_live_tup as строк from pg_stat_user_tables order by n_live_tup desc limit 12" 2>/dev/null
        if [ "${TABLES:-0}" -lt 5 ]; then
          echo "✗ восстановление дало меньше 5 таблиц — копия негодная"; FAIL=1
        else
          echo "✓ копия восстанавливается"
        fi
        [ "$RC_CODE" -ne 0 ] && { echo "── замечания pg_restore (последние 15) ──"; tail -15 "$WORK/restore.log"; }
      else
        echo "✗ временный Postgres не поднялся за 60 с — проверить копию не удалось"; FAIL=1
      fi
      docker rm -f "$T" >/dev/null 2>&1
    else
      echo "✗ не удалось запустить временный контейнер $DB_IMAGE"; FAIL=1
    fi
  elif [ "$VERIFY" = "true" ]; then
    echo; echo "проверка восстановления пропущена: дампа нет"
  fi

  if [ "$OFFSITE" = "true" ]; then
    echo
    echo "════ ВЫГРУЗКА В GOOGLE DRIVE ════"
    if [ -z "$BACKUP_PASSPHRASE" ]; then
      echo "✗ пароль шифрования не задан — наружу ничего не уходит."
      echo "  Архив содержит astro.env и заявки клиентов; открытым он не выгружается."
      echo "  Копия осталась только на сервере — прогон считается неуспешным."
      FAIL=1
    elif [ -z "$RCLONE_BIN" ]; then
      echo "✗ rclone на сервере не найден — выгружать нечем (см. README-RESTORE.md §3)."
      echo "  Копия осталась только на сервере — прогон считается неуспешным."
      FAIL=1
    elif [ -z "$RC" ]; then
      echo "✗ конфиг rclone не найден или битый — выгружать некуда."
      echo "  Копия осталась только на сервере — прогон считается неуспешным."
      FAIL=1
    else
      ENC="$ARCHIVE.enc"
      # -pbkdf2: без него openssl использует устаревший вывод ключа из
      # пароля; расшифровка — командой из README-RESTORE.md.
      if BP="$BACKUP_PASSPHRASE" openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 \
           -in "$ARCHIVE" -out "$ENC" -pass env:BP 2>/dev/null; then
        echo "зашифровано: $(du -h "$ENC" | cut -f1)"
        LOCAL_SUM=$(sha256sum "$ENC" | awk '{print $1}')
        NAME=$(basename "$ENC")
        "$RCLONE_BIN" --config "$RC" mkdir "$REMOTE:$GDIR" 2>&1 | mask
        if "$RCLONE_BIN" --config "$RC" copyto "$ENC" "$REMOTE:$GDIR/$NAME" \
             --retries 3 --low-level-retries 10 2>&1 | mask; then
          # Сверка обязательна: «залилось без ошибки» и «в облаке лежит
          # тот же файл» — разные утверждения.
          REMOTE_SUM=$("$RCLONE_BIN" --config "$RC" hashsum sha256 "$REMOTE:$GDIR/$NAME" 2>/dev/null | awk '{print $1}' | head -1)
          SRC=api
          if [ "${#REMOTE_SUM}" -ne 64 ]; then
            # Drive не отдал sha256 — считаем сами по скачанному потоку.
            # Медленнее, зато заодно проверяет читаемость.
            REMOTE_SUM=$("$RCLONE_BIN" --config "$RC" cat "$REMOTE:$GDIR/$NAME" 2>/dev/null | sha256sum | awk '{print $1}')
            SRC=поток
          fi
          echo "sha256 локально: $LOCAL_SUM"
          echo "sha256 в облаке: ${REMOTE_SUM:-НЕ ПОЛУЧЕН} (источник: $SRC)"
          if [ -n "$REMOTE_SUM" ] && [ "$REMOTE_SUM" = "$LOCAL_SUM" ]; then
            echo "✓ выгружено и сверено: $GDIR/$NAME"
            if [ -f "$DEST/README-RESTORE.md" ]; then
              "$RCLONE_BIN" --config "$RC" copyto "$DEST/README-RESTORE.md" \
                "$REMOTE:$GDIR/README-RESTORE.md" 2>&1 | mask \
                && echo "✓ README-RESTORE.md выложен рядом с архивами"
            fi
          else
            echo "✗ контрольные суммы не совпали — файл в облаке считаем негодным"; FAIL=1
          fi
        else
          echo "✗ rclone не смог выгрузить архив"; FAIL=1
        fi
        rm -f "$ENC"
      else
        echo "✗ шифрование не удалось — наружу ничего не отправлено"; FAIL=1
      fi
    fi
  fi

  echo
  case "$KEEP_D" in ''|*[!0-9]*|0) echo "keep_daily=$KEEP_D не число — берём 7"; KEEP_D=7;; esac
  case "$KEEP_W" in ''|*[!0-9]*) echo "keep_weekly=$KEEP_W не число — берём 4"; KEEP_W=4;; esac
  case "$KEEP_M" in ''|*[!0-9]*) echo "keep_monthly=$KEEP_M не число — берём 6"; KEEP_M=6;; esac
  echo "════ РОТАЦИЯ НА СЕРВЕРЕ (${KEEP_D} ежедневных + ${KEEP_W} еженедельных + ${KEEP_M} ежемесячных) ════"
  if [ "$FAIL" != "0" ]; then
    echo "  прогон с ошибками — ничего не удаляем, старые копии остаются на месте"
    echo
    echo "✗ ИТОГ: в ходе копирования были ошибки — см. выше"
    return 1
  fi

  LOCAL_ALL=$(ls -1 "$DEST" 2>/dev/null | grep -E '^bizsoft-[0-9]{8}-[0-9]{4}\.tar\.gz$' | sort -r)
  LOCAL_KEEP=$(printf '%s\n' "$LOCAL_ALL" | keepset)
  echo "── на сервере ──"
  printf '%s\n' "$LOCAL_ALL" | while read -r f; do
    [ -n "$f" ] || continue
    if printf '%s\n' "$LOCAL_KEEP" | grep -qx "$f"; then
      echo "  оставляем $f"
    else
      echo "  удаляем   $f"
      rm -f "$DEST/$f" "$DEST/$f.sha256"
    fi
  done
  echo "осталось копий: $(ls -1 "$DEST"/bizsoft-*.tar.gz 2>/dev/null | wc -l), занято: $(du -sh "$DEST" 2>/dev/null | cut -f1)"
  echo "свободно на диске: $(df -Pm "$BASE" | awk 'NR==2{print $4}') МБ"

  # В облаке ничего не удаляется — намеренно. Место на Диске не ограничено,
  # а скрипт, у которого нет ни одной команды удаления в облаке, защищает
  # копии от того, кто получил доступ к серверу: стереть прод и следом все
  # копии одной командой не выйдет. Чистка Диска — ручная, раз в несколько
  # месяцев.
  if [ -n "$RC" ]; then
    echo "── в Google Drive (ротация не применяется, только показ) ──"
    "$RCLONE_BIN" --config "$RC" lsl "$REMOTE:$GDIR" 2>&1 | mask | tail -20
    echo "  архивов в облаке: $("$RCLONE_BIN" --config "$RC" lsf "$REMOTE:$GDIR" 2>/dev/null | grep -c 'tar.gz.enc')"
    echo "  занято в облаке: $("$RCLONE_BIN" --config "$RC" size "$REMOTE:$GDIR" 2>/dev/null | tail -1)"
  fi

  echo
  if [ "$FAIL" = "0" ]; then
    echo "✓ ИТОГ: копия снята, проверена и выгружена"
  else
    echo "✗ ИТОГ: в ходе копирования были ошибки — см. выше"
  fi
  return "$FAIL"
}

# Правило хранения: последние N ежедневных, плюс по одной самой свежей
# копии за каждую из W последних недель и M последних месяцев. Копия
# недельной давности переживает неделю ежедневных, копия трёхмесячной
# давности — переживает всё: порчу данных замечают не в тот же день.
keepset() {
  # stdin: имена файлов (basename), по одному в строке
  # stdout: имена, которые нужно СОХРАНИТЬ
  sort -r | awk -v kd="$KEEP_D" -v kw="$KEEP_W" -v km="$KEEP_M" '
    {
      name = $0
      if (match(name, /[0-9]{8}-[0-9]{4}/) == 0) { print name; next }  # чужое имя не трогаем
      d = substr(name, RSTART, 8)
      mo = substr(d, 1, 6)
      keep = 0
      if (++n <= kd) keep = 1
      # неделя: номер дня от эпохи, делённый нацело на 7, — календарь для
      # этого не нужен, важна только группировка
      y = substr(d,1,4)+0; m = substr(d,5,2)+0; dd = substr(d,7,2)+0
      a = int((14-m)/12); yy = y + 4800 - a; mm = m + 12*a - 3
      jdn = dd + int((153*mm+2)/5) + 365*yy + int(yy/4) - int(yy/100) + int(yy/400) - 32045
      wk = int(jdn/7)
      if (!(wk in seenw) && cw < kw) { seenw[wk]=1; cw++; keep = 1 }
      if (!(mo in seenm) && cm < km) { seenm[mo]=1; cm++; keep = 1 }
      if (keep) print name
    }'
}

# ── отчёт письмом ─────────────────────────────────────────────────────
# Реквизиты SMTP берутся из astro.env — того же файла, которым живёт сайт.
# Отдельных секретов на сервере ради письма не заводится.
send_report() {
  rc=$1; log=$2
  [ "$MAIL_ON" = "never" ] && return 0
  [ -z "$MAIL_TO" ] && return 0
  if [ "$MAIL_ON" = "error" ] && [ "$rc" = "0" ]; then return 0; fi
  [ -f "$BASE/astro.env" ] || { echo "письмо не отправлено: нет $BASE/astro.env"; return 0; }
  for k in SMTP_HOST SMTP_PORT SMTP_SECURE SMTP_USER SMTP_PASS SMTP_FROM; do
    v=$(sed -n "s/^$k=//p" "$BASE/astro.env" | tr -d '"\r')
    export "$k=$v"
  done
  MARK=$([ "$rc" = "0" ] && echo "✓" || echo "✗")
  # Время в теме — московское: по нему руководитель и сверяет, была ли
  # ночная копия (правило проекта — расписания и письма по Москве).
  WHEN=$(TZ=Europe/Moscow date +'%d.%m %H:%M')
  export MAIL_TO MAIL_SUBJECT="[BIZSoft] Резервная копия $MARK $WHEN"
  export MAIL_BODY_FILE="$log" MAIL_RC="$rc"
  python3 - <<'PYEOF' 2>&1 | tail -3
import os, smtplib, ssl
from email.message import EmailMessage

host = os.environ.get('SMTP_HOST', '')
if not host:
    print('SMTP не настроен в astro.env — письмо не отправлено'); raise SystemExit(0)
log = open(os.environ['MAIL_BODY_FILE'], encoding='utf-8', errors='replace').read()
rc = os.environ.get('MAIL_RC', '1')
# В письмо кладём итог и хвост лога: полный лог остаётся на сервере,
# письму хватает того, по чему видно, случилась копия или нет.
head = 'Копия снята, проверена и выгружена.' if rc == '0' else 'ПРОГОН ЗАВЕРШИЛСЯ С ОШИБКОЙ. Разобраться сегодня же: копии, о которой узнают в момент аварии, не существует.'
tail = log if len(log) < 12000 else '…\n' + log[-12000:]
msg = EmailMessage()
msg['Subject'] = os.environ['MAIL_SUBJECT']
msg['From'] = os.environ.get('SMTP_FROM') or 'BIZSoft <hello@biz-soft.pro>'
msg['To'] = os.environ['MAIL_TO']
msg.set_content(head + '\n\nПолный лог: /opt/bizsoft/backups/logs/ на сервере.\n\n' + tail)
port = int(os.environ.get('SMTP_PORT') or 587)
secure = (os.environ.get('SMTP_SECURE') or 'false').lower() == 'true'
user = os.environ.get('SMTP_USER', '')
if secure:
    s = smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30)
else:
    s = smtplib.SMTP(host, port, timeout=30); s.starttls(context=ssl.create_default_context())
if user:
    s.login(user, os.environ.get('SMTP_PASS', ''))
s.send_message(msg); s.quit()
print('отчёт отправлен на', os.environ['MAIL_TO'])
PYEOF
}

mkdir -p "$LOGDIR" && chmod 700 "$LOGDIR" 2>/dev/null
LOG="$LOGDIR/$STAMP-$MODE.log"
main >"$LOG" 2>&1
RC=$?
ln -sf "$LOG" "$LOGDIR/last.log"
# Вывод печатаем и в stdout: при запуске из workflow его забирает GitHub,
# под cron он уходит в /dev/null, а лог остаётся файлом в любом случае.
cat "$LOG"
[ "$MODE" = "backup" ] && send_report "$RC" "$LOG"
# Логи храним 60 последних: они мелкие, но каталог не должен расти вечно.
ls -1t "$LOGDIR"/*.log 2>/dev/null | tail -n +61 | while read -r old; do rm -f "$old"; done
exit "$RC"
