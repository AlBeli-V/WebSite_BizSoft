"""Сборка спецификации расширения из отобранных фраз (21.09.2026).

Сотня фраз руками не собирается, а ошибка здесь тихая: лимит заголовка
Директа превышен на символ — и прогон падает на середине, оставив кампанию
наполовину заведённой. Ровно так 21.09 вышло с автотаргетингом.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ppc"))
import spec_from_targets as S  # noqa: E402

TITLES = {"bmd-resolve-studio": "DaVinci Resolve Studio",
          "gemini-workspace-enterprise": "Корпоративный Google Workspace с Gemini: безопасность"}
VENDORS = {"blackmagic": "Blackmagic Design", "google": "Google",
           "freepik": "Magnific (Freepik)"}
LIVE = {"/product/bmd-resolve-studio", "/vendors/google", "/vendors/freepik"}


def targets(rows):
    return {"intent": "commercial", "min_frequency": 30, "ready": rows}


class LimitsTest(unittest.TestCase):
    def test_длинное_имя_не_обрезается_а_сокращается_текст(self):
        ads = S.ads_for("DaVinci Resolve Studio", "Blackmagic Design")
        self.assertTrue(ads[0]["title1"].startswith("DaVinci Resolve Studio"))
        for a in ads:
            self.assertLessEqual(len(a["title1"]) + len(a["title2"]), 52)
            self.assertLessEqual(len(a["text"]), 81)

    def test_короткое_имя_получает_развёрнутый_текст(self):
        ads = S.ads_for("Suno", "Suno")
        self.assertIn("лицензия", ads[0]["text"])


class NameTest(unittest.TestCase):
    def test_составное_имя_теряет_скобки(self):
        self.assertEqual(S.pretty_name("/vendors/freepik", "freepik", {}, VENDORS), "Magnific")

    def test_название_карточки_обрезается_до_продукта(self):
        name = S.pretty_name("/product/gemini-workspace-enterprise", "google", TITLES, VENDORS)
        self.assertEqual(name, "Google Workspace")


class BuildTest(unittest.TestCase):
    def rows(self):
        return [
            {"phrase": "davinci resolve купить", "frequency": 1000,
             "url": "/product/bmd-resolve-studio", "vendor": "blackmagic", "position": None},
            {"phrase": "gemini купить", "frequency": 5300,
             "url": "/vendors/google", "vendor": "google", "position": 9},
            {"phrase": "лицензии freepik", "frequency": 30,
             "url": "/vendors/me", "vendor": "me", "position": None},
        ]

    def build(self, exclude=None):
        return S.build(targets(self.rows()), "bs-catalog-2026-09", TITLES,
                       exclude or set(), vendors=VENDORS, paths=LIVE)

    def test_мёртвая_посадочная_в_кампанию_не_попадает(self):
        spec = self.build()
        self.assertEqual([d["url"] for d in spec["dropped"]], ["/vendors/me"])
        self.assertNotIn("/vendors/me", [g["landing"] for g in spec["groups"]])

    def test_фразы_прошлого_раунда_не_дублируются(self):
        spec = self.build(exclude={"gemini купить"})
        phrases = [k["keyword"] for g in spec["groups"] for k in g["keywords"]]
        self.assertNotIn('"gemini купить"', phrases)

    def test_фразы_идут_в_строгом_соответствии(self):
        spec = self.build()
        for g in spec["groups"]:
            for k in g["keywords"]:
                self.assertTrue(k["keyword"].startswith('"') and k["keyword"].endswith('"'))

    def test_группы_по_убыванию_спроса(self):
        spec = self.build()
        demand = [sum(k["wordstat_frequency"] for k in g["keywords"]) for g in spec["groups"]]
        self.assertEqual(demand, sorted(demand, reverse=True))

    def test_бюджет_и_автотаргетинг_заданы_как_в_кампании(self):
        spec = self.build()
        self.assertEqual(spec["plan_kind"], "extend_campaign")
        self.assertEqual(spec["campaign"]["autotargeting"], "off")
        self.assertNotIn("strategy", spec["campaign"])  # бюджет не трогаем


if __name__ == "__main__":
    unittest.main()
