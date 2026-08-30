#!/usr/bin/env python3
"""Регрессии правил отбора спроса.

Каждый случай здесь — фраза с фактического замера 21.08.2026, на которой
прежние правила ошибались. Числа в комментариях — частотность в месяц.

Запуск: python3 scripts/seo/tests/test_demand_rules.py
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "seo" / "wordstat"))

import normalize as N  # noqa: E402

# Данные из фикстур: копии machine-данных вычищены из main 30.08.2026.
N._DOMINANCE_PATH = (pathlib.Path(__file__).resolve().parent
                     / "fixtures/reports/seo/wordstat/brand-dominance.json")
N._DOMINANT_CACHE = None


def relevant(phrase: str, seed: str | None) -> bool:
    return N.in_scope(phrase) and N.relevant_to_seed(phrase, seed)


class TestОмонимичныеБренды(unittest.TestCase):
    def test_кроссовки_не_попадают_в_спрос(self):
        # «ai» внутри «air» пропускало Nike Air Zoom как признак софта.
        self.assertFalse(relevant("nike air zoom купить", "zoom купить")      )  # 687
        self.assertFalse(relevant("air zoom pegasus купить", "zoom купить")   )  # 243
        self.assertFalse(relevant("nike air zoom pegasus 41 купить", "zoom купить"))  # 76

    def test_маркер_ai_не_ищется_внутри_слова(self):
        self.assertTrue(N.has_software_marker("claude ai купить"))
        self.assertFalse(N.has_software_marker("nike air купить"))
        self.assertFalse(N.has_software_marker("hyundai solaris купить"))
        self.assertFalse(N.has_software_marker("clip studio paint"))

    def test_тариф_омонимичного_бренда_остаётся(self):
        self.assertTrue(relevant("zoom pro купить", "zoom купить"))
        self.assertTrue(relevant("zoom купить подписку", "zoom купить"))

    def test_голая_фраза_бренда_не_атрибутируется_без_замера(self):
        # 96 % пространства имени «zoom» — посторонний товар, поэтому голую
        # фразу нельзя записать ни вендору, ни мусору: у неё третий статус.
        self.assertEqual(N.attribution_of("zoom купить", "zoom купить"), "ambiguous")
        self.assertEqual(N.attribution_of("box купить", "box купить"), "ambiguous")

    def test_измеренно_доминирующий_бренд_забирает_голую_фразу(self):
        # У «cursor» 21 957 софтверных показов против нуля посторонних.
        self.assertEqual(N.attribution_of("cursor купить", "cursor купить"), "confident")


class TestТехника(unittest.TestCase):
    def test_смартфоны_не_являются_спросом_bizsoft(self):
        self.assertFalse(relevant("google pixel купить", "google")      )  # 31 598
        self.assertFalse(relevant("google pixel 10 pro купить", "google"))  # 6 168
        self.assertFalse(relevant("google fitbit air купить", "google")  )  # 3 417

    def test_название_модели_распознаётся(self):
        self.assertFalse(relevant("google 10 pro купить", "google") )  # 6 255
        self.assertFalse(relevant("google 9 купить", "google")      )  # 5 910
        self.assertFalse(relevant("купить google xl", "google")     )  # 3 845

    def test_товар_каталога_под_тем_же_брендом_остаётся(self):
        self.assertTrue(relevant("google workspace купить", "google"))
        self.assertTrue(relevant("google workspace для юрлиц", "google"))

    def test_pro_у_бренда_без_техники_это_тариф(self):
        # Правило моделей применяется только к брендам с линейкой устройств.
        self.assertFalse(N.looks_like_device_model("zoom pro", ["zoom"]))
        self.assertTrue(N.looks_like_device_model("google pro", ["google"]))


class TestИнтент(unittest.TestCase):
    def test_поломка_без_признака_оплаты_не_коммерческая(self):
        # «google не работает» — 13 018 показов, попадало в коммерческий спрос.
        self.assertNotEqual(N.classify_intent("google не работает"), "commercial")

    def test_невозможность_оплатить_из_рф_коммерческая(self):
        # Это ровно наш клиент: сервис нужен, а заплатить нечем.
        self.assertEqual(N.classify_intent("canva не принимает карты"), "commercial")
        self.assertEqual(N.classify_intent("оплата figma из россии"), "commercial")


class TestЧужойИнтент(unittest.TestCase):
    def test_платёжные_карты_для_физлиц_вне_области(self):
        self.assertFalse(N.in_scope("виртуальная карта для оплаты зарубежных сервисов"))

    def test_физические_товары_вне_области(self):
        self.assertFalse(N.in_scope("кроссовки zoom купить"))
        self.assertFalse(N.in_scope("assassins creed unity купить"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
