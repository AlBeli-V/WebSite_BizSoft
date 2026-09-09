#!/usr/bin/env python3
"""google_gap: надбавка к GIPS за спрос со стороны выдачи.

Приоритет подачи на обход — единственный в проекте (решение руководителя
08.09.2026: две очереди с разными ответами хуже одной). Поэтому проверяется
не только счёт, но и то, что надбавка меняет порядок, а не подменяет
модель: базовый счёт остаётся в отчёте и в нём же сверяется.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402


def row(**kw):
    base = {
        "path": "/vendors/x", "page_type": "vendor", "yandex_position": 5,
        "yandex_state": "in_search", "google_impressions": 0,
        "google_crawled": False, "google_indexed": False,
        "serp_queries_held": 0, "serp_weakness_avg": 0,
    }
    base.update(kw)
    return base


class TestScore(unittest.TestCase):
    def setUp(self):
        self.m = mocks.load("google_gap")

    def test_base_score_unchanged_without_demand(self):
        """Страница без удерживаемого спроса считается ровно как раньше."""
        total, base, _ = self.m.score(row())
        self.assertEqual(total, base)

    def test_more_held_queries_ranks_higher(self):
        """Базовый счёт видит одну позицию по одному запросу: страница на 32
        запроса и страница на один получали поровну. Теперь — нет."""
        one, base_one, _ = self.m.score(row(serp_queries_held=1))
        many, base_many, _ = self.m.score(row(serp_queries_held=32))
        self.assertEqual(base_one, base_many)
        self.assertGreater(many, one)

    def test_weak_serp_ranks_higher(self):
        """Там, где топ Google занят UGC вместо продавцов, обход окупается
        быстрее — при прочих равных такая страница идёт раньше."""
        strong, _, _ = self.m.score(row(serp_queries_held=3, serp_weakness_avg=5))
        weak, _, _ = self.m.score(row(serp_queries_held=3, serp_weakness_avg=45))
        self.assertGreater(weak, strong)

    def test_bonus_is_capped(self):
        """Надбавка ограничена: спрос уточняет порядок, но не отменяет
        коммерческий вес типа страницы и состояние обхода."""
        _, base, _ = self.m.score(row(page_type="blog_tag"))
        total, _, _ = self.m.score(
            row(page_type="blog_tag", serp_queries_held=500, serp_weakness_avg=100))
        self.assertLessEqual(total - base, 20)

    def test_score_never_leaves_scale(self):
        top, _, tier = self.m.score(
            row(yandex_position=1, page_type="vendor", google_impressions=99,
                serp_queries_held=99, serp_weakness_avg=99))
        self.assertLessEqual(top, 100)
        self.assertEqual(tier, "TIER 1")
        low, _, _ = self.m.score(
            row(yandex_position=None, yandex_state="excluded", page_type="blog_tag",
                google_crawled=True, google_indexed=True))
        self.assertGreaterEqual(low, 0)

    def test_report_keeps_base_score_for_audit(self):
        """gips_base — в списке колонок отчёта: без него нельзя проверить,
        что надбавка меняет порядок, а не переписывает модель."""
        self.assertIn("gips_base", self.m.FIELDS)
        self.assertIn("serp_queries_held", self.m.FIELDS)
        self.assertIn("serp_weakness_avg", self.m.FIELDS)


if __name__ == "__main__":
    unittest.main()
