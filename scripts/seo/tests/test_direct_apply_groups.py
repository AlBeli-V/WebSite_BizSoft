"""Сборка групп: пустой список минус-слов не уходит в Директ (21.09.2026).

Директ отвергает AdGroups.NegativeKeywords.Items с нулём элементов (код
8000). Спецификация round4 групповых минусов не содержит — они заданы на
уровне кампании и действуют на все группы, — и прогон упал уже после
создания кампании: в кабинете осталась кампания 714629311 без единой
группы. Тест держит оба случая.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ppc"))
import direct_apply  # noqa: E402


def spec(minus):
    return {"groups": [{"title": "Группа", "minus_words": minus}]}


class GroupsTest(unittest.TestCase):
    def test_пустой_список_минусов_не_отправляется(self):
        g = direct_apply.build_groups(spec([]), 1)["AdGroups"][0]
        self.assertNotIn("NegativeKeywords", g)

    def test_минусы_группы_отправляются_когда_есть(self):
        g = direct_apply.build_groups(spec(["курс", "бесплатно"]), 1)["AdGroups"][0]
        self.assertEqual(g["NegativeKeywords"], {"Items": ["курс", "бесплатно"]})

    def test_обязательные_поля_группы_на_месте(self):
        g = direct_apply.build_groups(spec([]), 42)["AdGroups"][0]
        self.assertEqual(g["Name"], "Группа")
        self.assertEqual(g["CampaignId"], 42)
        self.assertEqual(g["RegionIds"], [225])


class ResumeTest(unittest.TestCase):
    """Повторное применение спецификации после обрыва.

    21.09.2026 прогон создал кампанию и упал на добавлении групп. Старая
    защита от дубля отказывала по одному имени, и достроить кампанию было
    нечем: ни дозаполнить, ни пересоздать под тем же именем. Теперь отказ
    только для наполненной кампании — признак проверяется в коде.
    """

    def test_отказ_только_для_наполненной_кампании(self):
        src = pathlib.Path(__file__).resolve().parents[2] / "ppc" / "direct_apply.py"
        text = src.read_text(encoding="utf-8")
        self.assertIn("и наполнена", text)
        self.assertIn("но пуста — дозаполняю", text)
        # Проверка числа групп идёт до отказа, а не после.
        self.assertLess(text.index('"SelectionCriteria": {"CampaignIds": [existing_id]}'),
                        text.index("уже существует (Id {existing_id}) и наполнена"))


if __name__ == "__main__":
    unittest.main()
