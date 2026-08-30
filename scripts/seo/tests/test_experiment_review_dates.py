"""Контрольные точки экспериментов (вопрос руководителя 30.08.2026).

Письмо показывало прошедшую дату «26.08» в блоке «Следующие проверки»:
дефолт next_review был зашит строкой и не пересчитывался от старта.
Правило: «следующая проверка» — только будущая дата; явная дата реестра
уважается, пока не наступила; когда все вехи позади — точки нет.
"""

import datetime as dt
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from experiments import next_review_for  # noqa: E402
import report_v4  # noqa: E402


class NextReviewTest(unittest.TestCase):
    def test_прошедшая_явная_дата_заменяется_ближайшей_вехой(self):
        # Старт 19.08, в реестре явная точка 26.08, сегодня 30.08:
        # 26.08 позади, ближайшая веха — старт+14 = 02.09.
        got = next_review_for(dt.date(2026, 8, 19), dt.date(2026, 8, 30),
                              explicit="2026-08-26")
        self.assertEqual(got, "2026-09-02")

    def test_будущая_явная_дата_уважается(self):
        got = next_review_for(dt.date(2026, 8, 19), dt.date(2026, 8, 20),
                              explicit="2026-08-27")
        self.assertEqual(got, "2026-08-27")

    def test_без_явной_даты_первая_веха_от_старта(self):
        got = next_review_for(dt.date(2026, 8, 30), dt.date(2026, 8, 30))
        self.assertEqual(got, "2026-09-06")

    def test_все_вехи_позади_точки_нет(self):
        got = next_review_for(dt.date(2026, 7, 1), dt.date(2026, 8, 30))
        self.assertIsNone(got)

    def test_день_вехи_ещё_считается_будущим(self):
        got = next_review_for(dt.date(2026, 8, 23), dt.date(2026, 8, 30))
        self.assertEqual(got, "2026-08-30")


class CheckpointsBlockTest(unittest.TestCase):
    def test_эксперимент_без_точки_не_попадает_в_следующие_проверки(self):
        exps = [
            {"ticket": "SEO-EXP-001", "next_review": None},
            {"ticket": "SEO-EXP-002", "next_review": "2026-09-02"},
        ]
        cps = report_v4._checkpoints(exps, {"actions": []})
        self.assertEqual(len(cps), 1)
        self.assertIn("SEO-EXP-002", cps[0]["what"])


if __name__ == "__main__":
    unittest.main()
