#!/usr/bin/env python3
"""Веб-отчёт: сортировка разделов по критичности и оглавление."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402


class TestSectionOrder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = mocks.load("webreport")

    def test_sorted_by_criticality_desc(self):
        sections = [
            {"id": "a", "title": "Справочный", "crit": 0},
            {"id": "b", "title": "Критичный", "crit": 3},
            {"id": "c", "title": "Рабочий", "crit": 1},
            {"id": "d", "title": "Важный", "crit": 2},
        ]
        self.assertEqual([s["id"] for s in self.w.order_sections(sections)],
                         ["b", "d", "c", "a"])

    def test_stable_within_level(self):
        """Внутри уровня — редакционный порядок, а не алфавит."""
        sections = [{"id": i, "crit": 1} for i in ("z", "a", "m")]
        self.assertEqual([s["id"] for s in self.w.order_sections(sections)],
                         ["z", "a", "m"])

    def test_toc_has_anchors_and_severity_chips(self):
        sections = [
            {"id": "loop", "title": "Работа конвейера", "crit": 3},
            {"id": "charts", "title": "Графики", "crit": 0},
        ]
        toc = self.w._toc(sections)
        self.assertIn("href='#loop'", toc)
        self.assertIn("href='#charts'", toc)
        self.assertIn("критично", toc)
        self.assertIn("справочно", toc)
        self.assertIn("отсортированы по критичности", toc)


class TestNewSections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = mocks.load("webreport")

    def test_loop_section_absent_registry(self):
        html = self.w._loop_section({"available": False})
        self.assertIn("Реестра исполнения контуров нет", html)

    def test_loop_section_marks_overdue(self):
        html = self.w._loop_section({"available": True, "contours": [
            {"id": "x", "label": "Сбор", "cadence": "ежедневно",
             "last_run": "2026-08-25", "expected_since": "2026-08-27",
             "overdue": True, "days_late": 2, "note": None},
            {"id": "y", "label": "Письмо", "cadence": "ежедневно",
             "last_run": "2026-08-26", "expected_since": "2026-08-26",
             "overdue": False, "days_late": 0, "note": None}]})
        self.assertIn("просрочен", html)
        self.assertIn("в срок", html)
        self.assertIn("2 дн.", html)

    def test_money_section_lists_queries(self):
        html = self.w._money_section({"available": True, "considered": 2,
                                      "note": "показы сайта", "items": [
            {"query": "купить figma", "engine": "yandex", "impressions": 120,
             "clicks": 0, "position": 6.1, "zone_label": "в первой десятке",
             "recommended_action": "переписать заголовок"}]})
        self.assertIn("купить figma", html)
        self.assertIn("Яндекс", html)

    def test_money_section_empty_reason(self):
        html = self.w._money_section({"available": False, "reason": "нет данных"})
        self.assertIn("нет данных", html)


if __name__ == "__main__":
    unittest.main()
