"""Окна сравнения из дневной витрины: равная длина, лаг, дыры, нулевые дни."""

import datetime as dt
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import daily_windows as dw  # noqa: E402

REPORT_DATE = "2026-08-26"


def series(source: str, start: str, days: int, value=10.0, skip=()):
    """Ряд подряд идущих дней с заданным значением; skip — пропущенные даты."""
    first = dt.date.fromisoformat(start)
    out = {}
    for metric in dw.METRICS[source]:
        out[metric] = {}
        for i in range(days):
            d = (first + dt.timedelta(days=i)).isoformat()
            if d not in skip:
                out[metric][d] = value
    return {"series": out, "updated_at": "2026-08-26T00:00:00+00:00"}


class TestWindows(unittest.TestCase):
    def test_equal_adjacent_windows_with_lag(self):
        blk = dw.build_source(REPORT_DATE, "yandex",
                              series("yandex", "2026-06-01", 90))
        self.assertTrue(blk["complete"])
        w = blk["windows"]["impressions"]
        # Лаг Яндекса 3 дня: текущее окно заканчивается 23.08.
        self.assertEqual(w["current"]["to"], "2026-08-23")
        self.assertEqual(w["current"]["from"], "2026-08-17")
        # Предыдущее окно той же длины, встык, без пересечения.
        self.assertEqual(w["previous"]["to"], "2026-08-16")
        self.assertEqual(w["previous"]["from"], "2026-08-10")
        self.assertEqual(w["delta"], 0.0)

    def test_horizon_shifts_window_back(self):
        """Граница зрелости источника двигает окно, сохраняя длину и стык."""
        store = series("yandex", "2026-06-01", 90)
        store["horizon"] = "2026-08-21"
        blk = dw.build_source(REPORT_DATE, "yandex", store)
        w = blk["windows"]["impressions"]
        # Лаг довёл бы окно до 23.08, но источник посчитал только по 21.08.
        self.assertEqual(w["current"]["to"], "2026-08-21")
        self.assertEqual(w["current"]["from"], "2026-08-15")
        # Предыдущее окно сдвинулось вместе с текущим: длина и стык прежние.
        self.assertEqual(w["previous"]["to"], "2026-08-14")
        self.assertEqual(w["previous"]["from"], "2026-08-08")
        self.assertTrue(blk["complete"])
        self.assertEqual(blk["horizon"], "2026-08-21")

    def test_horizon_later_than_lag_does_not_extend_window(self):
        """Горизонт из будущего не делает данные свежее, чем позволяет лаг."""
        store = series("yandex", "2026-06-01", 90)
        store["horizon"] = "2026-08-26"
        blk = dw.build_source(REPORT_DATE, "yandex", store)
        self.assertEqual(blk["windows"]["impressions"]["current"]["to"],
                         "2026-08-23")

    def test_broken_horizon_falls_back_to_lag(self):
        store = series("yandex", "2026-06-01", 90)
        store["horizon"] = "не дата"
        blk = dw.build_source(REPORT_DATE, "yandex", store)
        self.assertEqual(blk["windows"]["impressions"]["current"]["to"],
                         "2026-08-23")

    def test_aligned_window_takes_earliest_horizon(self):
        """Общее окно воронки кончается там, где кончился самый отстающий."""
        stores = {s: series(s, "2026-06-01", 90) for s in dw.METRICS}
        stores["yandex"]["horizon"] = "2026-08-20"
        out = dw.build_aligned(REPORT_DATE, stores)
        self.assertEqual(out["current"]["to"], "2026-08-20")
        self.assertEqual(out["current"]["from"], "2026-08-14")
        self.assertEqual(out["previous"]["to"], "2026-08-13")
        # Все источники обрезаны одним концом, а не каждый своим.
        for source in dw.METRICS:
            metric = dw.METRICS[source][0]
            self.assertEqual(out["sources"][source][metric]["current"]["to"],
                             "2026-08-20")

    def test_gap_blocks_delta_and_is_reported(self):
        blk = dw.build_source(REPORT_DATE, "yandex",
                              series("yandex", "2026-06-01", 90,
                                     skip=("2026-08-19",)))
        self.assertFalse(blk["complete"])
        self.assertIn("2026-08-19", blk["missing_dates"])
        self.assertIsNone(blk["windows"]["impressions"]["delta"])

    def test_analytics_missing_day_inside_span_is_zero(self):
        # У stat-API день без визитов отсутствует в ответе — это ноль.
        blk = dw.build_source(REPORT_DATE, "metrika",
                              series("metrika", "2026-07-06", 51,
                                     skip=("2026-08-12",)))
        self.assertTrue(blk["complete"])
        w = blk["windows"]["visits_organic"]
        # 12.08 попадает в предыдущее окно (19–25 текущее при лаге 1).
        self.assertEqual(w["previous"]["sum"], 6 * 10.0)
        self.assertEqual(w["delta"], 10.0)

    def test_search_source_missing_day_stays_gap(self):
        # У Вебмастера нули приходят явно; отсутствие даты — настоящая дыра.
        blk = dw.build_source(REPORT_DATE, "yandex",
                              series("yandex", "2026-06-01", 90,
                                     skip=("2026-08-20",)))
        self.assertFalse(blk["complete"])

    def test_analytics_missing_tail_is_gap_not_zero(self):
        # Дни после конца ряда нулями не считаются: данных ещё нет.
        blk = dw.build_source(REPORT_DATE, "metrika",
                              series("metrika", "2026-07-06", 40))
        self.assertFalse(blk["complete"])
        self.assertIn("2026-08-25", blk["missing_dates"])

    def test_empty_store_unavailable(self):
        blk = dw.build_source(REPORT_DATE, "gsc", None)
        self.assertFalse(blk["available"])
        self.assertFalse(blk["complete"])

    def test_tail_covers_both_windows(self):
        blk = dw.build_source(REPORT_DATE, "gsc",
                              series("gsc", "2026-06-27", 60))
        tail = blk["windows"]["impressions"]["tail"]
        self.assertEqual(len(tail), 2 * dw.WINDOW_DAYS)


if __name__ == "__main__":
    unittest.main()
