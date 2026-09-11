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


def decision(eid="a", date="2026-09-11", verdict="INCONCLUSIVE",
             owner="KEEP", note=""):
    return {"experiment_id": eid, "date": date, "verdict": verdict,
            "recommendation": owner, "owner_decision": owner, "note": note}


class TestDecisions(unittest.TestCase):
    """Перенос решения владельца: журнал и закрытие записи в реестре.

    Пока запись остаётся running, остановленный эксперимент для всех
    моделей идёт: его страницы заняты, кластер закрыт для новых проверок.
    """

    def setUp(self):
        self.reg = {"experiments": [rec("a", status="running", start="2026-08-29")]}
        self.journal = []

    def test_решение_пишется_и_закрывает_запись(self):
        r = es.merge_decisions(self.reg, self.journal,
                               [(pathlib.Path("d.json"), decision())])
        self.assertEqual([i[1] for i in r["appended"]], ["a"])
        self.assertEqual([i[1] for i in r["closed"]], ["a"])
        self.assertEqual(self.reg["experiments"][0]["status"], "closed")
        self.assertEqual(self.reg["experiments"][0]["end"], "2026-09-11")
        self.assertEqual(len(self.journal), 1)

    def test_повторный_прогон_не_задваивает(self):
        pend = [(pathlib.Path("d.json"), decision())]
        es.merge_decisions(self.reg, self.journal, pend)
        r = es.merge_decisions(self.reg, self.journal, pend)
        self.assertEqual(r["appended"], [])
        self.assertEqual([i[1] for i in r["skipped"]], ["a"])
        self.assertEqual(len(self.journal), 1)

    def test_решение_по_чужому_эксперименту_не_пишется(self):
        # Расхождение кода и реестра должно быть видно, а не осесть
        # записью в журнале про эксперимент, которого нет.
        r = es.merge_decisions(self.reg, self.journal,
                               [(pathlib.Path("d.json"), decision(eid="нет-такого"))])
        self.assertEqual(self.journal, [])
        self.assertEqual(len(r["broken"]), 1)
        self.assertIn("нет в реестре", r["broken"][0][2])

    def test_чужое_слово_в_вердикте_не_проходит(self):
        # Словарь общий с оценкой: своё слово здесь означало бы, что журнал
        # и письма говорят разное.
        r = es.merge_decisions(self.reg, self.journal,
                               [(pathlib.Path("d.json"), decision(verdict="ХОРОШО"))])
        self.assertEqual(self.journal, [])
        self.assertIn("вердикт", r["broken"][0][2])

    def test_продление_не_закрывает_эксперимент(self):
        r = es.merge_decisions(self.reg, self.journal,
                               [(pathlib.Path("d.json"), decision(owner="EXTEND"))])
        self.assertEqual(r["closed"], [])
        self.assertEqual(self.reg["experiments"][0]["status"], "running")
        self.assertEqual(len(self.journal), 1)


class TestРеальныйФайлРешений(unittest.TestCase):
    def test_заготовленные_решения_проходят_проверку(self):
        root = ROOT / "data" / "seo" / "decisions-pending"
        for path, record in es.load_decisions(root):
            self.assertEqual(es.validate_decision(record), [], f"{path.name}: {record}")


if __name__ == "__main__":
    unittest.main()
