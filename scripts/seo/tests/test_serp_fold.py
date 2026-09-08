#!/usr/bin/env python3
"""Проверки вывода по замеру первого экрана выдачи."""

import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import serp_fold as sf  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
PROBE = ROOT / "data" / "seo" / "serp-fold-probe.json"


def row(query, role="target", mobile=None, desktop=1, blocks=0, kinds=None,
        answer=False, clicks=0):
    return {"query": query, "role": role, "impressions": 50, "clicks": clicks,
            "avg_position": 3.0, "serp_position": 1, "our_url": "/x",
            "observation": {"our_result_screen_mobile": mobile,
                            "our_result_screen_desktop": desktop,
                            "blocks_above_organic": blocks,
                            "block_kinds": kinds or [],
                            "answer_block_above": answer,
                            "snippet_visible_fully": True, "screenshot": None}}


class TestProbeFile(unittest.TestCase):
    def test_протокол_лежит_незаполненным_и_правило_записано(self):
        p = json.loads(PROBE.read_text(encoding="utf-8"))
        # Правило вывода обязано существовать до замера: иначе результат
        # будет истолкован под уже сделанную работу.
        for key in ("fold", "non_human", "intercepted", "control"):
            self.assertIn(key, p["decision_rule"])
        targets = [r for r in p["queries"] if r["role"] == "target"]
        self.assertGreaterEqual(len(targets), 5)
        self.assertTrue(any(r["role"] == "control_brand" for r in p["queries"]))
        # Целевые — только запросы без переходов: замеряется именно этот случай.
        self.assertTrue(all(r["clicks"] == 0 for r in targets))


class TestClassify(unittest.TestCase):
    def test_второй_экран_телефона_это_первый_экран(self):
        self.assertEqual(sf.classify(row("q", mobile=2, blocks=3))[0], "fold")

    def test_чистый_первый_экран_снимает_версию_вёрстки(self):
        self.assertEqual(sf.classify(row("q", mobile=1, blocks=1))[0], "non_human")

    def test_блок_с_ответом_важнее_позиции(self):
        # Быстрый ответ забирает клик даже с первого места органики.
        v, _ = sf.classify(row("q", mobile=1, blocks=1, answer=True,
                               kinds=["быстрый ответ"]))
        self.assertEqual(v, "intercepted")

    def test_зажатая_органика_отделена_от_обеих_версий(self):
        self.assertEqual(sf.classify(row("q", mobile=1, blocks=4))[0], "crowded")


class TestBuild(unittest.TestCase):
    def probe(self, rows):
        return {"measured_at": "2026-09-15", "decision_rule": {}, "queries": rows}

    def test_меньше_трёх_замеров_вывода_не_даёт(self):
        r = sf.build(self.probe([row("a", mobile=2), row("b", mobile=2),
                                 row("c"), row("d"), row("e")]))
        self.assertFalse(r["available"])

    def test_большинство_решает(self):
        r = sf.build(self.probe([row("a", mobile=2, blocks=3),
                                 row("b", mobile=3, blocks=4),
                                 row("c", mobile=1, blocks=1)]))
        self.assertTrue(r["decided"])
        self.assertEqual(r["verdict"], "fold")

    def test_ничья_не_выдаётся_за_вывод(self):
        r = sf.build(self.probe([row("a", mobile=2, blocks=3),
                                 row("b", mobile=1, blocks=1),
                                 row("c", mobile=1, blocks=4)]))
        self.assertFalse(r["decided"])
        self.assertEqual(r["verdict"], "не решено")

    def test_брендовый_контроль_снимает_объяснение_вёрсткой(self):
        rows = [row("a", mobile=2, blocks=3), row("b", mobile=2, blocks=3),
                row("c", mobile=2, blocks=3),
                row("бренд", role="control_brand", mobile=2, blocks=3, clicks=11)]
        r = sf.build(self.probe(rows))
        self.assertIn("вёрстка разницу не объясняет", r["control_note"])

    def test_брендовый_контроль_подтверждает_объяснение_вёрсткой(self):
        rows = [row("a", mobile=2, blocks=3), row("b", mobile=2, blocks=3),
                row("c", mobile=2, blocks=3),
                row("бренд", role="control_brand", mobile=1, blocks=1, clicks=11)]
        r = sf.build(self.probe(rows))
        self.assertIn("вёрстка разницу объясняет", r["control_note"])


if __name__ == "__main__":
    unittest.main()
