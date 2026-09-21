"""Автотаргетинг новых групп: режим из спецификации (21.09.2026).

Решение руководителя: платим только за строгие совпадения заданных фраз.
Даже EXACT-режим оставляет Директу право подбирать похожие запросы, а
разбор трёх недель показал цену этого права — 24% расхода на классы C и D.

Проверяется, что режим читается из спецификации, что умолчание не меняет
прежнее поведение и что отключение идёт через остановку условия, а не
через обнуление категорий: обнулить все категории Директ не позволяет.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ppc"))
import direct_apply  # noqa: E402

SRC = (pathlib.Path(__file__).resolve().parents[2] / "ppc" / "direct_apply.py").read_text(encoding="utf-8")


class AutotargetingTest(unittest.TestCase):
    def test_режим_берётся_из_спецификации(self):
        self.assertIn('spec.get("campaign") or {}).get("autotargeting", "exact")', SRC)

    def test_отключение_через_остановку_условия(self):
        self.assertIn('call("keywords", "suspend"', SRC)

    def test_умолчание_прежнее(self):
        # Спецификации без поля продолжают работать в режиме EXACT-only.
        self.assertIn('"AutotargetingCategories": EXACT_ONLY', SRC)

    def test_exact_only_разрешает_ровно_одну_категорию(self):
        yes = [c for c in direct_apply.EXACT_ONLY if c["Value"] == "YES"]
        self.assertEqual([c["Category"] for c in yes], ["EXACT"])

    def test_автотаргетинг_гасится_и_при_создании_кампании(self):
        # Раньше ветка создания кампании режим не задавала вовсе.
        self.assertEqual(SRC.count("apply_autotargeting("), 3)


if __name__ == "__main__":
    unittest.main()
