#!/usr/bin/env python3
"""Инварианты письма ловят нарушения — и молчат на корректном письме."""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402

MINUS = "−"

OK_SNAP = {"yandex": {"available": True}, "google": {"available": True},
           "analytics": {"metrika": {"available": True}, "ga4": {"available": True}}}
OK_DQ = {"findings": []}
OK_BLOCKS = {"kpis": [], "signals": [], "pills": [{"label": "ДАННЫЕ", "state": "limited"}]}


class TestInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inv = mocks.load("invariants")

    def test_clean_letter_has_no_violations(self):
        self.assertEqual(self.inv.check(OK_SNAP, OK_DQ, OK_BLOCKS, "текст"), [])

    def test_no_data_kpi_with_delta_is_violation(self):
        blocks = dict(OK_BLOCKS, kpis=[{"key": "google", "value": "нет данных",
                                        "delta": "+5", "relative": None}])
        v = self.inv.check(OK_SNAP, OK_DQ, blocks, "")
        self.assertTrue(any("нет данных" in x for x in v))

    def test_negative_delta_with_positive_tone_is_violation(self):
        blocks = dict(OK_BLOCKS, signals=[{"metric": "Показы", "tone": "positive",
                                           "delta": f"{MINUS}7"}])
        v = self.inv.check(OK_SNAP, OK_DQ, blocks, "")
        self.assertTrue(any("positive" in x for x in v))

    def test_positive_delta_with_negative_tone_is_violation(self):
        blocks = dict(OK_BLOCKS, signals=[{"metric": "Показы", "tone": "negative",
                                           "delta": "+7"}])
        v = self.inv.check(OK_SNAP, OK_DQ, blocks, "")
        self.assertTrue(any("negative" in x for x in v))

    def test_unavailable_source_requires_degraded_pill(self):
        snap = {"yandex": {"available": False}, "google": {"available": True},
                "analytics": {"metrika": {"available": True},
                              "ga4": {"available": True}}}
        v = self.inv.check(snap, OK_DQ, OK_BLOCKS, "")
        self.assertTrue(any("сбой" in x for x in v))
        blocks = dict(OK_BLOCKS, pills=[{"label": "ДАННЫЕ", "state": "degraded"}])
        self.assertEqual(self.inv.check(snap, OK_DQ, blocks, ""), [])

    def test_source_unavailable_finding_requires_degraded_pill(self):
        dq = {"findings": [{"code": "SOURCE_UNAVAILABLE", "source": "ga4"}]}
        v = self.inv.check(OK_SNAP, dq, OK_BLOCKS, "")
        self.assertTrue(any("сбой" in x for x in v))

    def test_unprovable_wording_is_violation(self):
        v = self.inv.check(OK_SNAP, OK_DQ, OK_BLOCKS, "показов по-прежнему нет")
        self.assertTrue(any("по-прежнему" in x for x in v))

    def test_write_report_records_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.inv.write_report("2026-08-25", OK_SNAP, OK_DQ, OK_BLOCKS,
                                        "текст", out_dir=pathlib.Path(tmp))
            self.assertTrue(out["passed"])
            saved = json.loads((pathlib.Path(tmp) / "2026-08-25-invariants.json")
                               .read_text(encoding="utf-8"))
            self.assertEqual(saved["violations"], [])


if __name__ == "__main__":
    unittest.main()
