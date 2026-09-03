#!/usr/bin/env python3
"""serp_analysis: Google-режим читает свой файл, разрыв между системами."""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402

DATE = "2026-09-09"


def top(*domains):
    return [{"domain": d, "url": f"https://{d}/", "title": d} for d in domains]


class Base(unittest.TestCase):
    def setUp(self):
        self.m = mocks.load("serp_analysis")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.m.SERP_DIR = pathlib.Path(self.tmp.name)

    def write(self, name, rows):
        p = self.m.SERP_DIR / name
        p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
                     + "\n", encoding="utf-8")


class TestEngines(Base):
    def test_google_reads_its_own_file_and_region(self):
        self.write("2026-09-07-serp-google.jsonl", [
            {"date": "2026-09-07", "query": "купить figma", "engine": "google",
             "region": "2643", "top": top("softline.ru", "biz-soft.pro")},
        ])
        self.write("2026-09-09-serp.jsonl", [
            {"date": DATE, "query": "купить figma", "region": "213",
             "top": top("biz-soft.pro")},
        ])
        g = self.m.build(DATE, engine="google")
        self.assertTrue(g["available"])
        self.assertEqual((g["engine"], g["as_of"], g["region"]),
                         ("google", "2026-09-07", "2643"))
        self.assertEqual(g["items"][0]["our_position"], 2)
        self.assertIn("xmlriver", g["note"])
        # Яндекс не видит Google-файл и наоборот
        y = self.m.build(DATE)
        self.assertEqual((y["engine"], y["as_of"]), ("yandex", DATE))
        self.assertEqual(y["items"][0]["our_position"], 1)

    def test_google_lookback_is_a_week_plus(self):
        self.write("2026-09-01-serp-google.jsonl", [
            {"date": "2026-09-01", "query": "q", "region": "2643",
             "top": top("a.ru")}])
        self.assertTrue(self.m.build(DATE, engine="google")["available"])
        self.assertFalse(self.m.build("2026-09-10", engine="google")["available"])
        self.assertIn("еженедельный", self.m.build("2026-09-10", engine="google")["reason"])


class TestGap(Base):
    def test_gap_groups_by_presence_not_position(self):
        self.write("2026-09-09-serp.jsonl", [
            {"date": DATE, "query": "Купить Figma", "region": "213",
             "top": top("biz-soft.pro", "softline.ru")},
            {"date": DATE, "query": "zoom для юрлиц", "region": "213",
             "top": top("x.ru", "biz-soft.pro")},
            {"date": DATE, "query": "только яндекс", "region": "213",
             "top": top("biz-soft.pro")},
            {"date": DATE, "query": "наоборот", "region": "213",
             "top": top("a.ru", "b.ru")},
            {"date": DATE, "query": "zoom для юрлиц", "region": "2",
             "top": top("biz-soft.pro")},
        ])
        self.write("2026-09-07-serp-google.jsonl", [
            {"date": "2026-09-07", "query": "купить figma", "region": "2643",
             "top": top("softline.ru", "allsoft.ru", "syssoft.ru")},
            {"date": "2026-09-07", "query": "zoom для юрлиц", "region": "2643",
             "top": top("x.ru", "y.ru", "biz-soft.pro")},
            {"date": "2026-09-07", "query": "наоборот", "region": "2643",
             "top": top("biz-soft.pro")},
        ])
        gap = self.m.cross_engine_gap(DATE)
        self.assertTrue(gap["available"])
        self.assertEqual(gap["queries_compared"], 3)     # «только яндекс» не измерен в Google
        self.assertEqual(gap["both_top10"], 1)
        ya = gap["yandex_top10_google_absent"]
        self.assertEqual([i["query"] for i in ya], ["Купить Figma"])
        self.assertEqual(ya[0]["yandex_position"], 1)
        self.assertEqual(ya[0]["google_top3"], ["softline.ru", "allsoft.ru", "syssoft.ru"])
        g = gap["google_top10_yandex_absent"]
        self.assertEqual([i["query"] for i in g], ["наоборот"])
        self.assertEqual(g[0]["yandex_top3"], ["a.ru", "b.ru"])

    def test_gap_needs_both_snapshots(self):
        self.write("2026-09-09-serp.jsonl", [
            {"date": DATE, "query": "q", "region": "213", "top": top("a.ru")}])
        gap = self.m.cross_engine_gap(DATE)
        self.assertFalse(gap["available"])
        self.assertIn("Google", gap["reason"])


if __name__ == "__main__":
    unittest.main()
