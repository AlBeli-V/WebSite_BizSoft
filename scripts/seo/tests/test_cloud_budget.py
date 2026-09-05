#!/usr/bin/env python3
"""Контроль бюджета Yandex Cloud: расчётный остаток, прогноз, дисциплина писем."""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402

DATE = "2026-09-06"   # неделя после базовой точки 30.08


class TestCloudBudget(unittest.TestCase):
    def setUp(self):
        self.cb = mocks.load("cloud_budget")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = pathlib.Path(self.tmp.name)
        self.cb.BALANCE_FILE = base / "cloud-balance.json"
        self.cb.OUT_FILE = base / "cloud-budget.json"
        self.cb.NOTICE_FILE = base / "cloud-budget-notice.txt"
        self.cb.WORDSTAT_LEDGER_DIR = base / "wledger"
        self.cb.SERP_LEDGER_DIR = base / "sledger"
        # Факт из Billing API и история остатка тоже читаются из рабочей копии:
        # без подмены боевой cloud-billing.json подменял базовую точку теста, и
        # расчёт шёл от реального остатка (04.09.2026 — два падения).
        self.cb.BILLING_FILE = base / "cloud-billing.json"
        self.cb.HISTORY_FILE = base / "cloud-balance-history.jsonl"

    def set_balance(self, rub=10000, date="2026-08-30"):
        self.cb.BALANCE_FILE.write_text(json.dumps(
            {"baseline": {"date": date, "balance_rub": rub,
                          "note": "пополнение руководителя"}}),
            encoding="utf-8")

    def ledger(self, dir_, entries):
        dir_.mkdir(parents=True, exist_ok=True)
        (dir_ / "2026-09.jsonl").write_text(
            "\n".join(json.dumps(e, ensure_ascii=False) for e in entries)
            + "\n", encoding="utf-8")

    def test_no_baseline_is_honest(self):
        res = self.cb.build(DATE)
        self.assertFalse(res["available"])
        self.assertIn("базовая точка", res["reason"])

    def test_balance_minus_ledgers(self):
        self.set_balance()
        self.ledger(self.cb.WORDSTAT_LEDGER_DIR,
                    [{"at": "2026-09-01T02:00:00Z", "cost_rub": 100.0},
                     {"at": "2026-08-29T02:00:00Z", "cost_rub": 999.0}])  # до базы
        self.ledger(self.cb.SERP_LEDGER_DIR,
                    [{"at": f"2026-09-0{d}T22:40:00Z", "query": "x"}
                     for d in range(1, 6)])
        res = self.cb.build(DATE)
        self.assertTrue(res["available"])
        spent = res["spent_since_baseline"]
        self.assertEqual(spent["wordstat_rub"], 100.0)
        self.assertEqual(spent["serp_requests"], 5)
        self.assertAlmostEqual(
            res["balance_estimate_rub"],
            10000 - 100 - 5 * self.cb.SERP_COST_RUB, places=2)
        self.assertFalse(res["needs_topup"])
        self.assertGreater(res["runway_days"], self.cb.RUNWAY_ALERT_DAYS)

    def test_high_burn_triggers_topup(self):
        self.set_balance(rub=1000)
        self.ledger(self.cb.WORDSTAT_LEDGER_DIR,
                    [{"at": f"2026-09-0{d}T02:00:00Z", "cost_rub": 120.0}
                     for d in range(1, 7)])
        res = self.cb.build(DATE)
        self.assertTrue(res["needs_topup"])
        self.assertLess(res["runway_days"], self.cb.RUNWAY_ALERT_DAYS)

    def test_zero_spend_means_no_alarm(self):
        self.set_balance()
        res = self.cb.build(DATE)
        self.assertIsNone(res["runway_days"])
        self.assertFalse(res["needs_topup"])

    def test_notice_cooldown(self):
        self.cb.NOTICE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.cb.NOTICE_FILE.write_text("2026-09-05", encoding="utf-8")
        self.assertTrue(self.cb._notice_recent("2026-09-06"))
        self.assertFalse(self.cb._notice_recent("2026-09-09"))


if __name__ == "__main__":
    unittest.main()
