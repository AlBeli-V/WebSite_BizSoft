"""Сторож доменов scripts/ops/domain_watch.py: разбор ответа RDAP.

Проверка живёт здесь, потому что это единственный каталог python-тестов,
который CI обходит целиком. Сеть не используется: ответы RDAP подставляются
фикстурами — тест проверяет разбор и пороги, а не доступность реестров.

Смысл сторожа — ловить то, что нельзя увидеть из кабинета, когда доступ к
кабинету потерян: приближающийся срок, статусы освобождения, снятый замок
на трансфер и смену регистратора.
"""
from __future__ import annotations

import datetime as dt
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts" / "ops"))
import domain_watch  # noqa: E402

BOOTSTRAP = {"services": [[["pro", "com"], ["https://rdap.example/"]]]}
TODAY = dt.date(2026, 9, 8)


def record(expires: str, statuses: list[str], registrar: str = "Example Registrar") -> dict:
    return {
        "events": [{"eventAction": "expiration", "eventDate": expires}],
        "status": statuses,
        "entities": [{
            "roles": ["registrar"],
            "vcardArray": ["vcard", [["version", {}, "text", "4.0"],
                                     ["fn", {}, "text", registrar]]],
        }],
    }


class DomainWatchTest(unittest.TestCase):
    def check(self, domain: dict, rec: dict | Exception):
        def fake_fetch(url: str):
            if isinstance(rec, Exception):
                raise rec
            return rec
        original = domain_watch.fetch
        domain_watch.fetch = fake_fetch
        try:
            return domain_watch.check(domain, BOOTSTRAP, TODAY)
        finally:
            domain_watch.fetch = original

    def test_здоровый_домен_находок_не_даёт(self):
        lines, bad = self.check(
            {"name": "biz-soft.pro", "warn_days": 60, "expected_registrar": "Example Registrar"},
            record("2027-06-01T00:00:00Z", ["client transfer prohibited"]))
        self.assertFalse(bad, lines)

    def test_срок_в_пределах_порога_даёт_находку(self):
        lines, bad = self.check(
            {"name": "biz-soft.pro", "warn_days": 60, "expected_registrar": "Example Registrar"},
            record("2026-10-01T00:00:00Z", ["client transfer prohibited"]))
        self.assertTrue(bad)
        self.assertTrue(any("до истечения 23 дн." in ln for ln in lines), lines)

    def test_истёкший_срок_даёт_находку(self):
        lines, bad = self.check(
            {"name": "biz-soft.pro", "warn_days": 60, "expected_registrar": "Example Registrar"},
            record("2026-09-01T00:00:00Z", ["client transfer prohibited"]))
        self.assertTrue(bad)
        self.assertTrue(any("срок истёк" in ln for ln in lines), lines)

    def test_статус_освобождения_даёт_находку(self):
        lines, bad = self.check(
            {"name": "biz-soft.pro", "warn_days": 30, "expected_registrar": "Example Registrar"},
            record("2027-06-01T00:00:00Z", ["client transfer prohibited", "pending delete"]))
        self.assertTrue(bad)
        self.assertTrue(any("статусы реестра" in ln for ln in lines), lines)

    def test_снятый_замок_на_трансфер_даёт_находку(self):
        lines, bad = self.check(
            {"name": "biz-soft.pro", "warn_days": 30, "expected_registrar": "Example Registrar"},
            record("2027-06-01T00:00:00Z", ["active"]))
        self.assertTrue(bad)
        self.assertTrue(any("замок на трансфер снят" in ln for ln in lines), lines)

    def test_смена_регистратора_даёт_находку(self):
        lines, bad = self.check(
            {"name": "biz-soft.pro", "warn_days": 30, "expected_registrar": "Example Registrar"},
            record("2027-06-01T00:00:00Z", ["client transfer prohibited"], registrar="Другой"))
        self.assertTrue(bad)
        self.assertTrue(any("в реестре" in ln for ln in lines), lines)

    def test_незаполненный_регистратор_просит_заполнить(self):
        lines, bad = self.check(
            {"name": "biz-soft.pro", "warn_days": 30, "expected_registrar": None},
            record("2027-06-01T00:00:00Z", ["client transfer prohibited"]))
        self.assertTrue(bad)
        self.assertTrue(any("expected_registrar" in ln for ln in lines), lines)

    def test_зона_без_rdap_не_выдаётся_за_порядок(self):
        lines, bad = self.check(
            {"name": "пример.рф", "warn_days": 30, "expected_registrar": None}, {})
        self.assertTrue(bad)
        self.assertTrue(any("нет RDAP-сервера" in ln for ln in lines), lines)

    def test_молчание_реестра_не_считается_нормой(self):
        lines, bad = self.check(
            {"name": "biz-soft.pro", "warn_days": 30, "expected_registrar": "Example Registrar"},
            TimeoutError("таймаут"))
        self.assertTrue(bad)
        self.assertTrue(any("RDAP не ответил" in ln for ln in lines), lines)


if __name__ == "__main__":
    unittest.main()
