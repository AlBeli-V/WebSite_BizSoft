"""Реестр внешних аккаунтов ops/accounts/registry.json.

Блокировка аккаунта в группе TurnCommerce 08.09.2026 показала, что связку
«аккаунт — что от него зависит» никто не хранил: объём потери выяснялся
постфактум. Тест держит реестр пригодным к этому вопросу — каждый секрет
принадлежит аккаунту, у каждого аккаунта записан импакт, а незаполненное
поле объясняет себя вместо молчаливого null.
"""
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
ACCOUNTS = ROOT / "ops" / "accounts" / "registry.json"
SECRETS = ROOT / "ops" / "secrets" / "registry.json"
SOURCES = ROOT / "data" / "seo" / "domain-data-sources.json"


class AccountsRegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(ACCOUNTS.read_text(encoding="utf-8"))
        self.accounts = self.data["accounts"]

    def test_у_каждого_аккаунта_есть_назначение_статус_и_импакт(self):
        for acc in self.accounts:
            for field in ("vendor", "purpose", "status", "impact"):
                self.assertTrue(acc.get(field), f"{acc['id']}: не заполнено {field}")
            # declined — аккаунт не заводится решением руководителя (google-cloud-cse, 13.09.2026)
            self.assertIn(acc["status"], {"active", "blocked", "planned", "declined"}, acc["id"])

    def test_незаполненное_поле_объясняет_себя(self):
        for acc in self.accounts:
            for field in ("owner_contact", "payment"):
                if acc.get(field) is None:
                    self.assertTrue(acc.get(f"_{field}"),
                                    f"{acc['id']}: null в {field} без пояснения")

    def test_каждый_секрет_принадлежит_аккаунту(self):
        known = {s["name"] for s in json.loads(SECRETS.read_text(encoding="utf-8"))["secrets"]}
        covered = {name for acc in self.accounts for name in acc.get("secrets", [])}
        exempt = {e["name"] for e in self.data.get("secrets_without_account", [])}
        for entry in self.data.get("secrets_without_account", []):
            self.assertTrue(entry.get("reason"), f"{entry['name']}: исключение без причины")
        missing = sorted(known - covered - exempt)
        self.assertFalse(missing, f"секреты без аккаунта в реестре: {missing}")

    def test_секреты_реестра_существуют(self):
        known = {s["name"] for s in json.loads(SECRETS.read_text(encoding="utf-8"))["secrets"]}
        for acc in self.accounts:
            for name in acc.get("secrets", []):
                self.assertIn(name, known, f"{acc['id']}: секрета {name} нет в реестре секретов")

    def test_заблокированные_аккаунты_совпадают_с_реестром_источников(self):
        blocked_here = {acc["group"] for acc in self.accounts if acc["status"] == "blocked"}
        sources = json.loads(SOURCES.read_text(encoding="utf-8"))
        blocked_there = {g["id"] for g in sources["blocked_groups"]}
        self.assertTrue(blocked_here <= blocked_there,
                        f"группы {sorted(blocked_here - blocked_there)} заблокированы в аккаунтах, "
                        "но не в реестре источников — переключатель их пропустит")

    def test_домены_сторожа_описаны(self):
        domains = self.data.get("domains") or []
        self.assertTrue(domains, "сторожу ops-domain-watch нечего проверять")
        for dom in domains:
            self.assertTrue(dom.get("name"), "домен без имени")
            self.assertTrue(dom.get("role"), f"{dom.get('name')}: не указана роль")
            self.assertGreater(int(dom.get("warn_days", 0)), 0, f"{dom['name']}: warn_days")
            if dom.get("expected_registrar") is None:
                self.assertTrue(dom.get("_expected_registrar"),
                                f"{dom['name']}: null в expected_registrar без пояснения")


if __name__ == "__main__":
    unittest.main()
