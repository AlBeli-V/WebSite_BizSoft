"""Перезапуск SEO-EXP-002 (03.09.2026): per-page маркеры, фиксированные окна,
активация по факту выката и выгрузка окон.

Разбор показал три дефекта прежней методики: маркеры кластера приписывали
vendor-странице показы карточек товаров, baseline брался из усечённой
выгрузки (топ-100), а окно после внедрения не росло. Здесь закрепляется,
что новый слой делает ровно то, ради чего заведён.
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
import experiment_windows as ew  # noqa: E402
import experiments  # noqa: E402


def q(text, shows, clicks, pos):
    return {"query_id": text, "query_text": text,
            "indicators": {"TOTAL_SHOWS": float(shows),
                           "TOTAL_CLICKS": float(clicks),
                           "AVG_SHOW_POSITION": float(pos),
                           "AVG_CLICK_POSITION": None}}


EXP = {
    "id": "snippets-2-price-intent", "ticket": "SEO-EXP-002-R",
    "start": "2026-09-05", "status": "running",
    "pages": ["/vendors/clip-studio-paint", "/vendors/procreate"],
    "page_markers": {
        "/vendors/clip-studio-paint": ["clip studio", "клип студио"],
        "/vendors/procreate": ["procreate", "прокриэйт"],
    },
    "query_exclude": ["скачать", "взлом"],
    "query_intent_any": ["купить", "цена", "сколько стоит", "подписк", "лицензи"],
    "windows": {"days": 28,
                "baseline": {"from": "2026-08-05", "to": "2026-09-01"},
                "experiment": {"from": "2026-09-06", "to": "2026-10-03"}},
}


class PageMarkersTest(unittest.TestCase):
    def test_общие_ключи_объединяют_маркеры_страниц(self):
        keys = experiments.cluster_keys(EXP)
        self.assertEqual(keys["any"], ["clip studio", "procreate", "клип студио", "прокриэйт"])
        self.assertTrue(experiments.query_matches("procreate цена", keys))
        self.assertFalse(experiments.query_matches("procreate скачать", keys))
        # Без интент-маркера запрос чужой: «clip studio paint кисти» — не покупка.
        self.assertFalse(experiments.query_matches("clip studio paint кисти", keys))

    def test_ключи_страницы_видят_только_свои_запросы(self):
        pk = experiments.page_keys(EXP)
        self.assertEqual(set(pk), set(EXP["pages"]))
        clip, pro = pk["/vendors/clip-studio-paint"], pk["/vendors/procreate"]
        self.assertTrue(experiments.query_matches("клип студио купить лицензию", clip))
        self.assertFalse(experiments.query_matches("клип студио купить лицензию", pro))
        self.assertTrue(experiments.query_matches("прокриэйт цена", pro))
        # Исключения и интент общие с экспериментом.
        self.assertFalse(experiments.query_matches("procreate взлом купить", pro))

    def test_без_page_markers_разбивки_нет(self):
        self.assertEqual(experiments.page_keys({"pages": ["/vendors/canva"]}), {})

    def test_экспозиция_страниц_в_блоке_письма(self):
        snap = {"yandex": {"entities": [
            {"entity_type": "query", "entity_id": "procreate цена",
             "impressions": 5, "clicks": 0},
            {"entity_type": "query", "entity_id": "клип студио купить",
             "impressions": 7, "clicks": 1},
        ]}}
        tmp = pathlib.Path(tempfile.mkdtemp())
        old = experiments.REGISTRY
        experiments.REGISTRY = tmp / "reg.json"
        experiments.REGISTRY.write_text(json.dumps({"experiments": [EXP]}), encoding="utf-8")
        try:
            out = experiments.build(snap, "2026-09-10")
        finally:
            experiments.REGISTRY = old
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(len(out), 1)
        per = {p["page"]: p for p in out[0]["per_page"]}
        self.assertEqual(per["/vendors/procreate"]["impressions"], 5)
        self.assertEqual(per["/vendors/clip-studio-paint"]["clicks"], 1)
        self.assertEqual(out[0]["impressions_since_deploy"], 12)


class FixedWindowsTest(unittest.TestCase):
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

    def window(self, w, queries):
        st.window_path(w["from"], w["to"]).write_text(json.dumps({
            "date": "2026-10-06", "window_kind": "fixed", "window": w,
            "popular_queries": {"date_from": w["from"], "date_to": w["to"],
                                "count": len(queries), "fetched": len(queries),
                                "queries": queries}}, ensure_ascii=False),
            encoding="utf-8")

    def test_план_окон_равной_длины_с_лагом_источника(self):
        w = st.plan_windows(dt.date(2026, 9, 5))
        self.assertEqual(w["days"], 28)
        self.assertEqual(w["baseline"], {"from": "2026-08-05", "to": "2026-09-01"})
        self.assertEqual(w["experiment"], {"from": "2026-09-06", "to": "2026-10-03"})
        self.assertFalse(st.window_ready(w["experiment"], dt.date(2026, 10, 5)))
        self.assertTrue(st.window_ready(w["experiment"], dt.date(2026, 10, 6)))

    def test_фиксированные_файлы_имеют_приоритет_над_скользящими(self):
        # Скользящая усечённая выгрузка до старта и грязная после.
        self.day("2026-09-03", "2026-08-20", "2026-08-31", [q("procreate цена", 3, 0, 9)])
        self.day("2026-09-20", "2026-09-05", "2026-09-17", [q("procreate цена", 20, 0, 9)])
        self.window(EXP["windows"]["baseline"], [q("procreate цена", 40, 0, 9)] * 1)
        win = st.pick_windows(dt.date(2026, 9, 5), dt.date(2026, 9, 20), EXP)
        self.assertTrue(win["fixed"]["baseline"])
        self.assertFalse(win["fixed"]["experiment"])
        self.assertEqual(win["baseline"]["from"], "2026-08-05")
        self.assertTrue(win["experiment_tainted"])
        self.assertEqual(win["fixed_experiment_eta"], "2026-10-06")
        # Появилось полное окно после внедрения — оно чистое по построению.
        self.window(EXP["windows"]["experiment"], [q("procreate цена", 45, 2, 9)])
        win = st.pick_windows(dt.date(2026, 9, 5), dt.date(2026, 10, 6), EXP)
        self.assertTrue(win["fixed"]["experiment"])
        self.assertFalse(win["experiment_tainted"])
        self.assertEqual(win["experiment"]["to"], "2026-10-03")

    def test_без_реестра_окон_прежний_выбор(self):
        self.day("2026-09-03", "2026-08-20", "2026-08-31", [q("a", 3, 0, 9)])
        win = st.pick_windows(dt.date(2026, 9, 5), dt.date(2026, 9, 20))
        self.assertEqual(win["fixed"], {"baseline": False, "experiment": False})
        self.assertIsNone(win["planned"])

    def test_оценка_считает_страницы_отдельно_и_не_ругает_усечение(self):
        clip = [q(f"клип студио купить {i}", 20, 0, 8) for i in range(5)]
        pro = [q(f"procreate цена {i}", 4, 0, 10) for i in range(5)]
        self.window(EXP["windows"]["baseline"], clip + pro)
        clip2 = [q(f"клип студио купить {i}", 22, 1, 8) for i in range(5)]
        pro2 = [q(f"procreate цена {i}", 4, 0, 10) for i in range(5)]
        self.window(EXP["windows"]["experiment"], clip2 + pro2)
        r = ver.evaluate(EXP, "2026-10-06")
        self.assertTrue(r["windows"]["baseline"]["fixed"])
        self.assertTrue(r["windows"]["experiment"]["fixed"])
        self.assertFalse(any("усечённой" in s for s in r["sample_quality"]))
        per = {p["page"]: p for p in r["per_page"]}
        self.assertEqual(per["/vendors/clip-studio-paint"]["baseline"]["impressions"], 100)
        self.assertEqual(per["/vendors/clip-studio-paint"]["experiment"]["clicks"], 5)
        self.assertEqual(per["/vendors/procreate"]["experiment"]["impressions"], 20)
        self.assertEqual(per["/vendors/procreate"]["matched_queries"], 5)

    def test_предварительное_сравнение_помечает_фиксированный_baseline(self):
        self.window(EXP["windows"]["baseline"], [q("procreate цена", 40, 0, 9)])
        self.day("2026-09-20", "2026-09-05", "2026-09-17", [q("procreate цена", 20, 1, 9)])
        keys = experiments.cluster_keys(EXP)
        interim = st.interim_comparison(keys, dt.date(2026, 9, 5), dt.date(2026, 9, 20), EXP)
        self.assertEqual(interim["baseline"]["impressions"], 40)
        self.assertTrue(any("фиксированное" in c for c in interim["caveats"]))
        self.assertFalse(any("усечённой" in c for c in interim["caveats"]))


class ActivateTest(unittest.TestCase):
    def planned(self):
        e = {k: v for k, v in EXP.items() if k not in ("start", "windows")}
        e.update({"status": "planned", "start": None,
                  "title_marker": r"(цена|сколько стоит)"})
        return {"experiments": [e]}

    def test_активация_когда_все_страницы_отдают_новый_вариант(self):
        titles = {"https://x/vendors/clip-studio-paint": "Clip Studio Paint: цена | BIZSoft",
                  "https://x/vendors/procreate": "Procreate: цена в рублях | BIZSoft"}
        reg = self.planned()
        done = ew.activate(reg, dt.date(2026, 9, 5), "https://x", titles.get)
        self.assertEqual(len(done), 1)
        e = reg["experiments"][0]
        self.assertEqual(e["status"], "running")
        self.assertEqual(e["start"], "2026-09-05")
        self.assertEqual(e["windows"]["baseline"], {"from": "2026-08-05", "to": "2026-09-01"})
        self.assertEqual(e["windows"]["experiment"], {"from": "2026-09-06", "to": "2026-10-03"})
        self.assertEqual(len(e["activated"]["pages"]), 2)

    def test_одна_страница_со_старым_заголовком_держит_planned(self):
        titles = {"https://x/vendors/clip-studio-paint": "Clip Studio Paint: цена | BIZSoft",
                  "https://x/vendors/procreate": "Procreate для компании | BIZSoft"}
        reg = self.planned()
        self.assertEqual(ew.activate(reg, dt.date(2026, 9, 5), "https://x", titles.get), [])
        self.assertEqual(reg["experiments"][0]["status"], "planned")
        self.assertIsNone(reg["experiments"][0]["start"])

    def test_недоступная_страница_не_считается_выкаченной(self):
        reg = self.planned()
        self.assertEqual(ew.activate(reg, dt.date(2026, 9, 5), "https://x",
                                     lambda url: None), [])
        self.assertEqual(reg["experiments"][0]["status"], "planned")

    def test_running_эксперименты_не_трогаются(self):
        reg = {"experiments": [dict(EXP)]}
        ew.activate(reg, dt.date(2026, 9, 5), "https://x", lambda url: "цена")
        self.assertEqual(reg["experiments"][0]["start"], "2026-09-05")
        self.assertEqual(reg["experiments"][0]["windows"], EXP["windows"])

    def test_реестр_сохраняется_в_том_же_формате(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            p = tmp / "reg.json"
            ew.save_registry(self.planned(), p)
            self.assertEqual(ew.load_registry(p)["experiments"][0]["status"], "planned")
            self.assertTrue(p.read_text(encoding="utf-8").endswith("}\n"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class BackfillTest(unittest.TestCase):
    """Фиксированный baseline идущим экспериментам (решение 04.09.2026)."""

    def test_ставится_только_baseline_окна_после_нет(self):
        e = {k: v for k, v in EXP.items() if k != "windows"}
        reg = {"experiments": [e]}
        done = ew.backfill(reg, dt.date(2026, 9, 4))
        self.assertEqual(len(done), 1)
        w = reg["experiments"][0]["windows"]
        # 28 дней, заканчивающихся за лаг источника до старта 05.09.
        self.assertEqual(w["baseline"], {"from": "2026-08-05", "to": "2026-09-01"})
        self.assertIsNone(w["experiment"])
        self.assertEqual(reg["experiments"][0]["windows_backfilled"], "2026-09-04")

    def test_эксперимент_с_окнами_не_переписывается(self):
        reg = {"experiments": [dict(EXP)]}
        self.assertEqual(ew.backfill(reg, dt.date(2026, 9, 4)), [])
        self.assertEqual(reg["experiments"][0]["windows"], EXP["windows"])

    def test_planned_без_даты_старта_пропускается(self):
        e = {k: v for k, v in EXP.items() if k != "windows"}
        e.update({"status": "planned", "start": None})
        reg = {"experiments": [e]}
        self.assertEqual(ew.backfill(reg, dt.date(2026, 9, 4)), [])
        self.assertNotIn("windows", reg["experiments"][0])

    def test_после_backfill_окно_ставится_в_очередь_выгрузки(self):
        e = {k: v for k, v in EXP.items() if k != "windows"}
        reg = {"experiments": [e]}
        ew.backfill(reg, dt.date(2026, 9, 4))
        due = ew.windows_due(reg, dt.date(2026, 9, 4))
        self.assertEqual([(r, w["from"]) for _, r, w in due],
                         [("baseline", "2026-08-05")])


class RegistryRuleTest(unittest.TestCase):
    """Правило порога экспозиции для новых экспериментов (решение 04.09.2026)."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.old_dir, st.DATA_DIR = st.DATA_DIR, self.tmp
        self.addCleanup(setattr, st, "DATA_DIR", self.old_dir)
        self.old_reg, experiments.REGISTRY = experiments.REGISTRY, self.tmp / "reg.json"
        self.addCleanup(setattr, experiments, "REGISTRY", self.old_reg)
        (self.tmp / "yandex-2026-09-04.json").write_text(json.dumps({
            "date": "2026-09-04",
            "popular_queries": {"date_from": "2026-08-22", "date_to": "2026-09-02",
                                "queries": [q("клип студио купить", 120, 0, 8),
                                            q("procreate цена", 20, 0, 10)]}},
            ensure_ascii=False), encoding="utf-8")

    def reg(self, *experiments_):
        experiments.REGISTRY.write_text(
            json.dumps({"experiments": list(experiments_)}, ensure_ascii=False),
            encoding="utf-8")

    def planned(self, page, markers, **kw):
        e = {"id": f"exp-{page}", "ticket": "SEO-EXP-X", "status": "planned",
             "start": None, "pages": [page], "page_markers": {page: markers},
             "query_intent_any": ["купить", "цена"]}
        e.update(kw)
        return e

    def test_кластер_с_экспозицией_проходит(self):
        self.reg(self.planned("/vendors/clip-studio-paint", ["клип студио"]))
        self.assertEqual(experiments.registry_issues("2026-09-04"), [])

    def test_кластер_без_экспозиции_отклоняется(self):
        self.reg(self.planned("/vendors/procreate", ["procreate"]))
        issues = experiments.registry_issues("2026-09-04")
        self.assertEqual(len(issues), 1)
        self.assertIn("20 показов", issues[0])
        self.assertIn("/день", issues[0])

    def test_порог_нормирован_на_длину_окна(self):
        # Кластер Recraft 04.09: 180 показов за 28 дней августа (всплеск от
        # внешней публикации) и 4 показа за последние 12 дней. Абсолютный
        # порог сравнивал бы несравнимые окна — правило считает показы в день.
        self.assertAlmostEqual(experiments.MIN_EXPOSURE_PER_DAY_FOR_NEW_EXPERIMENT,
                               100 / 28, places=4)
        (self.tmp / "yandex-2026-09-04.json").write_text(json.dumps({
            "date": "2026-09-04",
            "popular_queries": {"date_from": "2026-08-03", "date_to": "2026-08-30",
                                "queries": [q("клип студио купить", 120, 0, 8)]}},
            ensure_ascii=False), encoding="utf-8")
        # 120 показов за 28 дней — это 4,3/день, порог пройден; те же 120 за
        # 12-дневное окно дали бы 10/день, вывод тот же, но без нормировки
        # порог «100 за окно» отклонил бы кластер на длинном окне.
        self.reg(self.planned("/vendors/clip-studio-paint", ["клип студио"]))
        self.assertEqual(experiments.registry_issues("2026-09-04"), [])

    def test_идущие_до_правила_не_проверяются(self):
        # Шесть записей, заведённых до 04.09, имеют экспозицию ниже порога —
        # решения по ним уже приняты, правило их не пересматривает.
        old = self.planned("/vendors/procreate", ["procreate"],
                           status="running", start="2026-08-20")
        self.reg(old)
        self.assertEqual(experiments.registry_issues("2026-09-04"), [])

    def test_running_заведённый_после_правила_проверяется(self):
        new = self.planned("/vendors/procreate", ["procreate"],
                           status="running", start="2026-09-05")
        self.reg(new)
        self.assertEqual(len(experiments.registry_issues("2026-09-04")), 1)

    def test_закрытые_и_черновые_статусы_не_проверяются(self):
        self.reg(self.planned("/vendors/procreate", ["procreate"], status="closed"))
        self.assertEqual(experiments.registry_issues("2026-09-04"), [])

    def test_без_выгрузки_вебмастера_правило_молчит(self):
        (self.tmp / "yandex-2026-09-04.json").unlink()
        self.reg(self.planned("/vendors/procreate", ["procreate"]))
        self.assertEqual(experiments.registry_issues("2026-09-04"), [])


class FetchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.old_dir = st.DATA_DIR
        st.DATA_DIR = self.tmp

    def tearDown(self):
        st.DATA_DIR = self.old_dir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_выгружается_только_устоявшееся_и_отсутствующее_окно(self):
        reg = {"experiments": [dict(EXP)]}
        due = ew.windows_due(reg, dt.date(2026, 9, 10))
        self.assertEqual([(r, w["from"]) for _, r, w in due], [("baseline", "2026-08-05")])
        calls = []

        def fetcher(d_from, d_to):
            calls.append((d_from.isoformat(), d_to.isoformat()))
            return {"count": 1, "fetched": 1, "queries": [q("procreate цена", 3, 0, 9)]}

        written = ew.fetch(reg, dt.date(2026, 9, 10), fetcher)
        self.assertEqual(calls, [("2026-08-05", "2026-09-01")])
        self.assertEqual(written, [st.window_path("2026-08-05", "2026-09-01")])
        loaded = st.load_window("2026-08-05", "2026-09-01")
        self.assertTrue(loaded["fixed"])
        self.assertEqual(loaded["queries"][0]["query_text"], "procreate цена")
        # Повторный прогон: окно уже есть, второе ещё не устоялось — тишина.
        self.assertEqual(ew.fetch(reg, dt.date(2026, 9, 10), fetcher), [])
        self.assertEqual(len(calls), 1)
        # Пришёл срок второго окна.
        self.assertEqual([r for _, r, _ in ew.windows_due(reg, dt.date(2026, 10, 6))],
                         ["experiment"])

    def test_сбой_источника_не_оставляет_пустого_файла(self):
        reg = {"experiments": [dict(EXP)]}
        written = ew.fetch(reg, dt.date(2026, 9, 10),
                           lambda a, b: {"error": "HTTP 500", "queries": []})
        self.assertEqual(written, [])
        self.assertFalse(st.window_path("2026-08-05", "2026-09-01").exists())

    def test_planned_и_closed_окон_не_требуют(self):
        e1 = dict(EXP, status="planned")
        e2 = dict(EXP, status="closed")
        self.assertEqual(ew.windows_due({"experiments": [e1, e2]}, dt.date(2026, 12, 1)), [])


if __name__ == "__main__":
    unittest.main()
