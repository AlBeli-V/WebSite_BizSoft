#!/usr/bin/env python3
"""serp_source: срезы Яндекса и Google (xmlriver) не путаются между собой."""

import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from discovery import serp_source  # noqa: E402

LISTING = "\n".join([
    "reports/seo/serp/2026-09-02-serp.jsonl",
    "reports/seo/serp/2026-09-03-serp.jsonl",
    "reports/seo/serp/2026-08-24-serp-google.jsonl",
    "reports/seo/serp/2026-09-03-serp-google.jsonl",
    "reports/seo/serp/ledger",
    "reports/seo/serp/xmlriver-balance.json",
]) + "\n"

GOOGLE_ROW = ('{"date": "2026-09-03", "query": "купить figma", "engine": "google", '
              '"region": "2643", "loc": 2643, "found": 10, '
              '"top": [{"domain": "biz-soft.pro", "url": "https://biz-soft.pro/", '
              '"title": "x"}]}\n')


def fake_git(*args):
    if args[0] == "ls-tree":
        return LISTING if args[-1].startswith("reports/seo/serp/") else ""
    if args[0] == "show":
        if args[1].endswith("2026-09-03-serp-google.jsonl"):
            return GOOGLE_ROW
        if args[1].endswith("2026-08-24-serp-google.jsonl"):
            return GOOGLE_ROW.replace("2026-09-03", "2026-08-24")
        raise serp_source.subprocess.CalledProcessError(128, "git")
    raise AssertionError(args)


class TestEngines(unittest.TestCase):
    def test_dates_per_engine(self):
        with mock.patch.object(serp_source, "_git", fake_git):
            self.assertEqual(serp_source.available_dates(),
                             ["2026-09-02", "2026-09-03"])
            self.assertEqual(serp_source.available_dates(engine="google"),
                             ["2026-08-24", "2026-09-03"])

    def test_google_snapshot_rows(self):
        with mock.patch.object(serp_source, "_git", fake_git):
            rows = serp_source.read_snapshot("2026-09-03", engine="google")
            self.assertEqual(serp_source.read_snapshot("2026-09-03"), [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].engine, "google")
        self.assertEqual(rows[0].region, "2643")
        self.assertTrue(rows[0].has_data)


class TestLatest(unittest.TestCase):
    """Потребитель берёт последний свежий срез, а не «за сегодня»."""

    def test_latest_within_window(self):
        with mock.patch.object(serp_source, "_git", fake_git):
            date, rows = serp_source.latest_snapshot("google", "2026-09-09", 8)
            self.assertEqual(date, "2026-09-03")
            self.assertEqual(len(rows), 1)
            # 12 дней — старше окна: NO DATA, а не устаревший срез
            self.assertEqual(serp_source.latest_snapshot("google", "2026-09-15", 8),
                             (None, []))
            # срезы из будущего относительно даты прогона не берутся
            date, _ = serp_source.latest_snapshot("google", "2026-08-30", 8)
            self.assertEqual(date, "2026-08-24")


if __name__ == "__main__":
    unittest.main()
