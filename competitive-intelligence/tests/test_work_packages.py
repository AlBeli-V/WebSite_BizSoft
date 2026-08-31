"""Тесты пакетов работ — единицы поручения вместо списка запросов."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from attack_engine import work_packages  # noqa: E402
from scoring import visibility  # noqa: E402


def attack(query, url, position, *, demand=100, rival="raketapay.ru",
           opportunity=60, confidence="MEDIUM", attack_id="ATT-001",
           demand_source="wordstat"):
    return {"attack_id": attack_id, "query": query, "our_url": url,
            "our_position": position, "demand": demand, "rival_domain": rival,
            "rival_position": 1, "opportunity": opportunity,
            "confidence": confidence, "demand_source": demand_source}


class TestGrouping(unittest.TestCase):
    def test_запросы_одной_страницы_в_одном_пакете(self):
        """Одна правка страницы закрывает несколько запросов — это и есть пакет."""
        attacks = [
            attack("оплата figma юрлицом", "https://biz-soft.pro/vendors/figma", 5),
            attack("купить figma на компанию", "https://biz-soft.pro/vendors/figma", 7),
            attack("canva для юрлиц", "https://biz-soft.pro/vendors/canva", 6),
        ]
        packages = work_packages.build(attacks)
        self.assertEqual(len(packages), 2)
        figma = next(p for p in packages if "figma" in p.url)
        self.assertEqual(figma.queries_count, 2)
        self.assertEqual(figma.demand_total, 200)

    def test_позиции_сводятся_в_диапазон(self):
        attacks = [
            attack("q1", "https://biz-soft.pro/vendors/x", 4),
            attack("q2", "https://biz-soft.pro/vendors/x", 9),
        ]
        pkg = work_packages.build(attacks)[0]
        self.assertEqual(pkg.position_best, 4)
        self.assertEqual(pkg.position_worst, 9)

    def test_нумерация_по_убыванию_потенциала(self):
        attacks = [
            attack("малый", "https://biz-soft.pro/vendors/small", 5, demand=10),
            attack("большой", "https://biz-soft.pro/vendors/big", 5, demand=900),
        ]
        packages = work_packages.build(attacks)
        self.assertEqual(packages[0].package_id, "WP-01")
        self.assertIn("big", packages[0].url)
        self.assertGreater(packages[0].potential_index, packages[1].potential_index)


class TestPotential(unittest.TestCase):
    """Версия 1.1.0: индекс потенциала и оценка переходов — разные величины.

    Дефект 1.0.0, найденный внешним аудитом: прирост переходов считался по
    спросу из разных источников. Частотность Wordstat (рынок за месяц) и
    показы Вебмастера (видимая нам часть за две недели) складывались в одну
    сумму, которая называлась переходами.
    """

    def setUp(self):
        self.config = visibility.load_config()

    def test_чем_ниже_позиция_тем_больше_потенциал(self):
        низко = work_packages.build([attack("q", "https://biz-soft.pro/a", 10)])[0]
        высоко = work_packages.build([attack("q", "https://biz-soft.pro/a", 4)])[0]
        self.assertGreater(низко.potential_index, высоко.potential_index)

    def test_позиция_в_топ3_не_даёт_прироста(self):
        """Мы уже в тройке — расти в рамках этой цели некуда."""
        pkg = work_packages.build([attack("q", "https://biz-soft.pro/a", 2)])[0]
        self.assertEqual(pkg.potential_index, 0.0)
        self.assertEqual(pkg.potential_label, "нет потенциала")

    def test_потенциал_растёт_со_спросом(self):
        мало = work_packages.build([attack("q", "https://biz-soft.pro/a", 8, demand=10)])[0]
        много = work_packages.build([attack("q", "https://biz-soft.pro/a", 8, demand=500)])[0]
        self.assertGreater(много.potential_index, мало.potential_index)

    def test_переходы_считаются_только_по_wordstat(self):
        по_рынку = work_packages.build([
            attack("q", "https://biz-soft.pro/a", 8, demand_source="wordstat")])[0]
        по_показам = work_packages.build([
            attack("q", "https://biz-soft.pro/a", 8, demand_source="webmaster")])[0]
        self.assertIsNotNone(по_рынку.traffic_upside)
        self.assertIsNone(по_показам.traffic_upside)
        self.assertIn("Вебмастера", по_показам.upside_note)

    def test_смешанные_шкалы_не_переводятся_в_переходы(self):
        """Главный дефект 1.0.0: разные знаменатели складывались в одну сумму."""
        pkg = work_packages.build([
            attack("q1", "https://biz-soft.pro/a", 8, demand_source="wordstat",
                   attack_id="ATT-001"),
            attack("q2", "https://biz-soft.pro/a", 9, demand_source="webmaster",
                   attack_id="ATT-002"),
        ])[0]
        self.assertIsNone(pkg.traffic_upside)
        self.assertIn("разными шкалами", pkg.upside_note)
        self.assertEqual(sorted(pkg.demand_sources), ["webmaster", "wordstat"])

    def test_индекс_потенциала_считается_всегда(self):
        """Сравнивать пакеты между собой можно и при разных источниках."""
        pkg = work_packages.build([
            attack("q1", "https://biz-soft.pro/a", 8, demand_source="wordstat",
                   attack_id="ATT-001"),
            attack("q2", "https://biz-soft.pro/a", 9, demand_source="webmaster",
                   attack_id="ATT-002"),
        ])[0]
        self.assertGreater(pkg.potential_index, 0)

    def test_метка_потенциала_относительная(self):
        """Абсолютные пороги были бы произволом: величина индекса зависит от
        конфигурации кривой и источника спроса."""
        attacks = [attack(f"q{i}", f"https://biz-soft.pro/p{i}", 5,
                          demand=1000 - i * 100, attack_id=f"ATT-{i}")
                   for i in range(9)]
        packages = work_packages.build(attacks)
        labels = [p.potential_label for p in packages]
        self.assertIn("высокий", labels)
        self.assertIn("низкий", labels)


class TestAction(unittest.TestCase):
    def test_действие_названо_конкретно(self):
        """«Улучшить SEO» поручить нельзя — формулировка запрещена заданием."""
        for url in ("https://biz-soft.pro/vendors/figma",
                    "https://biz-soft.pro/product/anthropic-team",
                    "https://biz-soft.pro/blog/kak-oplatit"):
            pkg = work_packages.build([attack("оплата юрлицом", url, 5)])[0]
            self.assertNotIn("улучшить", pkg.action.lower())
            self.assertNotIn("усилить контент", pkg.action.lower())
            self.assertTrue(pkg.checklist)

    def test_тип_страницы_определяет_действие(self):
        vendor = work_packages.build([
            attack("q", "https://biz-soft.pro/vendors/figma", 5)])[0]
        blog = work_packages.build([
            attack("q", "https://biz-soft.pro/blog/kak-oplatit", 5)])[0]
        self.assertEqual(vendor.page_kind, "vendor")
        self.assertEqual(blog.page_kind, "blog")
        self.assertNotEqual(vendor.action, blog.action)

    def test_чеклист_упоминает_юрлиц_для_b2b_запроса(self):
        pkg = work_packages.build([
            attack("оплата figma юридическим лицам",
                   "https://biz-soft.pro/vendors/figma", 5)])[0]
        joined = " ".join(pkg.checklist).lower()
        self.assertIn("юридическ", joined)

    def test_трудоёмкость_растёт_с_объёмом(self):
        один = work_packages.build([attack("q", "https://biz-soft.pro/a", 5)])[0]
        много = work_packages.build([
            attack(f"q{i}", "https://biz-soft.pro/a", 5, attack_id=f"ATT-{i}")
            for i in range(10)])[0]
        self.assertEqual(один.effort, "S")
        self.assertEqual(много.effort, "L")

    def test_уверенность_берётся_худшая(self):
        """Пакет не может быть увереннее самой слабой из своих оценок."""
        pkg = work_packages.build([
            attack("q1", "https://biz-soft.pro/a", 5, confidence="MEDIUM"),
            attack("q2", "https://biz-soft.pro/a", 6, confidence="LOW"),
        ])[0]
        self.assertEqual(pkg.confidence, "LOW")


class TestOurDomainExcluded(unittest.TestCase):
    """Наш домен не может попасть в конкурентные срезы — реальная ошибка,
    найденная руководителем: biz-soft.pro оказался в карточках конкурентов."""

    def test_снимок_не_содержит_нас_в_лидерах(self):
        from discovery import registry, run_discovery, serp_source
        rows = [serp_source.SerpRow(
            date="2026-08-30", query="купить figma юрлицу", region="213",
            top=[{"domain": "raketapay.ru", "url": "https://raketapay.ru/f"},
                 {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/f"}])]
        config = visibility.load_config()
        cards = registry.build(rows, config, date="2026-08-30")
        snapshot = run_discovery.build_snapshot("2026-08-30", cards, rows, config)
        domains = [d["домен"] for d in snapshot["лидеры"]]
        self.assertNotIn("biz-soft.pro", domains)

    def test_наша_доля_не_вливается_в_категорию_конкурентов(self):
        from discovery import registry, run_discovery, serp_source
        rows = [serp_source.SerpRow(
            date="2026-08-30", query="купить figma юрлицу", region="213",
            top=[{"domain": "syssoft.ru", "url": "https://syssoft.ru/f"},
                 {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/f"}])]
        config = visibility.load_config()
        cards = registry.build(rows, config, date="2026-08-30")
        snapshot = run_discovery.build_snapshot("2026-08-30", cards, rows, config)
        # Обе категории A, но наша доля учтена отдельно
        ours = snapshot["наши_показатели"]["доля_видимости"]
        category_a = snapshot["доли_по_категориям"].get("A", 0)
        self.assertAlmostEqual(category_a + ours, 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
