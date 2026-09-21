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


if __name__ == "__main__":
    unittest.main()
