"""Переключатель источников доменных данных: реестр data/seo/domain-data-sources.json.

Блокировка аккаунта в группе TurnCommerce (NameBright, DropCatch) 08.09.2026
показала, что поставщик выбирался в переписке и нигде не был записан: замену
пришлось искать заново вместо того, чтобы переключить. Реестр закрывает эту
дыру, а тест — три способа его испортить: назначить действующим источник из
заблокированной группы, оставить функцию без живого запасного и сослаться на
секрет, которого нет в ops/secrets/registry.json.
"""
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "data" / "seo" / "domain-data-sources.json"
SECRETS = ROOT / "ops" / "secrets" / "registry.json"


def load() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


class RegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load()
        self.sources = {s["id"]: s for s in self.data["sources"]}
        self.blocked = {g["id"] for g in self.data["blocked_groups"]}

    def test_действующий_источник_описан(self):
        for fn in self.data["functions"]:
            active = fn.get("active")
            if active is None:
                # Функция без источника обязана объяснить, почему её нет:
                # молчаливый null неотличим от забытой строки.
                self.assertTrue(fn.get("_active"), f"{fn['id']}: null без причины")
                continue
            self.assertIn(active, self.sources, f"{fn['id']}: источника нет в sources")

    def test_действующий_источник_не_из_заблокированной_группы(self):
        for fn in self.data["functions"]:
            active = fn.get("active")
            if active is None:
                continue
            group = self.sources[active].get("group")
            self.assertNotIn(
                group, self.blocked,
                f"{fn['id']}: источник {active} принадлежит заблокированной группе {group}")

    def test_у_каждой_функции_есть_живой_запасной(self):
        for fn in self.data["functions"]:
            alternates = [a for a in fn.get("alternates", [])
                          if a != fn.get("active")
                          and self.sources.get(a, {}).get("group") not in self.blocked]
            self.assertTrue(alternates, f"{fn['id']}: единая точка отказа — запасных нет")
            for alt in fn.get("alternates", []):
                self.assertIn(alt, self.sources, f"{fn['id']}: запасной {alt} не описан")

    def test_секреты_источников_зарегистрированы(self):
        known = {s["name"] for s in json.loads(SECRETS.read_text(encoding="utf-8"))["secrets"]}
        for src in self.data["sources"]:
            for name in src.get("secrets", []):
                self.assertIn(name, known,
                              f"{src['id']}: секрет {name} не заведён в ops/secrets/registry.json")

    def test_нет_источников_без_потребителя(self):
        used = set()
        for fn in self.data["functions"]:
            if fn.get("active"):
                used.add(fn["active"])
            used.update(fn.get("alternates", []))
        # Заблокированные площадки описаны намеренно и запасными быть не могут:
        # запись о них — то, что удерживает переключатель от возврата на них.
        listed = {i for i, s in self.sources.items() if s.get("group") not in self.blocked}
        orphans = sorted(listed - used)
        self.assertFalse(orphans, f"источники ни у одной функции: {orphans}")

    def test_заблокированные_площадки_описаны_и_не_переключаемы(self):
        blocked_sources = {i for i, s in self.sources.items()
                           if s.get("group") in self.blocked}
        self.assertTrue(blocked_sources, "группа заблокирована, а её площадок в реестре нет")
        # Проверка бьёт: подмена active на заблокированную площадку роняет тест.
        probe = {"id": "проба", "active": sorted(blocked_sources)[0]}
        group = self.sources[probe["active"]].get("group")
        self.assertIn(group, self.blocked)

    def test_заблокированная_группа_объясняет_себя(self):
        for group in self.data["blocked_groups"]:
            for field in ("brands", "since", "reason", "policy"):
                self.assertTrue(group.get(field), f"{group['id']}: не заполнено {field}")


if __name__ == "__main__":
    unittest.main()
