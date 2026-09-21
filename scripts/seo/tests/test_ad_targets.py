"""Отбор рекламных целей: три условия и ловушка названий тарифов (21.09.2026).

Решение руководителя после разбора трёх недель рекламы: рекламировать
только корпоративные формулировки и только там, где нас нет в выдаче.
Здесь проверяется, что отбор именно это и делает, а не набирает снова
широкий продуктовый трафик.

Отдельно закреплена ловушка первого прогона: слова business, enterprise и
teams чаще всего часть названия продукта. «Microsoft Teams» со спросом
16 439 в месяц прошёл в кандидаты и один съел бы весь бюджет — ровно так,
как это было с «claude code» в прошлой кампании.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "wordstat"))
import ad_targets as A  # noqa: E402


def phrase(text, freq=100, page=True, vendor="Vendor"):
    return {"phrase": text, "wordstat_frequency": freq, "vendor": vendor,
            "category": "категория", "mapped_url": "/vendors/x", "page_exists": page}


class B2BTest(unittest.TestCase):
    def test_русская_корпоративная_форма_проходит(self):
        for text in ("оплата artlist юридическим лицом", "adobe купить для компании",
                     "корпоративные лицензии atlassian", "claude team для организаций в россии",
                     "оплата perplexity для юрлица с договором и актом"):
            self.assertTrue(A.is_b2b(text), text)

    def test_название_продукта_не_корпоративный_интент(self):
        # Ловушка первого прогона: спрос 16 439 в месяц, интент розничный.
        for text in ("microsoft teams", "notion business", "business principles",
                     "canva teams", "capture one enterprise"):
            self.assertFalse(A.is_b2b(text), text)

    def test_слабый_признак_засчитывается_с_покупкой(self):
        for text in ("notion business купить", "microsoft office business купить",
                     "оплата notion enterprise"):
            self.assertTrue(A.is_b2b(text), text)


class ClassifyTest(unittest.TestCase):
    def test_берёт_фразу_без_нашей_выдачи(self):
        ok, why, pos = A.classify(phrase("оплата descript юридическим лицом"), {}, {}, 30)
        self.assertTrue(ok)
        self.assertIsNone(pos)

    def test_не_берёт_там_где_мы_в_топе(self):
        # Платить за трафик, который и так наш, — то, ради чего затеян отбор.
        ok, why, pos = A.classify(
            phrase("adobe купить для компании"), {}, {"adobe купить для компании": 1.3}, 30)
        self.assertFalse(ok)
        self.assertIn("сами", why)

    def test_позиция_ниже_третьей_не_мешает(self):
        # На таких позициях выдача трафика не даёт: 39 показов, ноль кликов.
        ok, _, pos = A.classify(
            phrase("оплата zoom для организации"), {}, {"оплата zoom для организации": 7.3}, 30)
        self.assertTrue(ok)
        self.assertEqual(pos, 7.3)

    def test_первая_тройка_отсеивается(self):
        ok, why, _ = A.classify(
            phrase("оплата artlist юридическим лицом"), {},
            {"оплата artlist юридическим лицом": 2.7}, 30)
        self.assertFalse(ok)
        self.assertIn("сами", why)

    def test_отсекает_розницу_и_пиратство(self):
        for text in ("adobe acrobat ключ активации для компании",
                     "как обойти лицензию для организации"):
            ok, why, _ = A.classify(phrase(text), {}, {}, 30)
            self.assertFalse(ok, text)
            self.assertIn("розничный", why)

    def test_отсекает_спрос_ниже_порога(self):
        ok, why, _ = A.classify(phrase("оплата spine юридическим лицом", freq=5), {}, {}, 30)
        self.assertFalse(ok)
        self.assertIn("ниже", why)

    def test_срез_без_нас_считается_отсутствием_в_топе(self):
        # В срезе запрос есть, нашего домена в выдаче нет — это кандидат.
        ok, _, pos = A.classify(
            phrase("оплата heygen юридическим лицом"),
            {"оплата heygen юридическим лицом": None}, {}, 30)
        self.assertTrue(ok)
        self.assertIsNone(pos)


class PositionsTest(unittest.TestCase):
    def test_позиция_нашего_домена_из_среза(self):
        import json, tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "срез.jsonl"
            p.write_text(json.dumps({"query": "тест", "top": [
                {"domain": "other.ru"}, {"domain": "www.biz-soft.pro"}]}, ensure_ascii=False),
                encoding="utf-8")
            self.assertEqual(A.serp_positions(p), {"тест": 2})


if __name__ == "__main__":
    unittest.main()
