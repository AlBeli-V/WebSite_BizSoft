"""Навигация отчёта: каты и плавающее меню разделов.

Отчёт вырос до двухсот килобайт: пакеты работ, карточки конкурентов, полная
таблица точек атаки. Читать его подряд нельзя, а найти нужный пакет прокруткой
— долго. Поэтому крупные блоки убраны под кат, а меню в правом нижнем углу
перечисляет структуру целиком, включая то, что лежит внутри свёрнутых блоков.

Тесты держат три обещания навигации:
  * у каждого пакета, конкурента и разобранной точки атаки есть свой якорь;
  * меню ссылается только на якоря, которые в документе действительно есть —
    ссылка в никуда хуже отсутствия ссылки;
  * идентификаторы уникальны, иначе переход попадает в первый попавшийся блок.
"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from reports import deep_report  # noqa: E402

DATE = "2026-09-09"

SNAPSHOT = {
    "дата": DATE,
    "наши_показатели": {"доля_видимости": 0.05, "топ3": 3, "топ10": 7,
                        "запросов_в_поле": 20},
    "доли_по_категориям": {"H": 0.2, "A": 0.1},
    "лидеры": [{"домен": "raketapay.ru", "категория": "H", "доля": 0.2,
                "топ3": 5, "топ10": 9},
               {"домен": "biz-soft.pro", "категория": "A", "доля": 0.05,
                "топ3": 3, "топ10": 7}],
    "покрытие": {"яндекс_запросов_с_данными": 20},
    "метаданные": {"версия_методики": "1.4.0"},
}

ATTACKS = [{"attack_id": "ATT-001", "query": "оплата figma для юрлица",
            "opportunity": 60, "confidence": "MEDIUM", "our_position": 5,
            "our_url": "https://biz-soft.pro/vendors/figma",
            "rival_domain": "raketapay.ru", "rival_position": 1,
            "demand": 40, "demand_source": "webmaster",
            "commercial_intent": 0.7, "b2b_intent": 0.6,
            "breakdown": {"commercial": 16.5}, "notes": ["заметка"]}]

PACKAGES = [{"package_id": "WP-01", "url": "https://biz-soft.pro/vendors/figma",
             "page_kind": "vendor", "action": "Дописать текст",
             "queries": ["оплата figma для юрлица"], "queries_count": 1,
             "demand_by_source": {"webmaster": 40},
             "demand_queries_by_source": {"webmaster": 1},
             "demand_coverage": "1/1", "potential_index": 0.03,
             "potential_label": "высокий", "traffic_upside": None,
             "upside_note": "перевод в переходы невозможен",
             "position_best": 5, "position_worst": 5,
             "rivals": ["raketapay.ru"], "confidence": "MEDIUM",
             "действия": [], "уже_сделано": [], "не_рекомендуем": []}]


def page() -> str:
    return deep_report.build(DATE, SNAPSHOT, None, ATTACKS, [], [],
                             packages=PACKAGES)


def ids(html: str) -> list[str]:
    return re.findall(r'id="([^"]+)"', html)


def anchors(html: str) -> set[str]:
    return set(re.findall(r'href="#([^"]+)"', html))


class TestAnchors(unittest.TestCase):
    def test_якоря_уникальны(self):
        found = ids(page())
        duplicates = {i for i in found if found.count(i) > 1}
        self.assertEqual(set(), duplicates)

    def test_меню_не_ссылается_в_никуда(self):
        html = page()
        self.assertEqual(set(), anchors(html) - set(ids(html)))

    def test_у_пакета_конкурента_и_атаки_есть_свой_якорь(self):
        found = set(ids(page()))
        self.assertIn("pkg-wp-01", found)
        self.assertIn("cmp-raketapay-ru", found)
        self.assertIn("att-001", found)

    def test_свой_домен_в_меню_конкурентов_не_попадает(self):
        self.assertNotIn("cmp-biz-soft-pro", set(ids(page())))

    def test_идентификатор_не_удваивает_префикс(self):
        self.assertEqual("att-001", deep_report.anchor("att", "ATT-001"))
        self.assertEqual("pkg-wp-01", deep_report.anchor("pkg", "WP-01"))


class TestCut(unittest.TestCase):
    def test_крупные_таблицы_убраны_под_кат(self):
        html = page()
        self.assertIn("Таблица угрозы", html)
        self.assertIn("Полная таблица точек атаки", html)
        self.assertIn('details class="cut"', html)

    def test_кат_свёрнут_по_умолчанию(self):
        # Открытый кат ничего не экономит: смысл в том, что содержимое
        # раскрывается по требованию, а не занимает экран сразу.
        for block in re.findall(r'<details class="cut"[^>]*>', page()):
            self.assertNotIn("open", block)

    def test_меню_есть_и_не_сдвигает_текст(self):
        html = page()
        self.assertIn('<details class="toc" id="toc">', html)
        self.assertIn(".toc{position:fixed", html)


class TestSelfContained(unittest.TestCase):
    def test_внешних_ресурсов_в_отчёте_нет(self):
        # Отчёт открывают с телефона по прямой ссылке: любая внешняя загрузка
        # — это зависимость от чужого CDN и след в чужих логах.
        html = page()
        self.assertNotIn("<script src=", html)
        self.assertNotIn("<link rel=\"stylesheet\"", html)


if __name__ == "__main__":
    unittest.main()
