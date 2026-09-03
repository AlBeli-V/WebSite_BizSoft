"""Тесты построения реестра конкурентов из среза выдачи."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from discovery import registry, serp_source  # noqa: E402
from scoring import visibility  # noqa: E402


def row(query, top, *, region="213", error=None, date="2026-08-30"):
    return serp_source.SerpRow(date=date, query=query, region=region,
                               top=top, error=error)


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.config = visibility.load_config()
        self.rows = [
            row("купить figma юрлицу", [
                {"domain": "raketapay.ru", "url": "https://raketapay.ru/figma"},
                {"domain": "www.biz-soft.pro", "url": "https://biz-soft.pro/vendors/figma"},
                {"domain": "dzen.ru", "url": "https://dzen.ru/a/x"},
            ]),
            row("figma для компании счёт", [
                {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/product/figma"},
                {"domain": "raketapay.ru", "url": "https://raketapay.ru/f"},
            ]),
        ]

    def test_домены_нормализуются(self):
        """www-вариант и голый домен — один участник, иначе видимость дробится."""
        cards = registry.build(self.rows, self.config)
        domains = [c.domain for c in cards]
        self.assertIn("biz-soft.pro", domains)
        self.assertNotIn("www.biz-soft.pro", domains)

    def test_первая_позиция_даёт_больше_видимости(self):
        cards = {c.domain: c for c in registry.build(self.rows, self.config)}
        # biz-soft: позиции 2 и 1; raketapay: позиции 1 и 2 — веса равны,
        # но обе выше информационного домена на третьей позиции
        self.assertGreater(cards["biz-soft.pro"].weighted_visibility,
                           cards["dzen.ru"].weighted_visibility)

    def test_доли_суммируются_в_единицу(self):
        # Доли хранятся округлёнными до 6 знаков, поэтому сумма сходится с
        # точностью до накопленного округления, а не побитово.
        cards = registry.build(self.rows, self.config)
        self.assertAlmostEqual(sum(c.share for c in cards), 1.0, places=5)

    def test_счётчики_позиций(self):
        cards = {c.domain: c for c in registry.build(self.rows, self.config)}
        ours = cards["biz-soft.pro"]
        self.assertEqual(ours.appearances, 2)
        self.assertEqual(ours.top3, 2)
        self.assertEqual(ours.best_position, 1)

    def test_строки_с_ошибкой_не_учитываются(self):
        """Сбой источника не должен выглядеть как чужая победа."""
        rows = self.rows + [row("сломанный запрос", [], error="timeout")]
        cards = registry.build(rows, self.config)
        self.assertAlmostEqual(sum(c.share for c in cards), 1.0, places=5)
        # И состав участников не изменился от появления сбойной строки
        self.assertEqual({c.domain for c in cards},
                         {c.domain for c in registry.build(self.rows, self.config)})

    def test_чужой_регион_отсекается(self):
        """Регионы не смешиваются (раздел 8 задания)."""
        rows = self.rows + [row("питерский запрос", [
            {"domain": "spb-only.ru", "url": "https://spb-only.ru"}], region="2")]
        cards = registry.build(rows, self.config)
        self.assertNotIn("spb-only.ru", [c.domain for c in cards])

    def test_пустой_срез_не_ломает(self):
        self.assertEqual(registry.build([], self.config), [])

    def test_b2b_confidence_пуст_а_не_ноль(self):
        """Непроверенный домен — NO DATA, а не «ноль по B2B»."""
        cards = registry.build(self.rows, self.config)
        self.assertTrue(all(c.b2b_confidence is None for c in cards))

    def test_категория_и_рейтинг_проставлены(self):
        cards = {c.domain: c for c in registry.build(self.rows, self.config)}
        self.assertEqual(cards["dzen.ru"].category, "G")
        self.assertFalse(cards["dzen.ru"].in_main_ranking)
        self.assertEqual(cards["raketapay.ru"].category, "H")
        self.assertTrue(cards["raketapay.ru"].in_main_ranking)


class TestAppend(unittest.TestCase):
    def test_реестр_дозаписывается_а_не_перезаписывается(self):
        import json
        import tempfile
        config = visibility.load_config()
        cards = registry.build([row("q", [{"domain": "a.ru", "url": "https://a.ru"}])],
                               config)
        with tempfile.TemporaryDirectory() as tmp:
            registry.append(cards, tmp)
            path = registry.append(cards, tmp)
            with open(path, encoding="utf-8") as fh:
                lines = [json.loads(line) for line in fh if line.strip()]
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[0]["domain"], "a.ru")


class TestGoogleBlockFromRows(unittest.TestCase):
    """Блок Google снимка дня: свой движок, свой регион, доля внутри поля."""

    def test_блок_по_google_срезу(self):
        from discovery import google_ru
        from scoring import visibility
        config = visibility.load_config()
        rows = [
            serp_source.SerpRow(date="2026-09-03", query="купить figma",
                                region="2643", engine="google", found=100,
                                top=[{"domain": "raketapay.ru", "url": "https://raketapay.ru/"},
                                     {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/"}]),
            serp_source.SerpRow(date="2026-09-03", query="купить miro",
                                region="2643", engine="google", found=100,
                                top=[{"domain": "raketapay.ru", "url": "https://raketapay.ru/"},
                                     {"domain": "ggsel.net", "url": "https://ggsel.net/"}]),
            serp_source.SerpRow(date="2026-09-03", query="сбой", region="2643",
                                engine="google", error="code=500"),
        ]
        g = google_ru.build_block("2026-09-03", "2026-09-03", rows, [], config)
        self.assertTrue(g["доступен"])
        self.assertEqual(g["покрытие"]["запросов_с_данными"], 2)
        self.assertEqual(g["покрытие"]["запросов_всего"], 3)
        self.assertEqual(g["глубина"], 10)
        self.assertEqual((g["название"], g["регион"]), ("Россия", "2643"))
        self.assertEqual(g["наши_показатели"]["топ10"], 1)
        self.assertEqual(g["наши_показатели"]["лучшая_позиция"], 2)
        self.assertEqual(g["наши_запросы"], [{"запрос": "купить figma", "позиция": 2}])
        # лидеры — только основной рейтинг: ggsel.net (категория E) туда не входит
        self.assertEqual([d["домен"] for d in g["лидеры"]], ["raketapay.ru"])
        self.assertIn("E", g["доли_по_категориям"])
        self.assertGreater(g["лидеры"][0]["доля"], g["наши_показатели"]["доля_видимости"])
        self.assertGreater(g["наши_показатели"]["доля_видимости"], 0)

    def test_без_среза_недоступен(self):
        from discovery import google_ru
        from scoring import visibility
        g = google_ru.build_block("2026-09-03", None, [], [], visibility.load_config())
        self.assertFalse(g["доступен"])
        self.assertIsNone(google_ru.share(g))


if __name__ == "__main__":
    unittest.main()
