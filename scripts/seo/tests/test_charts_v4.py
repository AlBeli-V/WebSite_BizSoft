#!/usr/bin/env python3
"""Шкала эксперимента в письме: подписи считаются по данным, а не по вере в них."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import charts_v4  # noqa: E402


def exp(**kw):
    base = {"ticket": "SEO-EXP-001", "start": "2026-08-19", "days_elapsed": 3,
            "next_review": "2026-09-20", "control_date_today": False}
    base.update(kw)
    return base


class TestReviewLabel(unittest.TestCase):
    def test_дата_проверки_печатается_днём_и_месяцем(self):
        self.assertEqual(charts_v4.review_label(exp()), "проверка 20.09")

    def test_контрольная_дата_сегодня_названа_сегодняшней(self):
        """Наступившая веха «следующей» быть не может — так решено 02.09.2026."""
        self.assertEqual(
            charts_v4.review_label(exp(next_review=None, control_date_today=True)),
            "проверка сегодня")

    def test_без_вех_впереди_шкала_не_падает(self):
        """Отчёт за 16.09.2026 упал здесь: на 28-й день дата стала пустой.

        Пустая дата — штатное состояние: все вехи 7/14/28 позади, эксперимент
        ждёт вердикта. Письмо должно это сказать, а не сломаться.
        """
        self.assertEqual(
            charts_v4.review_label(exp(next_review=None, days_elapsed=28)),
            "вехи пройдены")


class TestElapsedLabel(unittest.TestCase):
    def test_внутри_минимальной_экспозиции_счёт_идёт_к_семи(self):
        self.assertEqual(charts_v4.elapsed_label(exp(days_elapsed=3)),
                         "прошло 3 из 7 дней")

    def test_за_пределами_экспозиции_из_семи_не_пишется(self):
        """«Прошло 28 из 7 дней» — верная цифра в неверной фразе."""
        self.assertEqual(charts_v4.elapsed_label(exp(days_elapsed=28)),
                         "прошло 28 дней")

    def test_неизмеренный_срок_называется_неизмеренным(self):
        self.assertEqual(charts_v4.elapsed_label(exp(days_elapsed=None)),
                         "срок не измерен")


class TestTimelineHtml(unittest.TestCase):
    def test_шкала_собирается_без_даты_проверки(self):
        html = charts_v4.timeline_html(exp(next_review=None, days_elapsed=28), 610)
        self.assertIn("вехи пройдены", html)
        self.assertIn("прошло 28 дней", html)
        self.assertNotIn("из 7 дней", html)


if __name__ == "__main__":
    unittest.main()
