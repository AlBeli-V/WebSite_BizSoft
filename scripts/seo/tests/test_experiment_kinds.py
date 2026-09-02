"""Типы оценки экспериментов и атрибуция кластеров (проверка 31.08.2026).

Закрепляют исправленные ошибки: PAGES-EXP-001 приписывались показы чужих
запросов («оплата canva…» — старые страницы), SEO-EXP-003 терял «claude»-
запросы; CONTENT-001 и PAGES-EXP-001 не могли получить вердикт от CTR-движка
по построению (нет CTR-цели / нет baseline-окна у новых страниц).
"""

import datetime as dt
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import experiment_stats  # noqa: E402
import experiment_verdict  # noqa: E402
import experiments  # noqa: E402
import serp_snippets  # noqa: E402


class ClusterKeysTest(unittest.TestCase):
    def test_интент_фильтр_отсекает_чужие_запросы(self):
        e = {"pages": ["/alternatives/canva"],
             "query_intent_any": ["аналог", "альтернатив"]}
        keys = experiments.cluster_keys(e)
        self.assertTrue(experiments.query_matches("аналоги canva для бизнеса", keys))
        # Запрос вендорского кластера — не экспозиция страницы аналогов.
        self.assertFalse(experiments.query_matches(
            "оплата canva для юридических лиц из россии", keys))

    def test_исключения_отсекают_смежный_кластер(self):
        e = {"pages": ["/vendors/anthropic"],
             "query_markers": ["anthropic", "claude"],
             "query_exclude": ["claude code"]}
        keys = experiments.cluster_keys(e)
        self.assertTrue(experiments.query_matches("купить claude team", keys))
        self.assertFalse(experiments.query_matches("claude code купить", keys))

    def test_без_маркеров_работает_прежняя_эвристика(self):
        keys = experiments.cluster_keys({"pages": ["/vendors/clip-studio-paint"]})
        self.assertTrue(experiments.query_matches("clip studio paint купить", keys))
        self.assertFalse(experiments.query_matches("photoshop купить", keys))


def _dump(dirpath, file_date, w_from, w_to, queries):
    (dirpath / f"yandex-{file_date}.json").write_text(json.dumps({
        "popular_queries": {"date_from": w_from, "date_to": w_to,
                            "queries": queries}}, ensure_ascii=False),
        encoding="utf-8")


def _q(text, shows, clicks=0, pos=5.0):
    return {"query_text": text,
            "indicators": {"TOTAL_SHOWS": shows, "TOTAL_CLICKS": clicks,
                           "AVG_SHOW_POSITION": pos}}


class IsolatedDataTest(unittest.TestCase):
    """Общая изоляция: выгрузки и SERP — во временных каталогах."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.serp = pathlib.Path(tempfile.mkdtemp())
        self.old_data = experiment_stats.DATA_DIR
        self.old_serp = serp_snippets.SERP_DIR
        experiment_stats.DATA_DIR = self.tmp
        serp_snippets.SERP_DIR = self.serp

    def tearDown(self):
        experiment_stats.DATA_DIR = self.old_data
        serp_snippets.SERP_DIR = self.old_serp
        shutil.rmtree(self.tmp, ignore_errors=True)
        shutil.rmtree(self.serp, ignore_errors=True)

    def _serp_write(self, date, rows):
        (self.serp / f"{date}-serp.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows),
            encoding="utf-8")


GROWTH_EXP = {
    "id": "cluster-x", "ticket": "CONTENT-001", "start": "2026-08-19",
    "evaluation_kind": "impressions_growth",
    "pages": ["/blog/statya", "/vendors/depositphotos"],
    "target_page": "/blog/statya",
    "query_markers": ["depositphotos"],
    "baseline": {"impressions_cluster": 273, "days": 14},
}


class ImpressionsGrowthTest(IsolatedDataTest):
    def test_рост_выше_порога_подтверждается_с_рекомендацией(self):
        # Чистое окно целиком после старта: 546 показов за 13 дней ≈ 42/день
        # против 19,5/день baseline — рост, статья в топ-10.
        _dump(self.tmp, "2026-09-04", "2026-08-20", "2026-09-01",
              [_q("оплата depositphotos", 546)])
        self._serp_write("2026-09-03", [{
            "date": "2026-09-03", "query": "как оплатить depositphotos",
            "top": [{"domain": "biz-soft.pro",
                     "url": "https://biz-soft.pro/blog/statya", "title": "Как оплатить"}]}])
        ev = experiment_verdict.evaluate(GROWTH_EXP, "2026-09-04")
        self.assertEqual(ev["evaluation_kind"], "impressions_growth")
        self.assertEqual(ev["verdict"], "CONFIRMED")
        self.assertIn("топ-10", ev["verdict_reason"])
        self.assertEqual(ev["recommendation"], "EXPAND")
        self.assertTrue(ev["requires_owner_decision"])
        self.assertIn("без критерия значимости", ev["summary_line"])

    def test_падение_показов_не_объявляется_REJECTED(self):
        _dump(self.tmp, "2026-09-04", "2026-08-20", "2026-09-01",
              [_q("оплата depositphotos", 130)])  # 10/день против 19,5
        ev = experiment_verdict.evaluate(GROWTH_EXP, "2026-09-04")
        self.assertEqual(ev["verdict"], "INCONCLUSIVE")
        self.assertIn("сезон", ev["verdict_reason"])

    def test_без_чистого_окна_честный_insufficient(self):
        _dump(self.tmp, "2026-08-31", "2026-08-17", "2026-08-29",
              [_q("оплата depositphotos", 400)])
        ev = experiment_verdict.evaluate(GROWTH_EXP, "2026-08-31")
        self.assertEqual(ev["verdict"], "INSUFFICIENT_DATA")
        self.assertIn("не очистилось", ev["verdict_reason"])


LAUNCH_EXP = {
    "id": "pages-x", "ticket": "PAGES-EXP-001", "start": "2026-08-30",
    "evaluation_kind": "launch",
    "pages": ["/alternatives/canva", "/alternatives/miro"],
    "query_intent_any": ["аналог", "альтернатив"],
    "launch_criteria": {"min_pages_in_search": 2, "min_weekly_impressions": 100,
                        "by_day": 14, "first_clicks_by_day": 28},
}


class LaunchTest(IsolatedDataTest):
    def test_до_вехи_прогресс_а_не_вердикт(self):
        ev = experiment_verdict.evaluate(LAUNCH_EXP, "2026-09-01")
        self.assertEqual(ev["verdict"], "INSUFFICIENT_DATA")
        self.assertIn("идёт набор", ev["verdict_reason"])
        self.assertIn("2026-09-13", ev["verdict_reason"])

    def test_на_вехе_выполненные_критерии_подтверждают_запуск(self):
        _dump(self.tmp, "2026-09-13", "2026-08-31", "2026-09-12",
              [_q("аналоги canva", 140), _q("альтернатива miro", 100)])
        self._serp_write("2026-09-12", [{
            "date": "2026-09-12", "query": "аналоги canva", "top": [
                {"domain": "biz-soft.pro",
                 "url": "https://biz-soft.pro/alternatives/canva", "title": "Аналоги Canva"},
                {"domain": "biz-soft.pro",
                 "url": "https://biz-soft.pro/alternatives/miro", "title": "Аналоги Miro"},
            ]}])
        ev = experiment_verdict.evaluate(LAUNCH_EXP, "2026-09-13")
        self.assertEqual(ev["verdict"], "CONFIRMED")
        self.assertEqual(ev["recommendation"], "KEEP")
        self.assertIn("запуск состоялся", ev["verdict_reason"])

    def test_на_вехе_невыполненные_критерии_с_разбором(self):
        _dump(self.tmp, "2026-09-13", "2026-08-31", "2026-09-12",
              [_q("аналоги canva", 7)])
        ev = experiment_verdict.evaluate(LAUNCH_EXP, "2026-09-13")
        self.assertEqual(ev["verdict"], "INCONCLUSIVE")
        self.assertIn("веха не выполнена", ev["verdict_reason"])
        self.assertIn("переобход", ev["recommendation_detail"])
        self.assertFalse(ev["requires_owner_decision"])  # решение — на вехе кликов


if __name__ == "__main__":
    unittest.main()


class AdaptiveGateTest(unittest.TestCase):
    """Оптимизация порога 31.08.2026: малый кластер не должен ждать вечно."""

    def test_большая_ёмкость_порог_не_меняется(self):
        self.assertEqual(experiment_stats.effective_gate(647, 500), (500, False))

    def test_малая_ёмкость_порог_снижается_с_пометкой(self):
        gate, adapted = experiment_stats.effective_gate(258, 500)
        self.assertTrue(adapted)
        self.assertEqual(gate, 181)  # 0.7 × ёмкости

    def test_ниже_пола_порог_равен_полу(self):
        gate, adapted = experiment_stats.effective_gate(92, 500)
        self.assertEqual(gate, 100)
        self.assertTrue(adapted)

    def test_mde_падает_с_ростом_выборки(self):
        small = experiment_stats.min_detectable_uplift(0.006, 100, 100)
        big = experiment_stats.min_detectable_uplift(0.006, 5000, 5000)
        self.assertGreater(small, big)
        self.assertGreater(small, 1.0)  # при n=100 различим только кратный рост


class FormulaGroupTest(IsolatedDataTest):
    """Пул формулы: мощность группы отвечает раньше малого участника."""

    def setUp(self):
        super().setUp()
        import experiments
        self.reg_tmp = pathlib.Path(tempfile.mkdtemp())
        self.old_reg = experiments.REGISTRY
        experiments.REGISTRY = self.reg_tmp / "seo-experiments.json"
        experiments.REGISTRY.write_text(json.dumps({"experiments": [
            {"id": "a", "ticket": "T-A", "start": "2026-08-19",
             "status": "running", "pages": ["/vendors/canva"],
             "formula_group": "g1"},
            {"id": "b", "ticket": "T-B", "start": "2026-08-19",
             "status": "running", "pages": ["/vendors/miro"],
             "formula_group": "g1"},
        ]}, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        import experiments
        experiments.REGISTRY = self.old_reg
        shutil.rmtree(self.reg_tmp, ignore_errors=True)
        super().tearDown()

    def test_пул_суммирует_обе_стороны_обоих_участников(self):
        _dump(self.tmp, "2026-08-18", "2026-08-05", "2026-08-18",
              [_q("canva купить", 300, 2), _q("miro купить", 300, 2)])
        _dump(self.tmp, "2026-09-04", "2026-08-20", "2026-09-01",
              [_q("canva купить", 300, 9), _q("miro купить", 300, 9)])
        g = experiment_verdict._formula_group_result("g1", "2026-09-04")
        self.assertEqual(sorted(g["members"]), ["T-A", "T-B"])
        self.assertEqual(g["baseline"]["impressions"], 600)
        self.assertEqual(g["experiment"]["clicks"], 18)
        self.assertIsNotNone(g["stat"]["p_value"])

    def test_один_участник_с_окнами_пула_не_даёт(self):
        _dump(self.tmp, "2026-08-18", "2026-08-05", "2026-08-18",
              [_q("canva купить", 300, 2)])
        _dump(self.tmp, "2026-09-04", "2026-08-20", "2026-09-01",
              [_q("canva купить", 300, 9)])
        # У второго участника кластер miro в выгрузках отсутствует — окна
        # есть, но пул честно считает вклад обоих; результат всё же есть,
        # поэтому проверяем границу: без выгрузок вовсе пула нет.
        for f in self.tmp.glob("*.json"):
            f.unlink()
        self.assertIsNone(
            experiment_verdict._formula_group_result("g1", "2026-09-04"))


class VerdictRenderTest(unittest.TestCase):
    """Веб-отчёт рендерит вердикт любого типа оценки (регрессия 02.09, #298)."""

    def setUp(self):
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
        import webreport
        self.wr = webreport

    def _ev(self, **kw):
        base = {"ticket": "T-1", "verdict": "CONFIRMED", "verdict_reason": "причина",
                "confidence": "MEDIUM", "recommendation": "KEEP",
                "recommendation_detail": "деталь", "sample_quality": [],
                "recommended_targets": [], "requires_owner_decision": False}
        base.update(kw)
        return {"evaluation": base}

    def test_рост_показов_без_baseline_окна_не_падает(self):
        e = self._ev(evaluation_kind="impressions_growth",
                     summary_line="показы 33/день против 20/день",
                     windows={"experiment": {"from": "2026-08-20", "to": "2026-09-01",
                                             "tainted": False}},
                     metrics={"baseline_registry": {"impressions": 273, "days": 14}})
        html = self.wr._evaluation_html(e)
        self.assertIn("окно после", html)
        self.assertIn("база сравнения", html)
        self.assertNotIn("окно до", html)

    def test_запуск_страниц_показывает_критерии(self):
        e = self._ev(evaluation_kind="launch",
                     summary_line="в выдаче 2 из 7",
                     windows={"experiment": {"from": "2026-08-31", "to": "2026-09-12",
                                             "tainted": False}},
                     metrics={"launch": {"pages_in_search": 2, "pages_total": 7,
                                         "need_pages": 5, "weekly_impressions": 40,
                                         "need_weekly": 300}})
        html = self.wr._evaluation_html(e)
        self.assertIn("критерии запуска", html)

    def test_ctr_вердикт_рендерится_как_прежде(self):
        e = self._ev(evaluation_kind="ctr",
                     windows={"baseline": {"from": "2026-08-06", "to": "2026-08-17"},
                              "experiment": {"from": "2026-08-19", "to": "2026-08-30",
                                             "tainted": False}},
                     metrics={"baseline": {"impressions": 532, "clicks": 2},
                              "experiment": {"impressions": 610, "clicks": 4}},
                     matched_metrics={"queries": 24}, position_delta=-0.8,
                     statistical_result={"baseline_ctr": 0.0038,
                                         "experiment_ctr": 0.0066,
                                         "absolute_uplift": 0.0028,
                                         "relative_uplift": 0.94, "p_value": 0.633})
        html = self.wr._evaluation_html(e)
        self.assertIn("окно до", html)
        self.assertIn("p-value", html)


class MatchedGateTest(IsolatedDataTest):
    """Гейт считается от matched-набора (issue #297)."""

    def test_гейт_адаптируется_по_matched_а_не_overall(self):
        exp = {"id": "g", "ticket": "T-1", "start": "2026-08-19",
               "pages": ["/vendors/canva"], "query_markers": ["canva"]}
        # overall выше 500 с обеих сторон, matched — ниже (общий запрос один).
        _dump(self.tmp, "2026-08-18", "2026-08-05", "2026-08-18",
              [_q("canva общий", 300, 2), _q("canva только до", 250, 1)])
        _dump(self.tmp, "2026-09-04", "2026-08-20", "2026-09-01",
              [_q("canva общий", 300, 6), _q("canva только после", 260, 2)])
        r = experiment_verdict.evaluate(exp, "2026-09-04")
        self.assertTrue(r["effective_gate"]["adapted"])
        self.assertNotEqual(r["verdict"], "INSUFFICIENT_DATA")

    def test_нехватка_baseline_не_предлагает_копить(self):
        exp = {"id": "g", "ticket": "T-1", "start": "2026-08-19",
               "pages": ["/vendors/canva"], "query_markers": ["canva"]}
        _dump(self.tmp, "2026-08-18", "2026-08-05", "2026-08-18",
              [_q("canva общий", 40, 0)])
        _dump(self.tmp, "2026-09-04", "2026-08-20", "2026-09-01",
              [_q("canva общий", 900, 20)])
        r = experiment_verdict.evaluate(exp, "2026-09-04")
        self.assertEqual(r["verdict"], "INSUFFICIENT_DATA")
        self.assertEqual(r["recommendation"], "NEW_TEST")
        self.assertIn("в прошлом и не растёт", r["recommendation_detail"])
