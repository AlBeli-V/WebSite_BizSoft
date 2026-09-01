#!/usr/bin/env python3
"""Сборщики GSC, Метрики и GA4 на едином разборе api_json.

То же правило, что у Вебмастера: тело ошибки никогда не сохраняется как
данные — любой сбой (не-2xx, сеть/таймаут, не-JSON) превращается в
{'error': ...}, которое snapshot читает как «источник → нет данных».
"""

import os
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402
from mocks import FakeRequests, FakeResponse  # noqa: E402

DATE = "2026-08-25"


def stat_rows(name="Search engine traffic"):
    return {"data": [{"dimensions": [{"name": name}], "metrics": [5, 4, 10.0, 2.0, 1]}],
            "totals": [9, 7, 12.0, 2.1, 2]}


class TestCollectMetrika(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Переменные окружения — только на время этих тестов: глобальный токен
        # заставил бы соседние тесты (goals_sync) считать, что доступ есть.
        env = mock.patch.dict(os.environ, {"YANDEX_METRIKA_TOKEN": "test-token",
                                           "YANDEX_METRIKA_COUNTER_ID": "110206070"})
        env.start()
        cls.addClassCleanup(env.stop)
        cls.c = mocks.load("collect")
        cls.s = mocks.load("snapshot")

    def routes(self, goals=None, stat=None):
        return {
            "/goals": goals or FakeResponse(200, {"goals": [{"id": 1, "name": "x",
                                                             "type": "action"}]}),
            # Четыре запроса бьют в один эндпоинт /stat/v1/data — очередь
            # ответов в порядке traffic_sources, organic_by_engine,
            # organic_landing_pages, organic_goal_reaches (разбивка целей,
            # добавлена 01.09.2026 по вопросу руководителя).
            "stat/v1/data": stat if stat is not None else [
                FakeResponse(200, stat_rows()),
                FakeResponse(200, stat_rows("Яндекс")),
                FakeResponse(200, {"data": [], "totals": [0, 0, 0]}),
                FakeResponse(200, {"data": [], "totals": [7]}),
                # direct_attribution (этап B): первая дименсия-кандидат отвечает.
                FakeResponse(200, {"data": [
                    {"dimensions": [{"name": "Claude Code — для команд разработки"}],
                     "metrics": [10, 4, 1, 0]}]}),
            ],
        }

    def collect(self, **kw):
        with mock.patch.object(self.c, "requests", FakeRequests(self.routes(**kw))):
            return self.c.collect_metrika()

    def test_happy_path(self):
        out = self.collect()
        self.assertNotIn("error", out)
        self.assertEqual(len(out["goals"]), 1)
        self.assertIn("data", out["traffic_sources"])

    def test_goals_error_is_state_not_data(self):
        out = self.collect(goals=FakeResponse(403, text="Forbidden"))
        self.assertIn("HTTP 403", out["goals"]["error"])
        an = self.s.build_analytics_safe(out, None, DATE)
        self.assertFalse(an["metrika"]["available"])
        self.assertIn("goals", an["metrika"]["error"])

    def test_stat_timeout_becomes_error_state(self):
        out = self.collect(stat=[FakeRequests.Timeout("timed out"),
                                 FakeResponse(200, stat_rows("Яндекс")),
                                 FakeResponse(200, {"data": [], "totals": [0, 0, 0]}),
                                 FakeResponse(200, {"data": [], "totals": [7]}),
                                 FakeResponse(200, {"data": []})])
        self.assertIn("Timeout", out["traffic_sources"]["error"])
        an = self.s.build_analytics_safe(out, None, DATE)
        self.assertFalse(an["metrika"]["available"])
        self.assertIn("traffic_sources", an["metrika"]["error"])

    def test_invalid_json_slice(self):
        out = self.collect(stat=[FakeResponse(200, None, text="<html>"),
                                 FakeResponse(200, stat_rows("Яндекс")),
                                 FakeResponse(200, {"data": [], "totals": [0, 0, 0]}),
                                 FakeResponse(200, {"data": [], "totals": [7]}),
                                 FakeResponse(200, {"data": []})])
        self.assertIn("не является JSON", out["traffic_sources"]["error"])

    def test_разбивка_целей_собирается_по_достижениям(self):
        out = self.collect()
        self.assertEqual(out["organic_goal_reaches"], {"1": 7})

    def test_связка_директа_пишется_с_дименсией_и_строками(self):
        out = self.collect()
        att = out["direct_attribution"]
        self.assertEqual(att["dimension"], "ym:s:lastDirectBannerGroup")
        self.assertEqual(att["rows"][0]["visits"], 10)


class TestCollectGscGa4(unittest.TestCase):
    """GSC и GA4: google-auth подменяется, сеть — FakeRequests."""

    @classmethod
    def setUpClass(cls):
        env = mock.patch.dict(os.environ, {"GSC_SERVICE_ACCOUNT_JSON": "{}",
                                           "GA4_PROPERTY_ID": "543500233"})
        env.start()
        cls.addClassCleanup(env.stop)
        cls.c = mocks.load("collect")
        cls.s = mocks.load("snapshot")

    def collect_gsc(self, routes):
        with mock.patch.dict(sys.modules, mocks.fake_google_modules()), \
                mock.patch.object(self.c, "requests", FakeRequests(routes)):
            return self.c.collect_gsc()

    def collect_ga4(self, routes):
        with mock.patch.dict(sys.modules, mocks.fake_google_modules()), \
                mock.patch.object(self.c, "requests", FakeRequests(routes)):
            return self.c.collect_ga4()

    def gsc_routes(self, analytics=None):
        rows = {"rows": [{"keys": ["2026-08-20"], "impressions": 3, "clicks": 0,
                          "position": 20.0}]}
        pair_rows = {"rows": [{"keys": ["запрос", "https://biz-soft.pro/p/",
                                        "2026-08-20"],
                               "impressions": 3, "clicks": 0, "position": 12.0}]}
        # Очередь на один эндпоинт: три разреза письма (date, query, page),
        # затем пары «запрос × страница × день».
        return {
            "searchAnalytics/query": analytics if analytics is not None else [
                FakeResponse(200, rows), FakeResponse(200, rows),
                FakeResponse(200, rows), FakeResponse(200, pair_rows)],
            "/sites": FakeResponse(200, {"siteEntry": [
                {"siteUrl": "sc-domain:biz-soft.pro"}]}),
        }

    def test_gsc_happy_path(self):
        out = self.collect_gsc(self.gsc_routes())
        self.assertNotIn("error", out)
        self.assertIn("rows", out["analytics"]["date"])
        self.assertEqual(out["pairs"]["fetched"], 1)
        self.assertEqual(out["pairs"]["dimensions"], ["query", "page", "date"])

    def test_gsc_one_slice_error_is_partial(self):
        out = self.collect_gsc(self.gsc_routes(analytics=[
            FakeResponse(200, {"rows": []}),
            FakeResponse(500, text="boom"),
            FakeResponse(200, {"rows": []}),
            FakeResponse(200, {"rows": []})]))
        self.assertNotIn("error", out)                       # не все срезы упали
        self.assertIn("HTTP 500", out["analytics"]["query"]["error"])

    def test_gsc_all_slices_error_is_source_error(self):
        bad = [FakeResponse(500, text="boom")] * 4
        out = self.collect_gsc(self.gsc_routes(analytics=bad))
        self.assertIn("все разрезы", out["error"])

    def test_gsc_pairs_paginate_until_short_page(self):
        """Пары забираются страницами startRow, пока страница полная."""
        full = {"rows": [{"keys": [f"q{i}", "https://biz-soft.pro/p/",
                                   "2026-08-20"],
                          "impressions": 1, "clicks": 0, "position": 15.0}
                         for i in range(self.c.PAIRS_PAGE_LIMIT)]}
        tail = {"rows": [{"keys": ["хвост", "https://biz-soft.pro/p/",
                                   "2026-08-20"],
                          "impressions": 1, "clicks": 0, "position": 15.0}]}
        rows = {"rows": [{"keys": ["2026-08-20"], "impressions": 3, "clicks": 0,
                          "position": 20.0}]}
        out = self.collect_gsc(self.gsc_routes(analytics=[
            FakeResponse(200, rows), FakeResponse(200, rows), FakeResponse(200, rows),
            FakeResponse(200, full), FakeResponse(200, tail)]))
        self.assertEqual(out["pairs"]["fetched"], self.c.PAIRS_PAGE_LIMIT + 1)
        self.assertFalse(out["pairs"]["truncated"])

    def test_gsc_pairs_error_does_not_close_source(self):
        """Сбой вспомогательного сенсора пар не закрывает разрезы письма."""
        rows = {"rows": [{"keys": ["2026-08-20"], "impressions": 3, "clicks": 0,
                          "position": 20.0}]}
        out = self.collect_gsc(self.gsc_routes(analytics=[
            FakeResponse(200, rows), FakeResponse(200, rows), FakeResponse(200, rows),
            FakeResponse(500, text="boom")]))
        self.assertNotIn("error", out)
        self.assertIn("HTTP 500", out["pairs"]["error"])
        self.assertEqual(out["pairs"]["rows"], [])
        # Снимок письма собирается как обычно.
        snap = self.s.build_safe("google_search_console", self.s.build_google, out, None)
        self.assertTrue(snap["available"])

    def test_gsc_sites_invalid_json(self):
        routes = self.gsc_routes()
        routes["/sites"] = FakeResponse(200, None, text="<html>")
        out = self.collect_gsc(routes)
        self.assertIn("не является JSON", out["error"])

    def test_ga4_slice_error_reaches_snapshot_as_unavailable(self):
        ok = FakeResponse(200, {"rows": [{"dimensionValues": [{"value": "Direct"}],
                                          "metricValues": [{"value": "1"},
                                                           {"value": "1"},
                                                           {"value": "0"}]}]})
        out = self.collect_ga4({"runReport": [FakeResponse(429, text="quota"),
                                              ok, ok, ok]})
        self.assertIn("HTTP 429", out["channels"]["error"])
        an = self.s.build_analytics_safe(None, out, DATE)
        self.assertFalse(an["ga4"]["available"])
        self.assertIn("channels", an["ga4"]["error"])


if __name__ == "__main__":
    unittest.main()
