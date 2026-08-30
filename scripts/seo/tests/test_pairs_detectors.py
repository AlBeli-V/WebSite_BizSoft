#!/usr/bin/env python3
"""Пары query×page×day и детекторы: каннибализация и query-page mismatch."""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
# Модули детекторов импортируют pairs и snapshot по обычному пути.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import mocks  # noqa: E402

DATE = "2026-08-30"
SITE = "https://biz-soft.pro"


def row(q, page, day="2026-08-20", imp=10, clicks=0, pos=8.0):
    return {"keys": [q, SITE + page] + ([day] if day else []),
            "impressions": imp, "clicks": clicks, "position": pos}


class PairsBase(unittest.TestCase):
    def setUp(self):
        self.pairs = mocks.load("pairs")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data_dir = pathlib.Path(self.tmp.name) / "data"
        self.data_dir.mkdir(parents=True)
        self.pairs.DATA_DIR = self.data_dir

    def write_pairs(self, rows, date=DATE, error=None):
        pairs = {"rows": rows, "fetched": len(rows), "truncated": False,
                 "window": {"from": "2026-08-02", "to": DATE}}
        if error:
            pairs = {"error": error, "rows": []}
        (self.data_dir / f"gsc-{date}.json").write_text(
            json.dumps({"date": date, "pairs": pairs}), encoding="utf-8")

    def detector(self, name):
        mod = mocks.load(name)
        mod.pairs = self.pairs      # детектор смотрит в тот же tmp-каталог
        return mod


class TestPairsLayer(PairsBase):
    def test_normalize_survives_both_key_formats(self):
        rows = self.pairs.normalize_rows(
            [row("q", "/product/x"), row("q2", "/", day=None)])
        self.assertEqual(rows[0]["page"], "/product/x")
        self.assertEqual(rows[0]["date"], "2026-08-20")
        self.assertEqual(rows[1]["page"], "/")
        self.assertIsNone(rows[1]["date"])

    def test_load_latest_falls_back_and_skips_errors(self):
        self.write_pairs([], error="HTTP 500")
        self.write_pairs([row("q", "/product/x")], date="2026-08-28")
        data = self.pairs.load_latest(DATE)
        self.assertEqual(data["date"], "2026-08-28")

    def test_by_query_shares_and_leader_changes(self):
        rows = self.pairs.normalize_rows([
            row("q", "/a", "2026-08-18", imp=30),
            row("q", "/b", "2026-08-18", imp=10),
            row("q", "/b", "2026-08-19", imp=40),
            row("q", "/a", "2026-08-20", imp=20),
        ])
        q = self.pairs.by_query(rows)["q"]
        self.assertEqual(q["impressions"], 100)
        self.assertEqual(q["pages"]["/a"]["share"], 0.5)
        self.assertEqual(q["leader_series"], ["/a", "/b", "/a"])
        self.assertEqual(q["leader_changes"], 2)


class TestCannibalization(PairsBase):
    def test_no_data_is_honest(self):
        cb = self.detector("cannibalization").build(DATE)
        self.assertFalse(cb["available"])
        self.assertIn("не накопил", cb["reason"])

    def test_unstable_leader_ranks_first(self):
        self.write_pairs(
            # нестабильный: лидер меняется каждый день
            [row("figma купить", "/product/figma", d, imp=10)
             for d in ("2026-08-18", "2026-08-20")]
            + [row("figma купить", "/vendors/figma", "2026-08-19", imp=15)]
            + [row("figma купить", "/vendors/figma", "2026-08-21", imp=15)]
            # стабильное расщепление: доли есть, лидер один
            + [row("miro цена", "/product/miro", "2026-08-18", imp=40),
               row("miro цена", "/vendors/miro", "2026-08-18", imp=20)])
        cb = self.detector("cannibalization").build(DATE)
        self.assertTrue(cb["available"])
        self.assertEqual(cb["items"][0]["query"], "figma купить")
        self.assertEqual(cb["items"][0]["verdict"], "unstable")
        self.assertGreaterEqual(cb["items"][0]["leader_changes"], 2)
        self.assertEqual(cb["items"][1]["verdict"], "split")
        self.assertEqual(cb["unstable_count"], 1)

    def test_single_page_query_is_not_flagged(self):
        self.write_pairs([row("q", "/product/x", imp=100),
                          row("q", "/vendors/x", imp=5)])   # доля < 0.2
        cb = self.detector("cannibalization").build(DATE)
        self.assertEqual(cb["items"], [])


class TestMismatch(PairsBase):
    def test_commercial_query_on_blog_is_flagged_with_alt(self):
        self.write_pairs([
            row("купить figma", "/blog/figma-guide", imp=90),
            row("купить figma", "/product/figma-pro", imp=10),
            row("как выбрать сапр", "/blog/sapr", imp=50),      # инфо-запрос
            row("bizsoft купить", "/blog/x", imp=50),           # брендовый
        ])
        mm = self.detector("mismatch").build(DATE)
        self.assertEqual(len(mm["items"]), 1)
        item = mm["items"][0]
        self.assertEqual(item["query"], "купить figma")
        self.assertEqual(item["page_type"], "informational")
        self.assertEqual(item["commercial_alt"], "/product/figma-pro")
        self.assertIn("/product/figma-pro", item["recommended_action"])

    def test_commercial_query_without_landing_suggests_gate(self):
        self.write_pairs([row("купить heygen", "/blog/ai-video", imp=40)])
        mm = self.detector("mismatch").build(DATE)
        self.assertIn("анти-doorway", mm["items"][0]["recommended_action"])

    def test_commercial_page_is_fine(self):
        self.write_pairs([row("купить figma", "/product/figma-pro", imp=90)])
        mm = self.detector("mismatch").build(DATE)
        self.assertEqual(mm["items"], [])

    def test_page_types(self):
        m = self.detector("mismatch")
        self.assertEqual(m.page_type("/blog/x"), "informational")
        self.assertEqual(m.page_type("/product/figma"), "product")
        self.assertEqual(m.page_type("/alternatives/canva"), "comparison")
        self.assertEqual(m.page_type("/"), "home")
        self.assertEqual(m.page_type("/r-abc"), "other")


if __name__ == "__main__":
    unittest.main()
