#!/usr/bin/env python3
"""Радар вендоров: интерес в поиске из снимка, по правилам методики.

Показы — не «спрос», движки не складываются, недоступный источник не участвует,
PPC-кандидаты несут только измеренный сигнал.
"""

import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"
DATE = "2026-08-25"


def raw(prefix):
    return json.loads((FIX / f"{prefix}-{DATE}.json").read_text(encoding="utf-8"))


class TestVendorRadar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = mocks.load("snapshot")
        cls.v = mocks.load("vendor_radar")
        cls.r = mocks.load("report_v4")
        cls.q = mocks.load("quality")
        cls.snap = cls.make_snap(yandex=raw("yandex"), gsc=raw("gsc"),
                                 metrika=raw("metrika"), ga4=raw("ga4"))

    @classmethod
    def make_snap(cls, yandex=None, gsc=None, metrika=None, ga4=None):
        s = cls.s
        return {"schema_version": "test", "report_date": DATE, "generated_at": "",
                "reporting_timezone": s.TIMEZONE, "declared_goals": [],
                "goal_levels": {}, "thresholds": s.THRESHOLDS,
                "yandex": s.build_safe("yandex_webmaster", s.build_yandex, yandex, None, DATE),
                "google": s.build_safe("google_search_console", s.build_google, gsc, None),
                "analytics": s.build_analytics_safe(metrika, ga4, DATE),
                "experiments": [],
                "market_demand": {"available": False, "reason": "тест",
                                  "comparable_to_visibility": False},
                "data_revisions": [], "crm": {"connected": False},
                "ctr_model": {"approved": False}}

    def test_radar_builds_from_snapshot(self):
        vr = self.v.build(self.snap)
        self.assertTrue(vr["available"])
        self.assertTrue(vr["items"])
        vendors = [it["vendor"] for it in vr["items"]]
        self.assertIn("CorelDRAW", vendors)

    def test_engines_are_kept_separate(self):
        vr = self.v.build(self.snap)
        for it in vr["items"]:
            self.assertIn("yandex", it)
            self.assertIn("google", it)
            # Суммарного кросс-движкового числа в данных блока нет.
            self.assertNotIn("impressions", it)
            self.assertNotIn("shows", it)

    def test_note_forbids_demand_wording(self):
        vr = self.v.build(self.snap)
        self.assertIn("не рыночный спрос", vr["note"])

    def test_unavailable_search_sources_disable_block(self):
        snap = self.make_snap(yandex=None, gsc=None,
                              metrika=raw("metrika"), ga4=raw("ga4"))
        vr = self.v.build(snap)
        self.assertFalse(vr["available"])
        self.assertEqual(vr["reason_code"], "no_rows")
        self.assertIn("источники поиска", vr["reason"])

    def test_ppc_candidates_are_commercial_unbranded_with_base(self):
        for c in self.v.ppc_candidates(self.snap):
            self.assertGreaterEqual(c["shows"], self.v.PPC_MIN_SHOWS)
            lo, hi = self.v.PPC_POSITION
            self.assertGreater(c["position"], lo)
            self.assertLessEqual(c["position"], hi)
            # Только измеренный сигнал: ни ставок, ни прогнозов конверсии.
            self.assertNotIn("cpc", c)
            self.assertNotIn("budget", c)

    def test_word_boundary_matching(self):
        cat = self.v.catalogue()
        self.assertIsNone(self.v.vendor_of("купить боксовую версию", cat))

    def test_letter_renders_block_and_text(self):
        dq = self.q.run_checks(self.snap, None)
        b = self.r.assemble(self.snap, None, dq, {"roles": {}, "actions": []}, None)
        self.assertTrue(b["vendor_radar"]["available"])
        html = self.r.html_email(b, {}, cid_mode=False)
        text = self.r.plain_text(b)
        self.assertIn("Интерес к вендорам в поиске", html)
        self.assertIn("ИНТЕРЕС К ВЕНДОРАМ В ПОИСКЕ", text)
        self.assertIn("не рыночный спрос", html)

    def test_letter_omits_block_when_no_search_data(self):
        snap = self.make_snap(yandex=None, gsc=None,
                              metrika=raw("metrika"), ga4=raw("ga4"))
        dq = self.q.run_checks(snap, None)
        b = self.r.assemble(snap, None, dq, {"roles": {}, "actions": []}, None)
        html = self.r.html_email(b, {}, cid_mode=False)
        self.assertNotIn("Интерес к вендорам в поиске", html)


if __name__ == "__main__":
    unittest.main()
