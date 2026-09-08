#!/usr/bin/env python3
"""Проверки Money Query Opportunity Model."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import money_queries as mq  # noqa: E402


class TestIntent(unittest.TestCase):
    def test_b2b_выше_обычной_покупки(self):
        _, b2b = mq.intent_of("оплата capture one юридическим лицом")
        _, buy = mq.intent_of("купить capture one")
        self.assertGreater(b2b, buy)

    def test_дисквалификация_перебивает_покупку(self):
        # «купить» в запросе есть, деньгами он не станет.
        name, weight = mq.intent_of("купить и скачать бесплатно capture one")
        self.assertEqual(name, "disqualified")
        self.assertLess(weight, 0.1)

    def test_свой_бренд_не_считается_коммерческим(self):
        name, _ = mq.intent_of("cloude купить для юл biz-soft.pro")
        self.assertEqual(name, "navigational_own")


class TestCtrCurve(unittest.TestCase):
    def test_кривая_убывает(self):
        values = [mq.expected_ctr(p) for p in (1, 2, 3, 5, 8, 10, 15, 30)]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_достижимость_учтена(self):
        # Опорная кривая — отраслевая, в расчёт идёт её достижимая доля.
        self.assertAlmostEqual(mq.expected_ctr(1), mq.CTR_CURVE[1] * mq.ATTAINABLE)


class TestClustering(unittest.TestCase):
    slugs = {"capture-one", "freepik", "box", "dropbox"}

    def test_переставленные_слова_попадают_в_кластер(self):
        # Вебмастер отдаёт запросы в нормализованном виде.
        self.assertEqual(
            mq.cluster_of("capture оплата one лицом юридическим", self.slugs),
            "capture-one")

    def test_омоним_не_ломает_кластер(self):
        self.assertIsNone(mq.cluster_of("купить xbox game pass", self.slugs))
        self.assertEqual(mq.cluster_of("оплата dropbox для юрлица", self.slugs), "dropbox")

    def test_magnific_ведёт_на_freepik(self):
        self.assertEqual(
            mq.cluster_of("оплата magnific ai юридическим лицом", self.slugs), "freepik")

    def test_небрендовый_кластер_услуги(self):
        self.assertEqual(
            mq.cluster_of("оплата зарубежного по для юрлица документы", self.slugs),
            "generic-foreign-software")


class TestDemandShape(unittest.TestCase):
    def test_всплеск_с_откатом(self):
        # Кластер Recraft: доля падает до нуля и возвращается скачком.
        shape, _ = mq.demand_shape(
            [0.016, 0.014, 0.005, 0.001, 0.001, 0.013, 0.014, 0.033],
            [61, 50, 18, 3, 3, 81, 81, 216], 0.43)
        self.assertEqual(shape, "burst")

    def test_ровный_рост_всплеском_не_считается(self):
        shape, _ = mq.demand_shape(
            [0.015, 0.016, 0.021, 0.028, 0.033, 0.033, 0.034, 0.032],
            [58, 58, 79, 110, 139, 202, 202, 211], 0.59)
        self.assertEqual(shape, "growing")

    def test_затухание_требует_падения_и_доли_и_показов(self):
        # Доля падает, а показы стоят: сайт вырос в другом месте, кластер ровный.
        shape, _ = mq.demand_shape(
            [0.015, 0.014, 0.013, 0.014, 0.014, 0.010, 0.009, 0.008],
            [56, 51, 51, 53, 58, 61, 53, 50], 0.15)
        self.assertEqual(shape, "steady")
        shape, _ = mq.demand_shape(
            [0.112, 0.109, 0.099, 0.067, 0.041, 0.017, 0.010, 0.005],
            [426, 398, 379, 260, 172, 108, 59, 31], 0.51)
        self.assertEqual(shape, "decaying")

    def test_короткий_ряд_не_даёт_вывода(self):
        shape, _ = mq.demand_shape([0.01, 0.02, 0.02], [3, 22, 22], 0.37)
        self.assertEqual(shape, "unknown")


class TestRisk(unittest.TestCase):
    def test_занятый_кластер_почти_запрещён(self):
        risk, note = mq.risk_of("B", 0, "content-6-clusters", "/vendors/")
        self.assertGreaterEqual(risk, 0.9)
        self.assertIn("content-6-clusters", note)

    def test_топ3_с_переходами_дороже_топ3_без_них(self):
        with_clicks, _ = mq.risk_of("A", 4, None, "/vendors/")
        without, _ = mq.risk_of("A", 0, None, "/vendors/")
        self.assertGreater(with_clicks, without)


class TestOccupancy(unittest.TestCase):
    def test_код_считается_занятостью(self):
        # Партия snippets-10-expand выкачена в код, записи в реестре нет:
        # занятость по одному реестру отдала бы эти страницы под новую правку.
        occupied = mq.code_occupancy(pathlib.Path(__file__).resolve().parents[3])
        self.assertIn("unity", occupied)
        self.assertIn("anthropic", occupied)


class TestBacklog(unittest.TestCase):
    def base(self, **over):
        row = {"cluster": "x", "band": "B", "position": 5.0, "ctr": 0.0,
               "occupied_by": None, "demand_shape": "steady", "demand_note": "",
               "exposure_gate": True, "impressions_per_day": 10.0}
        row.update(over)
        return row

    def test_занятый_кластер_не_получает_действия(self):
        d = mq.diagnose(self.base(occupied_by="cluster-heygen"))
        self.assertEqual(d["experiment_type"], "blocked")
        self.assertEqual(d["priority"], "hold")

    def test_всплеск_уходит_в_наблюдение(self):
        d = mq.diagnose(self.base(demand_shape="burst"))
        self.assertEqual(d["experiment_type"], "observe")

    def test_ниже_порога_экспозиции_только_в_бэклог(self):
        d = mq.diagnose(self.base(exposure_gate=False, impressions_per_day=1.2))
        self.assertEqual(d["experiment_type"], "backlog")

    def test_вторая_страница_лечится_контентом(self):
        d = mq.diagnose(self.base(band="D", position=13.0))
        self.assertEqual(d["experiment_type"], mq.PROGRAM_B)


if __name__ == "__main__":
    unittest.main()
