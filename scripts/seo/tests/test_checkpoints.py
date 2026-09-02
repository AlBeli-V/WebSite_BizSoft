"""Блок «Следующие проверки» (вопрос руководителя 02.09.2026).

Письмо от 02.09 показывало «02.09 — SEO-EXP-001: замер…» как предстоящую
проверку, хотя вердикт этой проверки был в том же письме. Следующая — это
строго будущая веха; проведённая сегодня отражается подписью и разбором в
«Контроле эксперимента».
"""

import datetime as dt
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import experiments  # noqa: E402
import report_v4  # noqa: E402

ACTIONS = {"actions": []}


class NextReviewTest(unittest.TestCase):
    def test_в_контрольный_день_следующая_веха_строго_будущая(self):
        start = dt.date(2026, 8, 19)
        today = dt.date(2026, 9, 2)          # веха 14 дней — сегодня
        self.assertEqual(experiments.next_review_for(start, today), "2026-09-02")
        # После оценки следующей считается веха строго позже сегодняшней.
        nxt = experiments.next_review_for(start, today + dt.timedelta(days=1))
        self.assertEqual(nxt, "2026-09-16")

    def test_последняя_веха_позади_даёт_None(self):
        start = dt.date(2026, 8, 1)
        self.assertIsNone(
            experiments.next_review_for(start, dt.date(2026, 9, 20)))


class CheckpointsTest(unittest.TestCase):
    def _exp(self, ticket, next_review, control_today=False, kind="ctr"):
        return {"ticket": ticket, "next_review": next_review,
                "control_date_today": control_today, "evaluation_kind": kind,
                "evaluation": {"verdict": "CONFIRMED"}}

    def test_сегодняшняя_дата_не_попадает_в_следующие(self):
        exps = [self._exp("SEO-EXP-001", "2026-09-16", control_today=True)]
        rows = report_v4._checkpoints(exps, ACTIONS, "2026-09-02")
        self.assertTrue(all(c["date"] != "02.09" for c in rows))
        self.assertEqual(rows[0]["date"], "16.09")

    def test_формулировка_следует_метрике_эксперимента(self):
        exps = [self._exp("CONTENT-001", "2026-09-16", kind="impressions_growth"),
                self._exp("PAGES-EXP-001", "2026-09-13", kind="launch")]
        rows = report_v4._checkpoints(exps, ACTIONS, "2026-09-02")
        text = " | ".join(c["what"] for c in rows)
        self.assertIn("роста показов", text)
        self.assertIn("индексации", text)
        self.assertNotIn("кликабельности", text)

    def test_задача_журнала_не_дублирует_эксперимент(self):
        exps = [self._exp("SEO-EXP-002", "2026-09-03")]
        actions = {"actions": [{"id": "SEO-EXP-002", "title": "Сниппеты шести карточек",
                                "due": "2026-09-03", "status": "in_progress",
                                "zone": "GREEN"}]}
        rows = report_v4._checkpoints(exps, actions, "2026-09-02")
        self.assertEqual(len([c for c in rows if "SEO-EXP-002" in c["what"]]), 1)

    def test_строки_идут_по_возрастанию_даты(self):
        exps = [self._exp("A", "2026-09-13"), self._exp("B", "2026-09-03"),
                self._exp("C", "2026-09-05")]
        rows = report_v4._checkpoints(exps, ACTIONS, "2026-09-02")
        self.assertEqual([c["date"] for c in rows], ["03.09", "05.09", "13.09"])


if __name__ == "__main__":
    unittest.main()
