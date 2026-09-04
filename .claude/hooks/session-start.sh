#!/bin/bash
# SessionStart-хук: ставит зависимости репозитория в облачной сессии
# Claude Code, чтобы pnpm test / pnpm typecheck и python-скрипты контуров
# (scripts/seo, competitive-intelligence) сразу работали без ручной
# установки. Идемпотентен: при повторном запуске в уже готовом контейнере
# ничего не делает. Без сети — предупреждает и завершается кодом 0, чтобы
# не блокировать старт сессии.

set -uo pipefail

# Хук нужен только облачным сессиям — локально зависимости ставит сам
# разработчик.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# --- JS-зависимости (pnpm) ------------------------------------------------

if [ -f node_modules/.modules.yaml ] && [ node_modules/.modules.yaml -nt pnpm-lock.yaml ]; then
  echo "JS-зависимости уже установлены (node_modules актуален) — пропускаю pnpm install"
else
  PNPM_BIN="$(command -v pnpm || true)"

  if [ -z "$PNPM_BIN" ]; then
    # pnpm не найден — пробуем включить через corepack (версия берётся
    # из packageManager в package.json), иначе ставим глобально через npm.
    if command -v corepack >/dev/null 2>&1; then
      corepack enable >/dev/null 2>&1
      corepack prepare pnpm@9.15.9 --activate >/dev/null 2>&1
    fi
    PNPM_BIN="$(command -v pnpm || true)"
    if [ -z "$PNPM_BIN" ] && command -v npm >/dev/null 2>&1; then
      npm install -g pnpm@9.15.9 >/dev/null 2>&1
      PNPM_BIN="$(command -v pnpm || true)"
    fi
  fi

  if [ -z "$PNPM_BIN" ]; then
    echo "Предупреждение: pnpm недоступен и не удалось установить — JS-зависимости пропущены"
  else
    if "$PNPM_BIN" install --frozen-lockfile >/tmp/session-start-pnpm.log 2>&1; then
      echo "JS-зависимости установлены (pnpm install --frozen-lockfile)"
    else
      echo "Предупреждение: pnpm install не завершился успешно (нет сети или другая ошибка), смотри /tmp/session-start-pnpm.log — продолжаю без остановки сессии"
    fi
  fi
fi

# --- Python-зависимости контуров (scripts/seo, competitive-intelligence) --
# Набор пакетов взят из `pip install` в .github/workflows/*.yml:
# requests, pyjwt, cryptography, google-auth. cffi добавлен отдельно —
# в части образов системный пакет cryptography собран без него, из-за
# чего падает `cryptography.hazmat` (ModuleNotFoundError: _cffi_backend).

if python3 -c "import requests, jwt, cryptography, google.auth, cffi" >/dev/null 2>&1; then
  echo "Python-зависимости контуров уже на месте — пропускаю pip install"
else
  if command -v pip3 >/dev/null 2>&1; then
    if pip3 install --quiet requests pyjwt cryptography google-auth cffi >/tmp/session-start-pip.log 2>&1; then
      echo "Python-зависимости контуров установлены (requests, pyjwt, cryptography, google-auth, cffi)"
    else
      echo "Предупреждение: pip install не завершился успешно (нет сети или другая ошибка), смотри /tmp/session-start-pip.log — продолжаю без остановки сессии"
    fi
  else
    echo "Предупреждение: pip3 недоступен — python-зависимости контуров пропущены"
  fi
fi

exit 0
