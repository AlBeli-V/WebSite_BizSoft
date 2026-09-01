#!/usr/bin/env python3
"""Allocator: единый отбор ≤5 действий недели из кандидатов всех детекторов."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402


def cand(key, score, source="радар возможностей"):
    return {"key": key, "title": key, "action": "a", "evidence": "e",
            "source": source, "score": score, "confidence": "low", "effort": 1}


class TestSelect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.al = mocks.load("allocator")

    def test_limit_and_order(self):
        cands = [cand(f"q{i}", i / 10, source=f"s{i}") for i in range(8)]
        picked, sa, sn = self.al.select(cands, set(), set())
        self.assertEqual(len(picked), self.al.LIMIT)
        self.assertEqual(picked[0]["key"], "q7")   # сильнейший первым
        self.assertEqual(picked[0]["rank"], 1)
        self.assertEqual((sa, sn), (0, 0))

    def test_dedup_by_key(self):
        cands = [cand("same", 0.9), cand("same", 0.5, source="s2")]
        picked, _, _ = self.al.select(cands, set(), set())
        self.assertEqual(len(picked), 1)

    def test_active_actions_excluded(self):
        """Открытое действие не предлагается заново."""
        cands = [cand("claude team купить", 0.9), cand("другое", 0.5)]
        picked, sa, _ = self.al.select(
            cands, {"страница под claude team купить"}, set())
        self.assertEqual([c["key"] for c in picked], ["другое"])
        self.assertEqual(sa, 1)

    def test_negative_knowledge_excluded(self):
        """Отклонённая гипотеза не тестируется повторно."""
        cands = [cand("faq на карточке", 0.9), cand("другое", 0.5)]
        picked, _, sn = self.al.select(cands, set(), {"faq на карточке"})
        self.assertEqual([c["key"] for c in picked], ["другое"])
        self.assertEqual(sn, 1)

    def test_source_diversity(self):
        """Один детектор не забирает всю неделю (≤MAX_PER_SOURCE мест)."""
        cands = [cand(f"r{i}", 0.9 - i / 100) for i in range(5)]
        cands.append(cand("momentum-фраза", 0.1, source="momentum Вордстата"))
        picked, _, _ = self.al.select(cands, set(), set())
        sources = [c["source"] for c in picked]
        self.assertEqual(sources.count("радар возможностей"),
                         self.al.MAX_PER_SOURCE)
        self.assertIn("momentum Вордстата", sources)


class TestCandidateFilters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.al = mocks.load("allocator")

    def test_norm(self):
        self.assertEqual(self.al._norm(50, 100), 0.5)
        self.assertEqual(self.al._norm(200, 100), 1.0)
        self.assertEqual(self.al._norm(5, 0), 0.0)

    def test_page_type(self):
        self.assertEqual(self.al._page_type("/product/x"), "product")
        self.assertEqual(self.al._page_type("/vendors/figma"), "vendor")
        self.assertEqual(self.al._page_type("/alternatives/zoom"), "alternatives")
        self.assertEqual(self.al._page_type("/about"), "other")


if __name__ == "__main__":
    unittest.main()
