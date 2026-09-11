#!/usr/bin/env python3
"""SERP-watch: watchlist из данных, бюджетная дисциплина, анализ архива."""

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import mocks  # noqa: E402

DATE = "2026-08-30"


def snap(yandex_entities=(), demand=None):
    return {"yandex": {"available": True, "entities": list(yandex_entities)},
            "google": {"available": False},
            "market_demand": demand or {"available": False}}


def q(text, imp=10, intent="commercial", branded=False, pos=8.0):
    return {"entity_type": "query", "entity_id": text, "impressions": imp,
            "clicks": 0, "average_position": pos, "intent": intent,
            "branded": branded, "confidence": "sufficient"}


class TestWatchlist(unittest.TestCase):
    def setUp(self):
        self.wl = mocks.load("serp_watchlist")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = pathlib.Path(self.tmp.name)
        (base / "snaps").mkdir()
        self.wl.SNAP_DIR = base / "snaps"
        inv = mocks.load("inventory")
        inv.DATA_DIR = base / "data"
        (base / "data").mkdir()
        self.wl.inventory = inv
        self.base = base

    def write_snap(self, s, date=DATE):
        (self.wl.SNAP_DIR / f"{date}.json").write_text(
            json.dumps(s, ensure_ascii=False), encoding="utf-8")

    def test_sources_priority_and_dedup(self):
        self.write_snap(snap(
            yandex_entities=[q("купить figma", imp=50),
                             q("figma цена", imp=20),
                             q("что такое figma", intent="informational"),
                             q("bizsoft купить", branded=True)],
            demand={"available": True,
                    "top_commercial": [{"phrase": "купить figma"},
                                       {"phrase": "canva подписка"}],
                    "gaps": {"c": [{"phrase": "оплатить miro"}]}}))
        (self.base / "data" / f"sitemap-{DATE}.json").write_text(json.dumps(
            {"date": DATE, "urls": [{"path": "/alternatives/notion",
                                     "lastmod": None}]}), encoding="utf-8")
        out = self.wl.build(DATE)
        self.assertEqual(out[0], "купить figma")        # Вебмастер, топ показов
        self.assertEqual(out.count("купить figma"), 1)  # дедуп со спросом
        self.assertIn("canva подписка", out)
        self.assertIn("оплатить miro", out)
        self.assertIn("notion аналоги", out)
        self.assertNotIn("что такое figma", out)
        self.assertNotIn("bizsoft купить", out)

    def test_cap(self):
        self.write_snap(snap(
            yandex_entities=[q(f"купить продукт {i}") for i in range(200)]))
        self.assertEqual(len(self.wl.build(DATE, cap=150)), 150)

    def test_переставленные_формы_вебмастера_схлопываются(self):
        """Вебмастер отдаёт часть запросов в переставленном виде.

        Срез 09.09.2026 нёс 431 запрос, из них 33 — вторая форма того же
        смысла («оплата capture one юридическим лицом» и «capture оплата one
        лицом юридическим»). Выдачу по ним собирали дважды, а счёт «мы в
        топ-10 по N запросам» выходил завышенным.
        """
        self.write_snap(snap(yandex_entities=[
            q("оплата capture one юридическим лицом", imp=90),
            q("capture оплата one лицом юридическим", imp=40),
            q("купить claude team", imp=30),
            q("claude team купить", imp=20),
            q("купить claude enterprise", imp=10),
        ]))
        out = self.wl.build(DATE)
        self.assertEqual(out, ["оплата capture one юридическим лицом",
                               "купить claude team",
                               "купить claude enterprise"])

    def test_разные_запросы_схлопыванием_не_склеиваются(self):
        self.write_snap(snap(yandex_entities=[
            q("оплата box для юридических лиц из россии", imp=90),
            q("оплата box юридическим лицом", imp=40),
        ]))
        self.assertEqual(len(self.wl.build(DATE)), 2)

    def test_empty_without_data(self):
        self.assertEqual(self.wl.build(DATE), [])


class TestBudgetDiscipline(unittest.TestCase):
    def setUp(self):
        self.sw = mocks.load("serp_watch")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = pathlib.Path(self.tmp.name)
        self.sw.SERP_DIR = base / "serp"
        self.sw.LEDGER_DIR = base / "serp" / "ledger"

    def test_month_spent_counts_ledger_lines(self):
        import datetime as dt
        d = dt.date.fromisoformat(DATE)
        self.sw.LEDGER_DIR.mkdir(parents=True)
        self.sw.ledger_path(d).write_text(
            "\n".join('{"query": "x"}' for _ in range(7)) + "\n",
            encoding="utf-8")
        self.assertEqual(self.sw.month_spent(d), 7)

    def test_cap_exhausted_refuses(self):
        import datetime as dt
        d = dt.date.fromisoformat(DATE)
        self.sw.LEDGER_DIR.mkdir(parents=True)
        self.sw.ledger_path(d).write_text(
            "\n".join('{"q":1}' for _ in range(self.sw.MONTHLY_CAP)) + "\n",
            encoding="utf-8")
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {"WORDSTAT_API_KEY": "k"}):
            res = self.sw.run(DATE, [{"query": "купить figma",
                                      "region": "213"}])
        self.assertIn("потолок", res["error"])

    def test_daily_cap_holds_the_day_not_the_run(self):
        """Повторный прогон в тот же день не удваивает расход."""
        import datetime as dt
        import os
        from unittest import mock
        d = dt.date.fromisoformat(DATE)
        self.sw.LEDGER_DIR.mkdir(parents=True)
        self.sw.ledger_path(d).write_text(
            "\n".join(json.dumps({"at": f"{DATE}T01:40:00Z", "query": "x"})
                      for _ in range(self.sw.DAILY_CAP)) + "\n",
            encoding="utf-8")
        with mock.patch.dict(os.environ, {"WORDSTAT_API_KEY": "k"}):
            res = self.sw.run(DATE, ["купить figma"])
        self.assertIn("дневной потолок", res["error"])
        self.assertEqual(res["spent_today"], self.sw.DAILY_CAP)

    def test_daily_cap_trims_queue(self):
        import os
        from unittest import mock

        seen = []

        def fake_collect(session, key, date, tasks, writer):
            for t in tasks:
                seen.append(t["query"])
                self.sw.log_call(date, t["query"], "submitted", None,
                                 t["region"])
                writer({"date": DATE, "query": t["query"], "top": []})
            return len(tasks), 0

        with mock.patch.dict(os.environ, {"WORDSTAT_API_KEY": "k"}), \
                mock.patch.object(self.sw, "collect_deferred", fake_collect):
            res = self.sw.run(DATE, [{"query": f"q{i}", "region": "213"}
                                     for i in range(self.sw.DAILY_CAP + 30)])
        self.assertEqual(res["requested"], self.sw.DAILY_CAP)
        self.assertEqual(res["skipped_over_budget"], 30)
        self.assertEqual(res["mode"], "deferred-night")
        self.assertEqual(len(seen), self.sw.DAILY_CAP)
        # каждый вызов записан в журнал
        import datetime as dt
        self.assertEqual(self.sw.month_spent(dt.date.fromisoformat(DATE)),
                         self.sw.DAILY_CAP)


class TestDeferredFlow(unittest.TestCase):
    """Отложенный режим: отправка пакетом, добор опросом, честный дедлайн."""

    def setUp(self):
        self.sw = mocks.load("serp_watch")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = pathlib.Path(self.tmp.name)
        self.sw.SERP_DIR = base / "serp"
        self.sw.LEDGER_DIR = base / "serp" / "ledger"
        self.sw.SERP_DIR.mkdir(parents=True)
        self.rows = []
        import datetime as dt
        self.date = dt.date.fromisoformat(DATE)

    def collect(self, submit, fetch, timeout=None):
        import contextlib
        from unittest import mock
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(self.sw, "submit_deferred", submit))
            stack.enter_context(
                mock.patch.object(self.sw, "fetch_operation", fetch))
            stack.enter_context(
                mock.patch.object(self.sw.time, "sleep", lambda s: None))
            if timeout is not None:
                stack.enter_context(
                    mock.patch.object(self.sw, "POLL_TIMEOUT_S", timeout))
            return self.sw.collect_deferred(
                None, "k", self.date,
                [{"query": "купить figma", "region": "213"},
                 {"query": "купить miro", "region": "2"}],
                self.rows.append)

    def test_happy_path(self):
        polls = {"n": 0}

        def fetch(session, key, op):
            polls["n"] += 1
            if polls["n"] < 2:
                return None          # первая проверка — ещё выполняется
            return {"found": 10, "top": []}

        ok, failed = self.collect(
            lambda s, k, q, r: {"op": f"op-{q}-{r}"}, fetch)
        self.assertEqual((ok, failed), (2, 0))
        self.assertEqual(len(self.rows), 2)
        self.assertEqual({r["region"] for r in self.rows}, {"213", "2"})
        self.assertEqual(self.sw.month_spent(self.date), 2)

    def test_submit_error_is_logged_and_written(self):
        ok, failed = self.collect(
            lambda s, k, q, r: {"error": "HTTP 403: нет прав"},
            lambda s, k, op: None)
        self.assertEqual((ok, failed), (0, 2))
        self.assertIn("HTTP 403", self.rows[0]["error"])
        self.assertEqual(self.sw.month_spent(self.date), 2)  # submit платный

    def test_poll_network_error_does_not_finalize(self):
        """Сетевой сбой опроса — не вердикт: запрос остаётся pending до
        дедлайна (урок ночи 31.08: неверный хост похоронил весь срез)."""
        def broken_fetch(session, key, op):
            raise ConnectionError("нет маршрута")

        ok, failed = self.collect(
            lambda s, k, q, r: {"op": f"op-{q}"}, broken_fetch, timeout=0)
        self.assertEqual((ok, failed), (0, 2))
        # финализировано дедлайном (pending-файл есть), а не сетевой ошибкой
        self.assertTrue(all("не готов к дедлайну" in r["error"]
                            for r in self.rows))
        self.assertTrue((self.sw.SERP_DIR / f"pending-{DATE}.json").exists())

    def test_deadline_saves_pending_operations(self):
        ok, failed = self.collect(
            lambda s, k, q, r: {"op": f"op-{q}-{r}"},
            lambda s, k, op: None, timeout=0)
        self.assertEqual((ok, failed), (0, 2))
        self.assertTrue(all("не готов к дедлайну" in r["error"]
                            for r in self.rows))
        pending = json.loads(
            (self.sw.SERP_DIR / f"pending-{DATE}.json").read_text(
                encoding="utf-8"))
        self.assertEqual(len(pending), 2)
        self.assertEqual({p["region"] for p in pending}, {"213", "2"})

    def test_build_tasks_full_msk_plus_spb_top(self):
        core = [f"q{i}" for i in range(self.sw.SPB_TOP + 50)]
        tasks = self.sw.build_tasks(core)
        msk = [t for t in tasks if t["region"] == self.sw.REGION_MSK]
        spb = [t for t in tasks if t["region"] == self.sw.REGION_SPB]
        self.assertEqual(len(msk), len(core))
        self.assertEqual(len(spb), self.sw.SPB_TOP)
        # СПб — в хвосте: усечение бюджетом режет дубль-регион, не ядро
        self.assertTrue(all(t["region"] == self.sw.REGION_MSK
                            for t in tasks[:len(core)]))


class TestSerpAnalysis(unittest.TestCase):
    def setUp(self):
        self.sa = mocks.load("serp_analysis")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sa.SERP_DIR = pathlib.Path(self.tmp.name)

    def write_day(self, date, rows):
        p = self.sa.SERP_DIR / f"{date}-serp.jsonl"
        p.write_text("\n".join(json.dumps(r, ensure_ascii=False)
                               for r in rows) + "\n", encoding="utf-8")

    @staticmethod
    def doc(domain):
        return {"domain": domain, "url": f"https://{domain}/x", "title": domain}

    def test_positions_weakness_and_competitors(self):
        top_weak = [self.doc(d) for d in
                    ("avito.ru", "wildberries.ru", "ozon.ru", "plati.market",
                     "kupikod.com", "pikabu.ru", "dzen.ru", "ggsel.net",
                     "market.yandex.ru", "otzovik.com")]
        top_strong = ([self.doc("syssoft.ru"), self.doc("biz-soft.pro"),
                       self.doc("softline.ru")]
                      + [self.doc(f"site{i}.ru") for i in range(7)])
        self.write_day(DATE, [
            {"query": "купить heygen", "top": top_weak},
            {"query": "купить figma", "top": top_strong},
            {"query": "сбой", "error": "HTTP 500"},
        ])
        res = self.sa.build(DATE)
        self.assertTrue(res["available"])
        self.assertEqual(res["queries_total"], 2)      # ошибка не считается
        by_q = {i["query"]: i for i in res["items"]}
        self.assertEqual(by_q["купить figma"]["our_position"], 2)
        self.assertTrue(by_q["купить heygen"]["weak"])
        self.assertFalse(by_q["купить figma"]["weak"])
        self.assertEqual(res["ours_in_top10"], 1)
        doms = {d["domain"]: d for d in res["top_domains"]}
        self.assertEqual(doms["syssoft.ru"]["kind"], "competitor")
        self.assertEqual(self.sa.classify_domain("platipomiru.com"),
                         "intermediary")
        self.assertEqual(self.sa.classify_domain("www.raketapay.ru"),
                         "intermediary")
        self.assertNotIn("biz-soft.pro", doms)          # свои не «конкурент»
        # запрос без нас первым в сортировке не стоит: сортируем по нашей позиции
        self.assertEqual(res["items"][0]["query"], "купить figma")

    def test_diff_with_previous_snapshot(self):
        self.write_day("2026-08-29", [
            {"query": "купить figma",
             "top": [self.doc("syssoft.ru"), self.doc("old.ru")]}])
        self.write_day(DATE, [
            {"query": "купить figma",
             "top": [self.doc("syssoft.ru"), self.doc("new.ru")]}])
        res = self.sa.build(DATE)
        item = res["items"][0]
        self.assertEqual(item["entered_top10"], ["new.ru"])
        self.assertEqual(item["left_top10"], ["old.ru"])
        self.assertEqual(res["prev_date"], "2026-08-29")

    def test_empty_serp_is_a_measurement_not_an_error(self):
        """Успешный замер с пустой выдачей остаётся в срезе (аудит 03.09.2026)."""
        self.write_day(DATE, [{"query": "редкий запрос", "found": 0, "top": []},
                              {"query": "сбой", "error": "HTTP 500"}])
        loaded = self.sa._load(DATE)
        self.assertIsNotNone(loaded)
        self.assertEqual([r["query"] for r in loaded["rows"]], ["редкий запрос"])

    def test_no_archive_is_honest(self):
        res = self.sa.build(DATE)
        self.assertFalse(res["available"])
        self.assertIn("срезов за окно нет", res["reason"])


class TestModuleResolution(unittest.TestCase):
    """Одноимённые модули seo/ и seo/wordstat/ не должны подменять друг друга.

    Скрипты, которым нужны оба каталога, кладут их в sys.path вручную, и
    порядок вставок решает, чей opportunity.py импортируется: у своего есть
    money_radar, у wordstat — нет. Ошибка порядка тихая: внутри общего
    прогона тестов модуль уже загружен кем-то другим и подмена не видна,
    поэтому проверка идёт отдельным процессом, как в бою.
    """

    SEO = pathlib.Path(__file__).resolve().parents[1]

    def resolve(self, module: str, names: tuple[str, ...]) -> dict:
        code = (
            "import importlib, json, sys\n"
            f"sys.path.insert(0, {str(self.SEO)!r})\n"
            f"importlib.import_module({module!r})\n"
            "print(json.dumps({n: getattr(sys.modules.get(n), '__file__', None)"
            f" for n in {list(names)!r}}}))\n"
        )
        res = subprocess.run([sys.executable, "-c", code], cwd=self.SEO.parents[1],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)

    def test_serp_watchlist_takes_its_own_opportunity(self):
        got = self.resolve("serp_watchlist",
                           ("opportunity", "normalize", "inventory"))
        self.assertEqual(got["opportunity"], str(self.SEO / "opportunity.py"))
        self.assertEqual(got["normalize"], str(self.SEO / "wordstat" / "normalize.py"))
        self.assertEqual(got["inventory"], str(self.SEO / "inventory.py"))

    def test_watchlist_builds_in_a_clean_process(self):
        """Сбор ядра в чистом процессе: падение импорта роняло весь SERP-срез."""
        code = (
            "import sys, pathlib\n"
            f"sys.path.insert(0, {str(self.SEO)!r})\n"
            "import serp_watchlist\n"
            "serp_watchlist.build('2026-01-01')\n"
        )
        res = subprocess.run([sys.executable, "-c", code], cwd=self.SEO.parents[1],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)


if __name__ == "__main__":
    unittest.main()
