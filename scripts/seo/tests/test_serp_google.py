#!/usr/bin/env python3
"""Google-срез через xmlriver: расписание, бюджетная дисциплина, журнал, срез."""

import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402

DATE = "2026-09-07"        # понедельник
TUESDAY = "2026-09-08"


def cfg(**over):
    base = {"enabled": True, "price_rub_per_1000": 25, "cadence": "weekly",
            "weekday": 1, "daily_cap": 5, "monthly_cap": 8, "core_cap": 500,
            "top_n": 20, "query": {"loc": 2643, "device": "desktop"},
            "balance_warn_days": 14}
    base.update(over)
    return base


class Base(unittest.TestCase):
    def setUp(self):
        self.sg = mocks.load("serp_google")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = pathlib.Path(self.tmp.name)
        self.sg.SERP_DIR = base / "serp"
        self.sg.LEDGER_DIR = base / "serp" / "ledger"
        self.sg.BALANCE_FILE = base / "serp" / "xmlriver-balance.json"
        self.sg.PAUSE_S = 0
        self.date = dt.date.fromisoformat(DATE)

    def fake_search(self, results):
        def search(session, user, key, q, query_cfg=None, top_n=20):
            return results.get(q, {"found": 1, "top": [
                {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/",
                 "title": q}], "blocks": {"organic": 1}})
        return search


class TestSchedule(Base):
    def test_weekly_only_on_weekday(self):
        self.assertTrue(self.sg.is_collection_day(self.date, cfg()))
        self.assertFalse(self.sg.is_collection_day(
            dt.date.fromisoformat(TUESDAY), cfg()))
        self.assertTrue(self.sg.is_collection_day(
            dt.date.fromisoformat(TUESDAY), cfg(cadence="daily")))

    def test_skip_day_makes_no_calls(self):
        with mock.patch.object(self.sg.xmlriver, "search_google",
                               side_effect=AssertionError("вызов")):
            res = self.sg.run(TUESDAY, ["q"], cfg(), "u", "k")
        self.assertIn("не день сбора", res["skipped"])
        self.assertFalse(self.sg.ledger_path(self.date).exists())

    def test_force_overrides_schedule(self):
        with mock.patch.object(self.sg.xmlriver, "search_google",
                               self.fake_search({})), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"balance_rub": 100.0}):
            res = self.sg.run(TUESDAY, ["q"], cfg(), "u", "k", force=True)
        self.assertEqual(res["ok"], 1)

    def test_disabled(self):
        res = self.sg.run(DATE, ["q"], cfg(enabled=False), "u", "k")
        self.assertIn("выключен", res["skipped"])


class TestBudget(Base):
    def test_every_call_is_logged_and_written(self):
        with mock.patch.object(self.sg.xmlriver, "search_google",
                               self.fake_search({"плохой": {"error": "boom"}})), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"balance_rub": 100.0}):
            res = self.sg.run(DATE, ["купить figma", "плохой"], cfg(), "u", "k")
        self.assertEqual((res["ok"], res["failed"]), (1, 1))
        self.assertEqual(self.sg.month_spent(self.date), 2)
        self.assertEqual(self.sg.day_spent(self.date), 2)
        rows = [json.loads(l) for l in
                pathlib.Path(res["out"]).read_text(encoding="utf-8").splitlines()]
        by_q = {r["query"]: r for r in rows}
        self.assertEqual(by_q["купить figma"]["engine"], "google")
        self.assertEqual(by_q["купить figma"]["region"], "2643")
        self.assertEqual(by_q["купить figma"]["top"][0]["domain"], "biz-soft.pro")
        self.assertEqual(by_q["плохой"]["error"], "boom")
        self.assertTrue(res["out"].endswith("-serp-google.jsonl"))
        # баланс записан вместе с оценкой запаса
        bal = json.loads(self.sg.BALANCE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(bal["balance_rub"], 100.0)
        self.assertIn("days_left_estimate", bal)

    def test_daily_cap_trims_and_holds_the_day(self):
        with mock.patch.object(self.sg.xmlriver, "search_google",
                               self.fake_search({})), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"error": "нет сети"}):
            res = self.sg.run(DATE, [f"q{i}" for i in range(7)], cfg(), "u", "k")
            self.assertEqual(res["requested"], 5)
            self.assertEqual(res["skipped_over_budget"], 2)
            # повторный прогон в тот же день — потолок уже выбран
            res2 = self.sg.run(DATE, ["ещё"], cfg(), "u", "k")
        self.assertIn("дневной потолок", res2["error"])
        self.assertEqual(res2["spent_today"], 5)

    def test_monthly_cap(self):
        self.sg.LEDGER_DIR.mkdir(parents=True)
        self.sg.ledger_path(self.date).write_text(
            "\n".join(json.dumps({"at": "2026-09-01T00:00:00+00:00", "query": "x"})
                      for _ in range(8)) + "\n", encoding="utf-8")
        res = self.sg.run(DATE, ["q"], cfg(), "u", "k")
        self.assertIn("месячный потолок", res["error"])

    def test_balance_topup_flag(self):
        class S:
            pass
        with mock.patch.object(self.sg.xmlriver, "get_balance",
                               lambda s, u, k: {"balance_rub": 0.05}):
            out = self.sg.write_balance(S(), "u", "k", cfg(), spent_today=500)
        # 0,05 ₽ при расходе 12,5 ₽ за прогон — пополнять
        self.assertTrue(out["needs_topup"])
        with mock.patch.object(self.sg.xmlriver, "get_balance",
                               lambda s, u, k: {"balance_rub": 1000.0}):
            out = self.sg.write_balance(S(), "u", "k", cfg(), spent_today=500)
        self.assertFalse(out["needs_topup"])
        self.assertEqual(out["days_left_estimate"], 560)  # 80 прогонов × 7 дней


if __name__ == "__main__":
    unittest.main()
