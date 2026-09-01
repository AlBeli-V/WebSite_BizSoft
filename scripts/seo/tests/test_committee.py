#!/usr/bin/env python3
"""Growth Committee: окно недели, гейт содержания, negative knowledge."""

import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402


class TestWeekBounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cm = mocks.load("committee")

    def test_monday_send_covers_previous_full_week(self):
        # Отправка в понедельник 01.09 → неделя пн 24.08 – вс 30.08.
        p_from, p_to = self.cm.week_bounds(dt.date(2026, 9, 1))
        self.assertEqual(p_from.isoformat(), "2026-08-24")
        self.assertEqual(p_to.isoformat(), "2026-08-30")

    def test_midweek_send_still_last_finished_week(self):
        p_from, p_to = self.cm.week_bounds(dt.date(2026, 9, 3))
        self.assertEqual((p_from.isoformat(), p_to.isoformat()),
                         ("2026-08-24", "2026-08-30"))


class TestContentGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cm = mocks.load("committee")

    def _doc(self, extra=""):
        blocks = "".join(f"<h2>{b}</h2>" for b in self.cm.REQUIRED_BLOCKS)
        return f"<div>{blocks}{extra}</div>"

    def test_clean_letter_passes(self):
        self.assertEqual(self.cm.content_gate(self._doc()), [])

    def test_forbidden_word_blocks(self):
        """Ловится и форма с беглой гласной («заявок»), а не только «заявка»."""
        for text in ("получено 5 заявок", "рост заявки на 30%"):
            problems = self.cm.content_gate(self._doc(f"<p>{text}</p>"))
            self.assertTrue(any("заяв" in p for p in problems), text)

    def test_missing_block_blocks(self):
        doc = self._doc().replace("Вердикты экспериментов", "Вердикты")
        problems = self.cm.content_gate(doc)
        self.assertTrue(any("Вердикты экспериментов" in p for p in problems))


class TestNegativeKnowledge(unittest.TestCase):
    def setUp(self):
        self.cm = mocks.load("committee")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = pathlib.Path(self.tmp.name)
        self.cm.OUT_DIR = base
        self.cm.NEGATIVE = base / "negative-knowledge.json"
        self.cm.DECISIONS = base / "experiment-decisions.jsonl"

    def test_rejected_decision_lands_in_registry(self):
        self.cm.DECISIONS.write_text(
            json.dumps({"experiment_id": "SEO-EXP-009", "date": "2026-08-30",
                        "verdict": "REJECTED", "reason": "CTR упал"},
                       ensure_ascii=False) + "\n", encoding="utf-8")
        data = self.cm.refresh_negative_knowledge("2026-09-01")
        self.assertEqual(len(data["entries"]), 1)
        self.assertEqual(data["entries"][0]["key"], "seo-exp-009")

    def test_confirmed_decision_ignored_and_no_duplicates(self):
        lines = [
            {"experiment_id": "SEO-EXP-009", "date": "2026-08-30",
             "verdict": "REJECTED"},
            {"experiment_id": "SEO-EXP-009", "date": "2026-08-31",
             "verdict": "REJECTED"},
            {"experiment_id": "SEO-EXP-010", "date": "2026-08-31",
             "verdict": "CONFIRMED"},
        ]
        self.cm.DECISIONS.write_text(
            "\n".join(json.dumps(x, ensure_ascii=False) for x in lines),
            encoding="utf-8")
        data = self.cm.refresh_negative_knowledge("2026-09-01")
        self.assertEqual([e["key"] for e in data["entries"]], ["seo-exp-009"])

    def test_empty_sources_give_empty_registry(self):
        data = self.cm.refresh_negative_knowledge("2026-09-01")
        self.assertEqual(data["entries"], [])
        self.assertTrue(self.cm.NEGATIVE.exists())


class TestRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cm = mocks.load("committee")

    def _minimal(self):
        lh = {"contours": [{"label": "Сбор", "overdue": False,
                            "last_run": "2026-08-31"}]}
        return {
            "date": "2026-09-01",
            "week": {"from": "2026-08-24", "to": "2026-08-30"},
            "prev_week": {"from": "2026-08-17", "to": "2026-08-23"},
            "deltas": [], "grown": [], "fallen": [], "flat": [],
            "pages_up": [], "pages_down": [],
            "drivers": [],
            "opportunities": {"items": []},
            "allocator": {"items": [
                {"rank": 1, "title": "Запрос «x»", "action": "усилить",
                 "evidence": "10 показов", "source": "радар возможностей"}]},
            "loop_health": lh,
            "experiments": [],
            "negative": {"entries": []},
            "limits_note": "границы измерения",
        }

    def test_renders_all_required_blocks_and_passes_gate(self):
        html_doc, plain = self.cm.render(self._minimal())
        self.assertEqual(self.cm.content_gate(html_doc), [])
        self.assertIn("Действия недели", html_doc)
        self.assertIn("Запрос «x»", plain)

    def test_no_drivers_is_honest(self):
        html_doc, plain = self.cm.render(self._minimal())
        self.assertIn("Подтверждённых драйверов", html_doc)
        self.assertIn("подтверждённых драйверов нет", plain)


if __name__ == "__main__":
    unittest.main()
