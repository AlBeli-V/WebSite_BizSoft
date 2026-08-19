#!/usr/bin/env python3
"""Регрессионные и unit-проверки отчётности v2 (stdlib unittest, без новых зависимостей).

Fixture — реальный срез 2026-08-19; сырые выгрузки не изменяются.
Запуск: python3 -m unittest discover -s scripts/seo/tests -v
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "seo"))
sys.path.insert(0, str(ROOT))

import quality  # noqa: E402
import snapshot as snap_mod  # noqa: E402

DATE = "2026-08-19"
BASE = ROOT / "reports" / "seo" / "intelligence"


def load_json(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


class TestArithmetic(unittest.TestCase):
    def test_delta_44_to_49_is_5(self):
        self.assertEqual(quality.delta(49, 44)["absolute"], 5)

    def test_delta_31_vs_19(self):
        d = quality.delta(31, 19)
        self.assertEqual(d["absolute"], 12)
        self.assertAlmostEqual(d["relative"] * 100, 63.2, places=1)

    def test_relative_not_computed_on_zero_base(self):
        self.assertIsNone(quality.delta(5, 0)["relative"])

    def test_low_base_marked(self):
        self.assertTrue(quality.delta(31, 19)["low_base"])

    def test_missing_value_never_becomes_zero(self):
        d = quality.delta(None, 10)
        self.assertIsNone(d["absolute"])
        self.assertIsNone(d["relative"])

    def test_ctr_6_of_926(self):
        self.assertAlmostEqual(quality.ctr(6, 926) * 100, 0.65, places=2)

    def test_ctr_none_on_zero_impressions(self):
        self.assertIsNone(quality.ctr(0, 0))

    def test_period_05_17_is_13_days(self):
        self.assertEqual(snap_mod.days_inclusive("2026-08-05", "2026-08-17"), 13)


class TestSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snap = load_json(BASE / "snapshots" / f"{DATE}.json")

    def test_top10_strict_threshold(self):
        yx = self.snap["yandex"]
        for e in yx["entities"]:
            if e["average_position"] is not None and e["average_position"] > 10:
                self.assertNotIn(e, [x for x in yx["entities"]
                                     if x["average_position"] is not None and x["average_position"] <= 10])
        counted = len([e for e in yx["entities"]
                       if e["average_position"] is not None and e["average_position"] <= 10])
        self.assertEqual(yx["totals"]["queries_position_le_10"], counted)

    def test_positions_above_10_not_in_top10(self):
        yx = self.snap["yandex"]
        top = [e for e in yx["entities"]
               if e["average_position"] is not None and e["average_position"] <= 10]
        self.assertTrue(all(e["average_position"] <= 10 for e in top))
        self.assertTrue(any(e["average_position"] > 10 for e in yx["entities"]))

    def test_query_and_page_scopes_are_separate(self):
        g = self.snap["google"]
        self.assertIn("queries_position_le_10", g["totals"])
        self.assertIn("pages_position_le_10", g["totals"])
        self.assertEqual({e["entity_type"] for e in g["entities"]}, {"query"})
        self.assertEqual({p["entity_type"] for p in g["pages"]}, {"page"})

    def test_yandex_scope_is_sample_not_site(self):
        self.assertIn("выборка", self.snap["yandex"]["totals"]["scope_note"])

    def test_crm_metrics_are_none(self):
        crm = self.snap["crm"]
        self.assertIsNone(crm["qualified_leads"])
        self.assertIsNone(crm["deals"])
        self.assertIsNone(crm["revenue"])

    def test_ctr_model_not_approved(self):
        self.assertFalse(self.snap["ctr_model"]["approved"])

    def test_unique_goal_users_unknown(self):
        self.assertIsNone(self.snap["analytics"]["metrika"]["unique_goal_users"])

    def test_intra_day_conflict_77_78_recorded(self):
        revs = self.snap["analytics"]["intra_day_revisions"]
        vals = [v for r in revs for v in r["values_seen"]]
        self.assertIn(77.0, vals)
        self.assertIn(78.0, vals)
        self.assertEqual(revs[0]["canonical"], 78.0)

    def test_baseline_revision_recorded(self):
        vals = [v for r in self.snap["data_revisions"] for v in r["values_seen"]]
        self.assertIn(150.0, vals)
        self.assertIn(169.0, vals)


class TestQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dq = load_json(BASE / "data-quality" / f"{DATE}.json")
        cls.codes = {f["code"]: f for f in cls.dq["findings"]}

    def test_reconciliation_is_critical(self):
        self.assertEqual(self.codes["SOURCE_RECONCILIATION"]["level"], "critical")
        self.assertEqual(self.dq["status"], "critical")

    def test_no_green_status_when_critical(self):
        self.assertFalse(self.dq["publication_rules"]["allow_green_overall_status"])

    def test_measurement_change_warning(self):
        self.assertIn("MEASUREMENT_CHANGE", self.codes)

    def test_low_conversion_sample_warning(self):
        self.assertIn("LOW_CONVERSION_SAMPLE", self.codes)

    def test_lead_wording_forbidden(self):
        self.assertFalse(self.dq["publication_rules"]["allow_lead_wording"])

    def test_market_demand_wording_forbidden(self):
        self.assertFalse(self.dq["publication_rules"]["allow_market_demand_wording"])

    def test_expected_ctr_claims_forbidden(self):
        self.assertFalse(self.dq["publication_rules"]["allow_expected_ctr_claims"])


class TestExecutiveBrief(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.md = (BASE / f"{DATE}-executive.md").read_text(encoding="utf-8")
        cls.html = (BASE / f"{DATE}-executive.html").read_text(encoding="utf-8")

    def test_word_limit(self):
        self.assertLessEqual(len(self.md.split()), 900)

    def test_max_three_decisions(self):
        self.assertLessEqual(self.md.count("DEC-00"), 3)

    def test_no_trust_claim(self):
        self.assertNotIn("наращивает доверие", self.md)
        self.assertNotIn("наращивает доверие", self.html)

    def test_no_market_demand_claim(self):
        for bad in ("искали 96", "HeyGen ищут", "спрос вырос"):
            self.assertNotIn(bad, self.md)

    def test_no_top5_without_sample(self):
        self.assertNotIn("уже в топ-5", self.md)
        self.assertNotIn("уже в топ-5", self.html)

    def test_no_lead_wording_for_goal_events(self):
        self.assertNotIn("3 заявки", self.md)
        self.assertNotIn("заявки-действия", self.md)

    def test_no_technical_commands_in_body(self):
        for bad in ("pnpm ", "git ", "python3 ", "ПРОМТ", "Claude Code"):
            self.assertNotIn(bad, self.md.split("## Следующая контрольная точка")[0])

    def test_no_growth_score_in_body(self):
        self.assertNotIn("Growth Score", self.md)

    def test_no_expected_ctr_3_3(self):
        self.assertNotIn("3,3%", self.md)
        self.assertNotIn("потерянных кликов", self.md)

    def test_crm_metrics_shown_as_no_data(self):
        self.assertIn("Квалифицированные лиды: нет данных", self.md)

    def test_single_canonical_visits_value(self):
        self.assertNotIn("77", self.md.split("## Ключевые показатели")[1].split("## Что изменилось")[0])

    def test_critical_warning_visible_in_html_text(self):
        self.assertIn("КРИТИЧЕСКОЕ РАСХОЖДЕНИЕ ДАННЫХ", self.html)

    def test_html_container_width(self):
        self.assertIn("max-width:660px", self.html)


class TestAppendix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.md = (BASE / f"{DATE}-appendix.md").read_text(encoding="utf-8")

    def test_table_titles_are_precise(self):
        self.assertIn("10 запросов с наибольшим числом показов", self.md)
        self.assertIn("запросы со средней позицией до 10", self.md.lower())

    def test_scope_explained(self):
        self.assertIn("разные scope", self.md.lower())

    def test_tickets_listed(self):
        for t in ("DATA-001", "SEO-EXP-001", "CRO-EXP-002", "INDEX-001", "PPC-RES-001",
                  "BRAND-001", "CONTENT-001"):
            self.assertIn(t, self.md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
