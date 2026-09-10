"""Сторож регистраций scripts/ops/registrations_watch.py: разбор реестра.

Проверка живёт здесь, потому что это единственный каталог python-тестов,
который CI обходит целиком. Сеть не используется: ответы площадок
подставляются заглушкой — тест проверяет, как сторож раскладывает площадки
по исходам, а не доступность самих площадок.

Смысл сторожа — не верить полю `status` на слово. Поэтому проверяется
главным образом граница между «находка» (записанный профиль молчит — прогон
краснеет) и «напоминание» (регистрации ещё нет — прогон зелёный, письмо
уходит), а также случаи, где статический запрос ничего не доказывает.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts" / "ops"))
import registrations_watch as rw  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
REAL_REGISTRY = ROOT / "data" / "marketing" / "platform-accounts.json"


def registry(*accounts: dict) -> pathlib.Path:
    tmp = pathlib.Path(tempfile.mkdtemp()) / "accounts.json"
    tmp.write_text(json.dumps({"accounts": list(accounts)}, ensure_ascii=False),
                   encoding="utf-8")
    return tmp


class RegistrationsWatchTest(unittest.TestCase):
    def collect(self, path: pathlib.Path, responses: dict):
        """responses: адрес → (код, тело) либо исключение."""
        def fake_fetch(url: str):
            value = responses[url]
            if isinstance(value, Exception):
                return None, str(value)
            return value

        original, rw.fetch = rw.fetch, fake_fetch
        try:
            return rw.collect(path)
        finally:
            rw.fetch = original

    def test_живой_профиль_с_маркером_считается_проверенным(self):
        path = registry({"id": "a", "platform": "A", "status": "registered",
                         "url": "https://a.example", "check_marker": "БИЗСОФТ"})
        res = self.collect(path, {"https://a.example": (200, "<h1>БИЗСОФТ</h1>")})
        self.assertEqual([a["platform"] for a in res["checked"]], ["A"])
        self.assertEqual(res["failed"], [])

    def test_доказательство_можно_взять_не_со_страницы_профиля(self):
        """check_url важнее url: у Яндекс Бизнеса связку доказывает фид."""
        path = registry({"id": "yb", "platform": "Яндекс.Бизнес", "status": "registered",
                         "url": "", "check_url": "https://biz-soft.pro/feed.xml",
                         "check_marker": "offer"})
        res = self.collect(path, {"https://biz-soft.pro/feed.xml": (200, "<offer id=1/>")})
        self.assertEqual(len(res["checked"]), 1)
        self.assertEqual(res["no_address"], [])

    def test_молчащий_профиль_это_находка(self):
        path = registry({"id": "a", "platform": "A", "status": "registered",
                         "url": "https://a.example"})
        res = self.collect(path, {"https://a.example": (404, "")})
        self.assertEqual(len(res["failed"]), 1)
        self.assertIn("404", res["failed"][0]["detail"])

    def test_сетевая_ошибка_это_находка_а_не_тишина(self):
        path = registry({"id": "a", "platform": "A", "status": "registered",
                         "url": "https://a.example"})
        res = self.collect(path, {"https://a.example": OSError("таймаут")})
        self.assertEqual(len(res["failed"]), 1)

    def test_страница_без_ожидаемого_маркера_это_находка(self):
        """Код 200 сам по себе ничего не значит: заглушка тоже отдаёт 200."""
        path = registry({"id": "a", "platform": "A", "status": "registered",
                         "url": "https://a.example", "check_marker": "БИЗСОФТ"})
        res = self.collect(path, {"https://a.example": (200, "страница не найдена")})
        self.assertEqual(len(res["failed"]), 1)

    def test_отказ_роботу_не_выдаётся_за_пропажу_профиля(self):
        path = registry({"id": "a", "platform": "A", "status": "registered",
                         "url": "https://a.example"})
        res = self.collect(path, {"https://a.example": (403, "")})
        self.assertEqual(res["failed"], [])
        self.assertEqual(len(res["manual"]), 1)

    def test_площадка_на_javascript_не_дёргается(self):
        path = registry({"id": "dzen", "platform": "Дзен", "status": "registered",
                         "url": "https://dzen.ru/x", "check": "manual"})
        res = self.collect(path, {})  # сеть не должна понадобиться вовсе
        self.assertEqual(len(res["manual"]), 1)

    def test_зарегистрированы_но_без_адреса_отдельным_списком(self):
        path = registry({"id": "a", "platform": "A", "status": "registered", "url": ""})
        res = self.collect(path, {})
        self.assertEqual(len(res["no_address"]), 1)
        self.assertEqual(res["failed"], [])

    def test_отсутствие_регистрации_не_делает_прогон_красным(self):
        path = registry({"id": "a", "platform": "A", "status": "not_registered",
                         "url": "", "wave": 1, "signup_url": "https://a.example"})
        res = self.collect(path, {})
        self.assertEqual(len(res["pending"]), 1)
        self.assertEqual(res["failed"], [])

    def test_отложенные_и_отклонённые_не_напоминаются(self):
        path = registry({"id": "h", "platform": "Habr", "status": "deferred", "url": ""},
                        {"id": "p", "platform": "Пикабу", "status": "rejected", "url": ""})
        res = self.collect(path, {})
        self.assertEqual(len(res["quiet"]), 2)
        self.assertEqual(res["pending"], [])

    def test_отчёт_несёт_ссылку_куда_идти_регистрироваться(self):
        path = registry({"id": "a", "platform": "A", "status": "not_registered",
                         "url": "", "wave": 1, "signup_url": "https://a.example",
                         "purpose": "зачем-то"})
        text = rw.render(self.collect(path, {}))
        self.assertIn("https://a.example", text)
        self.assertIn("зачем-то", text)

    def test_боевой_реестр_разбирается_и_несёт_адреса_регистрации(self):
        """Реестр правится руками — проверяем, что он остаётся читаемым."""
        data = json.loads(REAL_REGISTRY.read_text(encoding="utf-8"))
        accounts = data["accounts"]
        self.assertTrue(accounts)
        for acc in accounts:
            self.assertIn("status", acc, acc.get("id"))
            if acc["status"] == "not_registered":
                self.assertTrue(acc.get("signup_url"),
                                f"у {acc['id']} нет адреса регистрации — "
                                "напоминание уйдёт без ссылки")


if __name__ == "__main__":
    unittest.main()
