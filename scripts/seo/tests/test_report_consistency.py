#!/usr/bin/env python3
"""Непротиворечивость письма: тексты, тона и дельты следуют из данных.

Два уровня проверок:
  1. Сценарии (рост, падение, нулевая база, неполные окна, stale, сбои,
     измеренные нули) — письмо собирается и говорит ровно то, что измерено.
  2. Инварианты — общие правила, которые обязаны выполняться в любом письме:
     «нет данных» не имеет дельт, знак дельты не противоречит тону, сбой
     источника всегда виден в здоровье данных, недоказуемых слов нет.
"""

import datetime as dt
import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
FIX = pathlib.Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "scripts" / "seo"))
DATE = "2026-08-25"
MINUS = "−"    # знак минуса из textfmt.signed
ACTIONS = {"roles": {}, "actions": []}


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / "seo" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def raw(prefix: str) -> dict:
    return json.loads((FIX / f"{prefix}-{DATE}.json").read_text(encoding="utf-8"))


def days_range(n: int, end: str) -> list[str]:
    last = dt.date.fromisoformat(end)
    return [(last - dt.timedelta(days=n - 1 - i)).isoformat() for i in range(n)]


def gsc_synth(day_values, date=DATE):
    """Синтетическая выгрузка GSC: day_values — список (дата, показы, клики)."""
    rows = [{"keys": [d], "impressions": i, "clicks": c, "ctr": 0.0, "position": 25.0}
            for d, i, c in day_values]
    return {"date": date, "analytics": {"date": {"rows": rows},
                                        "query": {"rows": []},
                                        "page": {"rows": []}}}


def week_pattern(prev_per_day, last_per_day, clicks_last=0, end="2026-08-24"):
    ds = days_range(14, end)
    return ([(d, prev_per_day, 0) for d in ds[:7]]
            + [(d, last_per_day, clicks_last) for d in ds[7:]])


class Pipeline(unittest.TestCase):
    """Общий каркас: снимок из сырых выгрузок тем же кодом, что в проде."""

    @classmethod
    def setUpClass(cls):
        cls.s, cls.q, cls.r = load("snapshot"), load("quality"), load("report_v4")

    def make_snap(self, yandex=None, gsc=None, metrika=None, ga4=None):
        s = self.s
        return {
            "schema_version": "test", "report_date": DATE, "generated_at": "",
            "reporting_timezone": s.TIMEZONE,
            "declared_goals": [], "goal_levels": {},
            "thresholds": s.THRESHOLDS,
            "yandex": s.build_safe("yandex_webmaster", s.build_yandex, yandex, None, DATE),
            "google": s.build_safe("google_search_console", s.build_google, gsc, None),
            "analytics": s.build_analytics_safe(metrika, ga4, DATE),
            "experiments": [],
            "market_demand": {"available": False, "reason": "замер не выполнялся",
                              "comparable_to_visibility": False},
            "data_revisions": [],
            "crm": {"connected": False},
            "ctr_model": {"approved": False},
        }

    def build_email(self, snap, prev=None):
        dq = self.q.run_checks(snap, prev)
        b = self.r.assemble(snap, prev, dq, ACTIONS, None)
        html = self.r.html_email(b, {}, cid_mode=False)
        text = self.r.plain_text(b)
        self.assertEqual(self.invariant_errors(snap, b, html), [])
        return dq, b, html, text

    def invariant_errors(self, snap, b, html) -> list[str]:
        errs = []
        for k in b["kpis"]:
            if k["value"] == "нет данных" and (k["delta"] is not None
                                               or k.get("relative") is not None):
                errs.append(f"{k['key']}: дельта или процент при «нет данных»")
        for s_ in b["signals"]:
            if s_["delta"].startswith("+") and s_["tone"] == "negative":
                errs.append(f"{s_['metric']}: положительная дельта с тоном negative")
            if s_["delta"].startswith(MINUS) and s_["tone"] == "positive":
                errs.append(f"{s_['metric']}: отрицательная дельта с тоном positive")
        sources = [snap["yandex"], snap["google"],
                   snap["analytics"]["metrika"], snap["analytics"]["ga4"]]
        states = {p["label"]: p["state"] for p in b["pills"]}
        if any(not x.get("available") for x in sources) and states["ДАННЫЕ"] != "degraded":
            errs.append("недоступный источник, а здоровье данных не degraded")
        if "по-прежнему" in html:
            errs.append("недоказуемое «по-прежнему» в письме")
        return errs

    def snap_pair(self, gsc_cur, gsc_prev):
        """Текущий и предыдущий снимки: Google свой в каждом, остальное — фикстуры."""
        snap = self.make_snap(yandex=raw("yandex"), gsc=gsc_cur,
                              metrika=raw("metrika"), ga4=raw("ga4"))
        prev = self.make_snap(yandex=raw("yandex"), gsc=gsc_prev,
                              metrika=raw("metrika"), ga4=raw("ga4"))
        return snap, prev

    def google_signal(self, b):
        return next(s_ for s_ in b["signals"] if "Google" in s_["metric"])

    def google_card(self, b):
        return next(k for k in b["kpis"] if k["key"] == "google")


class TestGoogleSignalDirection(Pipeline):
    """Тон и текст сигнала Google следуют из знака изменения (сценарии A и B)."""

    def test_growth_is_positive(self):
        snap, prev = self.snap_pair(gsc_synth(week_pattern(10, 20)),
                                    gsc_synth(week_pattern(10, 18, end="2026-08-23")))
        _, b, html, _ = self.build_email(snap, prev)
        sig = self.google_signal(b)
        self.assertEqual(sig["tone"], "positive")
        self.assertIn("чаще", sig["meaning"])
        self.assertTrue(sig["delta"].startswith("+"))

    def test_decline_is_negative_not_positive(self):
        snap, prev = self.snap_pair(gsc_synth(week_pattern(20, 10)),
                                    gsc_synth(week_pattern(20, 12, end="2026-08-23")))
        _, b, html, _ = self.build_email(snap, prev)
        sig = self.google_signal(b)
        self.assertEqual(sig["tone"], "negative")
        self.assertIn("реже", sig["meaning"])
        self.assertNotIn("чаще", sig["meaning"])

    def test_equal_is_neutral(self):
        snap, prev = self.snap_pair(gsc_synth(week_pattern(15, 15)),
                                    gsc_synth(week_pattern(15, 14, end="2026-08-23")))
        _, b, _, _ = self.build_email(snap, prev)
        sig = self.google_signal(b)
        self.assertEqual(sig["tone"], "neutral")
        self.assertIn("не изменилось", sig["meaning"])

    def test_zero_base_says_appeared_not_infinite_growth(self):
        snap, prev = self.snap_pair(gsc_synth(week_pattern(0, 5)),
                                    gsc_synth(week_pattern(0, 4, end="2026-08-23")))
        _, b, html, _ = self.build_email(snap, prev)
        sig = self.google_signal(b)
        self.assertEqual(sig["tone"], "positive")
        self.assertIn("Появились показы", sig["meaning"])
        # Никакого процента от нулевой базы.
        self.assertIsNone(self.google_card(b)["relative"])

    def test_partial_windows_suppress_comparison(self):
        ds = days_range(10, "2026-08-24")
        snap, prev = self.snap_pair(gsc_synth([(d, 10, 0) for d in ds]),
                                    gsc_synth([(d, 9, 0) for d in days_range(10, "2026-08-23")]))
        _, b, _, _ = self.build_email(snap, prev)
        card = self.google_card(b)
        self.assertIsNone(card["delta"])
        self.assertNotIn("slope", card)
        self.assertIn("неполные", self.google_signal(b)["meaning"])

    def test_stale_source_is_not_fresh_news(self):
        same = gsc_synth(week_pattern(10, 20))
        snap, prev = self.snap_pair(same, gsc_synth(week_pattern(10, 20)))
        dq, b, _, _ = self.build_email(snap, prev)
        sig = self.google_signal(b)
        self.assertEqual(sig["tone"], "neutral")
        self.assertIn("не отдал новых данных", sig["meaning"])
        self.assertIn("не обновились", self.google_card(b)["confidence"])
        self.assertTrue(any(f["code"] == "SOURCE_NOT_UPDATED"
                            and "Google" in f["title"] for f in dq["findings"]))


class TestGoogleClicksWording(Pipeline):
    """Текст о переходах выводится из измеренных кликов, а не константой."""

    def test_clicks_present_are_reported(self):
        snap, prev = self.snap_pair(gsc_synth(week_pattern(10, 20, clicks_last=3)),
                                    gsc_synth(week_pattern(10, 18, end="2026-08-23")))
        _, b, html, text = self.build_email(snap, prev)
        card = self.google_card(b)
        self.assertIn("Переходы из Google за окно", card["interpretation"])
        for out in (html, text):
            self.assertNotIn("Переходов из Google пока нет", out)
            self.assertNotIn("по-прежнему", out)

    def test_measured_zero_clicks_say_none_yet(self):
        snap, prev = self.snap_pair(gsc_synth(week_pattern(10, 20)),
                                    gsc_synth(week_pattern(10, 18, end="2026-08-23")))
        _, b, _, _ = self.build_email(snap, prev)
        self.assertIn("Переходов из Google пока нет",
                      self.google_card(b)["interpretation"])


class TestIndexationSignal(Pipeline):
    """Текст об индексации следует из дельты и не падает на None."""

    def idx_signal(self, b):
        return next(s_ for s_ in b["signals"] if "Страницы в поиске" in s_["metric"])

    def test_growth_is_not_called_unchanged(self):
        prev_raw = raw("yandex")
        prev_raw["summary"]["searchable_pages_count"] -= 3
        snap = self.make_snap(yandex=raw("yandex"), gsc=raw("gsc"),
                              metrika=raw("metrika"), ga4=raw("ga4"))
        prev = self.make_snap(yandex=prev_raw, gsc=raw("gsc"),
                              metrika=raw("metrika"), ga4=raw("ga4"))
        _, b, _, _ = self.build_email(snap, prev)
        sig = self.idx_signal(b)
        self.assertEqual(sig["tone"], "positive")
        self.assertIn("стало больше", sig["meaning"])
        self.assertNotIn("не изменился", sig["meaning"])

    def test_equal_is_called_unchanged(self):
        snap = self.make_snap(yandex=raw("yandex"), gsc=raw("gsc"),
                              metrika=raw("metrika"), ga4=raw("ga4"))
        prev = self.make_snap(yandex=raw("yandex"), gsc=raw("gsc"),
                              metrika=raw("metrika"), ga4=raw("ga4"))
        _, b, _, _ = self.build_email(snap, prev)
        self.assertIn("не изменился", self.idx_signal(b)["meaning"])

    def test_missing_measurement_does_not_crash_or_claim(self):
        cur_raw = raw("yandex")
        del cur_raw["summary"]["searchable_pages_count"]
        snap = self.make_snap(yandex=cur_raw, gsc=raw("gsc"),
                              metrika=raw("metrika"), ga4=raw("ga4"))
        prev = self.make_snap(yandex=raw("yandex"), gsc=raw("gsc"),
                              metrika=raw("metrika"), ga4=raw("ga4"))
        _, b, _, _ = self.build_email(snap, prev)
        sig = self.idx_signal(b)
        self.assertEqual(sig["delta"], "нет данных")
        self.assertIn("не измерено", sig["meaning"])


class TestValidZero(Pipeline):
    """Сценарий J: измеренный ноль остаётся нулём, а не «нет данных»."""

    def test_zero_queries_and_zero_organic_render_as_zero(self):
        y = raw("yandex")
        y["popular_queries"] = {"queries": [], "count": 0, "fetched": 0,
                                "date_from": "2026-08-11", "date_to": "2026-08-25"}
        m = raw("metrika")
        m["traffic_sources"]["data"] = [
            r_ for r_ in m["traffic_sources"]["data"]
            if r_["dimensions"][0]["name"] != "Search engine traffic"]
        snap = self.make_snap(yandex=y, gsc=raw("gsc"), metrika=m, ga4=raw("ga4"))
        _, b, _, _ = self.build_email(snap)
        cards = {k["key"]: k for k in b["kpis"]}
        self.assertEqual(cards["yandex"]["value"], "0")
        self.assertEqual(cards["traffic"]["value"], "0")
        self.assertNotEqual(cards["yandex"]["value"], "нет данных")
        # Ноль при малой базе — с пометкой о достоверности, а не как вывод.
        self.assertIn("низкая", cards["yandex"]["confidence"])


class TestEmptySuccessAndMalformed(Pipeline):
    """EMPTY_SUCCESS и MALFORMED не публикуются нулями и не роняют письмо."""

    def test_gsc_empty_success_is_unavailable(self):
        g = {"date": DATE, "analytics": {"date": {"rows": []},
                                         "query": {"rows": []}, "page": {"rows": []}}}
        block = self.s.build_google(g, None)
        self.assertFalse(block["available"])
        self.assertIn("без строк", block["error"])

    def test_ga4_empty_channels_is_unavailable(self):
        g4 = raw("ga4")
        g4["channels"]["rows"] = []
        snap = self.make_snap(yandex=raw("yandex"), gsc=raw("gsc"),
                              metrika=raw("metrika"), ga4=g4)
        self.assertFalse(snap["analytics"]["ga4"]["available"])
        self.assertIn("channels", snap["analytics"]["ga4"]["error"])
        self.build_email(snap)

    def test_yandex_declared_but_missing_queries_is_unavailable(self):
        y = raw("yandex")
        y["popular_queries"] = {"queries": [], "count": 120, "fetched": 0,
                                "date_from": "2026-08-11", "date_to": "2026-08-25"}
        block = self.s.build_yandex(y, None, DATE)
        self.assertFalse(block["available"])
        self.assertIn("count=120", block["error"])

    def test_malformed_metrika_rows_do_not_kill_the_email(self):
        m = {"date": DATE, "counter": "110206070",
             "window": {"from": "2026-08-11", "to": "2026-08-24"},
             "goals": [],
             "traffic_sources": {"data": [{"неожиданная": "структура"}],
                                 "totals": [1, 1, 0, 0, 0]},
             "organic_landing_pages": {"data": []}}
        snap = self.make_snap(yandex=raw("yandex"), gsc=raw("gsc"),
                              metrika=m, ga4=raw("ga4"))
        self.assertFalse(snap["analytics"]["metrika"]["available"])
        self.assertIn("формат выгрузки", snap["analytics"]["metrika"]["error"])
        self.build_email(snap)

    def test_metrika_totals_without_rows_is_unavailable(self):
        m = raw("metrika")
        m["traffic_sources"]["data"] = []          # итог заявляет визиты, строк нет
        an = self.s.build_analytics_safe(m, None, DATE)
        self.assertFalse(an["metrika"]["available"])
        self.assertIn("ненулевом итоге", an["metrika"]["error"])

    def test_malformed_gsc_rows_become_unavailable(self):
        g = {"date": DATE, "analytics": {"date": {"rows": [{"keys": []}]},
                                         "query": {"rows": []}, "page": {"rows": []}}}
        block = self.s.build_safe("google_search_console", self.s.build_google, g, None)
        self.assertFalse(block["available"])
        self.assertIn("формат выгрузки", block["error"])


class TestFailureScenarios(Pipeline):
    """Сценарии C–I: письмо собирается при любом составе сбоев."""

    def test_c_google_export_missing(self):
        snap = self.make_snap(yandex=raw("yandex"), gsc=None,
                              metrika=raw("metrika"), ga4=raw("ga4"))
        _, b, _, _ = self.build_email(snap)
        self.assertIn("Google: выгрузки нет", b["sources_line"])

    def test_d_metrika_error(self):
        m = raw("metrika")
        m["traffic_sources"] = {"error": "HTTP 503: Backend unavailable"}
        snap = self.make_snap(yandex=raw("yandex"), gsc=raw("gsc"),
                              metrika=m, ga4=raw("ga4"))
        _, b, _, _ = self.build_email(snap)
        self.assertIn("Метрика: сбой сбора", b["sources_line"])

    def test_e_webmaster_403_names_period(self):
        y = {"date": DATE, "window": {"from": "2026-08-11", "to": "2026-08-25"},
             "error": "/user: HTTP 403: Forbidden"}
        snap = self.make_snap(yandex=y, gsc=raw("gsc"),
                              metrika=raw("metrika"), ga4=raw("ga4"))
        dq, b, _, _ = self.build_email(snap)
        card = next(k for k in b["kpis"] if k["key"] == "yandex")
        self.assertEqual(card["value"], "нет данных")
        self.assertEqual(card["period"], "11.08–25.08")
        f = next(f_ for f_ in dq["findings"] if f_["code"] == "SOURCE_UNAVAILABLE"
                 and "Вебмастер" in f_["title"])
        self.assertIn("2026-08-11–2026-08-25", f["detail"])

    def test_h_two_sources_down_at_once(self):
        m = raw("metrika")
        m["traffic_sources"] = {"error": "HTTP 503"}
        g4 = raw("ga4")
        g4["channels"] = {"error": "HTTP 500"}
        snap = self.make_snap(yandex=raw("yandex"), gsc=raw("gsc"), metrika=m, ga4=g4)
        _, b, html, _ = self.build_email(snap)
        states = {p["label"]: p["state"] for p in b["pills"]}
        self.assertEqual(states["ДАННЫЕ"], "degraded")

    def test_i_everything_down_still_builds_a_letter(self):
        snap = self.make_snap()
        _, b, html, text = self.build_email(snap)
        states = {p["label"]: p["state"] for p in b["pills"]}
        self.assertEqual(states["ПОИСК"], "unknown")
        self.assertEqual(states["ДАННЫЕ"], "degraded")
        for label in ("Яндекс", "Google", "Метрика"):
            self.assertIn(f"{label}: выгрузки нет", b["sources_line"])
        self.assertIn("нет данных", html)
        self.assertIn("нет данных", text)


if __name__ == "__main__":
    unittest.main()
