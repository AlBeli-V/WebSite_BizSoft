"""Пакет доводки Директа, раунд 2 (02.09.2026): guard непересечения.

Минус-слово, совпадающее по корню с собственной ключевой фразой, тушит
свою же семантику: одиночное «команды» задевает «claude code +для
команды» — первую B2B-фразу кампании, давшую клик. Поэтому пакет
применяется только после проверки корней, и проверка обязана падать.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ppc"))
import direct_refine  # noqa: E402

GNAMES = {
    1: "Claude — подписки для компаний",
    2: direct_refine.CLAUDE_CODE_GROUP,
    3: "Adobe — подписки для юрлиц",
}
PHRASES = {
    1: ["claude купить", "оплатить claude +из россии"],
    2: ["claude code +для команды", "claude code цена", "claude code enterprise"],
    3: ["adobe купить", "лицензия adobe", "adobe +для юридических лиц"],
}


class GuardTest(unittest.TestCase):
    def test_current_package_passes(self):
        """Пакет как он есть — по живой семантике кампании конфликтов нет."""
        direct_refine.guard_no_overlap(PHRASES, GNAMES)

    def test_word_matching_own_phrase_fails(self):
        """Одиночное «команды» ловится корнем и роняет прогон."""
        saved = direct_refine.CAMPAIGN_NEGATIVES_ADD
        direct_refine.CAMPAIGN_NEGATIVES_ADD = [
            ("команды", "команд", "справочник команд claude code")]
        try:
            with self.assertRaises(SystemExit):
                direct_refine.guard_no_overlap(PHRASES, GNAMES)
        finally:
            direct_refine.CAMPAIGN_NEGATIVES_ADD = saved

    def test_negative_phrase_inside_own_phrase_fails(self):
        """Минус-фраза, входящая в собственную фразу группы, тоже роняет."""
        saved = direct_refine.GROUP_NEGATIVE_PHRASES
        direct_refine.GROUP_NEGATIVE_PHRASES = {
            direct_refine.CLAUDE_CODE_GROUP: [
                ("claude code цена", "claude code цена", "выдуманный конфликт")],
        }
        try:
            with self.assertRaises(SystemExit):
                direct_refine.guard_no_overlap(PHRASES, GNAMES)
        finally:
            direct_refine.GROUP_NEGATIVE_PHRASES = saved

    def test_deposit_intent_not_applied(self):
        """«пополнить» — интент оплаты, минусуется только решением владельца."""
        applied = ({w for w, _, _ in direct_refine.CAMPAIGN_NEGATIVES_ADD}
                   | {t for items in direct_refine.GROUP_NEGATIVE_PHRASES.values()
                      for t, _, _ in items})
        self.assertNotIn("пополнить", applied)
        self.assertIn("пополнить", {w for w, _ in direct_refine.DEFERRED})

    def test_new_phrases_avoid_group_negatives(self):
        """Новая фраза не должна содержать слово, уже стоящее минусом группы.

        «клод код нейросеть купить» дословно из ленты запросов взять
        нельзя: «нейросеть» стоит групповым минусом Claude Code с 31.08.
        """
        for phrase in direct_refine.NEW_PHRASES[direct_refine.CLAUDE_CODE_GROUP]:
            self.assertNotIn("нейросеть", phrase)


if __name__ == "__main__":
    unittest.main()
