#!/usr/bin/env python3
"""Общие моки для тестов сборщиков: HTTP-ответы и фальшивые google-модули.

Не является тест-файлом (нет префикса test_), unittest discover его не
собирает — модуль импортируется тестами напрямую.
"""

import importlib.util
import json
import pathlib
import types

ROOT = pathlib.Path(__file__).resolve().parents[3]


def load(name):
    """Импорт модуля из scripts/seo под собственным именем (как в тестах)."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / "seo" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeResponse:
    def __init__(self, status=200, payload=None, text=None):
        self.status_code = status
        self._payload = payload
        self.text = text if text is not None else json.dumps(payload or {}, ensure_ascii=False)

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        if self._payload is None:
            raise ValueError("not a json")
        return self._payload


class FakeRequests:
    """Маршрутизация по подстроке URL; первый совпавший ключ выигрывает.

    Значение маршрута: FakeResponse, исключение (сеть/таймаут) или список —
    очередь ответов для повторных запросов на один URL (пагинация, несколько
    срезов одного эндпоинта).
    """

    class RequestException(Exception):
        pass

    class Timeout(RequestException):
        pass

    def __init__(self, routes: dict):
        self.routes = routes

    def _resolve(self, url):
        for key, resp in self.routes.items():
            if key in url:
                if isinstance(resp, list):
                    resp = resp.pop(0)
                if isinstance(resp, Exception):
                    raise resp
                return resp
        raise AssertionError(f"нет маршрута для {url}")

    def get(self, url, **kw):
        return self._resolve(url)

    def post(self, url, **kw):
        return self._resolve(url)


def fake_google_modules() -> dict:
    """sys.modules-заглушки для google-auth: сборщики GSC/GA4 тестируются без
    установленной библиотеки и без сети. Использовать через
    mock.patch.dict(sys.modules, fake_google_modules())."""
    creds = types.SimpleNamespace(token="test-token", refresh=lambda request: None)

    transport_requests = types.ModuleType("google.auth.transport.requests")
    transport_requests.Request = lambda: None

    service_account = types.ModuleType("google.oauth2.service_account")
    service_account.Credentials = types.SimpleNamespace(
        from_service_account_info=lambda info, scopes=None: creds)

    oauth2 = types.ModuleType("google.oauth2")
    oauth2.service_account = service_account

    google = types.ModuleType("google")
    auth = types.ModuleType("google.auth")
    transport = types.ModuleType("google.auth.transport")

    return {
        "google": google,
        "google.auth": auth,
        "google.auth.transport": transport,
        "google.auth.transport.requests": transport_requests,
        "google.oauth2": oauth2,
        "google.oauth2.service_account": service_account,
    }
