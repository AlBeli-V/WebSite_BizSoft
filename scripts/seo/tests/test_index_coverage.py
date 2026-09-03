#!/usr/bin/env python3
"""Сенсор покрытия индекса: URL Inspection по инвентарю и выборки Вебмастера.

Проверяется договор с потребителями: квота прогона соблюдается, неинспектированные
URL наследуют прежний статус с пометкой, ошибка квоты останавливает обход, а
тело ошибки не сохраняется как данные; у Яндекса страница считается
исключённой только по последнему событию в окне.
"""

import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # inventory → pairs
import mocks  # noqa: E402
from mocks import FakeRequests, FakeResponse  # noqa: E402

DATE = "2026-09-03"
SITE = "https://biz-soft.pro"


def inspection(state, crawl="2026-08-21T20:15:46Z"):
    return FakeResponse(200, {"inspectionResult": {"indexStatusResult": {
        "coverageState": state, "verdict": "PASS" if "indexed" in state else "NEUTRAL",
        "lastCrawlTime": crawl}}})


class TestGoogleInspection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = mock.patch.dict(os.environ, {"GSC_SERVICE_ACCOUNT_JSON": "{}"})
        env.start()
        cls.addClassCleanup(env.stop)
        cls.ic = mocks.load("index_coverage")

    def run_inspect(self, paths, prev, inspect_responses, max_inspect=1800, workers=1):
        routes = {
            "/webmasters/v3/sites": FakeResponse(200, {"siteEntry": [
                {"siteUrl": "sc-domain:biz-soft.pro"}]}),
            "urlInspection": list(inspect_responses),
        }
        with mock.patch.dict(sys.modules, mocks.fake_google_modules()), \
                mock.patch.object(self.ic, "requests", FakeRequests(routes)):
            return self.ic.inspect_google(paths, prev, DATE,
                                          max_inspect=max_inspect, workers=workers)

    def test_statuses_recorded(self):
        out = self.run_inspect(["/", "/product/a"], {},
                               [inspection("Submitted and indexed"),
                                inspection("URL is unknown to Google", crawl=None)])
        self.assertNotIn("error", out)
        self.assertEqual(out["inspected"], 2)
        self.assertEqual(out["pages"]["/"]["coverage_state"], "Submitted and indexed")
        self.assertEqual(out["pages"]["/product/a"]["inspected_at"], DATE)
        self.assertEqual(out["site_url"], "sc-domain:biz-soft.pro")

    def test_quota_order_and_inheritance(self):
        """Без статуса — первыми; за квотой — прежний статус с пометкой."""
        prev = {"/old": {"coverage_state": "Submitted and indexed",
                         "inspected_at": "2026-09-01"},
                "/older": {"coverage_state": "Crawled - currently not indexed",
                           "inspected_at": "2026-08-25"}}
        out = self.run_inspect(["/old", "/older", "/new"], prev,
                               [inspection("URL is unknown to Google"),
                                inspection("Submitted and indexed")],
                               max_inspect=2)
        self.assertEqual(out["inspected"], 2)
        # /new (без статуса) и /older (самая давняя инспекция) ушли в API,
        # /old унаследовал вчерашний статус.
        self.assertEqual(out["pages"]["/new"]["coverage_state"], "URL is unknown to Google")
        self.assertEqual(out["pages"]["/older"]["inspected_at"], DATE)
        self.assertEqual(out["pages"]["/old"]["stale_from"], "2026-09-01")
        self.assertEqual(out["inherited"], 1)

    def test_quota_exhausted_stops_and_keeps_partial(self):
        out = self.run_inspect(["/a", "/b", "/c"], {},
                               [inspection("Submitted and indexed"),
                                FakeResponse(429, text="Quota exceeded")])
        self.assertNotIn("error", out)               # частичный срез — данные
        self.assertEqual(out["inspected"], 1)
        self.assertIsNone(out["pages"]["/b"]["coverage_state"])
        self.assertIsNone(out["pages"]["/c"]["inspected_at"])
        self.assertEqual(out["without_status"], 2)
        self.assertIn("HTTP 429", out["errors"][0])

    def test_parallel_workers_collect_all(self):
        """Потоки не теряют и не дублируют результаты."""
        paths = [f"/product/p{i}" for i in range(12)]
        out = self.run_inspect(paths, {}, [inspection("Submitted and indexed")] * 12,
                               workers=4)
        self.assertEqual(out["inspected"], 12)
        self.assertEqual(set(out["pages"]), set(paths))
        self.assertTrue(all(p["inspected_at"] == DATE for p in out["pages"].values()))

    def test_expired_token_is_refreshed_and_request_retried(self):
        """HTTP 401 — протухший токен, а не квота: обновить и повторить."""
        out = self.run_inspect(["/a", "/b"], {},
                               [FakeResponse(401, text="UNAUTHENTICATED"),
                                inspection("Submitted and indexed"),
                                inspection("URL is unknown to Google")])
        self.assertNotIn("error", out)
        self.assertEqual(out["inspected"], 2)
        self.assertNotIn("errors", out)
        self.assertEqual(out["pages"]["/a"]["coverage_state"], "Submitted and indexed")

    def test_no_inspection_at_all_is_error(self):
        out = self.run_inspect(["/a"], {}, [FakeResponse(403, text="Forbidden")])
        self.assertIn("error", out)
        self.assertIn("HTTP 403", out["error"])

    def test_site_missing_is_error_not_data(self):
        routes = {"/webmasters/v3/sites": FakeResponse(200, {"siteEntry": []})}
        with mock.patch.dict(sys.modules, mocks.fake_google_modules()), \
                mock.patch.object(self.ic, "requests", FakeRequests(routes)):
            out = self.ic.inspect_google(["/"], {}, DATE, workers=1)
        self.assertIn("не найден", out["error"])
        self.assertEqual(out["pages"], {})


class TestYandexPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = mock.patch.dict(os.environ, {"YANDEX_WEBMASTER_TOKEN": "t"})
        env.start()
        cls.addClassCleanup(env.stop)
        cls.ic = mocks.load("index_coverage")

    def collect(self, **overrides):
        routes = {
            "in-search/samples": FakeResponse(200, {"count": 2, "samples": [
                {"url": SITE + "/", "title": "BIZSoft"},
                {"url": SITE + "/product/a", "title": "A"}]}),
            "events/samples": FakeResponse(200, {"count": 3, "samples": [
                {"url": SITE + "/product/b", "event_date": "2026-08-20T00:00:00",
                 "event": "REMOVED_FROM_SEARCH", "excluded_url_status": "LOW_QUALITY"},
                {"url": SITE + "/product/c", "event_date": "2026-08-10T00:00:00",
                 "event": "REMOVED_FROM_SEARCH", "excluded_url_status": "DUPLICATE"},
                {"url": SITE + "/product/c", "event_date": "2026-08-25T00:00:00",
                 "event": "APPEARED_IN_SEARCH"}]}),
            "/hosts": FakeResponse(200, {"hosts": [{"host_id": "https:biz-soft.pro:443"}]}),
            "/user": FakeResponse(200, {"user_id": 7}),
        }
        routes.update(overrides)
        with mock.patch.object(self.ic, "requests", FakeRequests(routes)):
            return self.ic.collect_yandex_index(DATE)

    def test_in_search_and_last_event_wins(self):
        out = self.collect()
        self.assertNotIn("error", out)
        self.assertEqual(out["in_search"], ["/", "/product/a"])
        self.assertEqual(out["in_search_count"], 2)
        self.assertEqual(out["excluded"]["/product/b"]["status"], "LOW_QUALITY")
        self.assertNotIn("/product/c", out["excluded"])   # вернулась в поиск позже
        self.assertEqual(out["window"]["to"], DATE)

    def test_in_search_failure_is_error(self):
        out = self.collect(**{"in-search/samples": FakeResponse(500, text="boom")})
        self.assertIn("in-search/samples: HTTP 500", out["error"])
        self.assertNotIn("in_search", out)

    def test_events_failure_is_partial(self):
        out = self.collect(**{"events/samples": FakeResponse(500, text="boom")})
        self.assertNotIn("error", out)
        self.assertEqual(out["excluded"], {})
        self.assertIn("events/samples: HTTP 500", out["errors"][0])


class TestInventoryLoadersAndClasses(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.inv = mocks.load("inventory")
        self.inv.DATA_DIR = pathlib.Path(self.tmp.name)

    def test_google_class(self):
        gc = self.inv.google_class
        self.assertEqual(gc("Submitted and indexed"), "indexed")
        self.assertEqual(gc("Indexed, not submitted in sitemap"), "indexed")
        self.assertEqual(gc("URL is unknown to Google"), "unknown")
        self.assertEqual(gc("Discovered - currently not indexed"), "discovered")
        self.assertEqual(gc("Crawled - currently not indexed"), "crawled")
        self.assertEqual(gc("Excluded by ‘noindex’ tag"), "technical")
        self.assertEqual(gc("Page with redirect"), "technical")
        self.assertEqual(gc(None), "no_data")

    def test_loaders_skip_errors_and_take_latest(self):
        d = self.inv.DATA_DIR
        (d / "index-google-2026-09-03.json").write_text(json.dumps(
            {"date": "2026-09-03", "error": "квота"}), encoding="utf-8")
        (d / "index-google-2026-09-02.json").write_text(json.dumps(
            {"date": "2026-09-02", "pages": {"/": {"coverage_state": "Submitted and indexed"}}}),
            encoding="utf-8")
        g = self.inv.google_index("2026-09-03")
        self.assertEqual(g["as_of"], "2026-09-02")
        self.assertIn("/", g["pages"])
        self.assertIsNone(self.inv.yandex_index("2026-09-03"))
        (d / "index-yandex-2026-09-03.json").write_text(json.dumps(
            {"date": "2026-09-03", "in_search": ["/"], "excluded": {}}), encoding="utf-8")
        self.assertEqual(self.inv.yandex_index("2026-09-03")["in_search"], ["/"])

    def test_reason_label_falls_back_to_code(self):
        self.assertEqual(self.inv.yandex_reason_label("LOW_QUALITY"),
                         "малоценная или маловостребованная")
        self.assertEqual(self.inv.yandex_reason_label("NEW_CODE"), "NEW_CODE")
        self.assertEqual(self.inv.yandex_reason_label(None), "причина не зафиксирована")


if __name__ == "__main__":
    unittest.main()
