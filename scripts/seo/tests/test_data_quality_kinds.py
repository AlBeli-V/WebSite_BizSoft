#!/usr/bin/env python3
"""Классы находок качества данных и снятые противоречия (решения 03.09.2026).

Раздел «Качество данных» смешивал сбой дня, постоянное ограничение и
правило подсчёта в один список; статус отчёта считался по всему списку и
зелёным быть не мог. Здесь закреплено: статус — по сбоям, критический
уровень — только у сбоя, у ограничения есть условие снятия; общее окно
воронки; очищенная органика GA4; уникальные посетители по целям;
классификация исключённых URL; спрос из живого состояния Wordstat.
"""

import datetime as dt
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
FIX = pathlib.Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "scripts" / "seo"))
DATE = "2026-08-25"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / "seo" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def raw(prefix: str) -> dict:
    return json.loads((FIX / f"{prefix}-{DATE}.json").read_text(encoding="utf-8"))


def write_daily_stores(base: pathlib.Path, end: str, days: int = 21) -> None:
    """Дневные ряды всех источников: полные окна и полное общее окно."""
    dw = load("daily_windows")
    last = dt.date.fromisoformat(end)
    dates = [(last - dt.timedelta(days=i)).isoformat() for i in range(days)]
    for source, metrics in dw.METRICS.items():
        series = {m: {d: 10.0 + i for i, d in enumerate(dates)} for m in metrics}
        (base / f"{source}.json").write_text(
            json.dumps({"series": series, "updated_at": f"{end}T06:00:00+00:00"}),
            encoding="utf-8")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s, cls.q = load("snapshot"), load("quality")
        cls.dw = load("daily_windows")
        cls.tmp = tempfile.TemporaryDirectory()
        base = pathlib.Path(cls.tmp.name)
        write_daily_stores(base, DATE)
        cls.daily = cls.dw.build(DATE, base)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def make_snap(self, yandex=None, gsc=None, metrika=None, ga4=None, daily=None,
                  crm=None, market_demand=None):
        s = self.s
        return {
            "schema_version": "test", "report_date": DATE, "generated_at": "",
            "reporting_timezone": s.TIMEZONE,
            "declared_goals": [], "goal_levels": {},
            "thresholds": s.THRESHOLDS,
            "yandex": s.build_safe("yandex_webmaster", s.build_yandex,
                                   yandex or raw("yandex"), None, DATE),
            "google": s.build_safe("google_search_console", s.build_google,
                                   gsc or raw("gsc"), None),
            "analytics": s.build_analytics_safe(metrika or raw("metrika"),
                                                ga4 or raw("ga4"), DATE),
            "daily": daily if daily is not None else self.daily,
            "experiments": [],
            "market_demand": market_demand or {
                "available": False, "reason": "замер не выполнялся",
                "comparable_to_visibility": False},
            "data_revisions": [],
            "crm": crm or {"connected": False},
            "ctr_model": {"approved": False},
        }


class TestKinds(Base):
    """Каждая находка несёт класс; статус отчёта — только по сбоям."""

    def test_every_finding_has_kind_and_critical_is_incident(self):
        dq = self.q.run_checks(self.make_snap(), None)
        for f in dq["findings"]:
            self.assertIn(f["kind"], ("incident", "limit", "rule"), f["code"])
            if f["level"] == "critical":
                self.assertEqual(f["kind"], "incident", f["code"])

    def test_status_ignores_limits_and_rules(self):
        dq = self.q.run_checks(self.make_snap(), None)
        incidents = [f for f in dq["findings"] if f["kind"] == "incident"]
        self.assertEqual(incidents, [], [f["code"] for f in incidents])
        # Ограничения есть (CRM не подключена, CTR-модели нет), а статус зелёный.
        self.assertGreater(dq["counts"]["warning"], 0)
        self.assertEqual(dq["status"], "ok")
        self.assertTrue(dq["publication_rules"]["allow_green_overall_status"])
        self.assertEqual(dq["incident_counts"]["warning"], 0)

    def test_incident_turns_status_warning(self):
        snap = self.make_snap(crm={"connected": True, "revenue": None, "stale": True,
                                   "data_date": "2026-08-24", "block": {}})
        dq = self.q.run_checks(snap, None)
        codes = {f["code"]: f for f in dq["findings"]}
        self.assertEqual(codes["CRM_DATA_STALE"]["kind"], "incident")
        self.assertEqual(dq["status"], "warning")
        self.assertFalse(dq["publication_rules"]["allow_green_overall_status"])

    def test_limits_carry_lift_condition(self):
        dq = self.q.run_checks(self.make_snap(), None)
        for f in dq["findings"]:
            if f["kind"] == "limit" and f["level"] == "warning":
                self.assertTrue(f.get("lifted_when"), f["code"])

    def test_old_schema_finding_kind_by_code(self):
        self.assertEqual(self.q.finding_kind({"code": "NO_CTR_MODEL"}), "limit")
        self.assertEqual(self.q.finding_kind({"code": "SOURCE_UNAVAILABLE"}), "incident")
        self.assertEqual(self.q.finding_kind({"code": "SCOPE_QUERY_VS_PAGE"}), "rule")


class TestYandexScope(Base):
    """«Выборка 1016 из 1016» выборкой не является."""

    def test_full_fetch_is_rule_not_warning(self):
        dq = self.q.run_checks(self.make_snap(), None)
        f = next(f_ for f_ in dq["findings"] if f_["code"] == "YANDEX_SAMPLE_SCOPE")
        self.assertEqual((f["level"], f["kind"]), ("info", "rule"))
        self.assertIn("по всем", f["title"])
        self.assertNotIn("SAMPLE_TRUNCATED", {f_["code"] for f_ in dq["findings"]})
        self.assertIn("окно источника", dq["sample_ctr"]["caveat"])

    def test_truncated_fetch_stays_warning(self):
        y = raw("yandex")
        y["popular_queries"]["count"] = y["popular_queries"]["fetched"] + 200
        dq = self.q.run_checks(self.make_snap(yandex=y), None)
        codes = {f["code"]: f for f in dq["findings"]}
        self.assertEqual(codes["YANDEX_SAMPLE_SCOPE"]["level"], "warning")
        self.assertIn("SAMPLE_TRUNCATED", codes)

    def test_rolling_window_is_rule_with_daily(self):
        # Окно сравнения агрегатного пути — окно вчерашнего сырья: при том же
        # сырье оно совпадает с текущим целиком.
        snap = self.make_snap()
        snap["yandex"] = self.s.build_yandex(raw("yandex"), raw("yandex"), DATE)
        dq = self.q.run_checks(snap, self.make_snap())
        f = next(f_ for f_ in dq["findings"] if f_["code"] == "ROLLING_WINDOW_OVERLAP")
        self.assertEqual((f["level"], f["kind"]), ("info", "rule"))


class TestGoogleQueryCoverage(Base):
    def test_rule_names_share_of_impressions(self):
        dq = self.q.run_checks(self.make_snap(), None)
        f = next(f_ for f_ in dq["findings"] if f_["code"] == "SCOPE_QUERY_VS_PAGE")
        self.assertEqual(f["kind"], "rule")
        self.assertIn("покрывают", f["detail"])


class TestAlignedWindow(Base):
    """Общее окно воронки: все источники кончаются одним днём."""

    def test_aligned_ends_on_slowest_lag(self):
        a = self.daily["aligned"]
        self.assertTrue(a["available"] and a["complete"])
        end = dt.date.fromisoformat(DATE) - dt.timedelta(days=max(self.dw.LAG_DAYS.values()))
        self.assertEqual(a["current"]["to"], end.isoformat())
        for src, windows in a["sources"].items():
            for m, w in windows.items():
                self.assertEqual(w["current"]["to"], a["current"]["to"], f"{src}.{m}")
                self.assertEqual(w["previous"]["to"], a["previous"]["to"], f"{src}.{m}")
        # Свежее окно аналитики по-прежнему свежее общего.
        self.assertGreater(self.daily["metrika"]["windows"]["visits_organic"]["current"]["to"],
                           a["current"]["to"])

    def test_period_mismatch_is_rule_with_aligned_window(self):
        dq = self.q.run_checks(self.make_snap(), None)
        f = next(f_ for f_ in dq["findings"] if f_["code"] == "PERIOD_MISMATCH")
        self.assertEqual((f["level"], f["kind"]), ("info", "rule"))
        self.assertIn(self.daily["aligned"]["current"]["to"], f["effect_on_report"])
        self.assertTrue(dq["funnel"]["available"])
        self.assertEqual(dq["funnel"]["current"], self.daily["aligned"]["current"])

    def test_period_mismatch_stays_limit_without_aligned(self):
        daily = {k: v for k, v in self.daily.items() if k != "aligned"}
        dq = self.q.run_checks(self.make_snap(daily=daily), None)
        f = next(f_ for f_ in dq["findings"] if f_["code"] == "PERIOD_MISMATCH")
        self.assertEqual((f["level"], f["kind"]), ("warning", "limit"))
        self.assertFalse(dq["funnel"]["available"])


class TestGA4Clean(Base):
    """Свои визиты вычтены, Алиса — отдельный канал."""

    def test_snapshot_splits_internal_and_assistant(self):
        an = self.s.build_analytics_safe(raw("metrika"), raw("ga4"), DATE)
        ga = an["ga4"]
        self.assertEqual(ga["internal_in_organic"]["sources"], ["metrika.yandex.ru"])
        self.assertEqual(ga["ai_assistant_in_organic"]["sources"], ["alice.yandex.ru"])
        self.assertEqual(ga["organic_sessions_clean"], ga["organic_sessions"] - 7 - 2)

    def test_quality_publishes_clean_conversion(self):
        dq = self.q.run_checks(self.make_snap(), None)
        codes = {f["code"]: f for f in dq["findings"]}
        self.assertNotIn("INTERNAL_TRAFFIC_IN_ORGANIC", codes)
        self.assertEqual(codes["INTERNAL_TRAFFIC_EXCLUDED"]["kind"], "rule")
        self.assertIn("Алис", codes["INTERNAL_TRAFFIC_EXCLUDED"]["detail"])
        self.assertTrue(dq["publication_rules"]["allow_channel_conversion_claims"])
        ga_row = next(r for r in dq["measurement_map"] if r["source"] == "GA4")
        self.assertIn("без собственных визитов", ga_row["filters"])


class TestGoalUsers(Base):
    def test_users_by_key_summed(self):
        m = raw("metrika")
        m["organic_goal_users"] = {"lead_sent": 2, "click_phone": "1"}
        an = self.s.build_analytics_safe(m, raw("ga4"), DATE)
        self.assertEqual(an["metrika"]["unique_goal_users"], 3)
        self.assertEqual(an["metrika"]["goal_users_by_key"], {"lead_sent": 2, "click_phone": 1})
        dq = self.q.run_checks(self.make_snap(metrika=m), None)
        self.assertNotIn("GOAL_UNIQUENESS_UNKNOWN", {f["code"] for f in dq["findings"]})

    def test_error_or_missing_slice_is_unknown(self):
        m = raw("metrika")
        m["organic_goal_users"] = {"error": "HTTP 500"}
        an = self.s.build_analytics_safe(m, raw("ga4"), DATE)
        self.assertIsNone(an["metrika"]["unique_goal_users"])
        dq = self.q.run_checks(self.make_snap(metrika=m), None)
        f = next(f_ for f_ in dq["findings"] if f_["code"] == "GOAL_UNIQUENESS_UNKNOWN")
        self.assertEqual(f["kind"], "limit")


class TestClassifyExcluded(Base):
    """INDEX-001: причины исключения и коммерчески значимые адреса."""

    def events(self, *rows):
        return {"date_from": "2026-05-27", "date_to": DATE, "count": len(rows),
                "samples": [{"url": f"https://biz-soft.pro{p}", "event": ev,
                             "event_date": DATE, "excluded_url_status": st}
                            for p, ev, st in rows]}

    def test_no_slice_means_no_classification(self):
        out = self.s.classify_excluded(None, 50, DATE)
        self.assertIsNone(out["excluded_by_reason"])
        self.assertEqual(out["unclassified_excluded_urls"], 50)
        out = self.s.classify_excluded({"error": "HTTP 400"}, 50, DATE)
        self.assertIsNone(out["excluded_by_reason"])

    def test_expected_statuses_are_not_problems(self):
        ev = self.events(("/product/old-slug", "REMOVED_FROM_SEARCH", "REDIRECT_SEARCH"),
                         ("/product/a?x=1", "REMOVED_FROM_SEARCH", "NOT_CANONICAL"),
                         ("/product/new", "APPEARED_IN_SEARCH", None))
        out = self.s.classify_excluded(ev, 50, DATE)
        self.assertEqual(out["excluded_by_reason"], {"REDIRECT_SEARCH": 1, "NOT_CANONICAL": 1})
        self.assertEqual(out["commercial_excluded_urls"], 0)
        self.assertEqual(out["unclassified_excluded_urls"], 48)

    def test_commercial_unexpected_is_incident(self):
        ev = self.events(("/vendors/adobe", "REMOVED_FROM_SEARCH", "LOW_QUALITY"),
                         ("/blog/post", "REMOVED_FROM_SEARCH", "LOW_QUALITY"))
        y = raw("yandex")
        y["search_url_events"] = ev
        dq = self.q.run_checks(self.make_snap(yandex=y), None)
        codes = {f["code"]: f for f in dq["findings"]}
        self.assertEqual(codes["INDEXATION_COMMERCIAL_EXCLUDED"]["kind"], "incident")
        self.assertIn("/vendors/adobe", codes["INDEXATION_COMMERCIAL_EXCLUDED"]["detail"])
        self.assertEqual(codes["INDEXATION_UNCLASSIFIED"]["kind"], "limit")

    def test_classified_without_commercial_is_rule(self):
        y = raw("yandex")
        y["search_url_events"] = self.events(
            ("/product/x", "REMOVED_FROM_SEARCH", "REDIRECT_SEARCH"))
        dq = self.q.run_checks(self.make_snap(yandex=y), None)
        codes = {f["code"]: f for f in dq["findings"]}
        self.assertNotIn("INDEXATION_COMMERCIAL_EXCLUDED", codes)
        self.assertEqual(codes["INDEXATION_CLASSIFIED"]["kind"], "rule")


class TestDemandFromState(Base):
    def test_state_feeds_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            base = pathlib.Path(d)
            state = {"measured_at": "2026-08-24",
                     "coverage": {"available": True, "total_commercial_demand": 1000,
                                  "levels": {"page": 0.8}},
                     "universe": {"phrases": 100, "commercial_phrases": 20, "clusters": 5},
                     "opportunities": [
                         {"cluster": "adobe", "url": "/vendors/adobe", "commercial_demand": 500,
                          "indexed": False, "impressions": 0,
                          "top_phrases": [{"phrase": "adobe купить", "frequency": 300}]},
                         {"cluster": "zoom", "url": "/vendors/zoom", "commercial_demand": 100,
                          "indexed": True, "impressions": 50,
                          "top_phrases": [{"phrase": "zoom купить", "frequency": 90}]}]}
            (base / "intelligence-state.json").write_text(json.dumps(state), encoding="utf-8")
            (base / "2026-08-24-full-result.json").write_text("{}", encoding="utf-8")
            self.s.DEMAND_STATE = base / "intelligence-state.json"
            self.s.WORDSTAT_DIR = base
            try:
                md = self.s.build_market_demand(DATE)
            finally:
                self.s.WORDSTAT_DIR = pathlib.Path("reports/seo/wordstat")
                self.s.DEMAND_STATE = self.s.WORDSTAT_DIR / "intelligence-state.json"
        self.assertTrue(md["available"] and md["complete"])
        self.assertEqual(md["source"]["measured_at"], "2026-08-24")
        self.assertEqual(list(md["gaps"]), ["adobe"])
        self.assertEqual(md["gaps"]["adobe"][0]["impressions"], 300)
        dq = self.q.run_checks(self.make_snap(market_demand=md), None)
        codes = {f["code"] for f in dq["findings"]}
        self.assertNotIn("MARKET_DEMAND_PARTIAL", codes)
        self.assertNotIn("MARKET_DEMAND_STALE", codes)


class TestWebreportSection(Base):
    def test_three_blocks_and_counts(self):
        w = load("webreport")
        dq = self.q.run_checks(self.make_snap(), None)
        html = w._quality_section(dq)
        self.assertIn("сбоев нет", html)
        self.assertIn("Постоянные ограничения методики", html)
        self.assertIn("Правила подсчёта", html)
        self.assertIn("Снимается, когда", html)


class TestIndexDrop(Base):
    """Обвал индекса Яндекса виден отчёту, дневное дрожание — нет.

    09.09.2026 число страниц в поиске упало 650 → 455 (254 адреса вышли,
    почти все со статусом «малоценная или маловостребованная»), а отчёт
    напечатал «Страницы в поиске Яндекса 650 → 650, без изменений» и
    «ПОИСК: рост». Статус письма считался по показам, а показы — это окно
    прошлых дней, которое об индексе сегодняшнего дня ничего не знает.
    """

    def snap_with_index(self, pages, excluded=53):
        snap = self.make_snap()
        snap["yandex"]["indexation"] = dict(snap["yandex"].get("indexation") or {},
                                            indexed_urls=pages, excluded_urls=excluded)
        return snap

    def codes(self, now, was):
        dq = self.q.run_checks(self.snap_with_index(now), self.snap_with_index(was))
        return {f["code"] for f in dq["findings"]}

    def test_обвал_индекса_становится_находкой(self):
        self.assertIn("INDEXATION_DROP", self.codes(455, 650))

    def test_дневное_дрожание_находкой_не_становится(self):
        self.assertNotIn("INDEXATION_DROP", self.codes(650, 663))

    def test_рост_индекса_находкой_не_становится(self):
        self.assertNotIn("INDEXATION_DROP", self.codes(663, 650))

    def test_обвал_считается_сбоем_и_роняет_статус(self):
        dq = self.q.run_checks(self.snap_with_index(455), self.snap_with_index(650))
        drop = next(f for f in dq["findings"] if f["code"] == "INDEXATION_DROP")
        self.assertEqual(drop["kind"], self.q.KIND_INCIDENT)
        self.assertEqual(drop["level"], "warning")
        self.assertTrue(drop.get("lifted_when"))
        self.assertIn("455", drop["detail"])
        self.assertIn("650", drop["detail"])

    def test_без_предыдущего_снимка_проверка_молчит(self):
        dq = self.q.run_checks(self.snap_with_index(455), None)
        self.assertNotIn("INDEXATION_DROP", {f["code"] for f in dq["findings"]})


if __name__ == "__main__":
    unittest.main()
