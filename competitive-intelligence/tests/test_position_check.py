"""Сверка позиции среза с позицией показа по Вебмастеру.

Разбор 04.09.2026. Отчёт сообщил, что по запросу «как оплатить box business
из россии» мы в Яндексе первые; ручная проверка выдачи показала конкурента
первым, нас вторыми и четыре рекламных объявления перед обоими.

Отчёт передал срез верно — в срезе мы действительно первые. Ошибка была в
названии величины: срез приходит из Search API, который отдаёт только
органические документы, и меряет органическую позицию, а не место, которое
видит человек. Сверка с Вебмастером превращает это расхождение из невидимого
в измеряемое.

Правка 1.9.2 (разбор 10.09.2026). Сверка сравнивала срез дня прогона со
средней Вебмастера за окно, которое к этому дню уже закончилось: 10.09 срез
был за 10.09, окно — 08.08–04.09, и периоды не пересекались вовсе. Шесть дней
движения позиций попадали в «расхождение» и объяснялись рекламой. Вдобавок
одно измерение сравнивалось со средней: это даёт зависящий от позиции перекос
(регрессия к среднему), который рисует ровно тот профиль, что отчёт приписывал
рекламным блокам. Теперь обе стороны считаются по окну Вебмастера, а наша —
медианой по срезам внутри него.

Тесты держат пять обещаний:
  * расхождение считается по общим запросам и не смешивается со спросом;
  * обе стороны берутся из одного периода, срез дня прогона в сверку не идёт;
  * запросы, по которым внутри окна мы не ранжировались, исключаются —
    иначе выборка сравнивает страницу с периодом, когда её не было;
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


def срез(позиции: dict, даты=("2026-08-30", "2026-09-04")) -> dict:
    """Готовая сторона среза: медиана позиции по запросу внутри окна."""
    return {"даты": list(даты),
            "позиции": {pc._normalize(q): p for q, p in позиции.items()},
            "замеров": {pc._normalize(q): len(даты) for q in позиции}}


class TestCompare(unittest.TestCase):
    def setUp(self):
        self.positions = positions(**{f"запрос {i}": 4.0 for i in range(25)})
        self.serp = срез({f"запрос {i}": 2.0 for i in range(25)})

    def _compare(self, pos=None, s=None):
        return pc.compare(self.positions if pos is None else pos,
                          window=("2026-08-08", "2026-09-04"),
                          serp=self.serp if s is None else s)

    def test_расхождение_считается(self):
        # В срезе мы вторые, Вебмастер даёт 4.0 — расхождение +2.
        measure = self._compare()
        self.assertTrue(measure["доступна"])
        self.assertEqual(25, measure["сопоставлено"])
        self.assertEqual(2.0, measure["медиана_расхождения"])
        self.assertEqual(25, measure["срез_оптимистичнее"])

    def test_период_среза_и_окна_названы(self):
        """Читатель обязан видеть, что обе стороны считаны по одному времени."""
        measure = self._compare()
        self.assertEqual("2026-08-08 — 2026-09-04", measure["окно_вебмастера"])
        self.assertEqual("2026-08-30 — 2026-09-04", measure["окно_среза"])
        self.assertEqual(2, measure["срезов_в_окне"])
        self.assertEqual(28, measure["дней_в_окне"])

    def test_малая_выборка_вывода_не_даёт(self):
        measure = self._compare(s=срез({f"запрос {i}": 2.0 for i in range(5)}))
        self.assertFalse(measure["доступна"])
        self.assertIn("выборка", measure["причина"])

    def test_без_срезов_внутри_окна_сверки_нет(self):
        """Пустое пересечение периодов — не повод считать по чему попало."""
        measure = self._compare(s={"даты": [], "позиции": {}, "замеров": {}})
        self.assertFalse(measure["доступна"])
        self.assertIn("ни одного среза", measure["причина"])

    def test_запрос_без_позиции_внутри_окна_исключается(self):
        measure = self._compare(s=срез({f"запрос {i}": 2.0 for i in range(21)}))
        self.assertEqual(21, measure["сопоставлено"])
        self.assertEqual(4, measure["исключено_новых_страниц"])

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
        # Одно число по всей выборке скрывает, что сдвиг зависит от глубины.
        s = срез({**{f"верх {i}": 1.0 for i in range(12)},
                  **{f"низ {i}": 7.0 for i in range(12)}})
        pos = positions(**{f"верх {i}": 3.0 for i in range(12)})
        pos.update(positions(**{f"низ {i}": 7.0 for i in range(12)}))
        measure = self._compare(pos=pos, s=s)
        bands = {b["диапазон"]: b["медиана"] for b in measure["по_диапазонам"]}
        self.assertEqual(2.0, bands["1"])
        self.assertEqual(0.0, bands["6–10"])

    def test_без_выгрузки_вебмастера_сверки_нет(self):
        measure = pc.compare({}, window=("", ""))
        self.assertFalse(measure["доступна"])
        self.assertIn("недоступна", measure["причина"])


class TestWindowPositions(unittest.TestCase):
    """Наша сторона сверки собирается только из срезов внутри окна."""

    def setUp(self):
        self.снимки = {
            "2026-08-29": [row("q", "r.ru", "biz-soft.pro", date="2026-08-29")],
            "2026-08-30": [row("q", "biz-soft.pro", date="2026-08-30")],
            "2026-09-02": [row("q", "r.ru", "r2.ru", "biz-soft.pro",
                               date="2026-09-02")],
            "2026-09-10": [row("q", "biz-soft.pro", date="2026-09-10")],
        }
        self.даты = sorted(self.снимки)
        self._dates, self._read = pc.serp_source.available_dates, pc.serp_source.read_snapshot
        pc.serp_source.available_dates = lambda *a, **k: self.даты
        pc.serp_source.read_snapshot = lambda d, *a, **k: self.снимки[d]

    def tearDown(self):
        pc.serp_source.available_dates = self._dates
        pc.serp_source.read_snapshot = self._read

    def test_берутся_только_срезы_внутри_окна(self):
        out = pc.window_positions(("2026-08-30", "2026-09-04"))
        self.assertEqual(["2026-08-30", "2026-09-02"], out["даты"])
        # Медиана по 1 и 3 — это 2.0; срезы 29.08 и 10.09 за окном и не в счёт.
        self.assertEqual(2.0, out["позиции"]["q"])
        self.assertEqual(2, out["замеров"]["q"])

    def test_день_без_нас_в_выдаче_медиану_не_тянет(self):
        self.снимки["2026-09-02"] = [row("q", "r.ru", date="2026-09-02")]
        out = pc.window_positions(("2026-08-30", "2026-09-04"))
        self.assertEqual(1, out["позиции"]["q"])
        self.assertEqual(1, out["замеров"]["q"])


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
