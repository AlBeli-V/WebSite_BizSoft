#!/usr/bin/env python3
"""Тесты Wordstat Intelligence: бюджет, лимиты, кэш, семантика, покрытие."""

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
WS = ROOT / "scripts" / "seo" / "wordstat"
sys.path.insert(0, str(WS))


def load(name):
    spec = importlib.util.spec_from_file_location(name, WS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestConfig(unittest.TestCase):
    """Тарифы конфигурируемы и привязаны к дате."""

    def setUp(self):
        self.c = load("config")
        self.cfg = self.c.load()

    def test_prices_match_tariff(self):
        self.assertAlmostEqual(self.c.price_of("getTop", cfg=self.cfg), 0.02)
        self.assertAlmostEqual(self.c.price_of("getDynamics", cfg=self.cfg), 0.02)
        self.assertAlmostEqual(self.c.price_of("getRegionsDistribution", cfg=self.cfg), 0.05)
        self.assertEqual(self.c.price_of("getRegionsTree", cfg=self.cfg), 0.0)

    def test_price_uses_effective_date(self):
        cfg = json.loads(json.dumps(self.cfg))
        cfg["pricing"].append({"method": "getTop", "api_path": "/topRequests",
                               "price_per_1000": 40, "currency": "RUB",
                               "effective_date": "2026-12-01"})
        self.assertAlmostEqual(self.c.price_of("getTop", "2026-08-20", cfg), 0.02)
        self.assertAlmostEqual(self.c.price_of("getTop", "2026-12-05", cfg), 0.04)

    def test_quota_not_budget_is_the_constraint(self):
        """Ключевой вывод аудита: при 100/час бюджет израсходовать нельзя."""
        self.assertFalse(self.c.budget_is_binding(self.cfg, 100))
        self.assertLess(self.c.max_monthly_spend(self.cfg, 100),
                        self.cfg["budget"]["monthly_hard_cap_rub"])
        self.assertTrue(self.c.budget_is_binding(self.cfg, 500))


class TestBudget(unittest.TestCase):
    """Предохранители расхода."""

    def setUp(self):
        self.b = load("budget")
        self.c = load("config")
        self.cfg = self.c.load()
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.b.LEDGER_DIR = self.tmp

    def controller(self, pilot=False):
        ctl = self.b.BudgetController(self.cfg, today="2026-08-20", pilot=pilot)
        ctl.path = self.tmp / "2026-08.jsonl"
        ctl.entries = []
        return ctl

    def spend(self, ctl, rub):
        ctl.entries = [{"timestamp": "2026-08-20T00:00:00+00:00", "cost_rub": rub,
                        "cache_hit": False, "result_count": 0,
                        "unique_result_count": 0, "new_commercial_phrases": 0,
                        "new_clusters": 0, "status": "ok", "pilot": False}]

    def test_hard_cap_cannot_be_exceeded(self):
        ctl = self.controller()
        self.spend(ctl, 5500)
        self.assertEqual(ctl.state(), "hard_stop")
        ok, why = ctl.can_spend("getTop", "discovery")
        self.assertFalse(ok)
        self.assertIn("жёсткая остановка", why)

    def test_soft_stop_guards_the_working_share(self):
        """Мягкая остановка охраняет рабочую часть, резерв — только для проверок."""
        ctl = self.controller()
        self.spend(ctl, self.cfg["budget"]["working_cap_rub"] + 1)
        self.assertEqual(ctl.state(), "soft_stop")
        self.assertFalse(ctl.can_spend("getTop", "discovery")[0])
        self.assertTrue(ctl.can_spend("getTop", "decision_validation")[0])

    def test_reserve_is_a_fifth_of_the_cap(self):
        b = self.cfg["budget"]
        self.assertEqual(b["working_cap_rub"] + b["control_reserve_rub"],
                         b["monthly_hard_cap_rub"])
        self.assertLess(b["control_reserve_rub"], b["working_cap_rub"])

    def test_soft_stop_allows_only_critical(self):
        ctl = self.controller()
        self.spend(ctl, 5100)
        self.assertEqual(ctl.state(), "soft_stop")
        self.assertFalse(ctl.can_spend("getTop", "discovery")[0])
        self.assertFalse(ctl.can_spend("getTop", "exploration")[0])
        self.assertTrue(ctl.can_spend("getTop", "decision_validation")[0])

    def test_call_that_would_cross_cap_is_refused(self):
        ctl = self.controller()
        self.spend(ctl, 5499.995)
        self.assertFalse(ctl.can_spend("getRegionsDistribution", "decision_validation")[0])

    def test_free_method_always_allowed(self):
        ctl = self.controller()
        self.spend(ctl, 5500)
        self.assertTrue(ctl.can_spend("getRegionsTree", "discovery")[0])

    def test_pilot_has_own_cap(self):
        ctl = self.controller(pilot=True)
        ctl.entries = [{"timestamp": "2026-08-20T00:00:00+00:00", "cost_rub": 500,
                        "cache_hit": False, "result_count": 0,
                        "unique_result_count": 0, "new_commercial_phrases": 0,
                        "new_clusters": 0, "status": "ok", "pilot": True}]
        self.assertEqual(ctl.state(), "pilot_stop")
        self.assertFalse(ctl.can_spend("getTop", "discovery")[0])

    def test_every_paid_call_is_recorded_with_reason_and_cost(self):
        ctl = self.controller()
        entry = ctl.record(method="getTop", phrase="canva", cluster="canva",
                           reason="discovery", cache_hit=False, result_count=10,
                           unique_result_count=8)
        for field in ("reason", "cost_rub", "method", "phrase", "timestamp"):
            self.assertIn(field, entry)
        self.assertAlmostEqual(entry["cost_rub"], 0.02)

    def test_cache_hit_costs_nothing(self):
        ctl = self.controller()
        entry = ctl.record(method="getTop", phrase="canva", cluster="canva",
                           reason="discovery", cache_hit=True)
        self.assertEqual(entry["cost_rub"], 0.0)


class TestLimiter(unittest.TestCase):
    """Ограничитель частоты и повторы."""

    def setUp(self):
        self.L = load("limiter")
        self.tmp = pathlib.Path(tempfile.mkdtemp()) / "state.json"

    def limiter(self, rps=10, rph=5):
        return self.L.RateLimiter(rps, rph, now=1000.0, state_path=self.tmp)

    def test_hourly_quota_stops_the_run(self):
        rl = self.limiter()
        for _ in range(5):
            rl.acquire(sleep=lambda s: None)
        with self.assertRaises(self.L.QuotaExhausted):
            rl.acquire(sleep=lambda s: None)

    def test_state_survives_between_runs(self):
        rl = self.limiter()
        for _ in range(3):
            rl.acquire(sleep=lambda s: None)
        again = self.limiter()
        self.assertEqual(again.hour_used(), 3)
        self.assertEqual(again.hour_remaining(), 2)

    def test_unknown_state_pauses_briefly_not_for_an_hour(self):
        """Нечитаемое состояние — повод для короткой паузы, а не блокировки на час.

        Ограничитель не должен быть строже сервиса: он ждёт минуту и проверяет
        пробой, вместо того чтобы вслепую терять целое окно.
        """
        self.tmp.parent.mkdir(parents=True, exist_ok=True)
        self.tmp.write_text("не json", encoding="utf-8")
        rl = self.limiter()
        self.assertGreater(rl.seconds_until_slot(), 0)
        self.assertLessEqual(rl.seconds_until_slot(), self.L.PROBE_START_SEC)
        self.assertLess(rl.seconds_until_slot(), 3600)

    def test_quota_error_does_not_fake_own_usage(self):
        """Отказ сервиса не должен подделывать наш собственный счёт вызовов."""
        rl = self.limiter(rph=100)
        for _ in range(5):
            rl.acquire(sleep=lambda s: None)
        rl.note_quota_error("allowed 100 requests")
        self.assertEqual(rl.hour_used(), 5, "счёт реальных вызовов искажён")
        self.assertLessEqual(rl.seconds_until_slot(), self.L.PROBE_START_SEC)

    def test_wait_for_slot_returns_when_free(self):
        rl = self.limiter(rph=100)
        self.assertEqual(rl.wait_for_slot(sleep=lambda s: None), 0.0)

    def test_second_window_throttles(self):
        slept = []
        rl = self.L.RateLimiter(2, 100, now=1000.0, state_path=self.tmp)
        for _ in range(4):
            rl.acquire(sleep=slept.append)
        self.assertTrue(any(s > 0 for s in slept), "секундное окно не притормозило")

    def test_observed_quota_is_recorded(self):
        rl = self.limiter(rph=500)
        rl.note_quota_error("rate quota limit exceed: allowed 100 requests")
        self.assertEqual(rl.observed_quota, 100)
        self.assertEqual(rl.rph, 100)

    def test_quota_error_waits_probe_interval_not_full_hour(self):
        """После отказа ждём минуту и пробуем, а не блокируемся на час вслепую."""
        rl = self.limiter(rph=100)
        rl.note_quota_error("allowed 100 requests")
        self.assertLessEqual(rl.seconds_until_slot(), self.L.PROBE_START_SEC)
        self.assertLess(rl.seconds_until_slot(), 3600)

    def test_probe_is_allowed_after_interval(self):
        rl = self.limiter(rph=100)
        rl.note_quota_error("allowed 100 requests")
        later = self.L.RateLimiter(10, 100, now=1000.0 + self.L.PROBE_START_SEC + 1,
                                   state_path=self.tmp)
        self.assertTrue(later.probe_due())
        later.acquire(sleep=lambda s: None)          # проба обязана пройти
        self.assertEqual(later.hour_used(), 1)

    def test_success_clears_the_block(self):
        rl = self.limiter(rph=100)
        rl.note_quota_error("allowed 100 requests")
        later = self.L.RateLimiter(10, 100, now=1000.0 + self.L.PROBE_START_SEC + 1,
                                   state_path=self.tmp)
        later.acquire(sleep=lambda s: None)
        later.note_success()
        self.assertEqual(later.blocked_until, 0.0)
        self.assertEqual(later.probe_interval, self.L.PROBE_START_SEC)

    def test_repeated_refusal_doubles_the_wait(self):
        rl = self.limiter(rph=100)
        rl.note_quota_error("x")
        first = rl.probe_interval
        rl.note_quota_error("x")
        self.assertEqual(rl.probe_interval, min(self.L.PROBE_MAX_SEC, first * 2))

    def test_probe_interval_is_capped(self):
        rl = self.limiter(rph=100)
        for _ in range(10):
            rl.note_quota_error("x")
        self.assertLessEqual(rl.probe_interval, self.L.PROBE_MAX_SEC)

    def test_backoff_grows(self):
        rl = self.limiter()
        self.assertLess(rl.backoff_delay(0), rl.backoff_delay(3))

    def test_429_is_not_retried(self):
        rl = self.L.RateLimiter(10, 100, now=1000.0, state_path=self.tmp)
        calls = []

        class Resp:
            status_code = 429
            text = "allowed 100 requests"

        def call():
            calls.append(1)
            return Resp()

        with self.assertRaises(self.L.QuotaExhausted):
            self.L.with_retry(call, limiter=rl, sleep=lambda s: None)
        self.assertEqual(len(calls), 1, "429 повторяться не должен — это квота")

    def test_server_error_is_retried(self):
        rl = self.L.RateLimiter(10, 100, now=1000.0, state_path=self.tmp)
        seq = []

        class Resp:
            def __init__(self, code):
                self.status_code = code
                self.text = ""

        def call():
            seq.append(1)
            return Resp(500 if len(seq) < 3 else 200)

        r = self.L.with_retry(call, limiter=rl, sleep=lambda s: None)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(seq), 3)


class TestNormalize(unittest.TestCase):
    """Нормализация, дедупликация, интент, релевантность бизнесу."""

    def setUp(self):
        self.N = load("normalize")

    def test_morphological_variants_collapse(self):
        keys = {self.N.morph_key(p) for p in
                ("купить корела", "корел купить", "Купить КОРЕЛ", "корела  купить")}
        self.assertEqual(len(keys), 1)

    def test_intent_scores_are_independent(self):
        c, i = self.N.intent_scores("canva скачать бесплатно")
        self.assertEqual(self.N.classify_intent("canva скачать бесплатно"),
                         "informational")
        self.assertGreater(i, c)

    def test_problem_phrasing_is_commercial(self):
        self.assertEqual(self.N.classify_intent("midjourney не работает из россии"),
                         "commercial")

    def test_out_of_scope_filters_payment_cards(self):
        self.assertFalse(self.N.in_scope("виртуальная карта для оплаты зарубежных сервисов"))
        self.assertFalse(self.N.in_scope("карта для оплаты зарубежных сервисов"))
        self.assertTrue(self.N.in_scope("оплата canva для юридических лиц"))

    def test_cluster_name_is_not_a_word_stump(self):
        name = self.N.cluster_of("оплата зарубежных сервисов из россии", {},
                                 seed="оплата зарубежных сервисов")
        self.assertEqual(name, "оплата зарубежных сервисов")

    def test_subcluster_maps_to_page_need(self):
        self.assertEqual(self.N.subcluster_of("canva для юридических лиц"),
                         "покупка на юрлицо")
        self.assertEqual(self.N.subcluster_of("canva тарифы"), "цены и тарифы")

    def test_dedupe_keeps_most_frequent(self):
        rows = [{"phrase": "купить корела", "frequency": 10},
                {"phrase": "корел купить", "frequency": 40}]
        out = self.N.dedupe(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["frequency"], 40)


class TestUniverse(unittest.TestCase):
    """База семантики: история не перезаписывается."""

    def setUp(self):
        self.U = load("universe")
        self.uni = self.U.Universe(pathlib.Path(tempfile.mkdtemp()) / "u.jsonl")

    def observe(self, phrase, freq, date):
        return self.uni.observe(phrase=phrase, frequency=freq, date=date,
                                source_seed="canva", region="225", period="30d",
                                method="getTop", cost_rub=0.02, vendors={"canva": "canva"})

    def test_history_accumulates(self):
        self.observe("canva купить", 100, "2026-07-01")
        self.observe("canva купить", 150, "2026-08-01")
        row = self.uni.get("canva купить")
        self.assertEqual(len(row["historical_frequency"]), 2)
        self.assertEqual(row["first_seen"], "2026-07-01")
        self.assertEqual(row["last_seen"], "2026-08-01")

    def test_trend_needs_two_points(self):
        self.observe("canva купить", 100, "2026-07-01")
        self.assertEqual(self.uni.trend("canva купить")["direction"], "unknown")
        self.observe("canva купить", 150, "2026-08-01")
        self.assertEqual(self.uni.trend("canva купить")["direction"], "growing")

    def test_cost_accumulates_per_phrase(self):
        self.observe("canva купить", 100, "2026-07-01")
        self.observe("canva купить", 150, "2026-08-01")
        self.assertAlmostEqual(self.uni.get("canva купить")["api_cost_rub"], 0.04)


class TestClientCache(unittest.TestCase):
    """Кэш и дедупликация запросов."""

    def setUp(self):
        self.client_mod = load("client")
        self.budget_mod = load("budget")
        self.c = load("config")
        self.cfg = self.c.load()
        tmp = pathlib.Path(tempfile.mkdtemp())
        self.budget_mod.LEDGER_DIR = tmp
        self.ctl = self.budget_mod.BudgetController(self.cfg, today="2026-08-20")
        self.ctl.path = tmp / "led.jsonl"
        self.ctl.entries = []
        self.cl = self.client_mod.WordstatClient(self.ctl, self.cfg)
        self.cl.cache_dir = tmp / "cache"
        self.cl.cache_dir.mkdir()

    def test_cache_key_includes_parameters(self):
        a = self.cl.cache_key("getTop", {"phrase": "canva", "numPhrases": 300,
                                         "regions": ["225"]})
        b = self.cl.cache_key("getTop", {"phrase": "canva", "numPhrases": 300,
                                         "regions": ["213"]})
        c = self.cl.cache_key("getTop", {"phrase": "canva", "numPhrases": 100,
                                         "regions": ["225"]})
        self.assertNotEqual(a, b, "регион обязан входить в ключ кэша")
        self.assertNotEqual(a, c, "глубина выдачи обязана входить в ключ кэша")

    def test_cache_hit_is_free_and_recorded(self):
        body = {"phrase": "canva", "numPhrases": 300, "regions": ["225"]}
        self.cl.cache_put("getTop", body, {"results": []}, "ok", "2026-08-20")
        res = self.cl.call("getTop", body, reason="discovery", phrase="canva",
                           today="2026-08-20")
        self.assertEqual(res["source"], "cache")
        self.assertEqual(res["cost_rub"], 0.0)
        self.assertTrue(self.ctl.entries[-1]["cache_hit"])

    def test_expired_cache_is_ignored(self):
        body = {"phrase": "canva", "numPhrases": 300, "regions": ["225"]}
        self.cl.cache_put("getTop", body, {"results": []}, "ok", "2026-08-20")
        path = self.cl._cache_path(self.cl.cache_key("getTop", body))
        entry = json.loads(path.read_text(encoding="utf-8"))
        entry["fetched_at"] = "2026-06-01T00:00:00+00:00"
        path.write_text(json.dumps(entry), encoding="utf-8")
        self.assertIsNone(self.cl.cache_get("getTop", body, "2026-08-20"))

    def test_budget_block_prevents_call(self):
        self.ctl.entries = [{"timestamp": "2026-08-20T00:00:00+00:00", "cost_rub": 5500,
                             "cache_hit": False, "result_count": 0,
                             "unique_result_count": 0, "new_commercial_phrases": 0,
                             "new_clusters": 0, "status": "ok", "pilot": False}]
        res = self.cl.call("getTop", {"phrase": "x"}, reason="discovery", phrase="x",
                           today="2026-08-20")
        self.assertEqual(res["status"], "budget_blocked")


class TestDiscovery(unittest.TestCase):
    """Расширение оценивается до вызова, а не после."""

    def setUp(self):
        self.D = load("discovery")
        self.U = load("universe")
        self.c = load("config")
        self.cfg = self.c.load()
        self.uni = self.U.Universe(pathlib.Path(tempfile.mkdtemp()) / "u.jsonl")
        self.stats = self.D.PatternStats(pathlib.Path(tempfile.mkdtemp()) / "s.json")

    def test_unproductive_pattern_is_dropped(self):
        for _ in range(20):
            self.stats.record("{vendor} для юридических лиц", ok=False, unique_new=0)
        prod = self.stats.productivity("{vendor} для юридических лиц", 0.55)
        self.assertLess(prod, 0.2)

    def test_repeated_seed_has_low_gain(self):
        vendor = {"slug": "canva", "vendor": "Canva", "anchor": "canva",
                  "category": "Дизайн", "url": "/vendors/canva"}
        self.uni.observe(phrase="canva купить", frequency=200, date="2026-08-20",
                         source_seed="canva купить", region="225", period="30d",
                         method="getTop", cost_rub=0.02, vendors={"canva": "canva"})
        ig = self.D.information_gain(pattern="{vendor} купить", vendor=vendor,
                                     universe=self.uni, stats=self.stats, prior=0.95,
                                     covered_clusters=set())
        self.assertGreaterEqual(ig["duplicate_probability"], 0.9)
        self.assertLess(ig["expected_information_gain"], 0.2)

    def test_plan_respects_per_vendor_limit(self):
        vendors = self.D.site_vendors()[:3]
        plan = self.D.build_seed_plan(vendors, self.uni, self.stats, set(),
                                      self.cfg["thresholds"])
        from collections import Counter
        for _, n in Counter(p["cluster"] for p in plan).items():
            self.assertLessEqual(n, self.cfg["thresholds"]["max_calls_per_vendor"])


class TestCoverage(unittest.TestCase):
    """Покрытие считается по частотности, разрывы — по действию."""

    def setUp(self):
        self.C = load("coverage")

    def cluster(self, **kw):
        base = {"cluster": "x", "commercial_demand": 1000, "commercial_phrases": 5,
                "page_exists": False, "indexed": False, "best_position": None,
                "impressions": 0, "clicks": 0, "ctr": None, "demand": 1000,
                "phrases": 5, "url": None, "top_phrases": [], "vendor": None,
                "category": None, "subclusters": {}}
        return base | kw

    def test_coverage_is_weighted_by_demand(self):
        clusters = {"big": self.cluster(cluster="big", commercial_demand=9000,
                                        page_exists=True),
                    "small": self.cluster(cluster="small", commercial_demand=1000)}
        cov = self.C.demand_coverage(clusters, set())
        self.assertEqual(cov["levels"]["page"], 0.9)

    def test_gap_classes_match_state(self):
        self.assertEqual(self.C.classify_gap(self.cluster(), "stable", set()), "GAP-A")
        self.assertEqual(self.C.classify_gap(
            self.cluster(page_exists=True), "stable", set()), "GAP-B")
        self.assertEqual(self.C.classify_gap(
            self.cluster(page_exists=True, indexed=True, best_position=25),
            "stable", set()), "GAP-C")
        self.assertEqual(self.C.classify_gap(
            self.cluster(page_exists=True, indexed=True, best_position=4,
                         impressions=500, ctr=0.001), "stable", set()), "GAP-D")
        self.assertEqual(self.C.classify_gap(
            self.cluster(page_exists=True, indexed=True, best_position=25,
                         commercial_demand=9000), "stable", set()), "GAP-F")
        self.assertEqual(self.C.classify_gap(self.cluster(), "growing", set()), "GAP-G")
        self.assertEqual(self.C.classify_gap(self.cluster(), "declining", set()), "GAP-H")


class TestOpportunity(unittest.TestCase):
    """Модель возможностей прозрачна и объяснима."""

    def setUp(self):
        self.O = load("opportunity")

    def gap(self, **kw):
        base = {"cluster": "x", "gap": "GAP-A", "commercial_demand": 1000,
                "commercial_phrases": 5, "page_exists": False, "indexed": False,
                "best_position": None, "ctr": None, "trend": "stable"}
        return base | kw

    def test_components_are_stored_separately(self):
        s = self.O.score(self.gap(), 1000)
        for key in ("normalized_demand", "commercial_intent", "coverage_gap",
                    "trend_factor", "confidence", "estimated_effort"):
            self.assertIn(key, s["components"])

    def test_declining_demand_is_penalised(self):
        a = self.O.score(self.gap(trend="growing"), 1000)["opportunity_score"]
        b = self.O.score(self.gap(trend="declining"), 1000)["opportunity_score"]
        self.assertGreater(a, b)

    def test_cheap_fix_ranks_above_expensive_one_at_equal_demand(self):
        cheap = self.O.score(self.gap(gap="GAP-D", page_exists=True, indexed=True,
                                      best_position=4, ctr=0.001), 1000)
        costly = self.O.score(self.gap(gap="GAP-A"), 1000)
        self.assertLess(cheap["components"]["estimated_effort"],
                        costly["components"]["estimated_effort"])

    def test_limit_is_respected(self):
        gaps = [self.gap(cluster=f"c{i}", commercial_demand=100 * i) for i in range(1, 20)]
        self.assertEqual(len(self.O.rank(gaps, 5)), 5)


class TestFullCycle(unittest.TestCase):
    """Полный цикл: задачи не теряются, зацикливания нет, срок соблюдается."""

    def setUp(self):
        self.R = load("run")
        self.B = load("budget")
        self.U = load("universe")
        self.D = load("discovery")
        self.cfg = load("config").load()
        tmp = pathlib.Path(tempfile.mkdtemp())
        self.B.LEDGER_DIR = tmp
        self.ctl = self.B.BudgetController(self.cfg, today="2026-08-20")
        self.ctl.path = tmp / "l.jsonl"
        self.ctl.entries = []
        self.uni = self.U.Universe(tmp / "u.jsonl")
        self.stats = self.D.PatternStats(tmp / "s.json")
        self.tasks = [{"method": "getTop", "phrase": f"фраза {i}", "cluster": "c",
                       "reason": "discovery"} for i in range(5)]

    def client(self, quota_hits):
        limiter = type("L", (), {"wait_for_slot": lambda self, sleep=None,
                                 max_wait_sec=3600: 1.0})()

        class Fake:
            def __init__(self):
                self.n = 0
                self.limiter = limiter
                self.stopped_by = None

            def top(self, phrase, **kw):
                self.n += 1
                if self.n <= quota_hits:
                    return {"status": "quota_exceeded", "data": None,
                            "cost_rub": 0, "source": "quota"}
                return {"status": "ok", "cost_rub": 0.02, "source": "api",
                        "data": {"results": [{"phrase": f"{phrase} купить",
                                              "count": "100"}]}}

            dynamics = regions = top

        return Fake()

    def execute(self, client, **kw):
        return self.R.run_tasks(self.tasks, client, self.uni, [], self.stats,
                                self.ctl, self.cfg, "2026-08-20",
                                sleep=lambda s: None, **kw)

    def test_tasks_survive_quota_waits(self):
        done = self.execute(self.client(3), wait_for_quota=True)
        self.assertEqual(done["calls"], len(self.tasks))
        self.assertEqual(done["quota_waits"], 3)

    def test_deadline_stops_the_cycle(self):
        import time
        done = self.execute(self.client(10 ** 6), wait_for_quota=True,
                            deadline=time.time() - 1)
        self.assertIn("срок", done["stopped"])

    def test_without_waiting_run_stops_on_quota(self):
        done = self.execute(self.client(1), wait_for_quota=False)
        self.assertEqual(done["calls"], 0)
        self.assertEqual(done["stopped"], "quota_exceeded")


class TestHomonymFilter(unittest.TestCase):
    """Бренд-омоним: имя в запросе не доказывает, что запрос про софт."""

    def setUp(self):
        self.N = load("normalize")

    def test_foreign_products_are_dropped_for_ambiguous_brand(self):
        for phrase in ("tv box купить", "xiaomi box купить", "nike zoom купить",
                       "zoom отбеливание купить"):
            seed = "box купить" if "box" in phrase else "zoom купить"
            self.assertFalse(self.N.relevant_to_seed(phrase, seed), phrase)

    def test_software_marker_keeps_the_phrase(self):
        self.assertTrue(self.N.relevant_to_seed("box подписка", "box купить"))
        self.assertTrue(self.N.relevant_to_seed("zoom тариф", "zoom купить"))

    def test_distinct_brand_needs_no_marker(self):
        self.assertTrue(self.N.relevant_to_seed("claude купить", "claude купить"))
        self.assertTrue(self.N.relevant_to_seed("adobe photoshop купить",
                                                "adobe купить"))


class TestTrendFromSeries(unittest.TestCase):
    """Тренд считается по годовому ряду, а не по крайним точкам."""

    def setUp(self):
        self.U = load("universe")

    def test_halves_are_compared_not_endpoints(self):
        """Один провальный последний месяц не делает растущий спрос падающим."""
        series = [{"month": f"2025-{m:02d}", "frequency": f} for m, f in
                  enumerate([100, 110, 105, 115, 300, 320, 310, 200], start=1)]
        t = self.U.Universe._trend_from_series(series)
        self.assertEqual(t["direction"], "growing")

    def test_flat_series_is_stable(self):
        series = [{"month": f"2025-{m:02d}", "frequency": 100} for m in range(1, 9)]
        self.assertEqual(
            self.U.Universe._trend_from_series(series)["direction"], "stable")


class TestDynamicsRequest(unittest.TestCase):
    """Динамика: сервис принимает только целые завершённые месяцы."""

    def setUp(self):
        self.C = load("client")

    def _body(self, today):
        class Budget:
            pass
        b = Budget()
        b.today = today
        c = self.C.WordstatClient.__new__(self.C.WordstatClient)
        c.cfg = {"collection": {"region_id": "225"}}
        c.budget = b
        c.call = lambda method, body, **kw: body
        return c.dynamics("adobe купить", reason="trend_monitoring")

    def test_range_starts_on_first_and_ends_on_last_day(self):
        body = self._body("2026-08-20")
        self.assertTrue(body["fromDate"].startswith("2025-08-01"))
        self.assertTrue(body["toDate"].startswith("2026-07-31"))

    def test_current_incomplete_month_is_excluded(self):
        """Текущий месяц ещё набирает частотность — в ряд его ставить нельзя."""
        body = self._body("2026-08-20")
        self.assertNotIn("2026-08-31", body["toDate"])

    def test_year_boundary_is_handled(self):
        body = self._body("2026-01-05")
        self.assertTrue(body["fromDate"].startswith("2025-01-01"))
        self.assertTrue(body["toDate"].startswith("2025-12-31"))


class TestVendorExpansion(unittest.TestCase):
    """Расширение каталога: российские исключены, оплата влияет на порядок."""

    def setUp(self):
        self.V = load("vendor_expansion")
        self.P = load("payment_check")

    def test_russian_vendors_are_excluded(self):
        russian = ["1с", "битрикс", "kaspersky", "мойофис"]
        for brand in ("1С-Битрикс", "Kaspersky", "МойОфис"):
            self.assertTrue(self.V.is_russian(brand, russian), brand)
        self.assertFalse(self.V.is_russian("Notion", russian))

    def test_catalogue_vendors_are_not_recommended_again(self):
        vendors = [{"slug": "canva", "anchor": "canva", "vendor": "Canva",
                    "url": "/vendors/canva", "category": "Дизайн"}]
        self.assertTrue(self.V.already_in_catalogue("Canva", vendors))
        self.assertFalse(self.V.already_in_catalogue("Notion", vendors))

    def test_substring_is_not_a_catalogue_match(self):
        """«rive» внутри «pipedrive» — не тот же вендор."""
        vendors = [{"slug": "rive", "anchor": "rive", "vendor": "Rive",
                    "url": "/vendors/rive", "category": "Дизайн"},
                   {"slug": "sketch", "anchor": "sketch", "vendor": "Sketch",
                    "url": "/vendors/sketch", "category": "Дизайн"}]
        self.assertFalse(self.V.already_in_catalogue("pipedrive", vendors))
        self.assertFalse(self.V.already_in_catalogue("sketchup", vendors))
        self.assertTrue(self.V.already_in_catalogue("Rive", vendors))

    def test_product_of_catalogue_vendor_is_closed_question(self):
        """AutoCAD — это Autodesk: канал закупки уже есть, проверять нечего."""
        vendors = [{"slug": "autodesk", "anchor": "autodesk", "vendor": "Autodesk",
                    "url": "/vendors/autodesk", "category": "Дизайн"}]
        self.assertTrue(self.V.already_in_catalogue(
            "autocad", vendors, {"autocad": "Autodesk"}))
        self.assertFalse(self.V.already_in_catalogue("autocad", vendors))

    def test_seo_scaffold_is_ready_to_use(self):
        seo = self.V.seo_scaffold("notion", [{"phrase": "notion купить"}])
        self.assertEqual(seo["url"], "/vendors/notion")
        self.assertIn("Notion", seo["title"])
        self.assertLessEqual(len(seo["description"]), 200)
        self.assertEqual(len(seo["faq_topics"]), 4)

    def test_effort_grows_with_product_line(self):
        one = self.V.effort_of([{"phrase": "notion купить"}])[0]
        many = self.V.effort_of([
            {"phrase": "notion купить"}, {"phrase": "notion тариф"},
            {"phrase": "notion подписка"}, {"phrase": "notion лицензия"},
            {"phrase": "notion оплата"}, {"phrase": "notion для юридических лиц"}])[0]
        self.assertLess(one, many)

    def test_payment_classifier_distinguishes_models(self):
        card = self.P.classify("visa mastercard buy now $12 per month checkout.stripe")
        sales = self.P.classify("contact sales request a quote enterprise")
        empty = self.P.classify("about us careers")
        self.assertEqual(card["verdict"], "card")
        self.assertEqual(sales["verdict"], "sales_only")
        self.assertEqual(empty["verdict"], "unknown")

    def test_unknown_payment_means_manual_check(self):
        for verdict in ("unknown", "unreachable", "not_checked"):
            action, why = self.V.PAYMENT_ACTION[verdict]
            self.assertIn("вручную", action)

    def test_card_payment_is_recommended(self):
        action, why = self.V.PAYMENT_ACTION["card"]
        self.assertIn("рекомендуем", action)

    def test_failed_payment_check_is_retried_sooner(self):
        """«Сайт не открылся» — не ответ: держать такой вердикт месяц нельзя."""
        stale = {"verdict": "unreachable", "checked_at": "2026-08-10"}
        good = {"verdict": "card", "checked_at": "2026-08-10"}
        self.assertFalse(self.P.fresh(stale, 30))
        self.assertTrue(self.P.fresh(good, 30))

    def test_explicit_url_does_not_cancel_fallbacks(self):
        """Явный адрес может устареть — проверка продолжается по запасным."""
        urls = self.P.guess_urls("linear", "https://linear.com/pricing")
        self.assertEqual(urls[0], "https://linear.com/pricing")
        self.assertIn("https://linear.app/pricing", urls)

    def test_generic_word_brands_are_marked_low_confidence(self):
        """«box купить» ловит коробки, а не софт — цифру нельзя брать на веру."""
        phrases = [{"phrase": f"box {i}"} for i in range(5)]
        level, note = self.V.demand_confidence("box", phrases)
        self.assertEqual(level, "низкая")
        self.assertIn("вручную", note)

    def test_thin_evidence_is_not_high_confidence(self):
        level, note = self.V.demand_confidence("smartsheet", [{"phrase": "a"}])
        self.assertEqual(level, "средняя")
        self.assertIsNotNone(note)

    def test_distinct_brand_with_evidence_is_high_confidence(self):
        phrases = [{"phrase": f"smartsheet {i}"} for i in range(4)]
        level, note = self.V.demand_confidence("smartsheet", phrases)
        self.assertEqual(level, "высокая")
        self.assertIsNone(note)


class TestIntegration(unittest.TestCase):
    """Сквозные свойства системы на реальных артефактах."""

    @classmethod
    def setUpClass(cls):
        cls.state_path = ROOT / "reports/seo/wordstat/intelligence-state.json"
        cls.state = (json.loads(cls.state_path.read_text(encoding="utf-8"))
                     if cls.state_path.exists() else None)

    def test_state_exists(self):
        self.assertIsNotNone(self.state, "отчёт исследования не сформирован")

    def test_coverage_levels_are_nested(self):
        lv = self.state["coverage"]["levels"]
        self.assertGreaterEqual(lv["page"], lv["indexed"])
        self.assertGreaterEqual(lv["indexed"], lv["top10"])
        self.assertGreaterEqual(lv["top10"], lv["clicks"])

    def test_executive_block_has_no_api_details(self):
        block = self.state["executive_block"]
        text = json.dumps(block, ensure_ascii=False).lower()
        for term in ("api", "getTop".lower(), "квота", "₽", "кэш", "вызов"):
            self.assertNotIn(term, text, f"технический термин «{term}» в письме")

    def test_budget_cannot_be_exceeded_by_construction(self):
        eff = self.state["efficiency"]
        self.assertLessEqual(eff["cost_month_rub"], 5500)
        self.assertGreaterEqual(eff["remaining_budget_rub"], 0)


if __name__ == "__main__":
    unittest.main()
