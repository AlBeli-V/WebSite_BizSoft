"""Вердикт-движок SEO-экспериментов: контрольные сценарии задания 30.08.2026.

Номера сценариев соответствуют §15 постановки. Данные подставные: выгрузки
Вебмастера кладутся во временный каталог, окна и лаг — как у реального
источника (скользящий агрегат, лаг ~3 дня).
"""

import datetime as dt
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import experiment_stats as st  # noqa: E402
import experiment_verdict as ver  # noqa: E402


def q(text, shows, clicks, pos):
    return {"query_id": text, "query_text": text,
            "indicators": {"TOTAL_SHOWS": float(shows),
                           "TOTAL_CLICKS": float(clicks),
                           "AVG_SHOW_POSITION": float(pos),
                           "AVG_CLICK_POSITION": None}}


def cluster(prefix, shows, clicks, pos, n=5):
    """n запросов кластера с равными долями показов/кликов."""
    per_s, per_c = shows // n, clicks // n
    return [q(f"{prefix} запрос {i}", per_s, per_c, pos) for i in range(n)]


EXP = {"id": "test-exp", "ticket": "SEO-EXP-T", "start": "2026-08-19",
       "pages": ["/vendors/canva"]}


class VerdictScenarioTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.old_dir = st.DATA_DIR
        st.DATA_DIR = self.tmp

    def tearDown(self):
        st.DATA_DIR = self.old_dir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def day(self, file_date, w_from, w_to, queries):
        (self.tmp / f"yandex-{file_date}.json").write_text(json.dumps({
            "date": file_date,
            "popular_queries": {"date_from": w_from, "date_to": w_to,
                                "count": len(queries), "queries": queries}},
            ensure_ascii=False), encoding="utf-8")

    def base_exp(self, base_q, exp_q):
        self.day("2026-08-18", "2026-08-04", "2026-08-16", base_q)
        self.day("2026-09-02", "2026-08-20", "2026-08-30", exp_q)

    # 1. Явный рост CTR при стабильной позиции → CONFIRMED.
    def test_01_рост_ctr_при_стабильной_позиции_подтверждён(self):
        self.base_exp(cluster("canva", 2500, 70, 6.3),
                      cluster("canva", 2500, 105, 6.1))
        r = ver.evaluate(EXP, "2026-09-02")
        self.assertEqual(r["verdict"], "CONFIRMED")
        self.assertTrue(r["requires_owner_decision"])
        self.assertEqual(r["recommendation"], "EXPAND")

    # 2. Явное падение CTR → REJECTED.
    def test_02_падение_ctr_отвергнут(self):
        self.base_exp(cluster("canva", 2500, 105, 6.3),
                      cluster("canva", 2500, 55, 6.3))
        r = ver.evaluate(EXP, "2026-09-02")
        self.assertEqual(r["verdict"], "REJECTED")
        self.assertEqual(r["recommendation"], "REVERT")
        self.assertTrue(r["requires_owner_decision"])

    # 3. Практически нет изменения → INCONCLUSIVE.
    def test_03_нет_изменения_вывод_невозможен(self):
        self.base_exp(cluster("canva", 2500, 70, 6.3),
                      cluster("canva", 2500, 72, 6.3))
        r = ver.evaluate(EXP, "2026-09-02")
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertFalse(r["requires_owner_decision"])

    # 4. Рост CTR при сильном улучшении позиции → INCONCLUSIVE.
    def test_04_рост_объясним_позицией(self):
        self.base_exp(cluster("canva", 2500, 70, 9.0),
                      cluster("canva", 2500, 105, 5.0))
        r = ver.evaluate(EXP, "2026-09-02")
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertIn("позиц", r["verdict_reason"])

    # 5. CTR вырос, но matched query set почти отсутствует → INCONCLUSIVE.
    def test_05_мало_совпадающих_запросов(self):
        self.base_exp(cluster("canva", 2500, 70, 6.3, n=2),
                      cluster("canva", 2500, 105, 6.3, n=2))
        r = ver.evaluate(EXP, "2026-09-02")
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertIn("мало", r["verdict_reason"])

    # 6. Малая ёмкость кластера (оптимизация 31.08.2026): окно скользящее,
    # 500 такой кластер не наберёт никогда — порог адаптируется, вывод
    # выносится с пометкой и ограниченной уверенностью, а не вечное
    # «мало данных».
    def test_06_малая_ёмкость_порог_адаптируется(self):
        self.base_exp(cluster("canva", 1200, 30, 6.3),
                      cluster("canva", 280, 12, 6.3))
        r = ver.evaluate(EXP, "2026-09-02")
        self.assertNotEqual(r["verdict"], "INSUFFICIENT_DATA")
        self.assertNotEqual(r["verdict"], "REJECTED")
        self.assertTrue(r["effective_gate"]["adapted"])
        self.assertIn("адаптирован", " ".join(r["sample_quality"]))
        self.assertNotEqual(r["confidence"], "HIGH")

    # 6а. Ниже пола адаптации любой вывод — шум: честный INSUFFICIENT_DATA.
    def test_06а_ниже_пола_insufficient(self):
        self.base_exp(cluster("canva", 1200, 30, 6.3),
                      cluster("canva", 80, 3, 6.3))
        r = ver.evaluate(EXP, "2026-09-02")
        self.assertEqual(r["verdict"], "INSUFFICIENT_DATA")
        self.assertIn("не хватает", r["recommendation_detail"])

    # 7. Недостаточно baseline (ниже пола) → INSUFFICIENT_DATA.
    def test_07_мало_baseline(self):
        self.base_exp(cluster("canva", 60, 2, 6.3),
                      cluster("canva", 2500, 100, 6.3))
        r = ver.evaluate(EXP, "2026-09-02")
        self.assertEqual(r["verdict"], "INSUFFICIENT_DATA")

    # 8–9. Нулевые клики с любой стороны — система не падает.
    def test_08_нулевые_клики_baseline_не_падает(self):
        self.base_exp(cluster("canva", 2500, 0, 6.3),
                      cluster("canva", 2500, 100, 6.3))
        r = ver.evaluate(EXP, "2026-09-02")
        self.assertIn(r["verdict"], ("CONFIRMED", "INCONCLUSIVE"))

    def test_09_нулевые_клики_experiment_не_падает(self):
        self.base_exp(cluster("canva", 2500, 100, 6.3),
                      cluster("canva", 2500, 0, 6.3))
        r = ver.evaluate(EXP, "2026-09-02")
        self.assertEqual(r["verdict"], "REJECTED")

    # 10. Чистого окна после внедрения ещё нет → отчёт формируется, причина ясна.
    def test_10_нет_чистого_окна_после_внедрения(self):
        self.day("2026-08-18", "2026-08-04", "2026-08-16",
                 cluster("canva", 2500, 70, 6.3))
        self.day("2026-08-30", "2026-08-16", "2026-08-27",
                 cluster("canva", 2500, 105, 6.3))
        r = ver.evaluate(EXP, "2026-08-30")
        self.assertEqual(r["verdict"], "INSUFFICIENT_DATA")
        self.assertIn("захватывает период до внедрения", r["verdict_reason"])
        # Дата очистки посчитана: старт 19.08 + 1 день чистоты + лаг ~14 дн.
        self.assertIsNotNone(r["recommendation_detail"])

    # 11. Несколько экспериментов оцениваются независимо.
    def test_11_эксперименты_независимы(self):
        base = cluster("canva", 2500, 70, 6.3) + cluster("figma", 2500, 100, 5.0)
        after = cluster("canva", 2500, 105, 6.3) + cluster("figma", 2500, 40, 5.0)
        self.base_exp(base, after)
        r1 = ver.evaluate(EXP, "2026-09-02")
        r2 = ver.evaluate({**EXP, "id": "test-2", "pages": ["/vendors/figma"]},
                          "2026-09-02")
        self.assertEqual(r1["verdict"], "CONFIRMED")
        self.assertEqual(r2["verdict"], "REJECTED")

    # 12. Огромная выборка, значимый, но крошечный uplift → не CONFIRMED.
    def test_12_эффект_ниже_бизнес_порога(self):
        self.base_exp(cluster("canva", 2_000_000, 60_000, 6.3),
                      cluster("canva", 2_000_000, 61_500, 6.3))
        r = ver.evaluate(EXP, "2026-09-02")
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertIn("порог", r["verdict_reason"])

    # 13. Большой uplift на крошечной выборке → INSUFFICIENT_DATA.
    def test_13_большой_uplift_на_малой_выборке(self):
        self.base_exp(cluster("canva", 100, 1, 6.3),
                      cluster("canva", 80, 10, 6.3))
        r = ver.evaluate(EXP, "2026-09-02")
        self.assertEqual(r["verdict"], "INSUFFICIENT_DATA")

    # 14. Matched CTR растёт, общий падает из-за новых запросов — видны оба.
    def test_14_matched_растёт_общий_падает(self):
        base = cluster("canva", 2500, 70, 6.3)
        after = cluster("canva", 2500, 105, 6.3) + [
            q("canva новый мусорный", 5000, 0, 40.0)]
        self.base_exp(base, after)
        r = ver.evaluate(EXP, "2026-09-02")
        self.assertEqual(r["verdict"], "CONFIRMED")  # вывод — по matched
        m, o = r["matched_metrics"], r["metrics"]
        self.assertGreater(m["experiment"]["ctr"], m["baseline"]["ctr"])
        self.assertLess(o["experiment"]["ctr"], o["baseline"]["ctr"])

    # 15. Общий CTR растёт за счёт новых запросов, matched не меняется → не CONFIRMED.
    def test_15_рост_только_за_счёт_новых_запросов(self):
        base = cluster("canva", 2500, 70, 6.3)
        after = cluster("canva", 2500, 70, 6.3) + [
            q("canva хайповый новый", 1000, 200, 2.0)]
        self.base_exp(base, after)
        r = ver.evaluate(EXP, "2026-09-02")
        self.assertNotEqual(r["verdict"], "CONFIRMED")

    # Окно, захватившее день внедрения, помечается и снижает качество выборки.
    def test_окно_с_днём_внедрения_помечено(self):
        self.day("2026-08-18", "2026-08-04", "2026-08-16",
                 cluster("canva", 2500, 70, 6.3))
        self.day("2026-09-01", "2026-08-19", "2026-08-29",
                 cluster("canva", 2500, 105, 6.1))
        r = ver.evaluate(EXP, "2026-09-01")
        self.assertTrue(r["windows"]["experiment"]["tainted"])
        self.assertTrue(any("внедрения" in s for s in r["sample_quality"]))

    # История контрольной точки не перезаписывается.
    def test_история_не_перезаписывается(self):
        self.base_exp(cluster("canva", 2500, 70, 6.3),
                      cluster("canva", 2500, 105, 6.1))
        r = ver.evaluate(EXP, "2026-09-02")
        old_hist = ver.HISTORY_DIR
        ver.HISTORY_DIR = self.tmp / "hist"
        try:
            p = ver.save_history(r)
            first = p.read_text(encoding="utf-8")
            r2 = dict(r, verdict="REJECTED")
            ver.save_history(r2)
            self.assertEqual(p.read_text(encoding="utf-8"), first)
        finally:
            ver.HISTORY_DIR = old_hist


class ZTestTest(unittest.TestCase):
    def test_известный_случай_значим(self):
        r = st.two_proportion_test(70, 2500, 105, 2500)
        self.assertLess(r["p_value"], 0.05)
        self.assertGreater(r["absolute_uplift"], 0)

    def test_равные_доли_незначимы(self):
        r = st.two_proportion_test(70, 2500, 70, 2500)
        self.assertGreater(r["p_value"], 0.9)

    def test_нулевые_показы_не_падают(self):
        r = st.two_proportion_test(0, 0, 5, 100)
        self.assertIsNone(r["p_value"])

    def test_обе_стороны_без_кликов(self):
        r = st.two_proportion_test(0, 1000, 0, 1000)
        self.assertEqual(r["p_value"], 1.0)


if __name__ == "__main__":
    unittest.main()


class RenderTest(unittest.TestCase):
    """Панель контрольной даты в письме — чистые функции рендера."""

    def _exp_with_eval(self, verdict="CONFIRMED", rec="EXPAND", req=True):
        return {
            "ticket": "SEO-EXP-T", "control_date_today": True,
            "evaluation": {
                "verdict": verdict, "confidence": "HIGH",
                "verdict_reason": "статистически значимый рост CTR",
                "recommendation": rec,
                "recommendation_detail": "применить формулу к следующим карточкам",
                "recommended_targets": ["/vendors/a", "/vendors/b", "/vendors/c",
                                        "/vendors/d"],
                "requires_owner_decision": req,
                "position_delta": 0.2,
                "windows": {"baseline": {"from": "2026-08-04", "to": "2026-08-16"},
                            "experiment": {"from": "2026-08-20", "to": "2026-08-30",
                                           "tainted": False}},
                "matched_metrics": {"baseline": {"impressions": 2500, "ctr": 0.028},
                                    "experiment": {"impressions": 2500, "ctr": 0.041},
                                    "queries": 37},
                "statistical_result": {"p_value": 0.018, "baseline_ctr": 0.028,
                                       "experiment_ctr": 0.041},
            }}

    def test_панель_подтверждённого_вердикта(self):
        import report_v4
        html = report_v4._verdict_panel(self._exp_with_eval())
        for needle in ("ПОДТВЕРЖДЁН", "ТРЕБУЕТСЯ ВАШЕ РЕШЕНИЕ",
                       "EXPAND SEO-EXP-T", "p=0.018", "37"):
            self.assertIn(needle, html)
        self.assertIn("и ещё 1", html)  # 4 targets → 3 + «ещё 1»

    def test_панель_не_показывается_вне_контрольной_даты(self):
        import report_v4
        e = self._exp_with_eval()
        e["control_date_today"] = False
        self.assertEqual(report_v4._verdict_panel(e), "")

    def test_строка_решения_для_блока_от_вас(self):
        import report_v4
        line = report_v4._experiment_decision_line(self._exp_with_eval())
        self.assertIn("SEO-EXP-T", line)
        self.assertIn("расширить", line)
        self.assertIn("Ответьте в чате", line)
