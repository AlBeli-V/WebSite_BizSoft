#!/usr/bin/env bash
# Пересборка и перезапуск SSR-сервиса Astro на сервере.
# Запуск: bash /opt/bizsoft/deploy.sh
set -euo pipefail
cd /opt/bizsoft

# PUBLIC_* нужны на этапе сборки (Astro вшивает их в клиентский бандл), а
# env_file в compose действует только в рантайме. Подставляем их в окружение
# перед сборкой, чтобы build args из docker-compose.override.yml не были пустыми.
if [ -f ./astro.env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./astro.env
  set +a
fi

echo "→ Сборка образа Astro…"
docker compose build astro

echo "→ Перезапуск сервиса…"
docker compose up -d astro

echo "→ Очистка старых образов…"
docker image prune -f >/dev/null 2>&1 || true

# Build cache копится с каждой сборки (наблюдали ~9.6 ГБ / 277 записей).
# Оставляем до 2 ГБ горячего кэша — ускоряет следующую сборку, но не даёт
# кэшу расти бесконтрольно.
echo "→ Очистка build-кэша (оставляем 2 ГБ)…"
docker builder prune -f --keep-storage=2GB >/dev/null 2>&1 || true

echo "→ Статус:"
docker compose ps astro
echo "✓ Готово. Проверьте https://biz-soft.pro"
