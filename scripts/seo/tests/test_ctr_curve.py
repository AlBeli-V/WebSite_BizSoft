"""Кривая CTR по позициям: отбор окон, интервалы, дисквалификация корзин.

Главное, что проверяется, — кривая не выдаёт за оценку позиции то, что на
самом деле описывает один крупный запрос, и не складывает перекрывающиеся
окна источника.
"""

import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
# snapshot импортирует соседние модули по короткому имени, поэтому каталог
# конвейера обязан быть в пути и при запуске одного этого файла.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import mocks  # noqa: E402

cc = mocks.load("ctr_curve")


def query(text, shows, clicks, position):
    return {"query_text": text,
            "indicators": {"TOTAL_SHOWS": shows, "TOTAL_CLICKS": clicks,
                           "AVG_SHOW_POSITION": position}}


def write_slice(dir_path, name, date_from, date_to, queries):
    (dir_path / name).write_text(json.dumps({
        "date": date_to,
        "popular_queries": {"date_from": date_from, "date_to": date_to,
                            "queries": queries},
    }, ensure_ascii=False), encoding="utf-8")


class TestWilson(unittest.TestCase):
    def test_interval_stays_inside_unit_range(self):
        lo, hi = cc.wilson(0, 500)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)
        self.assertLess(hi, 0.05)

    def test_small_sample_gives_wide_interval(self):
        narrow = cc.wilson(50, 5000)
        wide = cc.wilson(1, 100)
        self.assertLess(narrow[1] - narrow[0], wide[1] - wide[0])

    def test_no_shows_is_not_a_division_error(self):
        self.assertEqual(cc.wilson(0, 0), (0.0, 0.0))


class TestWindowPick(unittest.TestCase):
    def test_overlapping_windows_are_never_summed(self):
        slices = [
            {"source": "a", "from": "2026-08-01", "to": "2026-08-12", "shows": 100},
            {"source": "b", "from": "2026-08-05", "to": "2026-08-16", "shows": 120},
        ]
        picked = cc.pick_windows(slices)
        self.assertEqual(len(picked), 1)
        self.assertEqual(picked[0]["source"], "b")

    def test_two_narrow_windows_beat_one_wide(self):
        """Жадный отбор взял бы широкое окно и проиграл бы по показам."""
        slices = [
            {"source": "narrow-1", "from": "2026-08-01", "to": "2026-08-10", "shows": 90},
            {"source": "narrow-2", "from": "2026-08-11", "to": "2026-08-20", "shows": 90},
            {"source": "wide", "from": "2026-08-01", "to": "2026-08-20", "shows": 150},
        ]
        picked = cc.pick_windows(slices)
        self.assertEqual([w["source"] for w in picked], ["narrow-1", "narrow-2"])

    def test_adjacent_windows_both_taken(self):
        slices = [
            {"source": "a", "from": "2026-08-01", "to": "2026-08-10", "shows": 10},
            {"source": "b", "from": "2026-08-11", "to": "2026-08-20", "shows": 10},
        ]
        self.assertEqual(len(cc.pick_windows(slices)), 2)

    def test_no_slices(self):
        self.assertEqual(cc.pick_windows([]), [])


class TestBuild(unittest.TestCase):
    def bucket(self, curve, name):
        return next(p for p in curve["points"] if p["position"] == name)

    def test_bucket_dominated_by_one_query_is_unusable(self):
        """Корзина из одного крупного запроса описывает запрос, а не позицию."""
        window = {"queries": [query("бренд", 900, 700, 1.1),
                              query("хвост", 100, 1, 1.2)]}
        point = self.bucket(cc.build([window]), "1")
        self.assertEqual(point["impressions"], 1000)
        self.assertFalse(point["usable"])
        self.assertIn("один запрос", point["unusable_reason"])

    def test_thin_bucket_is_unusable(self):
        window = {"queries": [query(f"q{i}", 10, 0, 6.0) for i in range(10)]}
        point = self.bucket(cc.build([window]), "6–7")
        self.assertEqual(point["impressions"], 100)
        self.assertFalse(point["usable"])
        self.assertIn("мало показов", point["unusable_reason"])

    def test_wide_bucket_is_usable_and_ctr_is_weighted(self):
        window = {"queries": [query(f"q{i}", 100, 1, 6.0) for i in range(40)]}
        point = self.bucket(cc.build([window]), "6–7")
        self.assertEqual(point["impressions"], 4000)
        self.assertEqual(point["clicks"], 40)
        self.assertAlmostEqual(point["ctr"], 0.01, places=4)
        self.assertTrue(point["usable"])
        self.assertLess(point["ctr_low"], point["ctr"])
        self.assertGreater(point["ctr_high"], point["ctr"])

    def test_query_without_position_is_skipped(self):
        window = {"queries": [query("без позиции", 500, 5, None),
                              query("с позицией", 600, 6, 3.0)]}
        curve = cc.build([window])
        self.assertEqual(sum(p["impressions"] for p in curve["points"]), 600)


class TestEndToEnd(unittest.TestCase):
    def test_run_writes_curve_without_approving_it(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            data = root / "data"
            data.mkdir()
            write_slice(data, "yandex-2026-09-01.json", "2026-08-01", "2026-08-12",
                        [query(f"q{i}", 100, 1, 4.0) for i in range(40)])
            # Перекрывающийся срез: в расчёт войти не должен.
            write_slice(data, "yandex-2026-09-02.json", "2026-08-05", "2026-08-16",
                        [query(f"q{i}", 10, 0, 4.0) for i in range(5)])
            out = root / "ctr-curve.json"
            argv = sys.argv
            sys.argv = ["ctr_curve", "--data-dir", str(data), "--out", str(out)]
            try:
                self.assertEqual(cc.main(), 0)
            finally:
                sys.argv = argv
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertFalse(payload["approved"])
            self.assertEqual(len(payload["windows"]), 1)
            self.assertEqual(payload["coverage"]["impressions"], 4000)
            self.assertEqual(payload["coverage"]["slices_available"], 2)


class TestSnapshotReadsCurve(unittest.TestCase):
    """Снимок сам кривую не утверждает и без реестра ведёт себя как прежде."""

    @classmethod
    def setUpClass(cls):
        cls.s = mocks.load("snapshot")

    def with_curve(self, payload):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "ctr-curve.json"
            if payload is not None:
                path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with mock.patch.object(self.s, "CTR_CURVE", path):
                return self.s.build_ctr_model()

    def test_missing_registry_keeps_old_behaviour(self):
        model = self.with_curve(None)
        self.assertFalse(model["approved"])
        self.assertNotIn("curve", model)

    def test_computed_but_not_approved_hides_the_curve(self):
        model = self.with_curve({
            "approved": False, "coverage": {"impressions": 19969, "clicks": 171},
            "points": [{"position": "3", "usable": True},
                       {"position": "1", "usable": False}]})
        self.assertFalse(model["approved"])
        self.assertTrue(model["computed"])
        self.assertEqual(model["buckets_usable"], 1)
        self.assertEqual(model["buckets_total"], 2)
        self.assertIsNone(model["curve"])

    def test_approved_registry_exposes_the_curve(self):
        model = self.with_curve({
            "approved": True, "coverage": {"impressions": 19969, "clicks": 171},
            "points": [{"position": "3", "usable": True}]})
        self.assertTrue(model["approved"])
        self.assertEqual(len(model["curve"]), 1)

    def test_broken_registry_is_not_an_approved_model(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "ctr-curve.json"
            path.write_text("{не json", encoding="utf-8")
            with mock.patch.object(self.s, "CTR_CURVE", path):
                model = self.s.build_ctr_model()
        self.assertFalse(model["approved"])
        self.assertIn("не читается", model["note"])


if __name__ == "__main__":
    unittest.main()
