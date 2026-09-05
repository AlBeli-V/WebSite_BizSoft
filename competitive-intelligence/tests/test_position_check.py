"""Сверка позиции среза с позицией показа по Вебмастеру.

Разбор 04.09.2026. Отчёт сообщил, что по запросу «как оплатить box business
из россии» мы в Яндексе первые; ручная проверка выдачи показала конкурента
первым, нас вторыми и четыре рекламных объявления перед обоими.

Отчёт передал срез верно — в срезе мы действительно первые. Ошибка была в
названии величины: срез приходит из Search API, который отдаёт только
органические документы, и меряет органическую позицию, а не место, которое
видит человек. Сверка с Вебмастером превращает это расхождение из невидимого
в измеряемое.

Тесты держат четыре обещания:
  * расхождение считается по общим запросам и не смешивается со спросом;
  * запросы со страницами, созданными после окна Вебмастера, исключаются —
    иначе половина выборки сравнивает страницу с периодом, когда её не было;
  * маленькая выборка не даёт вывода вовсе;
  * тревога поднимается на рост расхождения, а не на его величину.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from decision_engine import position_check as pc  # noqa: E402
from discovery import serp_source  # noqa: E402


def row(query, *domains, region="213", date="2026-09-04"):
    top = [{"domain": d, "url": f"https://{d}/x", "title": d} for d in domains]
    return serp_source.SerpRow(date=date, query=query, region=region, top=top)


def positions(**pairs):
    return {pc._normalize(q): {"позиция": p, "показов": 10}
            for q, p in pairs.items()}


class TestOurPosition(unittest.TestCase):
    def test_позиция_считается_по_нашему_домену(self):
        self.assertEqual(2, pc.our_position(row("q", "rival.ru", "biz-soft.pro")))

    def test_www_не_мешает(self):
        self.assertEqual(1, pc.our_position(row("q", "www.biz-soft.pro")))

    def test_нас_нет_в_выдаче(self):
        self.assertIsNone(pc.our_position(row("q", "rival.ru")))


class TestCompare(unittest.TestCase):
    def setUp(self):
        self.rows = [row(f"запрос {i}", "rival.ru", "biz-soft.pro")
                     for i in range(25)]
        self.positions = positions(**{f"запрос {i}": 4.0 for i in range(25)})
        self.eligible = {pc._normalize(f"запрос {i}") for i in range(25)}

    def _compare(self, rows=None, pos=None, eligible=None):
        original = pc.baseline_queries
        pc.baseline_queries = lambda *a, **k: (
            self.eligible if eligible is None else eligible)
        try:
            return pc.compare(rows or self.rows,
                              self.positions if pos is None else pos,
                              window=("2026-08-03", "2026-08-30"))
        finally:
            pc.baseline_queries = original

    def test_расхождение_считается(self):
        # В срезе мы вторые, Вебмастер даёт 4.0 — расхождение +2.
        measure = self._compare()
        self.assertTrue(measure["доступна"])
        self.assertEqual(25, measure["сопоставлено"])
        self.assertEqual(2.0, measure["медиана_расхождения"])
        self.assertEqual(25, measure["срез_оптимистичнее"])

    def test_малая_выборка_вывода_не_даёт(self):
        measure = self._compare(rows=self.rows[:5])
        self.assertFalse(measure["доступна"])
        self.assertIn("выборка", measure["причина"])

    def test_новые_страницы_исключаются(self):
        # Ни один запрос не входит в базовую выборку: все страницы созданы
        # после окна Вебмастера, сравнивать не с чем.
        measure = self._compare(eligible=set())
        self.assertFalse(measure["доступна"])

    def test_запрос_без_позиции_вебмастера_не_учитывается(self):
        measure = self._compare(pos=positions(**{f"запрос {i}": 4.0
                                                 for i in range(21)}))
        self.assertEqual(21, measure["сопоставлено"])

    def test_редкий_запрос_отбрасывается(self):
        rare = dict(self.positions)
        for i in range(5):
            rare[pc._normalize(f"запрос {i}")] = {"позиция": 9.0, "показов": 1}
        measure = self._compare(pos=rare)
        self.assertEqual(20, measure["сопоставлено"])

    def test_расхождение_разбирается_по_диапазонам(self):
        # Одно число по всей выборке скрывает, что сдвиг зависит от глубины:
        # именно эта неравномерность показала, что дело не только в рекламе.
        rows = ([row(f"верх {i}", "biz-soft.pro") for i in range(12)]
                + [row(f"низ {i}", *(["r.ru"] * 6), "biz-soft.pro")
                   for i in range(12)])
        pos = positions(**{f"верх {i}": 3.0 for i in range(12)})
        pos.update(positions(**{f"низ {i}": 7.0 for i in range(12)}))
        eligible = {pc._normalize(r.query) for r in rows}
        measure = self._compare(rows=rows, pos=pos, eligible=eligible)
        bands = {b["диапазон"]: b["медиана"] for b in measure["по_диапазонам"]}
        self.assertEqual(2.0, bands["1"])
        self.assertEqual(0.0, bands["6–10"])

    def test_без_выгрузки_вебмастера_сверки_нет(self):
        measure = pc.compare(self.rows, {}, window=("", ""))
        self.assertFalse(measure["доступна"])
        self.assertIn("недоступна", measure["причина"])


class TestVerdict(unittest.TestCase):
    def test_известное_расхождение_тревоги_не_поднимает(self):
        v = pc.verdict({"доступна": True, "медиана_расхождения": 1.9})
        self.assertFalse(v["тревога"])

    def test_рост_расхождения_поднимает_тревогу(self):
        v = pc.verdict({"доступна": True, "медиана_расхождения": 3.5})
        self.assertTrue(v["тревога"])
        self.assertIn("сравнивать с прежними", v["объяснение"])

    def test_порог_берётся_из_конфига(self):
        config = {"сверка_позиций": {"базовая_линия_медианы": 1.0,
                                     "допустимый_рост_медианы": 0.5}}
        v = pc.verdict({"доступна": True, "медиана_расхождения": 1.9}, config)
        self.assertTrue(v["тревога"])

    def test_невыполненная_сверка_тревогой_не_является(self):
        # Отсутствие сверки — неизвестность, а не подтверждение точности, но
        # и не повод блокировать выпуск: блокировать можно на факт, не на его
        # отсутствие.
        v = pc.verdict({"доступна": False, "причина": "нет выгрузки"})
        self.assertFalse(v["тревога"])
        self.assertIn("нет выгрузки", v["объяснение"])


if __name__ == "__main__":
    unittest.main()
