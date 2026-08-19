#!/usr/bin/env python3
"""Регрессионные и unit-проверки отчётности v2 (stdlib unittest, без новых зависимостей).

Fixture — реальный срез 2026-08-19; сырые выгрузки не изменяются.
Запуск: python3 -m unittest discover -s scripts/seo/tests -v
"""

from __future__ import annotations

import json
import pathlib
import sys
import re
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


class TestExecutiveV3(unittest.TestCase):
    """Письмо V3: объём, структура, язык, отсутствие противоречий."""

    @classmethod
    def setUpClass(cls):
        cls.email = (BASE / f"{DATE}-executive-email.html").read_text(encoding="utf-8")
        cls.preview = (BASE / f"{DATE}-executive.html").read_text(encoding="utf-8")
        cls.text = (BASE / f"{DATE}-executive.txt").read_text(encoding="utf-8")
        cls.lint = load_json(BASE / f"{DATE}-uxlint.json")
        cls.actions = load_json(BASE / "actions.json")

    def test_uxlint_passes(self):
        self.assertEqual(self.lint["status"], "pass", self.lint["summary"])

    def test_visible_words_in_range(self):
        c = next(x for x in self.lint["checks"] if x["check"] == "visible_words")
        self.assertEqual(c["status"], "pass", c["detail"])

    def test_plain_text_within_limit(self):
        self.assertLessEqual(len(self.text.split()), 650)

    def test_no_inline_svg_in_email(self):
        self.assertNotIn("<svg", self.email)

    def test_charts_are_png_with_alt(self):
        imgs = re.findall(r"<img [^>]+>", self.email)
        self.assertLessEqual(len(imgs), 2)
        for tag in imgs:
            self.assertIn("alt=", tag)
            self.assertTrue("cid:" in tag or ".png" in tag)

    def test_no_funnel_before_reconciliation(self):
        self.assertFalse(re.search(r"(src|cid)[^>]*funnel", self.email))

    def test_zero_delta_wording(self):
        """delta = 0 → запрещены слова роста и падения в этом блоке."""
        forbidden = ["вырос", "рост", "увеличил", "снизил", "падени", "сократил", "прибав"]
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", self.text) if "169" in s]
        self.assertTrue(sentences, "предложение с числом страниц не найдено")
        for s in sentences:
            for w in forbidden:
                self.assertNotIn(w, s.lower(), f"в блоке с нулевой дельтой: {s}")
        self.assertIn("не изменилось", " ".join(sentences))

    def test_forbidden_technical_terms_absent(self):
        body = self.email.split('<tr><td style="background:#fafafb;')[0]
        body = re.sub(r'alt="[^"]*"', " ", body)
        for term in ("SOURCE_RECONCILIATION", "guardrail", "snapshot", "ym:s:",
                     "popular queries", "rollback", "stop-condition", "key events"):
            self.assertNotIn(term.lower(), body.lower())

    def test_composite_status_present(self):
        self.assertIn("Яндекс —", self.text)
        self.assertIn("Google —", self.text)
        self.assertIn("вывод предварительный", self.text)

    def test_from_you_block_no_action_required(self):
        self.assertIn("ОТ ВАС: Действий не требуется.", self.text)

    def test_no_manual_owner_assignment(self):
        self.assertNotIn("назначает руководитель", self.text)
        for a in self.actions["actions"]:
            if a["zone"] in ("GREEN", "YELLOW"):
                self.assertTrue(a.get("owner_role"))

    def test_roles_are_resolved(self):
        for role in ("Data Auditor", "SEO Lead", "PPC Lead"):
            self.assertIn(role, self.text)

    def test_ppc_blocked_by_policy(self):
        ppc = next(a for a in self.actions["actions"] if a["id"] == "PPC-RES-001")
        self.assertEqual(ppc["status"], "blocked_by_policy")

    def test_combined_experiment_not_split(self):
        combined = [a for a in self.actions["actions"] if a.get("combined_deployment")]
        self.assertEqual(len(combined), 1)
        self.assertNotIn("CRO-EXP-002", self.text)

    def test_no_full_freshness_table_in_body(self):
        self.assertIn("Данные: Яндекс/Google по", self.text)
        self.assertNotIn("current_period_days", self.email)

    def test_links_are_clickable_urls(self):
        for key in ("appendix.md", "/tree/", "data-quality", "/pull/"):
            self.assertIn(key, self.email)
        self.assertNotIn(">reports/seo/", self.email)

    def test_container_and_typography(self):
        self.assertIn("max-width:640px", self.email)
        self.assertIn("font-size:21px", self.email)

    def test_plain_text_tables_are_narrow(self):
        for line in self.text.splitlines():
            self.assertLessEqual(line.count("|"), 2, line)

    def test_eml_has_inline_images(self):
        eml = (BASE / f"{DATE}-executive.eml").read_bytes()
        self.assertIn(b"image/png", eml)
        self.assertIn(b"inline", eml)

    def test_previews_exist(self):
        for name in ("mobile", "desktop"):
            self.assertTrue((BASE / "previews" / f"{DATE}-{name}.png").exists())


class TestAppendix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.md = (BASE / f"{DATE}-appendix.md").read_text(encoding="utf-8")

    def test_table_titles_are_precise(self):
        self.assertIn("10 запросов с наибольшим числом показов", self.md)
        self.assertIn("запросы со средней позицией до 10", self.md.lower())

    def test_scope_explained(self):
        self.assertIn("разные scope", self.md.lower())

    def test_full_freshness_table_moved_here(self):
        self.assertIn("Свежесть источников (полная таблица)", self.md)

    def test_all_warnings_here(self):
        self.assertIn("Все предупреждения качества данных", self.md)

    def test_technical_glossary(self):
        for term in ("ym:s:visits", "guardrails", "stop-condition", "SOURCE_RECONCILIATION"):
            self.assertIn(term, self.md)

    def test_roles_and_zones_documented(self):
        self.assertIn("Data Auditor", self.md)
        self.assertIn("GREEN", self.md)

    def test_combined_deployment_documented(self):
        self.assertIn("один эксперимент", self.md)

    def test_tickets_listed(self):
        for t in ("DATA-001", "SEO-EXP-001", "CRO-EXP-002", "INDEX-001", "PPC-RES-001",
                  "BRAND-001", "CONTENT-001"):
            self.assertIn(t, self.md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
