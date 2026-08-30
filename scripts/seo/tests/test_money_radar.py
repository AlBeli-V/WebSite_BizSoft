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
        self.assertIn("сейчас нет", res["reason"])


if __name__ == "__main__":
    unittest.main()
