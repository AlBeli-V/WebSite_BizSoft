#!/usr/bin/env python3
"""Клиент Yandex Direct API v5 — строго только чтение (этап 1).

У OAuth-токенов Яндекса нет области действия «только чтение» для Директа,
поэтому режим READ ONLY обеспечивается кодом: клиент пропускает единственный
метод `get`; любой другой (add/update/delete/suspend/resume/archive/…)
блокируется исключением WriteAttemptBlocked ещё до обращения к сети.
Кода, способного изменить рекламный кабинет, в репозитории нет.

Токен читается только из окружения: YANDEX_DIRECT_TOKEN (основное имя,
в стиле YANDEX_METRIKA_TOKEN) либо DIRECT_OAUTH_TOKEN (имя из SEM-001).
В вывод, отчёты и сохраняемые данные токен не попадает никогда.
"""

from __future__ import annotations

import os

import requests

PROD_BASE = "https://api.direct.yandex.com/json/v5/"
SANDBOX_BASE = "https://api-sandbox.direct.yandex.com/json/v5/"

TOKEN_ENV_NAMES = ("YANDEX_DIRECT_TOKEN", "DIRECT_OAUTH_TOKEN")
CLIENT_LOGIN_ENV = "YANDEX_DIRECT_CLIENT_LOGIN"

# Единственный разрешённый метод API. Расширять список на этапе 1 нельзя.
READ_ONLY_METHODS = {"get"}


class WriteAttemptBlocked(RuntimeError):
    """Попытка вызвать метод, способный изменить рекламный кабинет."""


def token_source() -> tuple[str, str]:
    """(значение токена, имя переменной окружения) либо ("", "")."""
    for name in TOKEN_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value, name
    return "", ""


class DirectClient:
    """Единственная точка обращения к Direct API.

    call() возвращает {status, data, units, source}; статусы:
    ok · api_error (код и текст ошибки API — без токена) · http_<код> ·
    network_error. Заголовок Units (израсходовано/доступно/суточный лимит
    баллов) сохраняется в last_units для диагностики квоты.
    """

    def __init__(self, sandbox: bool = False, session=None,
                 client_login: str | None = None):
        self.base = SANDBOX_BASE if sandbox else PROD_BASE
        self.sandbox = sandbox
        self.session = session or requests
        self.client_login = (client_login if client_login is not None
                             else os.environ.get(CLIENT_LOGIN_ENV, "").strip())
        self.last_units: str | None = None

    def headers(self) -> dict:
        token, _ = token_source()
        if not token:
            raise SystemExit(
                "токен Direct не задан (YANDEX_DIRECT_TOKEN или DIRECT_OAUTH_TOKEN)")
        h = {"Authorization": f"Bearer {token}",
             "Accept-Language": "ru",
             "Content-Type": "application/json; charset=utf-8"}
        if self.client_login:
            h["Client-Login"] = self.client_login
        return h

    def call(self, service: str, method: str, params: dict) -> dict:
        if method not in READ_ONLY_METHODS:
            raise WriteAttemptBlocked(
                f"метод {service}.{method} заблокирован: этап 1 — только чтение (get)")
        try:
            resp = self.session.post(self.base + service,
                                     json={"method": method, "params": params},
                                     headers=self.headers(), timeout=60)
        except Exception as e:                                  # сеть/таймаут
            return {"status": "network_error", "data": None, "units": None,
                    "source": "error", "error": type(e).__name__}

        units = (getattr(resp, "headers", None) or {}).get("Units")
        if units:
            self.last_units = units

        try:
            body = resp.json()
        except Exception:
            return {"status": f"http_{resp.status_code}", "data": None,
                    "units": units, "source": "error",
                    "error": (getattr(resp, "text", "") or "")[:300]}

        # Ошибки API Директ возвращает телом {"error": …} независимо от HTTP-кода.
        if isinstance(body, dict) and "error" in body:
            err = body.get("error") or {}
            detail = f"{err.get('error_string', '')}: {err.get('error_detail', '')}"
            return {"status": "api_error", "data": None, "units": units,
                    "source": "error", "error_code": err.get("error_code"),
                    "error": detail.strip(": ")}

        if resp.status_code != 200:
            return {"status": f"http_{resp.status_code}", "data": None,
                    "units": units, "source": "error"}

        result = body.get("result") if isinstance(body, dict) else None
        return {"status": "ok", "data": result, "units": units, "source": "api"}

    # ── Обёртки чтения ───────────────────────────────────────────────────
    def account(self) -> dict:
        """Логин и ClientId владельца токена (сервис clients)."""
        return self.call("clients", "get", {"FieldNames": ["ClientId", "Login"]})

    def campaigns(self, limit: int = 100) -> dict:
        return self.call("campaigns", "get", {
            "SelectionCriteria": {},
            "FieldNames": ["Id", "Name", "Type", "State", "Status"],
            "Page": {"Limit": limit},
        })
