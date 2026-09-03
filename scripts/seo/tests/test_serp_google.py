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
            "top_n": 20, "pages": 1,
            "query": {"loc": 2643, "device": "desktop"},
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
        def search(session, user, key, q, query_cfg=None, top_n=20, page=0):
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

    def test_two_pages_merge_into_one_row_and_two_ledger_lines(self):
        def page_top(page):
            return [{"domain": f"d{page}-{i}.ru", "url": "https://x/",
                     "title": ""} for i in range(10)]
        seen = []

        def search(session, user, key, q, query_cfg=None, top_n=20, page=0):
            seen.append((q, page))
            if q == "хвост" and page == 1:
                return {"error": "code=500"}
            return {"found": 100, "top": page_top(page),
                    "blocks": {"organic": 10}}

        with mock.patch.object(self.sg.xmlriver, "search_google", search), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"balance_rub": 100.0}):
            res = self.sg.run(DATE, ["купить figma", "хвост"],
                              cfg(pages=2, daily_cap=10, monthly_cap=10),
                              "u", "k")
        self.assertEqual(sorted(seen), [("купить figma", 0), ("купить figma", 1),
                                        ("хвост", 0), ("хвост", 1)])
        self.assertEqual((res["ok"], res["failed"], res["calls"]), (2, 0, 4))
        self.assertEqual(self.sg.month_spent(self.date), 4)   # в вызовах
        rows = {json.loads(l)["query"]: json.loads(l) for l in
                pathlib.Path(res["out"]).read_text(encoding="utf-8").splitlines()}
        top = rows["купить figma"]["top"]
        self.assertEqual(len(top), 20)
        self.assertEqual((top[0]["domain"], top[10]["domain"]),
                         ("d0-0.ru", "d1-0.ru"))
        self.assertEqual(rows["купить figma"]["pages_fetched"], 2)
        # сбой второй страницы: первая сохранена, ошибка помечена
        self.assertEqual(len(rows["хвост"]["top"]), 10)
        self.assertIn("500", rows["хвост"]["partial_error"])
        self.assertNotIn("error", rows["хвост"])

    def test_second_page_not_fetched_after_first_page_error_or_short(self):
        seen = []

        def search(session, user, key, q, query_cfg=None, top_n=20, page=0):
            seen.append((q, page))
            if q == "сбой":
                return {"error": "HTTP 403"}
            return {"found": 3, "top": [{"domain": "a.ru", "url": "", "title": ""}] * 3,
                    "blocks": {}}

        with mock.patch.object(self.sg.xmlriver, "search_google", search), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"error": "x"}):
            res = self.sg.run(DATE, ["сбой", "короткая"],
                              cfg(pages=2, daily_cap=10, monthly_cap=10),
                              "u", "k")
        self.assertEqual(sorted(seen), [("короткая", 0), ("сбой", 0)])
        self.assertEqual((res["ok"], res["failed"], res["calls"]), (1, 1, 2))

    def test_budget_is_counted_in_calls(self):
        """Потолок 5 вызовов при двух страницах — только 2 ключа."""
        with mock.patch.object(self.sg.xmlriver, "search_google",
                               self.fake_search({})), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"balance_rub": 100.0}):
            res = self.sg.run(DATE, [f"q{i}" for i in range(4)],
                              cfg(pages=2), "u", "k")
        self.assertEqual(res["requested"], 2)
        self.assertEqual(res["skipped_over_budget"], 2)

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
