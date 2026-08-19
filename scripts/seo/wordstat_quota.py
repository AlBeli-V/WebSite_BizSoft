#!/usr/bin/env python3
"""Диагностика квоты Вордстата: один запрос, полный ответ сервиса.

Печатает статус, заголовки лимитов и текст ошибки — по нему видно,
какая квота исчерпана (в секунду, в сутки) и когда она восстановится.
Ключ не печатается.

Запуск: python3 scripts/seo/wordstat_quota.py
"""

from __future__ import annotations

import os
import sys

import requests

BASE = "https://searchapi.api.cloud.yandex.net/v2/wordstat"


def main() -> int:
    token = os.environ.get("WORDSTAT_API_KEY", "").strip()
    if not token:
        print("WORDSTAT_API_KEY не задан", file=sys.stderr)
        return 1
    r = requests.post(f"{BASE}/topRequests",
                      json={"phrase": "canva", "numPhrases": 1, "regions": ["225"]},
                      headers={"Authorization": f"Api-Key {token}",
                               "Content-Type": "application/json"},
                      timeout=40)
    print(f"HTTP {r.status_code}")
    for k, v in r.headers.items():
        if any(t in k.lower() for t in ("limit", "quota", "retry", "reset", "remaining")):
            print(f"  заголовок {k}: {v}")
    print("тело:", r.text[:800] or "(пусто)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
