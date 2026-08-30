#!/usr/bin/env python3
"""Billing API: выбор аккаунта, цены SKU, история остатка, приоритет факта."""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402

DATE = "2026-09-06"


class TestYcBillingParsers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.yb = mocks.load("yc_billing")

    def test_pick_active_account(self):
        acc = self.yb.pick_account([{"id": "a", "active": False},
                                    {"id": "b", "active": True}])
        self.assertEqual(acc["id"], "b")
        self.assertIsNone(self.yb.pick_account([]))

    def test_sku_price_from_last_version(self):
        sku = {"pricingVersions": [
            {"pricingExpressions": [{"rates": [{"unitPrice": "0.1"}]}]},
            {"pricingExpressions": [{"rates": [{"unitPrice": "0.244"}]}]}]}
        self.assertEqual(self.yb.sku_price(sku), 0.244)
        self.assertIsNone(self.yb.sku_price({}))

    def test_relevant_skus_filters_by_name(self):
        skus = [{"id": "1", "name": "Search API — синхронный запрос",
                 "pricingUnit": "request", "pricingVersions": []},
                {"id": "2", "name": "Compute Cloud vCPU",
                 "pricingUnit": "core*hour"},
                {"id": "3", "name": "Search API Wordstat request"}]
        out = self.yb.relevant_skus(skus)
        self.assertEqual([s["id"] for s in out], ["1", "3"])

    def test_history_append_once_per_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.yb.HISTORY_FILE = pathlib.Path(tmp) / "h.jsonl"
            self.yb.append_history("2026-09-05", 9900.0)
            self.yb.append_history("2026-09-05", 9800.0)   # дубль даты
            self.yb.append_history("2026-09-06", 9700.0)
            lines = self.yb.HISTORY_FILE.read_text(
                encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["balance"], 9900.0)


class TestBudgetWithBillingFact(unittest.TestCase):
    def setUp(self):
        self.cb = mocks.load("cloud_budget")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = pathlib.Path(self.tmp.name)
        for attr in ("BALANCE_FILE", "BILLING_FILE", "HISTORY_FILE",
                     "OUT_FILE", "NOTICE_FILE"):
            setattr(self.cb, attr, base / attr.lower().replace("_", "-"))
        self.cb.WORDSTAT_LEDGER_DIR = base / "wl"
        self.cb.SERP_LEDGER_DIR = base / "sl"
        self.cb.BALANCE_FILE.write_text(json.dumps(
            {"baseline": {"date": "2026-08-30", "balance_rub": 10000}}),
            encoding="utf-8")

    def billing(self, balance, date=DATE, skus=()):
        self.cb.BILLING_FILE.write_text(json.dumps(
            {"date": date, "balance_rub": balance, "skus": list(skus)}),
            encoding="utf-8")

    def history(self, points):
        self.cb.HISTORY_FILE.write_text(
            "\n".join(json.dumps({"date": d, "balance": b})
                      for d, b in points) + "\n", encoding="utf-8")

    def test_billing_fact_overrides_estimate(self):
        self.billing(8500.0, skus=[{"name": "Search API", "price_rub": 0.244}])
        self.history([("2026-09-04", 8700.0), ("2026-09-05", 8600.0),
                      ("2026-09-06", 8500.0)])
        res = self.cb.build(DATE)
        self.assertEqual(res["balance_source"], "billing_api")
        self.assertEqual(res["balance_estimate_rub"], 8500.0)
        self.assertEqual(res["daily_rate_rub"], 100.0)   # по дельтам остатка
        self.assertEqual(res["runway_days"], 85.0)
        self.assertEqual(res["billing_skus"][0]["price_rub"], 0.244)

    def test_topup_delta_is_not_spend(self):
        self.billing(9500.0)
        self.history([("2026-09-04", 500.0), ("2026-09-05", 400.0),
                      ("2026-09-06", 9500.0)])            # пополнение
        res = self.cb.build(DATE)
        self.assertEqual(res["daily_rate_rub"], 100.0)    # только реальная трата

    def test_stale_billing_falls_back_to_estimate(self):
        self.billing(8500.0, date="2026-09-01")           # старше 2 дней
        res = self.cb.build(DATE)
        self.assertEqual(res["balance_source"], "estimate")

    def test_low_actual_balance_triggers_topup(self):
        self.billing(300.0)
        self.history([("2026-09-05", 400.0), ("2026-09-06", 300.0)])
        res = self.cb.build(DATE)
        self.assertTrue(res["needs_topup"])
        self.assertEqual(res["runway_days"], 3.0)


if __name__ == "__main__":
    unittest.main()
