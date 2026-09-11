#!/usr/bin/env python3
"""Money-радар и зоны позиций: коммерческий интент в полосе 4–20."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402


def query(text, *, imp=100, clicks=0, pos=6.0, intent="commercial",
          branded=False, engine="yandex"):
    return {"search_engine": engine, "entity_type": "query", "entity_id": text,
            "impressions": imp, "clicks": clicks, "ctr": None,
            "average_position": pos, "branded": branded, "intent": intent,
            "sample_size": imp, "confidence": "sufficient"}


def snap(entities, engine="yandex"):
    return {engine: {"available": True, "entities": entities},
            "google": {"available": False}} if engine == "yandex" else \
           {"yandex": {"available": False},
            "google": {"available": True, "entities": entities}}


class TestBands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = mocks.load("opportunity")

    def test_top3_is_its_own_zone(self):
        band = self.o.band_for(2.0)
        self.assertEqual(band["zone"], "top3")
        self.assertIn("сниппет", band["action"])

    def test_sweet_spot_covers_4_to_20(self):
        self.assertEqual(self.o.band_for(5.0)["zone"], "first_page")
        self.assertEqual(self.o.band_for(15.0)["zone"], "second_page")
        self.assertEqual(self.o.band_for(30.0)["zone"], "far")

    def test_first_page_with_clicks_is_not_an_opportunity(self):
        s = snap([query("купить figma", clicks=3, pos=5.0)])
        self.assertEqual(self.o.from_queries(s, "yandex"), [])

    def test_top3_without_clicks_is_snippet_task(self):
        s = snap([query("купить figma", pos=2.0)])
        items = self.o.from_queries(s, "yandex")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["zone"], "top3")


class TestMoneyRadar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = mocks.load("opportunity")

    def test_commercial_sweet_spot_only(self):
        s = snap([
            query("купить figma", pos=6.0),                       # берём
            query("figma цена", pos=15.0),                        # берём
            query("что такое figma", pos=6.0, intent="informational"),
            query("bizsoft купить", pos=6.0, branded=True),
            query("купить canva", pos=2.0),                       # топ-3 — не сюда
            query("купить miro", pos=35.0),                       # далеко
            query("купить sketch", pos=6.0, imp=3),               # мало показов
        ])
        res = self.o.money_radar(s)
        self.assertTrue(res["available"])
        self.assertEqual([i["query"] for i in res["items"]],
                         ["купить figma", "figma цена"])
        self.assertIn("рыночным спросом не являются", res["note"])

    def test_sorted_by_impressions_and_limited(self):
        s = snap([query(f"купить продукт {i}", imp=10 + i, pos=8.0)
                  for i in range(20)])
        res = self.o.money_radar(s, limit=5)
        self.assertEqual(len(res["items"]), 5)
        imps = [i["impressions"] for i in res["items"]]
        self.assertEqual(imps, sorted(imps, reverse=True))
        self.assertEqual(res["considered"], 20)

    def test_empty_is_honest(self):
        res = self.o.money_radar(snap([]))
        self.assertFalse(res["available"])
        self.assertEqual(res["reason_code"], "no_signal")
        self.assertIn("меньше порога", res["reason"])


class TestExperimentMoratorium(unittest.TestCase):
    """Кластер под действующим опытом правкой не рекомендуется.

    09.09.2026 радар предлагал «переписать заголовок и описание страницы под
    запрос» по двум кластерам из трёх, и оба мерялись экспериментом:
    «оплата coreldraw для россиян» — CONTENT-003, «оплата artlist юридическим
    лицом» — SEO-EXP-004. В таблице money-запросов таких строк было шесть из
    девяти верхних. Правка обнуляет замер, ради которого опыт и заведён.
    """

    @classmethod
    def setUpClass(cls):
        cls.o = mocks.load("opportunity")

    EXPS = [
        {"id": "cluster-coreldraw", "ticket": "CONTENT-003", "status": "running",
         "query_markers": ["coreldraw", "корел"]},
        {"id": "cluster-heygen", "ticket": "CONTENT-005", "status": "done",
         "query_markers": ["heygen", "хейген"]},
    ]

    def with_exps(self, entities):
        s = snap(entities)
        s["experiments"] = self.EXPS
        return s

    def test_действующий_опыт_находится_по_маркеру(self):
        s = self.with_exps([])
        self.assertEqual(self.o.under_experiment("оплата coreldraw для россиян", s),
                         "CONTENT-003")
        self.assertEqual(self.o.under_experiment("оплата корел дро из россии", s),
                         "CONTENT-003")

    def test_завершённый_опыт_мораторий_не_держит(self):
        s = self.with_exps([])
        self.assertIsNone(self.o.under_experiment("купить heygen юридическим лицом", s))

    def test_свободный_кластер_не_придержан(self):
        s = self.with_exps([])
        self.assertIsNone(self.o.under_experiment("оплата magnific ai", s))

    def test_money_радар_называет_опыт_вместо_правки(self):
        s = self.with_exps([query("оплата coreldraw для россиян", imp=134, pos=8.08),
                            query("оплата magnific ai юрлицом", imp=58, pos=4.33)])
        rows = {i["query"]: i for i in self.o.money_radar(s)["items"]}
        held = rows["оплата coreldraw для россиян"]
        self.assertEqual(held["experiment"], "CONTENT-003")
        self.assertIn("под замером CONTENT-003", held["recommended_action"])
        self.assertIsNone(rows["оплата magnific ai юрлицом"]["experiment"])
        self.assertNotIn("под замером",
                         rows["оплата magnific ai юрлицом"]["recommended_action"])

    def test_радар_возможностей_придерживает_но_не_прячет(self):
        s = self.with_exps([query("оплата coreldraw для россиян", imp=500, pos=8.08),
                            query("оплата magnific ai юрлицом", imp=58, pos=4.33)])
        s["market_demand"] = {"available": False}
        res = self.o.build(s)
        clusters = [i["cluster"] for i in res["items"]]
        self.assertNotIn("оплата coreldraw для россиян", clusters)
        self.assertIn("оплата magnific ai юрлицом", clusters)
        self.assertEqual(res["held_by_experiment"],
                         [{"cluster": "оплата coreldraw для россиян",
                           "experiment": "CONTENT-003"}])

    def test_без_экспериментов_поведение_прежнее(self):
        s = snap([query("оплата coreldraw для россиян", imp=134, pos=8.08)])
        s["market_demand"] = {"available": False}
        self.assertEqual(self.o.build(s)["held_by_experiment"], [])
        self.assertIsNone(self.o.money_radar(s)["items"][0]["experiment"])


if __name__ == "__main__":
    unittest.main()
