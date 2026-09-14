"""Сверка блока «Аудитория» с остальным письмом (правила contentcheck).

Три утверждения об одном предмете обязаны совпадать: итог показов блока и
карточка видимости читают один ряд; сумма каналов и сумма устройств равны
итогу системы; разбивка по устройствам покрывает показы. Расхождение — это
два разных числа об одном и том же в одном письме.
"""

import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import contentcheck  # noqa: E402

BASE = pathlib.Path("reports/seo/intelligence")


def _blocks(audience: dict) -> dict:
    return {"kpis": [{"key": "yandex", "value": "8 522", "unit": "показов за неделю",
                      "source": "Вебмастер", "period": "04.09–10.09",
                      "confidence": "достаточная", "muted": False,
                      "interpretation": "", "delta": None, "relative": None},
                     {"key": "google", "value": "98", "unit": "показов за неделю",
                      "source": "GSC", "period": "04.09–10.09",
                      "confidence": "достаточная", "muted": False,
                      "interpretation": "", "delta": None, "relative": None}],
            "audience": audience}


def _impressions(total_yandex: float, coverage: float = 1.0) -> dict:
    devices = {"desktop": total_yandex * coverage * 0.3,
               "mobile": total_yandex * coverage * 0.6,
               "tablet": total_yandex * coverage * 0.1}
    return {"available": True, "rows": [
        {"available": True, "key": "yandex", "label": "Яндекс",
         "total": total_yandex, "devices": devices,
         "devices_total": sum(devices.values()), "coverage": coverage}]}


def _visits(total: float, channel_total: float, device_total: float) -> dict:
    return {"available": True, "blocks": [
        {"available": True, "key": "metrika", "label": "Яндекс",
         "total": total, "devices": {"desktop": device_total},
         "channels": [{"key": "organic", "label": "Органика", "total": channel_total}]}]}


def _run(audience: dict) -> dict:
    """Только собственные проверки блока: остальные читают весь прогон."""
    checks = contentcheck.audience_checks(_blocks(audience))
    return {c["check"]: c for c in checks}


class AudienceConsistencyCase(unittest.TestCase):
    def test_impressions_equal_to_kpi_card(self):
        checks = _run({"available": True, "impressions": _impressions(8522),
                       "visits": {"available": False, "blocks": []}})
        self.assertTrue(checks["audience_matches_kpi"]["ok"])

    def test_impressions_differing_from_card_are_caught(self):
        checks = _run({"available": True, "impressions": _impressions(8000),
                       "visits": {"available": False, "blocks": []}})
        self.assertFalse(checks["audience_matches_kpi"]["ok"])
        self.assertIn("карточка 8522", checks["audience_matches_kpi"]["detail"])

    def test_channel_and_device_sums_must_equal_total(self):
        good = _run({"available": True,
                     "impressions": {"available": False, "rows": []},
                     "visits": _visits(100, 100, 100)})
        self.assertTrue(good["audience_internally_consistent"]["ok"])
        bad = _run({"available": True,
                    "impressions": {"available": False, "rows": []},
                    "visits": _visits(100, 90, 100)})
        self.assertFalse(bad["audience_internally_consistent"]["ok"])
        self.assertIn("сумма каналов", bad["audience_internally_consistent"]["detail"])

    def test_thin_device_coverage_is_caught(self):
        checks = _run({"available": True, "impressions": _impressions(8522, 0.7),
                       "visits": {"available": False, "blocks": []}})
        self.assertFalse(checks["audience_device_coverage"]["ok"])
        self.assertIn("покрытие 70%", checks["audience_device_coverage"]["detail"])


if __name__ == "__main__":
    unittest.main()
