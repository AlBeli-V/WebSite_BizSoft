#!/usr/bin/env python3
"""Проверки переноса заготовленных записей в реестр экспериментов."""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import experiments_sync as es  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
PENDING = ROOT / "data" / "seo" / "experiments-pending"


def rec(rid, status="planned", start=None, pages=("/vendors/x",)):
    return {"id": rid, "status": status, "start": start, "pages": list(pages)}


class TestMerge(unittest.TestCase):
    def test_новая_запись_добавляется(self):
        reg = {"experiments": [rec("a")]}
        r = es.merge(reg, [(pathlib.Path("p.json"), rec("b"))])
        self.assertEqual([i[1] for i in r["added"]], ["b"])
        self.assertEqual([e["id"] for e in reg["experiments"]], ["a", "b"])

    def test_существующая_запись_не_перезаписывается(self):
        # Реестр ведут и другие прогоны: activate проставляет старт и окна,
        # вердикт пишет оценку. Перезапись затёрла бы их работу.
        reg = {"experiments": [dict(rec("a", status="running", start="2026-09-01"),
                                    windows={"days": 28})]}
        r = es.merge(reg, [(pathlib.Path("p.json"), rec("a"))])
        self.assertEqual(r["added"], [])
        self.assertEqual([i[1] for i in r["skipped"]], ["a"])
        self.assertEqual(reg["experiments"][0]["status"], "running")
        self.assertIn("windows", reg["experiments"][0])

    def test_повторный_прогон_ничего_не_меняет(self):
        reg = {"experiments": []}
        pend = [(pathlib.Path("p.json"), rec("a"))]
        es.merge(reg, pend)
        before = json.dumps(reg, ensure_ascii=False, sort_keys=True)
        r = es.merge(reg, pend)
        self.assertEqual(r["added"], [])
        self.assertEqual(json.dumps(reg, ensure_ascii=False, sort_keys=True), before)

    def test_запись_без_обязательных_полей_не_проходит(self):
        reg = {"experiments": []}
        r = es.merge(reg, [(pathlib.Path("p.json"), {"id": "a", "status": "planned"})])
        self.assertEqual(reg["experiments"], [])
        self.assertEqual(len(r["broken"]), 1)
        self.assertIn("pages", r["broken"][0][2])

    def test_running_без_старта_не_проходит(self):
        # Окна считаются от даты старта: без неё эксперимент нечем измерять.
        reg = {"experiments": []}
        r = es.merge(reg, [(pathlib.Path("p.json"), rec("a", status="running"))])
        self.assertEqual(reg["experiments"], [])
        self.assertIn("start", r["broken"][0][2])

    def test_planned_без_старта_проходит(self):
        # Старт проставляет activate по факту выката — это норма.
        reg = {"experiments": []}
        r = es.merge(reg, [(pathlib.Path("p.json"), rec("a", status="planned"))])
        self.assertEqual([i[1] for i in r["added"]], ["a"])


class TestLoadPending(unittest.TestCase):
    def test_читает_все_файлы_папки(self):
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "one.json").write_text(json.dumps({"experiments": [rec("a")]}), encoding="utf-8")
        (d / "two.json").write_text(json.dumps({"experiments": [rec("b"), rec("c")]}),
                                    encoding="utf-8")
        (d / "readme.md").write_text("не json", encoding="utf-8")
        ids = [r["id"] for _, r in es.load_pending(d)]
        self.assertEqual(sorted(ids), ["a", "b", "c"])

    def test_пустая_папка_не_ломает(self):
        self.assertEqual(es.load_pending(pathlib.Path(tempfile.mkdtemp())), [])


class TestRealPending(unittest.TestCase):
    def test_заготовленные_записи_проходят_проверку(self):
        # Файл во входящей папке уедет в реестр без участия человека —
        # поломанная запись обнаружится в проде, а не здесь.
        pending = es.load_pending(PENDING)
        self.assertGreaterEqual(len(pending), 3)
        for path, record in pending:
            self.assertEqual(es.validate(record), [],
                             f"{path.name}: запись {record.get('id')}")

    def test_у_каждой_записи_есть_метрика_и_контроль(self):
        # Без них эксперимент нечем подводить, и он тихо превратится в правку.
        for path, record in es.load_pending(PENDING):
            self.assertTrue(record.get("success_metric"), record.get("id"))
            self.assertTrue(record.get("control_group"), record.get("id"))


if __name__ == "__main__":
    unittest.main()
