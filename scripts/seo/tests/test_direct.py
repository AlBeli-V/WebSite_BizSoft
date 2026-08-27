#!/usr/bin/env python3
"""Тесты интеграции Yandex Direct (этап 1): режим только чтение и диагностика."""

import importlib.util
import os
import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[3]
DIRECT = ROOT / "scripts" / "seo" / "direct"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import mocks  # noqa: E402

ENV = {"YANDEX_DIRECT_TOKEN": "test-token-XYZ"}
NO_TOKENS = {"YANDEX_DIRECT_TOKEN": "", "DIRECT_OAUTH_TOKEN": ""}


def load(name):
    spec = importlib.util.spec_from_file_location(
        f"seo_direct_{name}_test", DIRECT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestReadOnlyGuard(unittest.TestCase):
    """Любой метод, кроме get, блокируется до обращения к сети."""

    def setUp(self):
        self.c = load("client")

    def test_write_methods_blocked(self):
        # маршрутов нет: дойди клиент до сети — FakeRequests упал бы AssertionError
        cli = self.c.DirectClient(session=mocks.FakeRequests({}), client_login="")
        for method in ("add", "update", "delete", "suspend", "resume",
                       "archive", "unarchive", "moderate", "setBids"):
            with self.assertRaises(self.c.WriteAttemptBlocked):
                cli.call("campaigns", method, {})

    def test_whitelist_is_only_get(self):
        self.assertEqual(self.c.READ_ONLY_METHODS, {"get"})


class TestClient(unittest.TestCase):
    def setUp(self):
        self.c = load("client")

    def test_ok_call_parses_result(self):
        fake = mocks.FakeRequests({"api.direct.yandex.com/json/v5/campaigns":
                                   mocks.FakeResponse(200, {"result": {
                                       "Campaigns": [{"Id": 1, "Name": "Тест"}]}})})
        with mock.patch.dict(os.environ, ENV):
            res = self.c.DirectClient(session=fake, client_login="").campaigns()
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["data"]["Campaigns"][0]["Id"], 1)

    def test_api_error_keeps_code_without_token(self):
        payload = {"error": {"error_code": 53, "error_string": "Authorization error",
                             "error_detail": "Invalid OAuth token"}}
        fake = mocks.FakeRequests({"v5/clients": mocks.FakeResponse(200, payload)})
        with mock.patch.dict(os.environ, ENV):
            res = self.c.DirectClient(session=fake, client_login="").account()
        self.assertEqual(res["status"], "api_error")
        self.assertEqual(res["error_code"], 53)
        self.assertNotIn("test-token-XYZ", str(res))

    def test_network_error(self):
        fake = mocks.FakeRequests({"v5/clients": mocks.FakeRequests.Timeout()})
        with mock.patch.dict(os.environ, ENV):
            res = self.c.DirectClient(session=fake, client_login="").account()
        self.assertEqual(res["status"], "network_error")
        self.assertIsNone(res["data"])

    def test_missing_token_raises(self):
        cli = self.c.DirectClient(session=mocks.FakeRequests({}), client_login="")
        with mock.patch.dict(os.environ, NO_TOKENS):
            with self.assertRaises(SystemExit):
                cli.account()

    def test_sandbox_base(self):
        cli = self.c.DirectClient(sandbox=True, session=mocks.FakeRequests({}),
                                  client_login="")
        self.assertIn("api-sandbox", cli.base)


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.r = load("run")

    @staticmethod
    def routes_ok():
        return mocks.FakeRequests({
            "v5/clients": mocks.FakeResponse(200, {"result": {"Clients": [
                {"Login": "bizsoft-direct", "ClientId": 111}]}}),
            "v5/campaigns": mocks.FakeResponse(200, {"result": {"Campaigns": [
                {"Id": 5, "Name": "Кампания", "Type": "TEXT_CAMPAIGN",
                 "State": "ON", "Status": "ACCEPTED"}]}}),
        })

    def test_check_ok(self):
        with mock.patch.dict(os.environ, ENV):
            text, ok = self.r.check(session=self.routes_ok())
        self.assertTrue(ok)
        self.assertIn("Authentication: OK", text)
        self.assertIn("bizsoft-direct", text)
        self.assertIn("READ ONLY", text)
        self.assertIn("кампаний: 1", text)
        self.assertNotIn("test-token-XYZ", text)   # токен не утекает в отчёт

    def test_check_empty_account_is_ok(self):
        fake = mocks.FakeRequests({
            "v5/clients": mocks.FakeResponse(200, {"result": {"Clients": [
                {"Login": "bizsoft-direct", "ClientId": 111}]}}),
            "v5/campaigns": mocks.FakeResponse(200, {"result": {}}),
        })
        with mock.patch.dict(os.environ, ENV):
            text, ok = self.r.check(session=fake)
        self.assertTrue(ok)                        # пустой кабинет — не ошибка
        self.assertIn("кабинет пуст", text)

    def test_check_auth_error_falls_back_to_sandbox(self):
        err = mocks.FakeResponse(200, {"error": {
            "error_code": 53, "error_string": "Authorization error",
            "error_detail": ""}})
        fake = mocks.FakeRequests({
            "api.direct.yandex.com": err,          # боевой контур не пускает
            "api-sandbox": [
                mocks.FakeResponse(200, {"result": {"Clients": [
                    {"Login": "sandbox-login", "ClientId": 7}]}}),
                mocks.FakeResponse(200, {"result": {"Campaigns": []}}),
            ],
        })
        with mock.patch.dict(os.environ, ENV):
            text, ok = self.r.check(session=fake)
        self.assertTrue(ok)
        self.assertIn("песочница", text)
        self.assertIn("sandbox-login", text)
        self.assertIn("код 53", text)

    def test_check_without_token(self):
        with mock.patch.dict(os.environ, NO_TOKENS):
            text, ok = self.r.check(session=mocks.FakeRequests({}))
        self.assertFalse(ok)
        self.assertIn("токен не задан", text)
        self.assertIn("НЕ подтверждён", text)


if __name__ == "__main__":
    unittest.main()
