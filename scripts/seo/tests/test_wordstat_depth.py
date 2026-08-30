#!/usr/bin/env python3
"""Wordstat вглубь: momentum (динамика ядра) и региональная карта спроса."""

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
WS = ROOT / "scripts" / "seo" / "wordstat"
sys.path.insert(0, str(WS))
sys.path.insert(0, str(WS.parent))


def load(name):
    spec = importlib.util.spec_from_file_location(name, WS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def series(values, start_month="2025-07"):
    y, m = map(int, start_month.split("-"))
    out = []
    for v in values:
        out.append({"month": f"{y:04d}-{m:02d}", "value": v})
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


class TestMomentum(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load("momentum")

    def test_accelerating_trend(self):
        acc = self.m.acceleration(series([100, 100, 100, 100, 100, 100,
                                          100, 100, 100, 100, 200, 260]))
        self.assertEqual(acc["trend"], "accelerating")
        self.assertEqual(acc["recent_avg"], 230.0)

    def test_decelerating_trend(self):
        acc = self.m.acceleration(series([300, 300, 300, 300, 300, 300,
                                          300, 300, 300, 300, 120, 80]))
        self.assertEqual(acc["trend"], "decelerating")

    def test_low_base_hides_percentages(self):
        """Рост 5 → 15 показов — шум, а не ускорение (порог базы 50)."""
        acc = self.m.acceleration(series([5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 14, 16]))
        self.assertEqual(acc["trend"], "low_base")

    def test_short_series_is_honest(self):
        acc = self.m.acceleration(series([10, 20, 30]))
        self.assertEqual(acc["trend"], "insufficient_series")

    def test_yoy_ratio_needs_14_months(self):
        vals = [100] * 12 + [100, 100, 100, 100, 200, 260]
        acc = self.m.acceleration(series(vals, "2025-01"))
        self.assertIn("yoy_ratio", acc)
        self.assertEqual(acc["yoy_ratio"], 2.3)   # (200+260)/2 к (100+100)/2

    def test_parse_dynamics_both_shapes(self):
        rows = self.m.parse_dynamics(
            {"dynamics": [{"date": "2026-07-01T00:00:00Z", "value": "120"}]})
        self.assertEqual(rows, [{"month": "2026-07", "value": 120}])
        rows = self.m.parse_dynamics(
            {"points": [{"period": "2026-06-01", "count": 80}]})
        self.assertEqual(rows, [{"month": "2026-06", "value": 80}])
        self.assertEqual(self.m.parse_dynamics({}), [])


class TestRegionDemand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = load("region_demand")

    def test_parse_regions_sorts_and_limits(self):
        data = {"regions": [
            {"regionId": 2, "regionName": "Санкт-Петербург", "count": 50},
            {"regionId": 213, "regionName": "Москва", "count": 300},
        ]}
        rows = self.r.parse_regions(data)
        self.assertEqual(rows[0]["name"], "Москва")
        self.assertEqual(rows[0]["count"], 300)
        self.assertEqual(self.r.parse_regions({}), [])


if __name__ == "__main__":
    unittest.main()
