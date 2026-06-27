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

echo "→ Статус:"
docker compose ps astro
echo "✓ Готово. Проверьте https://biz-soft.pro"
