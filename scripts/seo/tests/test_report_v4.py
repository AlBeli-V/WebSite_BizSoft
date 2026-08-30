#!/usr/bin/env python3
"""Тесты письма V4: методика измерений, аналитика, объём и правила подачи."""

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "seo"))
DATE = "2026-08-19"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / "seo" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestMeasurementMap(unittest.TestCase):
    """DATA-001: разные сущности вместо ложного единого определения визита."""

    @classmethod
    def setUpClass(cls):
        cls.m = load("measurement")
        cls.snap = json.loads((ROOT / f"reports/seo/intelligence/snapshots/{DATE}.json")
                              .read_text(encoding="utf-8"))
        cls.dq = json.loads((ROOT / f"reports/seo/intelligence/data-quality/{DATE}.json")
                            .read_text(encoding="utf-8"))

    def test_five_entities_are_distinct(self):
        metrics = [r["metric"] for r in self.m.build_map(self.snap)]
        for expected in ("impressions", "clicks", "visits", "sessions", "leads"):
            self.assertIn(expected, metrics)

    def test_clicks_not_comparable_with_visits(self):
        rows = {(r["source"], r["metric"]): r for r in self.m.build_map(self.snap)}
        clicks = rows[("Яндекс.Вебмастер", "clicks")]
        self.assertNotIn("Яндекс.Метрика · visits", clicks["comparable_with"])
        self.assertIn("Яндекс.Вебмастер · impressions", clicks["comparable_with"])

    def test_visits_and_sessions_are_comparable(self):
        rows = {(r["source"], r["metric"]): r for r in self.m.build_map(self.snap)}
        self.assertIn("GA4 · sessions", rows[("Яндекс.Метрика", "visits")]["comparable_with"])

    def test_sample_ctr_is_marked_as_sample(self):
        ctr = self.m.sample_ctr(self.snap)
        self.assertAlmostEqual(ctr["value"], 6 / 926, places=6)
        self.assertIn("выборка", ctr["caveat"])
        self.assertIn("не CTR всего сайта", ctr["caveat"])

    def test_scope_mismatch_is_limited_not_degraded(self):
        self.assertEqual(self.dq["data_health"]["status"], "limited")
        self.assertEqual(self.dq["data_health"]["colour"], "warning")
        self.assertEqual(self.dq["counts"]["critical"], 0)

    def test_broken_source_is_degraded(self):
        broken = dict(self.snap, google={"available": False})
        self.assertEqual(self.m.data_health(broken, [])["status"], "degraded")

    def test_matching_scopes_are_verified(self):
        fixed = json.loads(json.dumps(self.snap))
        fixed["yandex"]["totals"]["scope_note"] = "весь сайт"
        self.assertEqual(self.m.data_health(fixed, [])["status"], "verified")

    def test_no_reconciliation_wording_left(self):
        text = json.dumps(self.dq, ensure_ascii=False).lower()
        self.assertNotIn("кратн", text)
        self.assertNotIn("единое определение визита", text)


class TestDrivers(unittest.TestCase):
    """Причина изменения либо подтверждена сущностями, либо не называется."""

    @classmethod
    def setUpClass(cls):
        cls.d = load("drivers")
        cls.snap = json.loads((ROOT / f"reports/seo/intelligence/snapshots/{DATE}.json")
                              .read_text(encoding="utf-8"))
        cls.prev = load("snapshot").prev_snapshot(DATE)

    def test_pages_are_named(self):
        res = self.d.build(self.snap, self.prev)
        google = next(b for b in res["blocks"] if b["engine"] == "google")
        self.assertTrue(google["pages"]["available"])
        self.assertTrue(any(p["entity"].startswith("/vendors/")
                            for p in google["pages"]["all"]))

    def test_no_previous_means_cause_unknown(self):
        res = self.d.build(self.snap, None)
        self.assertFalse(res["available"])
        self.assertIn("не определена", res["reason"])

    def test_shares_are_bounded(self):
        res = self.d.build(self.snap, self.prev)
        for b in res["blocks"]:
            for part in ("pages", "queries"):
                for row in b[part].get("all", []):
                    self.assertGreaterEqual(row["share_of_total_delta"], 0)
                    self.assertLessEqual(row["share_of_total_delta"], 1)

    def test_new_and_lost_states(self):
        res = self.d.build(self.snap, self.prev)
        states = {row["state"] for b in res["blocks"] for p in ("pages", "queries")
                  for row in b[p].get("all", [])}
        self.assertTrue(states <= {"new", "lost", "changed"})


class TestOpportunity(unittest.TestCase):
    """Радар: наши показы не выдаются за рыночный спрос."""

    @classmethod
    def setUpClass(cls):
        cls.o = load("opportunity")
        cls.snap = json.loads((ROOT / f"reports/seo/intelligence/snapshots/{DATE}.json")
                              .read_text(encoding="utf-8"))

    def test_limited_to_three(self):
        self.assertLessEqual(len(self.o.build(self.snap, "2026-08-26")["items"]), 3)

    def test_our_impressions_are_labelled_as_ours(self):
        for item in self.o.build(self.snap, "2026-08-26")["items"]:
            if item["evidence_kind"] == "our_impressions":
                self.assertIn("показов по запросу", item["evidence"])
                self.assertNotIn("рыночный спрос", item["evidence"])

    def test_market_demand_only_with_measurement(self):
        self.assertEqual(self.o.from_market_demand({"market_demand": {"available": False}}), [])

    def test_score_prefers_low_effort(self):
        cheap = self.o.band_for(5.0)
        costly = self.o.band_for(30.0)
        self.assertLess(cheap["effort"], costly["effort"])
        self.assertGreater(cheap["impact"], costly["impact"])


class TestExperimentControl(unittest.TestCase):
    """Экспозиция и вердикт; выкат не выдаётся за переобход поиском."""

    @classmethod
    def setUpClass(cls):
        cls.e = load("experiments")
        cls.snap = json.loads((ROOT / f"reports/seo/intelligence/snapshots/{DATE}.json")
                              .read_text(encoding="utf-8"))
        cls.rows = cls.e.build(cls.snap, DATE,
                               {"snippets-5-vendors": {"pages_recrawled": 5,
                                                       "new_snippets_detected": 5}})

    def test_deployment_is_not_search_refresh(self):
        e = self.rows[0]
        self.assertEqual(e["pages_live_with_treatment"], 5)
        self.assertEqual(e["search_snippet_refresh"], "не подтверждено")
        self.assertIn("Вебмастера", e["search_snippet_refresh_note"])

    def test_verdict_is_too_early_without_exposure(self):
        self.assertEqual(self.rows[0]["verdict"], "too_early")

    def test_combined_treatment_not_split(self):
        self.assertTrue(self.rows[0]["combined_treatment"])
        self.assertIn("не разделяются", self.rows[0]["combined_note"])

    def test_tickets_are_distinct_per_experiment(self):
        """Три эксперимента под одним номером в письме неразличимы."""
        tickets = [r["ticket"] for r in self.rows]
        self.assertEqual(len(tickets), len(set(tickets)))
        self.assertTrue(all(t for t in tickets))

    def test_verdict_needs_minimum_days(self):
        v, _ = self.e.verdict_for(days=3, impressions=9000, live=5, total=5)
        self.assertEqual(v, "too_early")

    def test_verdict_observes_when_exposure_reached(self):
        v, _ = self.e.verdict_for(days=9, impressions=9000, live=5, total=5)
        self.assertEqual(v, "observing")


class TestMeasurementLimits(unittest.TestCase):
    """Реестр пределов измерения: активный предупреждает, объявленный молчит."""

    @classmethod
    def setUpClass(cls):
        cls.q = load("quality")

    def _findings(self, limits, start="2026-08-07", end="2026-08-21"):
        """Тот же разбор записей, что в run_checks, но без снимка целиком."""
        out = []
        for lim in limits:
            resolved = lim.get("resolved_on")
            if lim.get("status") == "planned" and not resolved:
                continue
            if not resolved:
                out.append(("MEASUREMENT_GAP", lim["id"]))
            elif start <= resolved <= end:
                out.append(("MEASUREMENT_CHANGE", lim["id"]))
        return out

    def test_registry_is_readable(self):
        limits = self.q.load_measurement_limits()
        self.assertTrue(limits)
        for lim in limits:
            for field in ("id", "title", "detail", "evidence", "rule"):
                self.assertTrue(lim.get(field), f"{lim.get('id')}: пусто поле {field}")

    def test_anl_001_state_matches_its_consequences(self):
        """Состояние записи о целях и её последствия обязаны совпадать.

        Прежняя версия теста требовала, чтобы запись оставалась открытой:
        на момент написания цели не были заведены. Такой тест живёт ровно до
        дня починки, а потом падает именно тогда, когда всё стало хорошо, —
        и его посылку приходится вспоминать заново. Проверяем не состояние,
        а то, что состояние и его следствия не разъехались.

        Открыта — обязана давать MEASUREMENT_GAP и нести инструкцию на день
        закрытия. Закрыта — обязана нести дату границы в правиле, иначе
        сравнение конверсий через неё никто не запретит.
        """
        anl = next(l for l in self.q.load_measurement_limits() if l["id"] == "ANL-001")
        if anl["resolved_on"] is None:
            self.assertIn(("MEASUREMENT_GAP", "ANL-001"), self._findings([anl]))
            self.assertTrue(anl.get("on_resolve"))
        else:
            # Правило пишется для человека и потому датируется по-русски,
            # а поле — в ISO. Годится любая из двух записей одной даты.
            y, m, d = anl["resolved_on"].split("-")
            self.assertTrue(
                anl["resolved_on"] in anl["rule"] or f"{d}.{m}.{y}" in anl["rule"],
                "закрытая запись обязана называть дату границы в правиле")
            self.assertRegex(anl["evidence"], r"\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4}",
                             "закрытие обязано опираться на датированное доказательство")

    def test_open_limits_carry_closing_instructions(self):
        """Что делать в день закрытия — рядом с записью, а не в памяти сессии."""
        for lim in self.q.load_measurement_limits():
            if lim.get("resolved_on"):
                continue
            self.assertTrue(lim.get("on_resolve"),
                            f"{lim['id']}: нет инструкции на день закрытия")

    def test_planned_limit_is_silent(self):
        planned = {"id": "X", "status": "planned", "resolved_on": None}
        self.assertEqual(self._findings([planned]), [])

    def test_planned_limit_speaks_once_dated(self):
        happened = {"id": "X", "status": "planned", "resolved_on": "2026-08-10"}
        self.assertEqual(self._findings([happened]), [("MEASUREMENT_CHANGE", "X")])

    def test_resolved_outside_window_is_not_a_finding(self):
        old = {"id": "X", "resolved_on": "2026-07-01"}
        self.assertEqual(self._findings([old]), [])


class TestExpansionGuard(unittest.TestCase):
    """Уже заведённого вендора нельзя предлагать завести."""

    @classmethod
    def setUpClass(cls):
        cls.r = load("report_v4")

    def test_catalogue_vendors_are_dropped(self):
        # состояние исследования отстало от каталога — так ушло письмо 21.08.
        # Пример «вендора не с сайта» — basecamp: прежний пример wordpress
        # заведён в каталог 29.08.2026 и стал вычёркиваться по назначению.
        stale = {"available": True, "expansion": {
            "items": [{"brand": "suno"}, {"brand": "cloudflare"}, {"brand": "basecamp"}],
            "manual_check": ["capcut", "principle", "nordvpn", "leonardo ai"]}}
        out = self.r._drop_vendors_already_on_site(stale)
        brands = [i["brand"] for i in out["expansion"]["items"]]
        self.assertEqual(brands, ["basecamp"])
        self.assertEqual(out["expansion"]["manual_check"], ["nordvpn"])

    def test_fresh_catalogue_vendors_are_dropped_too(self):
        # Партия 29.08.2026: wordpress и slack заведены — guard обязан
        # вычёркивать их из рекомендаций к заведению.
        stale = {"available": True, "expansion": {
            "items": [{"brand": "wordpress"}, {"brand": "slack"}],
            "manual_check": []}}
        out = self.r._drop_vendors_already_on_site(stale)
        self.assertEqual(out["expansion"]["items"], [])

    def test_untouched_when_nothing_to_drop(self):
        block = {"available": True, "expansion": {
            "items": [{"brand": "basecamp"}], "manual_check": ["nordvpn"]}}
        self.assertIs(self.r._drop_vendors_already_on_site(block), block)

    def test_says_so_when_all_candidates_are_covered(self):
        block = {"available": True, "expansion": {
            "items": [{"brand": "suno"}], "manual_check": ["capcut"]}}
        out = self.r._drop_vendors_already_on_site(block)
        self.assertEqual(out["expansion"]["items"], [])
        self.assertIn("уже заведены", out["expansion"]["summary"])

    def test_partial_word_does_not_match(self):
        """«box» на сайте не должен вычёркивать «dropbox-подобные» бренды целиком."""
        words = self.r._site_vendor_words()
        self.assertIn("box", words)
        block = {"available": True, "expansion": {
            "items": [{"brand": "boxcryptor"}], "manual_check": []}}
        out = self.r._drop_vendors_already_on_site(block)
        self.assertEqual([i["brand"] for i in out["expansion"]["items"]], ["boxcryptor"])


class TestEmailV4(unittest.TestCase):
    """Письмо: объём, первый экран, структура и правила подачи."""

    @classmethod
    def setUpClass(cls):
        cls.r = load("report_v4")
        base = ROOT / "reports/seo/intelligence"
        cls.preview = (base / f"{DATE}-v4.html").read_text(encoding="utf-8")
        cls.text = (base / f"{DATE}-v4.txt").read_text(encoding="utf-8")
        cls.blocks = json.loads((base / f"{DATE}-v4-blocks.json").read_text(encoding="utf-8"))
        cls.lint = json.loads((base / f"{DATE}-v4-uxlint.json").read_text(encoding="utf-8"))

    def test_visible_words_in_range(self):
        n = self.r.visible_words(self.preview)
        self.assertGreaterEqual(n, 800)
        self.assertLessEqual(n, 1000)

    def test_first_screen_is_short(self):
        self.assertLessEqual(self.r.first_screen_words(self.preview), 250)

    def test_three_status_pills(self):
        states = {p["label"]: p["state"] for p in self.blocks["pills"]}
        self.assertEqual(states["ПОИСК"], "mixed")
        self.assertEqual(states["ДАННЫЕ"], "limited")
        self.assertEqual(states["ОТ ВАС"], "none")

    def test_four_kpi_and_muted_crm(self):
        self.assertEqual(len(self.blocks["kpis"]), 4)
        commercial = self.blocks["kpis"][-1]
        self.assertTrue(commercial["muted"])
        self.assertNotEqual(commercial["value"], "нет данных")

    def test_top10_decline_is_not_called_stable(self):
        neg = [s for s in self.blocks["signals"] if s["tone"] == "negative"]
        self.assertTrue(neg)
        self.assertIn("умеренное снижение", neg[0]["meaning"])
        self.assertNotIn("позиции держатся на прежнем уровне", self.preview)

    def test_no_unsupported_google_claim(self):
        self.assertNotIn("стал чаще показывать наши карточки", self.preview)

    def test_lint_passes(self):
        self.assertTrue(self.lint["passed"], self.lint["checks"])

    def test_plain_text_has_all_sections(self):
        for section in ("ПОКАЗАТЕЛИ", "СИГНАЛЫ ДНЯ", "ЧТО ДАЛО ИЗМЕНЕНИЕ",
                        "КОНТРОЛЬ ЭКСПЕРИМЕНТА", "СИСТЕМА УЖЕ ДЕЛАЕТ",
                        "ГДЕ БЛИЖЕ ВСЕГО РОСТ", "ЗДОРОВЬЕ ДАННЫХ", "СЛЕДУЮЩИЕ ПРОВЕРКИ"):
            self.assertIn(section, self.text)

    def test_cards_only_where_allowed(self):
        """Карточки — только показатели, эксперимент, решение и блокирующий риск."""
        self.assertLessEqual(self.preview.count("border-radius:12px"), 8)

    def test_web_report_exists(self):
        self.assertTrue((ROOT / f"reports/seo/public/daily/{DATE}/index.html").exists())


if __name__ == "__main__":
    unittest.main()
