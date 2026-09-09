#!/usr/bin/env python3
"""Проверки слоя созревания тикетов."""

import datetime as dt
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import tasks_due as td  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
TASKS = ROOT / "reports" / "seo" / "tasks"


def ticket(tid, title="Задача", prio="P2", status="queued", due=None, waits=None):
    head = f"**Приоритет:** {prio} · **Статус:** {status}"
    if due:
        head += f" · **Созревает:** {due}"
    if waits:
        head += f" · **Ждёт:** {waits}"
    return f"# {tid} — {title}\n\n{head}\n\n## Проблема\nтекст\n"


class TestParse(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp())

    def write(self, name, body):
        (self.dir / name).write_text(body, encoding="utf-8")

    def test_читает_срок_и_блокировку(self):
        self.write("A-1.md", ticket("A-1", due="2026-10-06", waits="MONEY-A1"))
        row = td.collect(self.dir)[0]
        self.assertEqual(row["id"], "A-1")
        self.assertEqual(row["due"], dt.date(2026, 10, 6))
        self.assertEqual(row["waits_for"], "MONEY-A1")

    def test_тикет_без_срока_не_созревает_никогда(self):
        # Иначе слой каждый день печатал бы один и тот же список.
        self.write("A-2.md", ticket("A-2"))
        rows = td.collect(self.dir)
        self.assertEqual(td.ripe(rows, dt.date(2030, 1, 1)), [])

    def test_закрытый_тикет_не_созревает(self):
        self.write("A-3.md", ticket("A-3", status="done", due="2026-09-01"))
        rows = td.collect(self.dir)
        self.assertEqual(td.ripe(rows, dt.date(2026, 9, 1)), [])

    def test_созревание_это_событие_а_не_ежедневный_список(self):
        self.write("A-4.md", ticket("A-4", due="2026-09-09"))
        rows = td.collect(self.dir)
        self.assertEqual(len(td.ripe(rows, dt.date(2026, 9, 9))), 1)
        # Через день окно ещё ловит — один упавший прогон не глотает срок.
        self.assertEqual(len(td.ripe(rows, dt.date(2026, 9, 10))), 1)
        # Дальше тикет замолкает сам, даже если его не закрыли.
        self.assertEqual(td.ripe(rows, dt.date(2026, 9, 20)), [])

    def test_будущий_срок_молчит(self):
        self.write("A-5.md", ticket("A-5", due="2026-12-01"))
        rows = td.collect(self.dir)
        self.assertEqual(td.ripe(rows, dt.date(2026, 9, 9)), [])

    def test_порядок_по_приоритету(self):
        self.write("A-6.md", ticket("A-6", prio="P2", due="2026-09-09"))
        self.write("A-7.md", ticket("A-7", prio="P0", due="2026-09-09"))
        ids = [r["id"] for r in td.ripe(td.collect(self.dir), dt.date(2026, 9, 9))]
        self.assertEqual(ids, ["A-7", "A-6"])


class TestUnmanaged(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp())

    def write(self, name, body):
        (self.dir / name).write_text(body, encoding="utf-8")

    def test_открытый_тикет_без_даты_попадает_в_аудит(self):
        # Тикет, у которого момент запуска записан прозой, слой созревания не
        # видит никогда — аудит для того и нужен.
        self.write("B-1.md", ticket("B-1", status="proposed"))
        self.write("B-2.md", ticket("B-2", due="2026-10-06"))
        ids = [r["id"] for r in td.unmanaged(td.collect(self.dir))]
        self.assertEqual(ids, ["B-1"])

    def test_закрытый_тикет_в_аудит_не_попадает(self):
        self.write("B-3.md", ticket("B-3", status="done"))
        self.write("B-4.md", ticket("B-4", status="deferred"))
        self.assertEqual(td.unmanaged(td.collect(self.dir)), [])

    def test_approved_и_implemented_считаются_незакрытыми(self):
        # У approved решение принято, но не применено; у implemented код
        # выкачен, но результат не снят. Обоим ещё нужен следующий шаг.
        self.write("B-5.md", ticket("B-5", status="approved"))
        self.write("B-6.md", ticket("B-6", status="implemented"))
        ids = sorted(r["id"] for r in td.unmanaged(td.collect(self.dir)))
        self.assertEqual(ids, ["B-5", "B-6"])


class TestRealTickets(unittest.TestCase):
    def test_все_тикеты_money_имеют_срок_и_разбираются(self):
        rows = {r["id"]: r for r in td.collect(TASKS)}
        money = {k: v for k, v in rows.items() if k.startswith("MONEY-")}
        self.assertGreaterEqual(len(money), 11)
        # Тикет без срока слой не покажет никогда — значит, срок обязателен.
        without = [k for k, v in money.items() if not v["due"]]
        self.assertEqual(without, [], f"тикеты без срока созревания: {without}")

    def test_старые_тикеты_проекта_не_сломали_разбор(self):
        rows = td.collect(TASKS)
        self.assertTrue(all(r["id"] and r["title"] for r in rows))

    def test_аудит_на_реальной_папке_согласован(self):
        # Первая версия этой проверки требовала, чтобы в аудите были тикеты
        # GIDX: их завели 08.09 без дат, и аудит их находил. Через час
        # соседний контур проставил даты всем семи — и проверка упала, хотя
        # произошло ровно то, ради чего аудит и сделан. Утверждать состояние
        # чужих файлов нельзя: поведение аудита проверяется на фикстурах
        # (TestUnmanaged), а здесь — только его согласованность с папкой.
        rows = td.collect(TASKS)
        audited = td.unmanaged(rows)
        for r in audited:
            self.assertTrue(r["status_open"], f"{r['id']}: тикет закрыт")
            self.assertIsNone(r["due"], f"{r['id']}: у тикета есть дата")
        # Тикет со сроком в аудит попасть не может ни при каком составе папки.
        dated = {r["id"] for r in rows if r["due"]}
        self.assertEqual(dated & {r["id"] for r in audited}, set())


if __name__ == "__main__":
    unittest.main()
