"""Очередь замера позиций (21.09.2026).

Правило «рекламируем только то, где нас нет в первой тройке» до сих пор
применялось к одному проценту спроса: остальные фразы никто не замерял, а
отбор считал их свободными. Очередь закрывает эту дыру — и сама не должна
стать источником лишних трат: замеренное в неё не возвращается, а то, что
продать нечем, в неё не попадает.
"""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "wordstat"))
import catalog_match as C  # noqa: E402
import serp_queue as Q  # noqa: E402

LEXICON = {"hardware_stop": ["pixel"], "generic_tokens": ["pro"],
           "class_synonyms": {}, "vendor_aliases": {}}
VENDORS = {"adobe": "Adobe", "google": "Google"}
CARDS = ["adobe-ps", "adobe-ai", "adobe-cc-std"]
TITLES = {"adobe-ps": "Adobe Photoshop", "adobe-ai": "Adobe Illustrator",
          "adobe-cc-std": "Adobe Creative Cloud"}


def catalog():
    return C.Catalog(lexicon=LEXICON, vendors=VENDORS, cards=CARDS,
                     sku_names={}, titles=TITLES)


def universe(tmp: pathlib.Path, rows: list[dict]) -> pathlib.Path:
    p = tmp / "universe.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return p


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.queue = self.tmp / "queue.json"
        self.rows = [
            {"phrase": "adobe photoshop купить", "commercial_intent_score": 0.8,
             "wordstat_frequency": 500},
            {"phrase": "google pixel купить", "commercial_intent_score": 0.9,
             "wordstat_frequency": 9000},
            {"phrase": "что такое adobe", "commercial_intent_score": 0.0,
             "wordstat_frequency": 900},
            {"phrase": "adobe illustrator купить", "commercial_intent_score": 0.7,
             "wordstat_frequency": 5},
        ]

    def build(self, measured=None):
        return Q.build(min_frequency=30, universe=universe(self.tmp, self.rows),
                       catalog=catalog(), measured=measured or set(),
                       queue_path=self.queue)

    def test_в_очередь_идёт_только_продаваемое(self):
        data = self.build()
        self.assertEqual([r["phrase"] for r in data["pending"]], ["adobe photoshop купить"])
        self.assertEqual(data["skipped"]["продавать нечего"], 1)

    def test_некоммерческое_и_редкое_не_замеряется(self):
        data = self.build()
        self.assertEqual(data["skipped"]["не коммерческая"], 1)
        self.assertEqual(data["skipped"]["спрос ниже порога"], 1)

    def test_уже_замеренное_в_очередь_не_возвращается(self):
        data = self.build(measured={"adobe photoshop купить"})
        self.assertEqual(data["pending"], [])
        self.assertEqual(data["skipped"]["уже замерено"], 1)

    def test_очередь_идёт_от_большего_спроса(self):
        self.rows.append({"phrase": "adobe illustrator купить сейчас",
                          "commercial_intent_score": 0.8, "wordstat_frequency": 900})
        data = self.build()
        self.assertEqual([r["frequency"] for r in data["pending"]], [900, 500])

    def test_разобранное_не_попадает_в_очередь_снова(self):
        self.build()
        moved = Q.mark_done(["adobe photoshop купить"], "2026-09-22", queue_path=self.queue)
        self.assertEqual(moved, 1)
        again = self.build()
        self.assertEqual(again["pending"], [])
        self.assertIn("adobe photoshop купить", again["done"])


class TakeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.queue = self.tmp / "queue.json"
        Q.save_queue({"pending": [{"phrase": f"фраза {i}", "frequency": 100 - i}
                                  for i in range(5)], "done": {}}, self.queue)

    def test_партия_ограничена_бюджетом(self):
        self.assertEqual(len(Q.take(2, queue_path=self.queue)), 2)

    def test_нулевой_бюджет_не_берёт_ничего(self):
        self.assertEqual(Q.take(0, queue_path=self.queue), [])

    def test_помечается_только_то_что_реально_замерено(self):
        Q.mark_done(["фраза 0"], "2026-09-22", queue_path=self.queue)
        left = [r["phrase"] for r in Q.load_queue(self.queue)["pending"]]
        self.assertNotIn("фраза 0", left)
        self.assertEqual(len(left), 4)


if __name__ == "__main__":
    unittest.main()
