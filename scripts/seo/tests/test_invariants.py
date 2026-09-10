#!/usr/bin/env python3
"""Инварианты письма ловят нарушения — и молчат на корректном письме."""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402

MINUS = "−"

OK_SNAP = {"yandex": {"available": True}, "google": {"available": True},
           "analytics": {"metrika": {"available": True}, "ga4": {"available": True}}}
OK_DQ = {"findings": []}
OK_BLOCKS = {"kpis": [], "signals": [], "pills": [{"label": "ДАННЫЕ", "state": "limited"}]}


class TestInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inv = mocks.load("invariants")

    def test_clean_letter_has_no_violations(self):
        self.assertEqual(self.inv.check(OK_SNAP, OK_DQ, OK_BLOCKS, "текст"), [])

    def test_no_data_kpi_with_delta_is_violation(self):
        blocks = dict(OK_BLOCKS, kpis=[{"key": "google", "value": "нет данных",
                                        "delta": "+5", "relative": None}])
        v = self.inv.check(OK_SNAP, OK_DQ, blocks, "")
        self.assertTrue(any("нет данных" in x for x in v))

    def test_negative_delta_with_positive_tone_is_violation(self):
        blocks = dict(OK_BLOCKS, signals=[{"metric": "Показы", "tone": "positive",
                                           "delta": f"{MINUS}7"}])
        v = self.inv.check(OK_SNAP, OK_DQ, blocks, "")
        self.assertTrue(any("positive" in x for x in v))

    def test_positive_delta_with_negative_tone_is_violation(self):
        blocks = dict(OK_BLOCKS, signals=[{"metric": "Показы", "tone": "negative",
                                           "delta": "+7"}])
        v = self.inv.check(OK_SNAP, OK_DQ, blocks, "")
        self.assertTrue(any("negative" in x for x in v))

    def test_unavailable_source_requires_degraded_pill(self):
        snap = {"yandex": {"available": False}, "google": {"available": True},
                "analytics": {"metrika": {"available": True},
                              "ga4": {"available": True}}}
        v = self.inv.check(snap, OK_DQ, OK_BLOCKS, "")
        self.assertTrue(any("сбой" in x for x in v))
        blocks = dict(OK_BLOCKS, pills=[{"label": "ДАННЫЕ", "state": "degraded"}])
        self.assertEqual(self.inv.check(snap, OK_DQ, blocks, ""), [])

    def test_source_unavailable_finding_requires_degraded_pill(self):
        dq = {"findings": [{"code": "SOURCE_UNAVAILABLE", "source": "ga4"}]}
        v = self.inv.check(OK_SNAP, dq, OK_BLOCKS, "")
        self.assertTrue(any("сбой" in x for x in v))

    def test_unprovable_wording_is_violation(self):
        v = self.inv.check(OK_SNAP, OK_DQ, OK_BLOCKS, "показов по-прежнему нет")
        self.assertTrue(any("по-прежнему" in x for x in v))

    def test_unavailable_block_without_reason_code_blocks_the_letter(self):
        """Ложь о причине — блокирующая: письмо с такой строкой не выпускается."""
        blocks = dict(OK_BLOCKS, ads={"available": False,
                                      "reason": "инструмент ждёт токена Вебмастера"})
        t = self.inv.check_tiers(OK_SNAP, OK_DQ, blocks, "")
        self.assertTrue(any("без кода причины" in x for x in t["blocking"]))
        self.assertEqual(t["soft"], [])

    def test_passport_block_passes(self):
        import passport
        blocks = dict(OK_BLOCKS, ads=passport.unavailable("no_file", source="витрина Директа"))
        self.assertEqual(self.inv.check_tiers(OK_SNAP, OK_DQ, blocks, "")["blocking"], [])

    def test_old_data_without_stale_mark_blocks(self):
        blocks = dict(OK_BLOCKS, leads={"available": True, "as_of": "2026-08-30",
                                        "expected_as_of": "2026-09-02"})
        t = self.inv.check_tiers(OK_SNAP, OK_DQ, blocks, "")
        self.assertTrue(any("без пометки stale" in x for x in t["blocking"]))

    def test_checkpoint_dated_today_blocks(self):
        blocks = dict(OK_BLOCKS, date="2026-09-03",
                      checkpoints=[{"date": "03.09", "what": "SEO-EXP-002: сниппеты"}])
        t = self.inv.check_tiers(OK_SNAP, OK_DQ, blocks, "")
        self.assertTrue(any("днём письма" in x for x in t["blocking"]))
        blocks["checkpoints"] = [{"date": "16.09", "what": "SEO-EXP-002: сниппеты"}]
        self.assertEqual(self.inv.check_tiers(OK_SNAP, OK_DQ, blocks, "")["blocking"], [])

    def test_form_violations_stay_soft(self):
        blocks = dict(OK_BLOCKS, kpis=[{"key": "google", "value": "нет данных",
                                        "delta": "+5", "relative": None}])
        t = self.inv.check_tiers(OK_SNAP, OK_DQ, blocks, "показов по-прежнему нет")
        self.assertEqual(t["blocking"], [])
        self.assertEqual(len(t["soft"]), 2)

    def test_exposure_contradiction_is_soft(self):
        # Форма — как у experiments.build: стадия строкой в verdict, вердикт
        # движка в evaluation. Прежняя редакция теста подставляла словарь в
        # verdict, такой формы конвейер не отдаёт никогда — тест закреплял
        # ошибку кода вместо того, чтобы её поймать.
        blocks = dict(OK_BLOCKS, experiments=[{"ticket": "SEO-EXP-002", "exposure_ok": True,
                                               "verdict": "observing",
                                               "exposure_basis": "matched",
                                               "evaluation": {"verdict": "INSUFFICIENT_DATA"}}])
        t = self.inv.check_tiers(OK_SNAP, OK_DQ, blocks, "")
        self.assertTrue(any("порог пройден" in x for x in t["soft"]))

    def test_write_report_records_tiers(self):
        blocks = dict(OK_BLOCKS, ads={"available": False, "reason": "ждёт токена"})
        with tempfile.TemporaryDirectory() as tmp:
            out = self.inv.write_report("2026-09-03", OK_SNAP, OK_DQ, blocks,
                                        "", out_dir=pathlib.Path(tmp))
            self.assertTrue(out["blocked"])
            self.assertFalse(out["passed"])
            saved = json.loads((pathlib.Path(tmp) / "2026-09-03-invariants.json")
                               .read_text(encoding="utf-8"))
            self.assertEqual(saved["blocking"], out["blocking"])

    def test_write_report_records_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.inv.write_report("2026-08-25", OK_SNAP, OK_DQ, OK_BLOCKS,
                                        "текст", out_dir=pathlib.Path(tmp))
            self.assertTrue(out["passed"])
            saved = json.loads((pathlib.Path(tmp) / "2026-08-25-invariants.json")
                               .read_text(encoding="utf-8"))
            self.assertEqual(saved["violations"], [])

    # Форма блока экспериментов — как её собирает experiments.build, а не как
    # удобно тесту: verdict эксперимента — строка стадии, вердикт движка лежит
    # в evaluation.verdict. Инвариант S4, написанный под словарь, ронял сборку
    # письма на реальных данных (03.09.2026) и молчал на фикстурах.
    EXPERIMENT = {"ticket": "SEO-EXP-001", "verdict": "observing",
                  "exposure_ok": True, "exposure_basis": "matched",
                  "evaluation": {"verdict": "INSUFFICIENT_DATA"}}

    def test_experiment_stage_is_a_string_and_does_not_crash(self):
        blocks = dict(OK_BLOCKS, experiments=[self.EXPERIMENT])
        self.assertEqual(self.inv.check(OK_SNAP, OK_DQ, blocks, "текст"),
                         ["SEO-EXP-001: «порог пройден» при вердикте «мало данных»"])

    def test_экспозиция_кластера_без_чистого_окна_не_нарушение(self):
        # Решение 04.09.2026: пока окно источника захватывает период до
        # внедрения, совпадающего набора не существует — экспозиция кластера
        # набрана, а сравнивать не с чем. Это стадия, а не ложь: строка письма
        # называет дату чистого окна. Прежде инвариант ругался на пять
        # действующих экспериментов сразу.
        exp = dict(self.EXPERIMENT)
        exp.pop("exposure_basis")
        exp["evaluation"] = {"verdict": "INSUFFICIENT_DATA",
                             "clean_window_eta": "2026-09-13"}
        blocks = dict(OK_BLOCKS, experiments=[exp])
        self.assertEqual(self.inv.check(OK_SNAP, OK_DQ, blocks, "текст"), [])

    def test_exposure_below_gate_is_not_a_violation(self):
        exp = dict(self.EXPERIMENT, exposure_ok=False)
        blocks = dict(OK_BLOCKS, experiments=[exp])
        self.assertEqual(self.inv.check(OK_SNAP, OK_DQ, blocks, "текст"), [])

    def test_confirmed_verdict_with_exposure_is_not_a_violation(self):
        exp = dict(self.EXPERIMENT, evaluation={"verdict": "CONFIRMED"})
        blocks = dict(OK_BLOCKS, experiments=[exp])
        self.assertEqual(self.inv.check(OK_SNAP, OK_DQ, blocks, "текст"), [])

    def test_experiment_without_evaluation_is_not_a_violation(self):
        exp = {"ticket": "X", "verdict": "too_early", "exposure_ok": True}
        blocks = dict(OK_BLOCKS, experiments=[exp])
        self.assertEqual(self.inv.check(OK_SNAP, OK_DQ, blocks, "текст"), [])


class CitedVerdictTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inv = mocks.load("invariants")

    """S5: вердикт чужого эксперимента сверяется с журналом решений.

    Случай из отчёта за 09.09.2026. В журнале одна запись по
    cluster-depositphotos: 03.09.2026, CONFIRMED, EXPAND. В гипотезе
    CONTENT-002 стояло «вердикт CONFIRMED 02.09.2026: +70% показов»,
    в CONTENT-004 — «CONFIRMED 03.09.2026: +62%». Первая дата журналу
    не известна, и утверждение о ней не проверял никто.
    """

    LOG = {"cluster-depositphotos": {"dates": ["2026-09-03"],
                                     "verdict": "CONFIRMED",
                                     "owner_decision": "EXPAND",
                                     "ticket": "CONTENT-001"},
           # Решение того же дня по другому эксперименту: чужая дата не
           # должна оправдывать ссылку на CONTENT-001.
           "snippets-5-vendors": {"dates": ["2026-09-02"],
                                  "verdict": "INSUFFICIENT_DATA",
                                  "owner_decision": "EXPAND",
                                  "ticket": "SEO-EXP-001"}}

    def blocks(self, hypothesis):
        return {"owner_decisions": self.LOG,
                "experiments": [{"ticket": "CONTENT-002",
                                 "hypothesis": hypothesis,
                                 "treatment": "", "primary_metric": ""}]}

    def test_дата_из_журнала_нарушением_не_является(self):
        b = self.blocks("Приём, подтверждённый на кластере Depositphotos "
                        "(CONTENT-001, вердикт CONFIRMED 03.09.2026: +62% показов).")
        self.assertEqual(self.inv.cited_verdicts(b), [])

    def test_дата_которой_нет_в_журнале_нарушение(self):
        b = self.blocks("Приём, подтверждённый на кластере Depositphotos "
                        "(CONTENT-001, вердикт CONFIRMED 02.09.2026: +70% показов).")
        found = self.inv.cited_verdicts(b)
        self.assertEqual(len(found), 1)
        self.assertIn("CONTENT-002", found[0])
        self.assertIn("02.09.2026", found[0])

    def test_нарушение_остаётся_мягким(self):
        b = self.blocks("(CONTENT-001, вердикт CONFIRMED 02.09.2026)")
        self.assertIn("02.09.2026", " ".join(self.inv.soft(b, "")))
        # Письмо от этого не блокируется: текст правится в реестре на ветке
        # данных, а не в коде, и выпуск дня из-за него не останавливается.
        blocking = self.inv.blocking(OK_SNAP, OK_DQ, dict(b, **OK_BLOCKS))
        self.assertNotIn("02.09.2026", " ".join(blocking))

    def test_ссылка_на_чужую_дату_того_же_журнала_не_оправдание(self):
        # 02.09.2026 в журнале есть, но по SEO-EXP-001, а ссылаются на
        # CONTENT-001: совпадение дня не делает утверждение проверенным.
        b = self.blocks("(CONTENT-001, вердикт CONFIRMED 02.09.2026)")
        self.assertEqual(len(self.inv.cited_verdicts(b)), 1)

    def test_тикет_неизвестный_журналу_не_нарушение(self):
        b = self.blocks("(PAGES-EXP-001, вердикт CONFIRMED 02.09.2026)")
        self.assertEqual(self.inv.cited_verdicts(b), [])

    def test_без_журнала_проверка_молчит(self):
        b = self.blocks("(CONTENT-001, вердикт CONFIRMED 02.09.2026)")
        b["owner_decisions"] = {}
        self.assertEqual(self.inv.cited_verdicts(b), [])


if __name__ == "__main__":
    unittest.main()
