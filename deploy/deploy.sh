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
docker image prune -f 2>&1 | tail -1 || true

# Build cache копится с каждой сборки. Прежняя команда без -a удаляла только
# висячие промежуточные записи и не сдерживала рост: 29.08 и 03.09.2026 кэш
# доходил до 68 ГБ (765 записей) на диске 77 ГБ, деплой падал на rsync с
# «no space left on device», Directus не мог писать. С -a удаляется всё сверх
# резерва в 2 ГБ (самое свежее остаётся), вывод не подавляется — сбой чистки
# виден в логе деплоя, а не только по заполненному диску.
echo "→ Очистка build-кэша (оставляем до 2 ГБ)…"
docker builder prune -af --reserved-space=2GB 2>&1 | tail -2 || true

echo "→ Статус:"
docker compose ps astro
echo "→ Диск:"
df -h / | tail -1
echo "✓ Готово. Проверьте https://biz-soft.pro"
