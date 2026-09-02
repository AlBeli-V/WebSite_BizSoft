"""Тесты защиты от наложения правок на чужой замер.

Разбор плана работ 02.09.2026: из 24 пакетов дня пять указывали на страницы,
по которым базовый SEO-контур в тот же день вёл собственный эксперимент. Две
правки в одном окне наблюдения лишают оценки оба эксперимента — ни свой
эффект, ни чужой после этого не измерить.

Тесты стерегут три обещания:
  * страница из `pages` действующего эксперимента поручением не становится;
  * решённый эксперимент страницу освобождает (так базовый контур поступил
    с /vendors/coreldraw 02.09.2026);
  * недоступность реестра не превращается в «занятых нет».
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from attack_engine import occupancy  # noqa: E402
from experiments import journal as jr  # noqa: E402
from experiments import lifecycle  # noqa: E402

REGISTRY = [
    {
        "id": "snippets-3-gap-d", "ticket": "SEO-EXP-004", "status": "running",
        "start": "2026-09-01",
        "pages": ["/vendors/artlist", "/vendors/motion-array",
                  "/vendors/coreldraw"],
        "success_metric": "CTR > 0 за 14 дней (контроль 15.09.2026 по Artlist "
                          "и Motion Array, 16.09.2026 по CorelDRAW)",
        "control_group": "остальные vendor-страницы без изменений",
    },
    {
        "id": "content-6-clusters", "ticket": "CONTENT-002", "status": "running",
        "start": "2026-09-02",
        "pages": ["/vendors/framer", "/vendors/runway"],
        "success_metric": "рост показов; контрольная точка 16.09.2026",
        "control_group": "кластеры Windsurf, GitLab, Box, Descript — прошли "
                         "те же гейты, но статей не получили",
    },
    {
        "id": "snippets-5-vendors", "ticket": "SEO-EXP-001", "status": "decided",
        "start": "2026-08-19",
        "pages": ["/vendors/marmoset"],
        "success_metric": "CTR ≥3% через 14 дней (02.09.2026)",
        "control_group": "остальные vendor-страницы без изменений",
    },
]
LIVE = [e for e in REGISTRY if e["status"] == "running"]


class TestOccupancy(unittest.TestCase):
    def test_страница_эксперимента_занята(self):
        hit = occupancy.find("https://biz-soft.pro/vendors/coreldraw",
                             "coreldraw", LIVE)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["степень"], occupancy.BUSY_PAGE)
        self.assertEqual(hit["эксперимент"], "snippets-3-gap-d")

    def test_срок_занятости_из_метрики_успеха(self):
        hit = occupancy.find("https://biz-soft.pro/vendors/coreldraw",
                             "coreldraw", LIVE)
        self.assertEqual(hit["до"], "2026-09-16")

    def test_решённый_эксперимент_страницу_освобождает(self):
        # snippets-5-vendors в состоянии decided: в действующие не попадает,
        # и /vendors/marmoset снова можно брать в работу.
        live = [e for e in REGISTRY
                if e["status"].lower() in occupancy.LIVE_STATES]
        self.assertIsNone(occupancy.find(
            "https://biz-soft.pro/vendors/marmoset", "marmoset", live))

    def test_кластер_в_контроле_помечен_но_не_запрещён(self):
        hit = occupancy.find("https://biz-soft.pro/vendors/gitlab",
                             "gitlab", LIVE)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["степень"], occupancy.BUSY_CONTROL)
        # Ограничение чужого эксперимента цитируется дословно: решать человеку.
        self.assertIn("статей не получили", hit["ограничение"])

    def test_общая_формулировка_контроля_никого_не_блокирует(self):
        # «остальные vendor-страницы без изменений» — контроль назван общо;
        # запрещать по нему работу со всем сайтом было бы подменой смысла.
        self.assertIsNone(occupancy.find(
            "https://biz-soft.pro/vendors/cursor", "cursor", LIVE))

    def test_свободная_страница_не_помечается(self):
        self.assertIsNone(occupancy.find(
            "https://biz-soft.pro/vendors/capture-one", "capture-one", LIVE))

    def test_mark_делит_пакеты(self):
        packages = [
            {"package_id": "WP-01", "url": "https://biz-soft.pro/vendors/runway",
             "subject": "runway"},
            {"package_id": "WP-02", "url": "https://biz-soft.pro/vendors/gitlab",
             "subject": "gitlab"},
            {"package_id": "WP-03", "url": "https://biz-soft.pro/vendors/cursor",
             "subject": "cursor"},
        ]
        free, busy = occupancy.mark(packages, LIVE)
        self.assertEqual([p["package_id"] for p in busy], ["WP-01"])
        # Контрольная группа остаётся в очереди — с пометкой, но остаётся.
        self.assertEqual([p["package_id"] for p in free], ["WP-02", "WP-03"])
        self.assertIn("занятость", packages[1])
        self.assertNotIn("занятость", packages[2])

    def test_нет_реестра_не_значит_нет_занятых(self):
        # Пустой список действующих экспериментов и недоступный реестр — разные
        # вещи. Различать их обязан вызывающий код: available() отвечает на
        # вопрос «прочитали ли», load() — «кто меряет».
        self.assertTrue(hasattr(occupancy, "available"))
        free, busy = occupancy.mark(
            [{"package_id": "WP-01", "url": "https://biz-soft.pro/vendors/x",
              "subject": "x"}], [])
        self.assertEqual(len(free), 1)
        self.assertEqual(busy, [])


class TestRegisterSkipsOccupied(unittest.TestCase):
    def test_по_занятой_странице_эксперимент_не_заводится(self):
        package = {
            "package_id": "WP-01",
            "url": "https://biz-soft.pro/vendors/coreldraw",
            "page_kind": "vendor",
            "queries": ["оплата coreldraw из россии"],
            "занятость": {"степень": occupancy.BUSY_PAGE,
                          "эксперимент": "snippets-3-gap-d",
                          "до": "2026-09-16"},
            "действия": [{"kind": "заголовки", "what": "Вынести 1 запрос",
                          "steps": ["«оплата coreldraw из россии»"]}],
        }
        experiments: list[jr.Experiment] = []
        created = lifecycle.register(experiments, [package], "2026-09-02")
        self.assertEqual(created, [])
        self.assertEqual(experiments, [])

    def test_по_свободной_странице_эксперимент_заводится(self):
        package = {
            "package_id": "WP-02",
            "url": "https://biz-soft.pro/vendors/cursor",
            "page_kind": "vendor",
            "queries": ["купить cursor pro юридическим лицом"],
            "действия": [{"kind": "заголовки", "what": "Вынести 1 запрос",
                          "steps": ["«купить cursor pro юридическим лицом»"]}],
        }
        experiments: list[jr.Experiment] = []
        created = lifecycle.register(experiments, [package], "2026-09-02")
        self.assertEqual(len(created), 1)


if __name__ == "__main__":
    unittest.main()
