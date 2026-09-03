"""Периодные отчёты (поручение руководителя 30.08.2026): границы и агрегация."""

import datetime as dt
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import period_report as pr  # noqa: E402


class BoundsTest(unittest.TestCase):
    def test_недельный_от_субботы_прошлая_сб_по_пятницу(self):
        f, t = pr.period_bounds("weekly", dt.date(2026, 9, 5))  # суббота
        self.assertEqual((f.isoformat(), t.isoformat()),
                         ("2026-08-29", "2026-09-04"))
        self.assertEqual((t - f).days, 6)

    def test_месячный_первого_числа_за_прошлый_месяц(self):
        f, t = pr.period_bounds("monthly", dt.date(2026, 9, 1))
        self.assertEqual((f.isoformat(), t.isoformat()),
                         ("2026-08-01", "2026-08-31"))

    def test_годовой_за_прошлый_календарный_год(self):
        f, t = pr.period_bounds("yearly", dt.date(2028, 1, 1))
        self.assertEqual((f.isoformat(), t.isoformat()),
                         ("2027-01-01", "2027-12-31"))

    def test_предыдущий_месяц_разной_длины(self):
        f, t = pr.prev_bounds("monthly", dt.date(2026, 8, 1), dt.date(2026, 8, 31))
        self.assertEqual((f.isoformat(), t.isoformat()),
                         ("2026-07-01", "2026-07-31"))
        f, t = pr.prev_bounds("monthly", dt.date(2026, 3, 1), dt.date(2026, 3, 31))
        self.assertEqual(t.isoformat(), "2026-02-28")

    def test_заголовки_периодов(self):
        self.assertEqual(
            pr.period_title("weekly", dt.date(2026, 8, 22), dt.date(2026, 8, 28)),
            "за период 22.08 по 28.08.2026")
        self.assertIn("за август 2026",
                      pr.period_title("monthly", dt.date(2026, 8, 1),
                                      dt.date(2026, 8, 31)))
        self.assertEqual(pr.period_title("yearly", dt.date(2027, 1, 1),
                                         dt.date(2027, 12, 31)), "за 2027 год")


class AggregationTest(unittest.TestCase):
    def test_дыры_в_ряду_считаются_покрытием_а_не_нулями(self):
        series = {"2026-08-01": 5, "2026-08-03": 7}  # 02.08 отсутствует
        total, covered = pr._agg(series, pr._days(dt.date(2026, 8, 1),
                                                  dt.date(2026, 8, 3)))
        self.assertEqual(total, 12)
        self.assertEqual(covered, 2)

    def test_реклама_агрегируется_только_за_дни_периода(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            old = pr.DIRECT
            pr.DIRECT = tmp / "direct-stats.json"
            pr.DIRECT.write_text(json.dumps({"groups": [
                {"Date": "2026-08-28", "AdGroupName": "Claude Code — x",
                 "Impressions": 10, "Clicks": 2, "Cost": 50.0},
                {"Date": "2026-09-10", "AdGroupName": "Claude Code — x",
                 "Impressions": 99, "Clicks": 9, "Cost": 900.0},
            ]}), encoding="utf-8")
            ads = pr.collect_ads(dt.date(2026, 8, 22), dt.date(2026, 8, 28))
            self.assertTrue(ads["available"])
            self.assertEqual(ads["clicks"], 2)
            self.assertAlmostEqual(ads["cost"], 50.0)
        finally:
            pr.DIRECT = old
            shutil.rmtree(tmp, ignore_errors=True)

    def test_годовой_guard_до_первого_полного_года(self):
        # main() с send 2027-01-01 (за 2026, неполный год работы) — пропуск.
        old_argv = sys.argv
        sys.argv = ["period_report.py", "yearly", "2027-01-01"]
        try:
            pr.main()  # не должен ничего собрать и не должен падать
        finally:
            sys.argv = old_argv
        self.assertFalse((pr.OUT_DIR / "yearly-2026-01-01_2026-12-31.html").exists())


if __name__ == "__main__":
    unittest.main()


class CoverageWordingTest(unittest.TestCase):
    """Вердикт и таблица не выдают неполное окно за измеренное (аудит 03.09.2026)."""

    @staticmethod
    def _m(total, covered, days=7, **kw):
        return {"label": "x", "total": total, "covered_days": covered, "days": days, **kw}

    def test_вердикт_только_по_полным_окнам(self):
        partial = pr._clicks_sentence(self._m(70, 4), self._m(100, 7))
        self.assertIn("не приводится", partial)
        self.assertIn("4 из 7 дн.", partial)
        self.assertNotIn("снизились", partial)
        full = pr._clicks_sentence(self._m(70, 7), self._m(100, 7))
        self.assertIn("снизились", full)

    def test_источник_без_данных_печатается_прочерком_а_не_нулём(self):
        self.assertEqual(pr._fmt_metric(self._m(0.0, 0)), "—")
        self.assertEqual(pr._fmt_metric(self._m(0.0, 7)), "0")
        self.assertTrue(pr._fully_covered(self._m(1, 7)))
        self.assertFalse(pr._fully_covered(self._m(1, 6)))
