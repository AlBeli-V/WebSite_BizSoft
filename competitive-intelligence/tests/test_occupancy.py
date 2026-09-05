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


class TestWindowExpiry(unittest.TestCase):
    """Занятость снимается по окну замера, а не по статусу в чужом реестре.

    Разбор 04.09.2026. Статус эксперимента в реестре базового контура ставит
    человек, и пока он этого не сделал, страница считалась занятой бессрочно.
    Два эксперимента с контрольной точкой 02.09 держали десять страниц, а
    отчёт печатал «страница занята … до 2026-09-02» — противоречие в одной
    строке.
    """

    RUNNING_BUT_OVER = {
        "id": "snippets-5-vendors", "ticket": "SEO-EXP-001", "status": "running",
        "start": "2026-08-19", "pages": ["/vendors/depositphotos"],
        "success_metric": "CTR ≥2% через 7 дней (26.08.2026), ≥3% через "
                          "14 дней (02.09.2026)",
        "control_group": "остальные vendor-страницы без изменений",
    }

    def test_окно_считается_по_последней_дате_метрики(self):
        self.assertEqual("2026-09-02",
                         occupancy.window_end(self.RUNNING_BUT_OVER))

    def test_истёкшее_окно_страницу_освобождает(self):
        hit = occupancy.find("/vendors/depositphotos", "depositphotos",
                             [self.RUNNING_BUT_OVER], today="2026-09-04")
        self.assertIsNone(hit)

    def test_действующее_окно_страницу_держит(self):
        hit = occupancy.find("/vendors/depositphotos", "depositphotos",
                             [self.RUNNING_BUT_OVER], today="2026-08-25")
        self.assertIsNotNone(hit)
        self.assertEqual(occupancy.BUSY_PAGE, hit["степень"])

    def test_истёкшие_называются_отдельно(self):
        stale = occupancy.expired([self.RUNNING_BUT_OVER], "2026-09-04")
        self.assertEqual(["snippets-5-vendors"], [e["id"] for e in stale])

    def test_дата_решения_из_контрольной_группы_окно_не_закрывает(self):
        # «KEEP 03.09.2026» в control_group — дата решения, а не конец окна.
        # По ней эксперимент закрывался в день собственного старта.
        experiment = {
            "id": "snippets-2-price-intent", "status": "running",
            "start": "2026-09-03", "pages": ["/vendors/procreate"],
            "windows": {"days": 28,
                        "experiment": {"from": "2026-09-04", "to": "2026-10-01"}},
            "success_metric": "CTR ≥2 % за фиксированное окно 28 дней",
            "control_group": "Adobe, Autodesk выведены (KEEP 03.09.2026)",
        }
        self.assertEqual("2026-10-01", occupancy.window_end(experiment))
        self.assertTrue(occupancy.is_live(experiment, "2026-09-04"))

    def test_дата_без_года_читается_по_году_старта(self):
        experiment = {
            "id": "pages-exp-001", "status": "running", "start": "2026-08-30",
            "pages": ["/vendors/x"],
            "success_metric": "К 13.09.2026: страницы в поиске. К 27.09: "
                              "первые клики.",
        }
        self.assertEqual("2026-09-27", occupancy.window_end(experiment))

    def test_эксперимент_без_дат_не_держит_страницу_вечно(self):
        experiment = {
            "id": "no-dates", "status": "running", "start": "2026-09-01",
            "pages": ["/vendors/x"],
            "success_metric": "CTR > 0 по каждому запросу",
        }
        end = occupancy.window_end(experiment)
        self.assertTrue(end)
        self.assertFalse(occupancy.is_live(experiment, "2026-12-01"))

    def test_без_даты_прогона_поведение_прежнее(self):
        # Вызов без today ничего не освобождает: так проверка остаётся
        # совместимой со старыми вызовами и не освобождает страницы молча.
        self.assertTrue(occupancy.is_live(self.RUNNING_BUT_OVER, ""))


if __name__ == "__main__":
    unittest.main()
