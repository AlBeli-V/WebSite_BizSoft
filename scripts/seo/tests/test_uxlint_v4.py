#!/usr/bin/env python3
"""Тесты UX lint письма V4: правило о причинных утверждениях со ссылкой на Google.

Регрессия к прогону 25.08 (issue #148): письмо честно написало «причина
изменения пока не определена», драйверов не было — и линт упал только из-за
слова «Google» в шапке и в названии показателя. Письмо за день задержали.

Фактические артефакты того дня лежат в fixtures/ (копия из ветки seo-data),
день с названной причиной берётся из отчётов репозитория за 19.08.
"""

import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
# Копии данных вычищены из main (контроль недели 30.08): реальный срез
# 19.08 живёт в фикстурах, зеркалируя структуру reports/seo.
REPORTS = FIXTURES / "reports/seo/intelligence"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / "seo" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestGoogleClaimHasPageEvidence(unittest.TestCase):
    """Доказательства требуются от утверждения о причине, а не от слова «Google»."""

    @classmethod
    def setUpClass(cls):
        cls.ux = load("uxlint_v4")
        # 25.08: драйверов нет, причина не названа — письмо обязано пройти.
        cls.blocks_25 = json.loads(
            (FIXTURES / "2026-08-25-v4-blocks.json").read_text(encoding="utf-8"))
        cls.vis_25 = cls.ux.strip_tags(
            (FIXTURES / "2026-08-25-v4.html").read_text(encoding="utf-8"))
        # 19.08: причина названа и подтверждена страницами.
        cls.blocks_19 = json.loads(
            (REPORTS / "2026-08-19-v4-blocks.json").read_text(encoding="utf-8"))
        cls.vis_19 = cls.ux.strip_tags(
            (REPORTS / "2026-08-19-v4.html").read_text(encoding="utf-8"))

    def evidence_ok(self, vis, blocks):
        """Условие проверки google_claim_has_page_evidence в том же виде, что в run()."""
        claim, _ = self.ux.google_causal_claim(vis, blocks)
        return (not claim) or bool(blocks.get("driver_rows"))

    def test_2508_state_is_the_real_one(self):
        """Состав данных 25.08: драйверов нет, причина явно не названа."""
        self.assertEqual(self.blocks_25["driver_rows"], [])
        self.assertFalse(self.blocks_25["drivers"]["available"])
        self.assertEqual(self.blocks_25["driver_summary"],
                         "Причина изменения пока не определена.")
        self.assertIn("Google", self.vis_25)

    def test_2508_passes(self):
        """На фактическом составе 25.08 линт проходит: утверждения о причине нет."""
        claim, note = self.ux.google_causal_claim(self.vis_25, self.blocks_25)
        self.assertFalse(claim, note)
        self.assertTrue(self.evidence_ok(self.vis_25, self.blocks_25))

    def test_mention_is_not_a_claim(self):
        """Упоминание источника и необновившийся Google утверждением не считаются."""
        blocks = {"drivers": {"available": False}, "driver_rows": []}
        vis = ("Видимость в Google: 41 показов за неделю (+23). "
               "Google не отдал новых данных: последний день выгрузки прежний — 22.08. "
               "Органический трафик · Google Search Console, весь сайт.")
        self.assertFalse(self.ux.google_causal_claim(vis, blocks)[0])
        self.assertTrue(self.evidence_ok(vis, blocks))

    def test_1908_still_passes(self):
        """День с названной и подтверждённой причиной проходит, как и раньше."""
        claim, _ = self.ux.google_causal_claim(self.vis_19, self.blocks_19)
        self.assertTrue(claim)
        self.assertTrue(self.blocks_19["driver_rows"])
        self.assertTrue(self.evidence_ok(self.vis_19, self.blocks_19))

    def test_claimed_cause_without_pages_fails(self):
        """Причина объявлена определённой, а страниц нет — линт обязан упасть.

        Структурный признак главнее текста: driver_rows пуст при
        drivers.available=true роняет проверку независимо от формулировок.
        """
        blocks = copy.deepcopy(self.blocks_19)
        blocks["driver_rows"] = []
        self.assertTrue(self.ux.google_causal_claim(self.vis_19, blocks)[0])
        self.assertFalse(self.evidence_ok(self.vis_19, blocks))

    def test_unsupported_causal_sentence_fails(self):
        """Необоснованное причинное утверждение о Google ловится и по тексту."""
        blocks = {"drivers": {"available": False}, "driver_rows": []}
        vis = ("Показы в Google за неделю: 18 → 41 (+23). "
               "Google стал чаще показывать наши карточки.")
        claim, note = self.ux.google_causal_claim(vis, blocks)
        self.assertTrue(claim)
        self.assertIn("стал чаще показывать", note)
        self.assertFalse(self.evidence_ok(vis, blocks))

    def test_causal_marker_with_evidence_passes(self):
        """Та же причина с перечисленными страницами нарушением не является."""
        blocks = {"drivers": {"available": True},
                  "driver_rows": [{"entity": "/vendors/jetbrains", "delta": 5}]}
        vis = "Рост показов в Google обеспечил /vendors/jetbrains: +5 показов."
        self.assertTrue(self.evidence_ok(vis, blocks))


if __name__ == "__main__":
    unittest.main()
