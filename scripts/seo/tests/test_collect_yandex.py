#!/usr/bin/env python3
"""collect_yandex: каждый вызов API защищён одинаково.

Правило: тело ошибки никогда не сохраняется как данные. Любое из состояний —
не-2xx, сетевой сбой/таймаут, не-JSON, ошибка в теле формально успешного
ответа — превращается в поле error, которое snapshot.py читает как
«источник → нет данных», а quality.py — как SOURCE_UNAVAILABLE.
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


def routes(**overrides):
    """Полностью исправный Вебмастер; отдельные ответы подменяются по имени.

    Порядок ключей важен: 'summary' и 'popular' специфичнее, чем '/hosts' и
    '/user', поэтому идут первыми.
    """
    base = {
        # 'search-urls/popular' обязан стоять раньше 'popular': оба метода
        # заканчиваются одним словом, а выигрывает первый совпавший ключ.
        "search-urls/popular": FakeResponse(200, {
            "urls": [{"url": "https://biz-soft.pro/product/chatgpt-business",
                      "indicators": {"TOTAL_SHOWS": 40, "TOTAL_CLICKS": 2}}],
            "count": 1, "date_from": "2026-08-11", "date_to": "2026-08-25"}),
        "summary": FakeResponse(200, {"searchable_pages_count": 50,
                                      "excluded_pages_count": 5, "sqi": 10}),
        "popular": FakeResponse(200, {
            "queries": [{"query_text": "купить canva",
                         "indicators": {"TOTAL_SHOWS": 12, "TOTAL_CLICKS": 1,
                                        "AVG_SHOW_POSITION": 4.2}}],
            "count": 1, "date_from": "2026-08-11", "date_to": "2026-08-25"}),
        "/hosts": FakeResponse(200, {"hosts": [{"host_id": "https:biz-soft.pro:443"}]}),
        "/user": FakeResponse(200, {"user_id": 7}),
    }
    base.update(overrides)
    return base


class TestCollectYandex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = mock.patch.dict(os.environ, {"YANDEX_WEBMASTER_TOKEN": "test-token"})
        env.start()
        cls.addClassCleanup(env.stop)
        cls.c = mocks.load("collect")
        cls.s = mocks.load("snapshot")

    def collect(self, **overrides):
        with mock.patch.object(self.c, "requests", FakeRequests(routes(**overrides))):
            return self.c.collect_yandex()

    def test_happy_path(self):
        out = self.collect()
        self.assertNotIn("error", out)
        self.assertEqual(out["summary"]["searchable_pages_count"], 50)
        self.assertEqual(out["popular_queries"]["fetched"], 1)
        self.assertEqual(out["popular_urls"]["fetched"], 1)
        self.assertEqual(out["popular_urls"]["urls"][0]["indicators"]["TOTAL_SHOWS"], 40)
        self.assertIn("window", out)

    def test_requested_window_recorded_even_on_failure(self):
        out = self.collect(**{"/user": FakeResponse(500, text="boom")})
        self.assertIn("window", out)
        self.assertIn("/user: HTTP 500", out["error"])

    def test_summary_http_error_is_not_data(self):
        out = self.collect(summary=FakeResponse(403, text="Forbidden"))
        self.assertEqual(set(out["summary"]), {"error"})
        self.assertIn("HTTP 403", out["summary"]["error"])
        # Остальные срезы при этом собираются: сбой одного вызова локален.
        self.assertEqual(out["popular_queries"]["fetched"], 1)
        # Snapshot читает такой срез как «источник недоступен», а не как пустоту.
        block = self.s.build_yandex(out, None, DATE)
        self.assertFalse(block["available"])
        self.assertIn("summary", block["error"])

    def test_summary_invalid_json(self):
        out = self.collect(summary=FakeResponse(200, None, text="<html>oops</html>"))
        self.assertIn("не является JSON", out["summary"]["error"])

    def test_summary_error_in_body_of_2xx(self):
        out = self.collect(summary=FakeResponse(200, {"error_message": "backend down"}))
        self.assertIn("backend down", out["summary"]["error"])

    def test_popular_timeout_becomes_error_state(self):
        out = self.collect(popular=FakeRequests.Timeout("timed out"))
        self.assertIn("Timeout", out["popular_queries"]["error"])
        self.assertEqual(out["popular_queries"]["queries"], [])
        block = self.s.build_yandex(out, None, DATE)
        self.assertFalse(block["available"])
        # Период известен из запрошенного окна даже при сбое среза.
        self.assertEqual(block["source"]["current_period_start"], out["window"]["from"])
        self.assertEqual(block["source"]["current_period_end"], out["window"]["to"])

    def test_zero_sqi_is_absence_not_a_score(self):
        """Ноль ИКС от API — «не определён», а не оценка качества в ноль."""
        out = self.collect(summary=FakeResponse(200, {
            "searchable_pages_count": 416, "excluded_pages_count": 869,
            "sqi": 0}))
        block = self.s.build_yandex(out, None, DATE)
        self.assertIsNone(block["indexation"]["sqi"])
        # Остальные поля сводки при этом читаются как обычно.
        self.assertEqual(block["indexation"]["indexed_urls"], 416)

    def test_popular_urls_failure_is_local(self):
        """Сбой разреза по страницам не отменяет показы и клики по хосту."""
        out = self.collect(**{"search-urls/popular": FakeResponse(500, text="boom")})
        self.assertIn("HTTP 500", out["popular_urls"]["error"])
        self.assertEqual(out["popular_urls"]["urls"], [])
        self.assertEqual(out["popular_queries"]["fetched"], 1)
        block = self.s.build_yandex(out, None, DATE)
        self.assertTrue(block["available"])

    def test_popular_urls_unexpected_shape_is_error_not_empty(self):
        """Ответ без ключа urls — ошибка контракта, а не «показов не было»."""
        out = self.collect(**{"search-urls/popular":
                              FakeResponse(200, {"queries": [], "count": 0})})
        self.assertIn("без ключа urls", out["popular_urls"]["error"])
        self.assertEqual(out["popular_urls"]["urls"], [])

    def test_hosts_network_error(self):
        out = self.collect(**{"/hosts": FakeRequests.RequestException("conn reset")})
        self.assertIn("/hosts", out["error"])

    def test_api_json_states(self):
        cases = {
            429: FakeResponse(429, text="слишком часто"),
            404: FakeResponse(404, text="нет такого"),
        }
        for status, resp in cases.items():
            with mock.patch.object(self.c, "requests", FakeRequests({"x": resp})):
                data, err = self.c.api_json("http://x")
                self.assertIsNone(data)
                self.assertIn(f"HTTP {status}", err)
        with mock.patch.object(self.c, "requests",
                               FakeRequests({"x": FakeResponse(200, {"a": 1})})):
            data, err = self.c.api_json("http://x")
            self.assertIsNone(err)
            self.assertEqual(data, {"a": 1})


if __name__ == "__main__":
    unittest.main()
