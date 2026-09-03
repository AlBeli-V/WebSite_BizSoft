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
        def search(session, user, key, q, query_cfg=None, top_n=20, page=1):
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
            return [{"domain": f"d{page}-{i}.ru",
                     "url": f"https://d{page}-{i}.ru/", "title": ""}
                    for i in range(10)]
        seen = []

        def search(session, user, key, q, query_cfg=None, top_n=20, page=1):
            seen.append((q, page))
            if q == "хвост" and page == 2:
                return {"error": "code=500"}
            return {"found": 100, "top": page_top(page),
                    "blocks": {"organic": 10}}

        with mock.patch.object(self.sg.xmlriver, "search_google", search), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"balance_rub": 100.0}):
            res = self.sg.run(DATE, ["купить figma", "хвост"],
                              cfg(pages=2, daily_cap=10, monthly_cap=10),
                              "u", "k")
        # страницы xmlriver нумеруются с единицы
        self.assertEqual(sorted(seen), [("купить figma", 1), ("купить figma", 2),
                                        ("хвост", 1), ("хвост", 2)])
        self.assertEqual((res["ok"], res["failed"], res["calls"]), (2, 0, 4))
        self.assertEqual(self.sg.month_spent(self.date), 4)   # в вызовах
        rows = {json.loads(l)["query"]: json.loads(l) for l in
                pathlib.Path(res["out"]).read_text(encoding="utf-8").splitlines()}
        top = rows["купить figma"]["top"]
        self.assertEqual(len(top), 20)
        self.assertEqual((top[0]["domain"], top[10]["domain"]),
                         ("d1-0.ru", "d2-0.ru"))
        self.assertEqual(rows["купить figma"]["pages_fetched"], 2)
        # сбой второй страницы: первая сохранена, ошибка помечена
        self.assertEqual(len(rows["хвост"]["top"]), 10)
        self.assertIn("500", rows["хвост"]["partial_error"])
        self.assertNotIn("error", rows["хвост"])

    def test_duplicate_second_page_is_not_glued(self):
        """Повтор URL на второй странице не должен удваивать топ."""
        same = [{"domain": f"d{i}.ru", "url": f"https://d{i}.ru/", "title": ""}
                for i in range(10)]
        res = self.sg.merge_pages(
            [{"found": 100, "top": same, "blocks": {"organic": 10}},
             {"found": 100, "top": same, "blocks": {"organic": 10}}], 20)
        self.assertEqual(len(res["top"]), 10)
        self.assertEqual(res["duplicates_dropped"], 10)
        self.assertEqual(res["pages_fetched"], 2)

    def test_second_page_not_fetched_after_first_page_error_or_short(self):
        seen = []

        def search(session, user, key, q, query_cfg=None, top_n=20, page=1):
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
        self.assertEqual(sorted(seen), [("короткая", 1), ("сбой", 1)])
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

    def test_pages_missing(self):
        c = cfg(pages=2)
        full9 = {"top": [{}] * 9, "pages_fetched": 1}
        self.assertEqual(self.sg.pages_missing(full9, c), 1)     # докачать 2-ю
        short = {"top": [{}] * 3, "pages_fetched": 1}
        self.assertEqual(self.sg.pages_missing(short, c), 0)     # глубина исчерпана
        done = {"top": [{}] * 18, "pages_fetched": 2}
        self.assertEqual(self.sg.pages_missing(done, c), 0)
        partial = {"top": [{}] * 9, "pages_fetched": 2, "partial_error": "500"}
        self.assertEqual(self.sg.pages_missing(partial, c), 1)   # повторить 2-ю
        self.assertEqual(self.sg.pages_missing(full9, cfg(pages=1)), 0)

    def test_second_page_topped_up_over_existing_row(self):
        """Строка с одной страницей из прежнего прогона получает вторую
        страницу без повторной оплаты первой (пересбор 03.09.2026)."""
        c = cfg(pages=2, daily_cap=10, monthly_cap=10)
        self.sg.SERP_DIR.mkdir(parents=True, exist_ok=True)
        prior = {"date": DATE, "query": "купить figma", "engine": "google",
                 "region": "2643", "loc": 2643, "series": "google_ru",
                 "found": 100, "pages_fetched": 1, "blocks": {"organic": 9},
                 "top": [{"domain": f"a{i}.ru", "url": f"https://a{i}.ru/",
                          "title": ""} for i in range(9)]}
        self.sg.snapshot_path(DATE).write_text(
            json.dumps(prior, ensure_ascii=False) + "\n", encoding="utf-8")
        seen = []

        def search(session, user, key, q, query_cfg=None, top_n=20, page=1):
            seen.append((q, page))
            return {"found": 100, "blocks": {"organic": 10},
                    "top": [{"domain": f"b{i}.ru", "url": f"https://b{i}.ru/",
                             "title": ""} for i in range(10)]}

        with mock.patch.object(self.sg.xmlriver, "search_google", search), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"balance_rub": 100.0}):
            res = self.sg.run(DATE, ["купить figma"], c, "u", "k", force=True)
        self.assertEqual(seen, [("купить figma", 2)])     # только вторая
        self.assertEqual((res["calls"], res["topped_up"], res["reused"]), (1, 1, 0))
        row = json.loads(pathlib.Path(res["out"]).read_text(encoding="utf-8")
                         .splitlines()[0])
        self.assertEqual(len(row["top"]), 19)
        self.assertEqual(row["top"][9]["domain"], "b0.ru")
        self.assertEqual(row["pages_fetched"], 2)
        # журнал: одна строка со страницей 2
        lines = [json.loads(l) for l in self.sg.ledger_path(self.date)
                 .read_text(encoding="utf-8").splitlines()]
        self.assertEqual([l["page"] for l in lines], [2])

    def test_nine_results_still_fetch_second_page(self):
        """Первая страница из 9 органических — полная, вторая нужна."""
        seen = []

        def search(session, user, key, q, query_cfg=None, top_n=20, page=1):
            seen.append(page)
            return {"found": 100, "blocks": {},
                    "top": [{"domain": f"p{page}-{i}.ru",
                             "url": f"https://p{page}-{i}.ru/", "title": ""}
                            for i in range(9)]}

        with mock.patch.object(self.sg.xmlriver, "search_google", search), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"error": "x"}):
            res = self.sg.run(DATE, ["q"], cfg(pages=2, daily_cap=10,
                                               monthly_cap=10), "u", "k")
        self.assertEqual(seen, [1, 2])
        self.assertEqual(res["calls"], 2)

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


class TestResume(Base):
    """Докачка: собранное за дату повторно не оплачивается."""

    def _rows(self, res):
        return {json.loads(l)["query"]: json.loads(l) for l in
                pathlib.Path(res["out"]).read_text(encoding="utf-8").splitlines()}

    def test_rows_carry_provenance(self):
        with mock.patch.object(self.sg.xmlriver, "search_google",
                               self.fake_search({})), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"balance_rub": 100.0}):
            res = self.sg.run(DATE, ["купить figma"], cfg(), "u", "k")
        row = self._rows(res)["купить figma"]
        self.assertEqual(row["provider"], "xmlriver")
        self.assertEqual(row["series"], "google_ru")
        self.assertEqual(row["device"], "desktop")
        self.assertEqual(row["collector_version"], self.sg.COLLECTOR_VERSION)

    def test_second_run_same_day_reuses_and_fetches_only_missing(self):
        # Сборщик многопоточный: порядок вызовов между ключами не задан,
        # поэтому считаем вызовы по ключу, а не сверяем последовательность.
        calls: dict[str, int] = {}

        def search(session, user, key, q, query_cfg=None, top_n=20, page=0):
            calls[q] = calls.get(q, 0) + 1
            if q == "сбой" and calls[q] == 1:
                return {"error": "HTTP 500"}
            return {"found": 1, "top": [{"domain": "a.ru", "url": "", "title": q}],
                    "blocks": {}}

        with mock.patch.object(self.sg.xmlriver, "search_google", search), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"balance_rub": 100.0}):
            first = self.sg.run(DATE, ["купить figma", "сбой"], cfg(), "u", "k")
            self.assertEqual((first["ok"], first["failed"]), (1, 1))
            # повторный запуск: figma уже есть, «сбой» докачивается, «новый» новый
            second = self.sg.run(DATE, ["купить figma", "сбой", "новый"],
                                 cfg(), "u", "k", force=True)
        self.assertEqual(calls, {"купить figma": 1, "сбой": 2, "новый": 1})
        self.assertEqual(second["reused"], 1)
        self.assertEqual(second["requested"], 2)
        self.assertEqual(second["calls"], 2)
        rows = self._rows(second)
        self.assertEqual(set(rows), {"купить figma", "сбой", "новый"})
        self.assertNotIn("error", rows["сбой"])
        # журнал вызовов — только фактические вызовы: 2 + 2
        self.assertEqual(self.sg.month_spent(self.date), 4)

    def test_empty_result_is_reused_not_refetched(self):
        """Пустая выдача без ошибки — полный замер: докачка за неё не платит."""
        calls: dict[str, int] = {}

        def search(session, user, key, q, query_cfg=None, top_n=20, page=0):
            calls[q] = calls.get(q, 0) + 1
            return {"found": 0, "top": [], "blocks": {}}

        with mock.patch.object(self.sg.xmlriver, "search_google", search), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"balance_rub": 100.0}):
            self.sg.run(DATE, ["пусто"], cfg(), "u", "k")
            second = self.sg.run(DATE, ["пусто"], cfg(), "u", "k", force=True)
        self.assertEqual(calls, {"пусто": 1})
        self.assertEqual(second["reused"], 1)

    def test_full_reuse_costs_nothing_and_is_success(self):
        with mock.patch.object(self.sg.xmlriver, "search_google",
                               self.fake_search({})), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"balance_rub": 100.0}):
            self.sg.run(DATE, ["q1", "q2"], cfg(), "u", "k")
        with mock.patch.object(self.sg.xmlriver, "search_google",
                               side_effect=AssertionError("платный вызов")), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"balance_rub": 100.0}):
            res = self.sg.run(DATE, ["q1", "q2"], cfg(), "u", "k", force=True)
        self.assertEqual((res["reused"], res["requested"], res["calls"]), (2, 0, 0))
        self.assertEqual(res["cost_rub"], 0)
        self.assertNotIn("error", res)
        # потолок не мешает докачке нулевого объёма
        runs = [json.loads(l) for l in
                (self.sg.LEDGER_DIR / self.sg.RUNS_FILE_NAME)
                .read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[-1]["reused"], 2)
        self.assertEqual(runs[-1]["calls"], 0)
        self.assertEqual(runs[0]["cost_rub"], 0.05)   # 2 вызова × 25 ₽/1000

    def test_refetch_ignores_ready_rows(self):
        with mock.patch.object(self.sg.xmlriver, "search_google",
                               self.fake_search({})), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"balance_rub": 100.0}):
            self.sg.run(DATE, ["q1"], cfg(), "u", "k")
            res = self.sg.run(DATE, ["q1"], cfg(), "u", "k", force=True,
                              refetch=True)
        self.assertEqual((res["reused"], res["requested"]), (0, 1))

    def test_other_series_or_loc_is_not_reused(self):
        with mock.patch.object(self.sg.xmlriver, "search_google",
                               self.fake_search({})), \
                mock.patch.object(self.sg.xmlriver, "get_balance",
                                  lambda s, u, k: {"balance_rub": 100.0}):
            self.sg.run(DATE, ["q1"], cfg(), "u", "k")
            moscow = cfg(query={"loc": 1011969, "device": "desktop"},
                         series="google_msk")
            res = self.sg.run(DATE, ["q1"], moscow, "u", "k", force=True)
        self.assertEqual((res["reused"], res["requested"]), (0, 1))


if __name__ == "__main__":
    unittest.main()
