#!/usr/bin/env python3
"""Этап 2: инвентарь sitemap, zero-impression и жизненный цикл страниц."""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import mocks  # noqa: E402

DATE = "2026-08-30"
SITE = "https://biz-soft.pro"

SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
 <url><loc>https://biz-soft.pro/</loc><lastmod>2026-08-01</lastmod></url>
 <url><loc>https://biz-soft.pro/product/figma-pro</loc></url>
</urlset>"""


class TestSitemapParse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.si = mocks.load("sitemap_inventory")

    def test_parse_paths_and_lastmod(self):
        urls = self.si.parse_sitemap(SITEMAP_XML)
        self.assertEqual(urls[0], {"path": "/", "lastmod": "2026-08-01"})
        self.assertEqual(urls[1]["path"], "/product/figma-pro")
        self.assertIsNone(urls[1]["lastmod"])

    def test_sitemapindex_fails_loudly(self):
        idx = ('<sitemapindex xmlns="http://www.sitemaps.org/schemas/'
               'sitemap/0.9"><sitemap><loc>x</loc></sitemap></sitemapindex>')
        with self.assertRaises(ValueError):
            self.si.parse_sitemap(idx)

    def test_empty_sitemap_fails_loudly(self):
        with self.assertRaises(ValueError):
            self.si.parse_sitemap('<urlset xmlns="http://www.sitemaps.org/'
                                  'schemas/sitemap/0.9"></urlset>')

    def test_first_seen_only_grows(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg_path = pathlib.Path(tmp) / "reg.json"
            self.si.update_first_seen(["/a", "/b"], "2026-08-28", reg_path)
            reg = self.si.update_first_seen(["/b", "/c"], DATE, reg_path)
            self.assertEqual(reg["paths"]["/a"], "2026-08-28")   # не исчез
            self.assertEqual(reg["paths"]["/b"], "2026-08-28")   # не пересмотрен
            self.assertEqual(reg["paths"]["/c"], DATE)
            self.assertEqual(reg["added_last_run"], 1)
            self.assertEqual(reg["started"], "2026-08-28")


class Stage2Base(unittest.TestCase):
    """Общий tmp-каталог данных для inventory/zero/lifecycle."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data_dir = pathlib.Path(self.tmp.name) / "data"
        self.data_dir.mkdir(parents=True)
        self.pairs = mocks.load("pairs")
        self.pairs.DATA_DIR = self.data_dir
        self.inv = mocks.load("inventory")
        self.inv.DATA_DIR = self.data_dir
        self.inv.pairs = self.pairs

    def write_sitemap(self, paths, date=DATE):
        (self.data_dir / f"sitemap-{date}.json").write_text(json.dumps(
            {"date": date, "count": len(paths),
             "urls": [{"path": p, "lastmod": None} for p in paths]}),
            encoding="utf-8")

    def write_first_seen(self, mapping, started):
        (self.data_dir / "url-first-seen.json").write_text(json.dumps(
            {"paths": mapping, "started": started}), encoding="utf-8")

    def write_gsc(self, pair_rows, page_rows=(), date=DATE):
        (self.data_dir / f"gsc-{date}.json").write_text(json.dumps(
            {"date": date,
             "analytics": {"page": {"rows": list(page_rows)}},
             "pairs": {"rows": pair_rows, "fetched": len(pair_rows),
                       "truncated": False,
                       "window": {"from": "2026-08-02", "to": date}}}),
            encoding="utf-8")

    def detector(self, name):
        mod = mocks.load(name)
        if hasattr(mod, "pairs"):
            mod.pairs = self.pairs
        if hasattr(mod, "inventory"):
            mod.inventory = self.inv
        return mod

    @staticmethod
    def pair(q, page, day, imp):
        return {"keys": [q, SITE + page, day], "impressions": imp,
                "clicks": 0, "position": 8.0}


class TestZeroImpression(Stage2Base):
    def test_no_inventory_is_honest(self):
        z = self.detector("zero_impression").build(DATE)
        self.assertFalse(z["available"])
        self.assertIn("ещё не собран", z["reason"])

    def test_classification_and_coverage(self):
        self.write_sitemap(["/", "/product/a", "/product/b", "/blog/c",
                            "/product/young"])
        self.write_first_seen(
            {"/": "2026-08-01", "/product/a": "2026-08-01",
             "/product/b": "2026-08-01", "/blog/c": "2026-08-01",
             "/product/young": "2026-08-25"},   # 5 дней — молодая
            started="2026-08-01")
        self.write_gsc([self.pair("q", "/product/a", "2026-08-29", 5)])
        z = self.detector("zero_impression").build(DATE)
        self.assertEqual(z["inventory_total"], 5)
        self.assertEqual(z["with_impressions"], 1)
        self.assertEqual(z["young_skipped"], 1)
        paths = {i["path"]: i for i in z["items"]}
        self.assertNotIn("/product/a", paths)       # есть показы
        self.assertNotIn("/product/young", paths)   # молодая
        self.assertIn("разобрать", paths["/product/b"]["verdict"])
        self.assertEqual(paths["/blog/c"]["page_type"], "informational")

    def test_sensor_floor_age_is_marked(self):
        """Страницы старше самого сенсора: возраст — нижняя оценка, не «молодая»."""
        self.write_sitemap(["/product/old"])
        self.write_first_seen({"/product/old": DATE}, started=DATE)
        self.write_gsc([])
        z = self.detector("zero_impression").build(DATE)
        self.assertEqual(len(z["items"]), 1)
        self.assertTrue(z["items"][0]["known_days_is_floor"])
        self.assertIn("разобрать", z["items"][0]["verdict"])


    def write_index(self, google=None, yandex=None, date=DATE):
        if google is not None:
            (self.data_dir / f"index-google-{date}.json").write_text(json.dumps(
                {"date": date, "inspected": len(google),
                 "pages": {p: {"coverage_state": st, "inspected_at": date}
                           for p, st in google.items()}}), encoding="utf-8")
        if yandex is not None:
            (self.data_dir / f"index-yandex-{date}.json").write_text(json.dumps(
                {"date": date, "in_search_count": 400, **yandex}), encoding="utf-8")

    def test_causes_from_index_coverage(self):
        """Статус индекса превращает общий «разобрать» в причину."""
        paths = ["/", "/product/unknown", "/product/crawled", "/product/idx",
                 "/vendors/tech", "/product/nodata"]
        self.write_sitemap(paths)
        self.write_first_seen({p: "2026-08-01" for p in paths}, started="2026-08-01")
        self.write_gsc([self.pair("q", "/", "2026-08-29", 5)])
        self.write_index(
            google={"/": "Submitted and indexed",
                    "/product/unknown": "URL is unknown to Google",
                    "/product/crawled": "Crawled - currently not indexed",
                    "/product/idx": "Indexed, not submitted in sitemap",
                    "/vendors/tech": "Excluded by ‘noindex’ tag"},
            yandex={"in_search": ["/", "/product/idx"],
                    "excluded": {"/product/crawled": {"status": "LOW_QUALITY",
                                                      "date": "2026-08-20"}}})
        z = self.detector("zero_impression").build(DATE)
        by = {i["path"]: i for i in z["items"]}
        self.assertIn("не знает URL", by["/product/unknown"]["verdict"])
        self.assertIn("разбор содержимого", by["/product/crawled"]["verdict"])
        self.assertIn("спрос, название, сниппет", by["/product/idx"]["verdict"])
        self.assertIn("noindex", by["/vendors/tech"]["verdict"])
        self.assertIn("разобрать", by["/product/nodata"]["verdict"])  # нет статуса
        self.assertEqual(by["/product/crawled"]["yandex_index"]["label"],
                         "исключена: малоценная или маловостребованная")
        self.assertEqual(by["/product/idx"]["yandex_index"]["status"], "in_search")
        self.assertEqual(by["/product/unknown"]["yandex_index"]["status"], "absent")
        # Сначала то, где действие ближе: crawled и indexed раньше unknown.
        order = [i["path"] for i in z["items"]]
        self.assertLess(order.index("/product/crawled"), order.index("/product/unknown"))
        # Index Efficiency: в индексе Google — 2 из 6 (главная и idx), в поиске
        # Яндекса — 2 из 6; исключения по причинам.
        self.assertEqual(z["index_google"]["indexed"], 2)
        self.assertAlmostEqual(z["index_google"]["coverage_indexed"], 0.333, places=3)
        self.assertEqual(z["index_google"]["by_class"]["unknown"], 1)
        self.assertEqual(z["index_yandex"]["in_search"], 2)
        self.assertEqual(z["index_yandex"]["excluded_by_reason"],
                         {"малоценная или маловостребованная": 1})
        self.assertEqual(z["by_cause"]["crawled"], 1)

    def test_without_coverage_files_behaviour_unchanged(self):
        self.write_sitemap(["/product/b"])
        self.write_first_seen({"/product/b": "2026-08-01"}, started="2026-08-01")
        self.write_gsc([])
        z = self.detector("zero_impression").build(DATE)
        self.assertFalse(z["index_google"]["available"])
        self.assertFalse(z["index_yandex"]["available"])
        self.assertEqual(z["items"][0]["google_index"]["class"], "no_data")
        self.assertEqual(z["items"][0]["yandex_index"]["status"], "no_data")
        self.assertIn("разобрать", z["items"][0]["verdict"])


class TestLifecycle(Stage2Base):
    def test_statuses(self):
        rows = (
            # declining: prev7 = 20, last7 = 5
            [self.pair("q1", "/product/down", "2026-08-19", 20),
             self.pair("q1", "/product/down", "2026-08-27", 5)]
            # gaining: prev7 = 10, last7 = 30
            + [self.pair("q2", "/product/up", "2026-08-05", 8),
               self.pair("q2", "/product/up", "2026-08-19", 10),
               self.pair("q2", "/product/up", "2026-08-27", 30)]
            # new: первая активность в последние 10 дней окна
            + [self.pair("q3", "/alternatives/fresh", "2026-08-28", 3)]
            # stable
            + [self.pair("q4", "/vendors/flat", "2026-08-10", 6),
               self.pair("q4", "/vendors/flat", "2026-08-27", 6)])
        self.write_gsc(rows)
        lc = self.detector("lifecycle").build(DATE)
        st = {i["page"]: i["status"] for i in lc["items"]}
        self.assertEqual(st["/product/down"], "declining")
        self.assertEqual(st["/product/up"], "gaining")
        self.assertEqual(st["/alternatives/fresh"], "new")
        self.assertEqual(st["/vendors/flat"], "stable")
        self.assertEqual(lc["items"][0]["page"], "/product/down")  # declining первым
        self.assertEqual(lc["counts"]["declining"], 1)

    def test_small_base_is_not_decline(self):
        self.write_gsc([self.pair("q", "/product/x", "2026-08-19", 5),
                        self.pair("q", "/product/x", "2026-08-27", 1)])
        lc = self.detector("lifecycle").build(DATE)
        self.assertEqual(lc["items"][0]["status"], "stable")


if __name__ == "__main__":
    unittest.main()
