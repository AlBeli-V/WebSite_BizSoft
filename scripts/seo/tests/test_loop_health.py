#!/usr/bin/env python3
"""Loop-health: контур подтверждается артефактом с датой, а не расписанием."""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402

DATE = "2026-08-27"  # четверг


class TestLoopHealth(unittest.TestCase):
    def setUp(self):
        self.lh = mocks.load("loop_health")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = pathlib.Path(self.tmp.name) / "reports" / "seo"
        self.base = base
        self.lh.BASE = base
        self.lh.OUT = base / "intelligence" / "loop-health.json"
        for d in ("data", "wordstat", "intelligence/snapshots",
                  "intelligence/data-quality", "ppc"):
            (base / d).mkdir(parents=True, exist_ok=True)

    # -- наполнение артефактами -------------------------------------------

    def touch(self, rel: str, text: str = "{}"):
        p = self.base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def fill_fresh(self, date=DATE, prev="2026-08-26"):
        for src in ("gsc", "yandex", "metrika", "ga4"):
            self.touch(f"data/{src}-{date}.json")
        self.touch(f"data/gsc-{date}.json", json.dumps(
            {"date": date, "pairs": {"rows": [], "fetched": 0}}))
        self.touch(f"wordstat/{date}-demand-report.md", "# отчёт")
        self.touch(f"intelligence/snapshots/{date}.json")
        self.touch(f"intelligence/data-quality/{date}.json")
        self.touch(f"intelligence/{prev}-v4.html", "<div></div>")
        self.touch("intelligence/last-mailed.txt", prev)
        self.touch("ppc/direct-stats.json", json.dumps(
            {"groups": [{"Date": prev, "Cost": 0, "Clicks": 0,
                         "Impressions": 0, "AdGroupName": "x"}]}))

    # -- сами проверки -----------------------------------------------------

    def test_all_fresh_means_no_overdue(self):
        self.fill_fresh()
        res = self.lh.build(DATE)
        self.assertEqual(res["overdue"], [])
        self.assertEqual(res["ok_count"], res["total"])

    def test_stale_collect_is_overdue_with_days(self):
        self.fill_fresh()
        for src in ("gsc", "yandex", "metrika", "ga4"):
            (self.base / f"data/{src}-{DATE}.json").unlink()
            self.touch(f"data/{src}-2026-08-25.json")
        res = self.lh.build(DATE)
        self.assertIn("collect", res["overdue"])
        row = next(r for r in res["contours"] if r["id"] == "collect")
        self.assertEqual(row["days_late"], 2)

    def test_missing_required_artifacts_are_overdue(self):
        res = self.lh.build(DATE)          # пустые каталоги
        row = next(r for r in res["contours"] if r["id"] == "snapshot")
        self.assertTrue(row["overdue"])
        self.assertIn("не найдено", row["note"])

    def test_new_sensor_without_history_is_waiting_not_overdue(self):
        """Пары GSC до первого прогона — «ожидает», а не ложная тревога."""
        self.fill_fresh()
        self.touch(f"data/gsc-{DATE}.json", json.dumps({"date": DATE}))
        res = self.lh.build(DATE)
        row = next(r for r in res["contours"] if r["id"] == "gsc-pairs")
        self.assertFalse(row["overdue"])
        self.assertIn("первого прогона", row["note"])

    def test_pairs_with_error_do_not_count_as_run(self):
        self.fill_fresh()
        self.touch(f"data/gsc-{DATE}.json", json.dumps(
            {"date": DATE, "pairs": {"error": "HTTP 500", "rows": []}}))
        self.touch("data/gsc-2026-08-26.json", json.dumps(
            {"date": "2026-08-26", "pairs": {"rows": [], "fetched": 0}}))
        res = self.lh.build(DATE)
        row = next(r for r in res["contours"] if r["id"] == "gsc-pairs")
        self.assertEqual(row["last_run"], "2026-08-26")
        self.assertTrue(row["overdue"])

    def test_letter_and_email_expected_with_one_day_lag(self):
        """Сегодняшнее письмо в момент проверки ещё строится — ждём вчерашнее."""
        self.fill_fresh()
        res = self.lh.build(DATE)
        for cid in ("report", "email"):
            row = next(r for r in res["contours"] if r["id"] == cid)
            self.assertEqual(row["expected_since"], "2026-08-26")
            self.assertFalse(row["overdue"])

    def test_direct_tolerates_weekend(self):
        """Директ по будням: в понедельник свежесть меряется от пятницы."""
        monday = "2026-08-31"
        self.fill_fresh(date=monday, prev="2026-08-30")
        # последний ряд Директа — за воскресенье (прогон понедельника 07:10)
        self.touch("ppc/direct-stats.json", json.dumps(
            {"groups": [{"Date": "2026-08-30"}]}))
        res = self.lh.build(monday)
        row = next(r for r in res["contours"] if r["id"] == "direct")
        self.assertFalse(row["overdue"])
        # а данные, оборвавшиеся в четверг, — просрочка и в понедельник
        self.touch("ppc/direct-stats.json", json.dumps(
            {"groups": [{"Date": "2026-08-27"}]}))
        row = next(r for r in self.lh.build(monday)["contours"]
                   if r["id"] == "direct")
        self.assertTrue(row["overdue"])

    def test_write_creates_registry(self):
        self.fill_fresh()
        res = self.lh.write(DATE)
        saved = json.loads(self.lh.OUT.read_text(encoding="utf-8"))
        self.assertEqual(saved["overdue"], res["overdue"])
        self.assertTrue(saved["available"])


class TestLoopHealthLine(unittest.TestCase):
    """Строка о конвейере в письме: коротко и без ложного «всё в срок»."""

    @classmethod
    def setUpClass(cls):
        cls.r = mocks.load("report_v4")

    def test_absent_registry_is_silent(self):
        self.assertIsNone(self.r.loop_health_line({"available": False}))
        self.assertIsNone(self.r.loop_health_line({}))

    def test_all_ok_is_one_calm_line(self):
        text, alarm = self.r.loop_health_line(
            {"available": True, "ok_count": 8, "total": 8, "contours": []})
        self.assertFalse(alarm)
        self.assertIn("в срок", text)

    def test_overdue_names_first_two_and_counts_rest(self):
        contours = [
            {"id": f"c{i}", "label": f"Контур {i}", "overdue": True,
             "last_run": "2026-08-25"} for i in range(3)]
        text, alarm = self.r.loop_health_line(
            {"available": True, "ok_count": 5, "total": 8, "contours": contours})
        self.assertTrue(alarm)
        self.assertIn("Контур 0", text)
        self.assertIn("Контур 1", text)
        self.assertNotIn("Контур 2", text)
        self.assertIn("ещё 1", text)


if __name__ == "__main__":
    unittest.main()
