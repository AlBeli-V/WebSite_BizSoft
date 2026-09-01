"""Тесты расчёта взвешенной видимости и B2B Share."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scoring import visibility  # noqa: E402


class TestCtrWeight(unittest.TestCase):
    def setUp(self):
        self.config = visibility.load_config()

    def test_кривая_убывает(self):
        """Вес позиции обязан монотонно убывать: иначе Share бессмысленен."""
        weights = [visibility.ctr_weight(p, self.config) for p in range(1, 21)]
        for earlier, later in zip(weights, weights[1:]):
            self.assertGreaterEqual(earlier, later)

    def test_вне_топ20_ноль(self):
        self.assertEqual(visibility.ctr_weight(21, self.config), 0.0)
        self.assertEqual(visibility.ctr_weight(0, self.config), 0.0)

    def test_первая_позиция_весит_больше_десятой(self):
        первая = visibility.ctr_weight(1, self.config)
        десятая = visibility.ctr_weight(10, self.config)
        self.assertGreater(первая, десятая * 5)


class TestFeatureFactor(unittest.TestCase):
    def setUp(self):
        self.config = visibility.load_config()

    def test_без_особенностей_не_меняет_вес(self):
        self.assertEqual(visibility.feature_factor(None, self.config), 1.0)
        self.assertEqual(visibility.feature_factor([], self.config), 1.0)

    def test_ai_ответ_понижает(self):
        self.assertLess(visibility.feature_factor(["ai_ответ"], self.config), 1.0)

    def test_берётся_самый_сильный_эффект_без_перемножения(self):
        """Складывать эффекты элементов выдачи — двойной счёт."""
        оба = visibility.feature_factor(["ai_ответ", "товарная_галерея"], self.config)
        только_ai = visibility.feature_factor(["ai_ответ"], self.config)
        self.assertEqual(оба, только_ai)

    def test_неизвестный_элемент_игнорируется(self):
        self.assertEqual(
            visibility.feature_factor(["невиданный_блок"], self.config), 1.0)


class TestShare(unittest.TestCase):
    def test_доля_считается(self):
        self.assertAlmostEqual(visibility.share(2.0, 8.0), 0.25)

    def test_пустое_поле_даёт_none_а_не_ноль(self):
        """NO DATA никогда не показывается как нулевая видимость."""
        self.assertIsNone(visibility.share(0.0, 0.0))
        self.assertIsNone(visibility.share(1.0, -1.0))


class TestQueryVisibility(unittest.TestCase):
    def setUp(self):
        self.config = visibility.load_config()

    def test_множители_по_умолчанию_нейтральны(self):
        """Пока интент не размечен, Share равен чистой CTR-кривой."""
        self.assertEqual(visibility.query_visibility(3, self.config),
                         visibility.ctr_weight(3, self.config))

    def test_множители_применяются(self):
        база = visibility.query_visibility(1, self.config)
        с_весом = visibility.query_visibility(1, self.config, b2b_intent=0.5)
        self.assertAlmostEqual(с_весом, база * 0.5)


if __name__ == "__main__":
    unittest.main()
