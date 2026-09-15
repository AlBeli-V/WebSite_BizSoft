"""Зонд разреза «устройство × канал»: разбор ответов без сети.

Зонд — приёмка нового разреза, поэтому проверяется главное: молчание не
выдаётся за успех (прогон без единой выполненной проверки красный),
пропавший ряд и разъехавшееся покрытие видны, а незнакомое значение
измерения названо, а не утекает в «прочее» незаметно.
"""

import datetime as dt
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import audience_probe as ap  # noqa: E402
import collect_daily as cd  # noqa: E402

FROM, TO = dt.date(2026, 9, 4), dt.date(2026, 9, 14)
DAYS = [(FROM + dt.timedelta(days=i)).isoformat() for i in range(11)]


def series(values: dict) -> dict:
    return {metric: {d: value for d in DAYS} for metric, value in values.items()}


def full_search_series() -> dict:
    return series({"impressions": 100, "clicks": 5, "position": 12.0,
                   "impressions_desktop": 30, "impressions_mobile": 60,
                   "impressions_tablet": 10, "clicks_desktop": 2,
                   "clicks_mobile": 3, "clicks_tablet": 0})


class ProbeReportCase(unittest.TestCase):
    def setUp(self):
        ap.checks.clear()

    def tearDown(self):
        ap.checks.clear()

    def test_no_secrets_means_red_not_green(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            code = ap.main(["audience_probe.py", "5"])
        self.assertEqual(code, 1)
        self.assertIn("проверок не выполнено ни одной", ap.report())

    def test_all_series_present_is_green(self):
        ap.check_series("yandex", full_search_series(), cd.EXPECTED["yandex"])
        rows = {c["check"]: c for c in ap.checks}
        self.assertTrue(rows["ряды витрины"]["ok"])
        self.assertIn("отсутствуют: нет", rows["ряды витрины"]["detail"])

    def test_missing_device_series_is_named(self):
        broken = full_search_series()
        del broken["impressions_tablet"]
        ap.check_series("yandex", broken, cd.EXPECTED["yandex"])
        row = next(c for c in ap.checks if c["check"] == "ряды витрины")
        self.assertFalse(row["ok"])
        self.assertIn("impressions_tablet", row["detail"])

    def test_empty_series_is_warning_not_failure(self):
        """Планшетов может не быть вовсе — это не поломка сбора."""
        zeroed = {**full_search_series(), "impressions_tablet": {d: 0 for d in DAYS}}
        ap.check_series("gsc", zeroed, cd.EXPECTED["gsc"])
        row = next(c for c in ap.checks if c["check"] == "непустые дни")
        self.assertTrue(row["ok"])
        self.assertIn("impressions_tablet", row["detail"])

    def test_coverage_gap_is_red(self):
        thin = {**full_search_series(),
                "impressions_mobile": {d: 5 for d in DAYS}}
        ap.check_device_coverage("yandex", thin, "impressions",
                                 [f"impressions_{d}" for d in cd.YANDEX_DEVICE])
        row = next(c for c in ap.checks if c["check"] == "покрытие устройствами")
        self.assertFalse(row["ok"])
        self.assertIn("расхождение", row["detail"])

    def test_coverage_matches_is_green(self):
        ap.check_device_coverage("yandex", full_search_series(), "impressions",
                                 [f"impressions_{d}" for d in cd.YANDEX_DEVICE])
        row = next(c for c in ap.checks if c["check"] == "покрытие устройствами")
        self.assertTrue(row["ok"])

    def test_empty_base_series_is_not_judged(self):
        empty = {"impressions": {}, "impressions_desktop": {}}
        ap.check_device_coverage("gsc", empty, "impressions", ["impressions_desktop"])
        row = next(c for c in ap.checks if c["check"] == "покрытие устройствами")
        self.assertIsNone(row["ok"])
        self.assertIn("сверять нечего", row["detail"])

    def test_unknown_dimension_values_are_reported(self):
        """Новая группа каналов у источника обязана быть названа поимённо."""
        stat_rows = {"data": [
            {"dimensions": [{"id": "organic"}, {"id": "mobile"}], "metrics": [10]},
            {"dimensions": [{"id": "wifi"}, {"id": "console"}], "metrics": [1]},
        ]}
        referral_rows = {"data": [
            {"dimensions": [{"name": "vc.ru"}], "metrics": [3]},
            {"dimensions": [{"name": "nowhere.io"}], "metrics": [1]},
        ]}
        env = {"YANDEX_METRIKA_TOKEN": "t", "YANDEX_METRIKA_COUNTER_ID": "110206070"}
        with mock.patch.dict("os.environ", env, clear=True), \
                mock.patch.object(cd, "fetch_metrika",
                                  return_value=(series({m: 1 for m in cd.EXPECTED["metrika"]}), None)), \
                mock.patch.object(ap.base, "api_json",
                                  side_effect=[(stat_rows, None), (referral_rows, None)]):
            ap.probe_metrika(FROM, TO)
        rows = {c["check"]: c for c in ap.checks}
        self.assertFalse(rows["словарь каналов"]["ok"])
        self.assertIn("wifi", rows["словарь каналов"]["detail"])
        self.assertFalse(rows["словарь устройств"]["ok"])
        self.assertIn("console", rows["словарь устройств"]["detail"])
        # Домен вне реестра назван, чтобы решение о классе принимал человек.
        self.assertIn("nowhere.io", rows["реестр внешних переходов"]["detail"])

    def test_api_error_stops_source_without_killing_probe(self):
        with mock.patch.dict("os.environ", {"YANDEX_WEBMASTER_TOKEN": "t"}, clear=True), \
                mock.patch.object(cd, "fetch_yandex",
                                  return_value=(None, "HTTP 403: forbidden")):
            ap.probe_yandex(FROM, TO)
        rows = [c for c in ap.checks if c["source"] == "yandex"]
        self.assertFalse(rows[0]["ok"])
        self.assertIn("403", rows[0]["detail"])
        self.assertEqual(len(rows), 1)

    def test_device_indicator_rejected_is_red(self):
        """Вебмастер не принял device_type_indicator — ряды не появились."""
        without_devices = series({"impressions": 100, "clicks": 5})
        with mock.patch.dict("os.environ", {"YANDEX_WEBMASTER_TOKEN": "t"}, clear=True), \
                mock.patch.object(cd, "fetch_yandex",
                                  return_value=(without_devices, None)):
            ap.probe_yandex(FROM, TO)
        row = next(c for c in ap.checks if c["check"] == "device_type_indicator")
        self.assertFalse(row["ok"])
        self.assertIn("ни одного", row["detail"])


if __name__ == "__main__":
    unittest.main()
