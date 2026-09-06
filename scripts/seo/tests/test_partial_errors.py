#!/usr/bin/env python3
"""Частичные сбои источников: письмо собирается всегда, ноль не выдумывается.

Дефекты аудита REP-001 и REP-002: срез GA4 с ошибкой превращался в нулевые
сессии при available: true, а срез Метрики с ошибкой ронял snapshot целиком —
и в день сбоя письма не было вовсе. Фикстуры — фактические артефакты сбора за
2026-08-25 из ветки seo-data; сбои моделируются подменой среза на {'error': ...}
ровно в том виде, в каком их пишет collect.py.
"""

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
FIX = pathlib.Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "scripts" / "seo"))
DATE = "2026-08-25"

# Минимальная конфигурация задач: сборке письма достаточно пустого списка.
ACTIONS = {"roles": {}, "actions": []}


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / "seo" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def raw(prefix: str) -> dict:
    return json.loads((FIX / f"{prefix}-{DATE}.json").read_text(encoding="utf-8"))


def make_snap(s, yandex=None, gsc=None, metrika=None, ga4=None) -> dict:
    """Снимок из сырых выгрузок — тем же кодом, что в проде (snapshot.main)."""
    return {
        "schema_version": "test",
        "report_date": DATE,
        "generated_at": "",
        "reporting_timezone": s.TIMEZONE,
        "declared_goals": [],
        "goal_levels": {},
        "thresholds": s.THRESHOLDS,
        "yandex": s.build_yandex(yandex, None, DATE),
        "google": s.build_google(gsc, None),
        "analytics": s.build_analytics(metrika, ga4, DATE),
        "experiments": [],
        "market_demand": {"available": False, "reason": "замер не выполнялся",
                          "comparable_to_visibility": False},
        "data_revisions": [],
        "crm": {"connected": False},
        "ctr_model": {"approved": False},
    }


def build_email(r, q, snap, prev=None):
    """Полный путь письма: проверки качества → сборка блоков → HTML и текст."""
    dq = q.run_checks(snap, prev)
    b = r.assemble(snap, prev, dq, ACTIONS, None)
    html = r.html_email(b, {}, cid_mode=False)
    text = r.plain_text(b)
    return dq, b, html, text


class TestGa4PartialError(unittest.TestCase):
    """REP-001: срез channels с ошибкой не должен превращаться в ноль сессий."""

    @classmethod
    def setUpClass(cls):
        cls.s, cls.q, cls.r = load("snapshot"), load("quality"), load("report_v4")
        ga4 = raw("ga4")
        ga4["channels"] = {"error": "HTTP 500: Internal error encountered."}
        cls.snap = make_snap(cls.s, yandex=raw("yandex"), gsc=raw("gsc"),
                             metrika=raw("metrika"), ga4=ga4)
        cls.dq, cls.b, cls.html, cls.text = build_email(cls.r, cls.q, cls.snap)

    def test_ga4_is_unavailable_not_zero(self):
        ga = self.snap["analytics"]["ga4"]
        self.assertFalse(ga["available"])
        self.assertIn("channels", ga["error"])
        # Нулевых сессий в снимке нет вовсе — показатель не измерен, а не нулевой.
        self.assertNotIn("sessions_total", ga)
        self.assertNotIn("organic_sessions", ga)

    def test_period_survives_slice_error(self):
        src = self.snap["analytics"]["ga4"]["source"]
        self.assertEqual(src["status"], "error")
        self.assertEqual(src["current_period_start"], "2026-08-11")
        self.assertEqual(src["current_period_end"], "2026-08-24")

    def test_quality_names_source_and_period(self):
        f = next(f for f in self.dq["findings"]
                 if f["code"] == "SOURCE_UNAVAILABLE" and "GA4" in f["title"])
        self.assertEqual(f["level"], "critical")
        self.assertIn("ошибку", f["title"])
        self.assertIn("2026-08-11–2026-08-24", f["detail"])

    def test_email_still_builds(self):
        # Бренд в мастхеде набран как BIZ + оранжевое Soft (айдентика сайта).
        self.assertIn("Soft</span> Growth Intelligence", self.html)
        self.assertTrue(self.text.strip())

    def test_measurement_map_marks_ga4_unavailable(self):
        row = next(r for r in self.dq["measurement_map"] if r["source"] == "GA4")
        self.assertEqual(row["status"], "unavailable")
        self.assertIsNone(row["value"])


class TestMetrikaPartialError(unittest.TestCase):
    """REP-002: срез traffic_sources без ключа data не должен ронять сборку."""

    @classmethod
    def setUpClass(cls):
        cls.s, cls.q, cls.r = load("snapshot"), load("quality"), load("report_v4")
        metrika = raw("metrika")
        # Ровно та форма, что пишет collect.py при HTTP-ошибке: ключа data нет.
        metrika["traffic_sources"] = {"error": "HTTP 503: Backend unavailable"}
        cls.snap = make_snap(cls.s, yandex=raw("yandex"), gsc=raw("gsc"),
                             metrika=metrika, ga4=raw("ga4"))
        cls.dq, cls.b, cls.html, cls.text = build_email(cls.r, cls.q, cls.snap)

    def test_snapshot_builds_without_keyerror(self):
        m = self.snap["analytics"]["metrika"]
        self.assertFalse(m["available"])
        self.assertIn("traffic_sources", m["error"])

    def test_traffic_card_says_no_data(self):
        card = next(k for k in self.b["kpis"] if k["key"] == "traffic")
        self.assertEqual(card["value"], "нет данных")
        self.assertIsNone(card["delta"])
        self.assertIsNone(card["relative"])
        self.assertIn("11.08–24.08", card["period"])
        self.assertIn("ошибку", card["confidence"])

    def test_commercial_card_says_no_data(self):
        card = next(k for k in self.b["kpis"] if k["key"] == "commercial")
        self.assertEqual(card["value"], "нет данных")

    def test_sources_line_names_failure(self):
        self.assertIn("Метрика: сбой сбора", self.b["sources_line"])

    def test_email_renders_no_data_not_zero(self):
        self.assertIn("нет данных", self.html)
        self.assertIn("нет данных", self.text)

    def test_goals_slice_error_also_survives(self):
        metrika = raw("metrika")
        metrika["goals"] = {"error": "HTTP 403: Access denied"}
        an = self.s.build_analytics(metrika, None, DATE)
        self.assertFalse(an["metrika"]["available"])
        self.assertIn("goals", an["metrika"]["error"])


class TestSourceFullyUnavailable(unittest.TestCase):
    """Источник с available: false целиком: письмо собирается, дельт нет."""

    @classmethod
    def setUpClass(cls):
        cls.s, cls.q, cls.r = load("snapshot"), load("quality"), load("report_v4")
        gsc = {"date": DATE, "error": "HTTP 403: permission denied"}
        cls.snap = make_snap(cls.s, yandex=raw("yandex"), gsc=gsc,
                             metrika=raw("metrika"), ga4=raw("ga4"))
        # Предыдущий снимок с тем же сбоем: сборка не должна падать и на prev.
        cls.prev = make_snap(cls.s, yandex=raw("yandex"), gsc=gsc,
                             metrika=raw("metrika"), ga4=raw("ga4"))
        cls.dq, cls.b, cls.html, cls.text = build_email(cls.r, cls.q, cls.snap, cls.prev)

    def test_google_card_says_no_data(self):
        card = next(k for k in self.b["kpis"] if k["key"] == "google")
        self.assertEqual(card["value"], "нет данных")
        self.assertIsNone(card["delta"])
        self.assertIsNone(card["relative"])

    def test_health_is_degraded(self):
        states = {p["label"]: p["state"] for p in self.b["pills"]}
        self.assertEqual(states["ДАННЫЕ"], "degraded")

    def test_search_status_uses_remaining_sources(self):
        self.assertIn(self.r.search_status(self.snap, self.prev),
                      ("positive", "mixed", "negative", "stable"))

    def test_no_google_signal_published(self):
        self.assertFalse([s for s in self.b["signals"] if "Google" in s["metric"]])

    def test_sources_line_names_failure(self):
        self.assertIn("Google: сбой сбора", self.b["sources_line"])

    def test_missing_file_is_distinct_from_error(self):
        g = self.s.build_google(None, None)
        self.assertEqual(g["source"]["status"], "missing")
        snap = make_snap(self.s, yandex=raw("yandex"), gsc=None,
                         metrika=raw("metrika"), ga4=raw("ga4"))
        _, b, _, _ = build_email(self.r, self.q, snap)
        self.assertIn("Google: выгрузки нет", b["sources_line"])


class TestYandexPartialError(unittest.TestCase):
    """Та же болезнь у Вебмастера: сбой постраничного забора — не ноль показов."""

    @classmethod
    def setUpClass(cls):
        cls.s = load("snapshot")

    def test_popular_queries_error_means_unavailable(self):
        y = raw("yandex")
        y["popular_queries"] = {"error": "HTTP 500: internal error",
                                "queries": [], "fetched": 0, "count": 0}
        block = self.s.build_yandex(y, None, DATE)
        self.assertFalse(block["available"])
        self.assertIn("popular_queries", block["error"])
        self.assertNotIn("totals", block)


class TestStaleVsError(unittest.TestCase):
    """«Источник не обновился» и «источник вернул ошибку» — разные состояния."""

    @classmethod
    def setUpClass(cls):
        cls.r = load("report_v4")

    @staticmethod
    def _snap(available: bool, latest: str | None):
        return {"google": {"available": available,
                           "source": {"latest_event_date": latest}}}

    def test_same_latest_event_date_is_stale(self):
        snap, prev = self._snap(True, "2026-08-22"), self._snap(True, "2026-08-22")
        self.assertTrue(self.r.source_stale(snap, prev, "google"))

    def test_unavailable_source_is_not_stale(self):
        # None == None не должно объявлять сбой «данными, которые не обновились».
        snap, prev = self._snap(False, None), self._snap(False, None)
        self.assertFalse(self.r.source_stale(snap, prev, "google"))

    def test_search_status_unknown_without_any_source(self):
        empty = {"google": {"available": False}, "yandex": {"available": False}}
        self.assertEqual(self.r.search_status(empty, empty), "unknown")


if __name__ == "__main__":
    unittest.main()
