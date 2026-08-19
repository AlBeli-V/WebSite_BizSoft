#!/usr/bin/env bash
# Пересборка и перезапуск SSR-сервиса Astro на сервере.
# Запуск: bash /opt/bizsoft/deploy.sh
set -euo pipefail
cd /opt/bizsoft

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
