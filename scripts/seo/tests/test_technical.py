"""Техническое состояние: пороги, регрессии и поведение без данных.

Блок PageSpeed попадает в письмо руководителя, поэтому здесь проверяется не
вёрстка, а решения: что считать деградацией, что шумом, когда объявлять
красный статус и что показывать, если PSI не ответил.
"""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import technical  # noqa: E402


def page(path="/", page_type="homepage", perf=93, lcp=2100, cls=0.02,
         strategy="mobile", **extra):
    return {"path": path, "pageType": page_type, "strategy": strategy,
            "performance": perf, "seo": 100, "accessibility": 96,
            "best_practices": 96, "lcp_ms": lcp, "cls": cls,
            "tbt_ms": 120, **extra}


def measurement(date="2026-09-05", pages=None, mode="daily"):
    return {"date": date, "mode": mode, "status": "ok",
            "pages": pages or [page()]}


class ScoreStatusTest(unittest.TestCase):
    def test_porogi_proizvoditelnosti(self):
        self.assertEqual(technical.score_status(93, 90, 80), "green")
        self.assertEqual(technical.score_status(90, 90, 80), "green")
        self.assertEqual(technical.score_status(89, 90, 80), "yellow")
        self.assertEqual(technical.score_status(80, 90, 80), "yellow")
        self.assertEqual(technical.score_status(79, 90, 80), "red")

    def test_bez_znacheniya_neizvestno(self):
        self.assertEqual(technical.score_status(None, 90, 80), "unknown")


class CompareTest(unittest.TestCase):
    def setUp(self):
        self.cfg = technical.load_config()

    def test_malenkoe_kolebanie_ne_regressiya(self):
        # Четыре очка — шум Lighthouse, а не деградация сайта.
        now = measurement(pages=[page(perf=89)])
        was = measurement(date="2026-09-04", pages=[page(perf=93)])
        self.assertEqual(technical.compare(now, was, self.cfg), [])

    def test_padenie_pyat_ochkov_preduprezhdenie(self):
        now = measurement(pages=[page(perf=88)])
        was = measurement(date="2026-09-04", pages=[page(perf=93)])
        r = technical.compare(now, was, self.cfg)
        self.assertEqual(r[0]["issues"][0]["level"], "warning")
        self.assertEqual(r[0]["issues"][0]["delta"], -5)

    def test_padenie_desyat_ochkov_kritichno(self):
        now = measurement(pages=[page(perf=84)])
        was = measurement(date="2026-09-04", pages=[page(perf=94)])
        r = technical.compare(now, was, self.cfg)
        self.assertEqual(r[0]["issues"][0]["level"], "critical")

    def test_lcp_huzhe_dvadtsati_protsentov(self):
        now = measurement(pages=[page(lcp=3000)])
        was = measurement(date="2026-09-04", pages=[page(lcp=2100)])
        r = technical.compare(now, was, self.cfg)
        self.assertEqual(r[0]["issues"][0]["kind"], "lcp")
        self.assertEqual(r[0]["issues"][0]["delta_pct"], 43)

    def test_lcp_v_predelah_shuma_molchit(self):
        now = measurement(pages=[page(lcp=2400)])
        was = measurement(date="2026-09-04", pages=[page(lcp=2100)])
        self.assertEqual(technical.compare(now, was, self.cfg), [])

    def test_cls_uhudshenie(self):
        now = measurement(pages=[page(cls=0.12)])
        was = measurement(date="2026-09-04", pages=[page(cls=0.02)])
        r = technical.compare(now, was, self.cfg)
        self.assertEqual(r[0]["issues"][0]["kind"], "cls")

    def test_desktop_v_sravnenie_ne_vhodit(self):
        # Решения принимаются по мобильной выдаче; desktop справочный.
        now = measurement(pages=[page(perf=70, strategy="desktop")])
        was = measurement(date="2026-09-04",
                          pages=[page(perf=95, strategy="desktop")])
        self.assertEqual(technical.compare(now, was, self.cfg), [])

    def test_bez_proshlogo_zamera_sravnivat_nechego(self):
        self.assertEqual(technical.compare(measurement(), None, self.cfg), [])

    def test_novaya_stranitsa_ne_daet_lozhnoy_regressii(self):
        now = measurement(pages=[page(path="/new", perf=60)])
        was = measurement(date="2026-09-04", pages=[page(path="/", perf=95)])
        self.assertEqual(technical.compare(now, was, self.cfg), [])


class CauseAndPriorityTest(unittest.TestCase):
    def test_cls_ukazyvaet_na_verstku(self):
        cause = technical.likely_cause(page(), [{"kind": "cls", "level": "warning"}])
        self.assertIn("смещения вёрстки", cause)

    def test_lcp_ukazyvaet_na_izobrazhenie(self):
        cause = technical.likely_cause(page(), [{"kind": "lcp", "level": "warning"}])
        self.assertIn("изображение", cause)

    def test_dlinnye_zadachi_javascript(self):
        cause = technical.likely_cause(
            page(tbt_ms=800), [{"kind": "performance", "level": "warning"}])
        self.assertIn("javascript", cause)

    def test_kritichnoe_daet_pervyy_prioritet(self):
        self.assertTrue(technical.priority(
            [{"kind": "performance", "level": "critical"}], 84).startswith("P1"))

    def test_nizkiy_ball_daet_pervyy_prioritet_dazhe_pri_warning(self):
        self.assertTrue(technical.priority(
            [{"kind": "lcp", "level": "warning"}], 78).startswith("P1"))

    def test_obychnoe_preduprezhdenie_vtoroy_prioritet(self):
        self.assertTrue(technical.priority(
            [{"kind": "lcp", "level": "warning"}], 92).startswith("P2"))


class EmailLineTest(unittest.TestCase):
    def test_zelyonaya_stroka_korotkaya(self):
        line = technical.email_line({"available": True, "level": "green",
                                     "mobile_performance": 93, "regressions": []})
        self.assertEqual(line, "Техника: GREEN · PSI mobile 93 · регрессий нет")
        self.assertLess(len(line), 100)

    def test_stroka_s_prosadkoy_nazyvaet_shablon(self):
        line = technical.email_line({
            "available": True, "level": "yellow", "mobile_performance": 84,
            "regressions": [{"page_type": "Карточка товара",
                             "issues": [{"kind": "performance", "level": "warning",
                                         "delta": -9}]}]})
        self.assertIn("YELLOW", line)
        self.assertIn("↓9", line)
        self.assertIn("карточка товара", line)

    def test_stroka_bez_dannyh_ne_pugaet_oshibkoy(self):
        line = technical.email_line({"available": False,
                                     "last_success": "2026-09-04"})
        self.assertIn("НЕТ ДАННЫХ", line)
        self.assertIn("2026-09-04", line)
        self.assertNotIn("ERROR", line.upper())


class BuildTest(unittest.TestCase):
    """Сборка блока на подменённом хранилище — без обращения к PSI."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.hist = root / "history"
        self.hist.mkdir()
        self._latest, self._history = technical.LATEST, technical.HISTORY
        technical.LATEST = root / "latest.json"
        technical.HISTORY = self.hist

    def tearDown(self):
        technical.LATEST, technical.HISTORY = self._latest, self._history
        self.tmp.cleanup()

    def write(self, data):
        (self.hist / f"{data['date']}.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8")
        technical.LATEST.write_text(json.dumps(data, ensure_ascii=False),
                                    encoding="utf-8")

    def test_bez_zamerov_otchyot_ne_lomaetsya(self):
        b = technical.build("2026-09-05")
        self.assertFalse(b["available"])
        self.assertEqual(b["level"], "unknown")
        # Правило достоверности: недоступный блок несёт код причины,
        # а не свободную формулировку.
        self.assertEqual(b["reason_code"], "no_file")

    def test_zelyonoe_sostoyanie(self):
        self.write(measurement(pages=[page(), page(path="/vendors/x", perf=94,
                                                   page_type="vendor")]))
        b = technical.build("2026-09-05")
        self.assertEqual(b["level"], "green")
        self.assertEqual(b["mobile_performance"], 93)
        self.assertEqual(b["pages_checked"], 2)
        self.assertEqual(b["regressions"], [])

    def test_nizkiy_ball_daet_krasnyy(self):
        self.write(measurement(pages=[page(perf=74)]))
        self.assertEqual(technical.build("2026-09-05")["level"], "red")

    def test_regressiya_popadaet_v_blok_s_prichinoy(self):
        (self.hist / "2026-09-04.json").write_text(json.dumps(
            measurement(date="2026-09-04",
                        pages=[page(path="/product/x", page_type="product",
                                    perf=94, lcp=2100)])), encoding="utf-8")
        self.write(measurement(pages=[page(path="/product/x", page_type="product",
                                           perf=84, lcp=3000)]))
        b = technical.build("2026-09-05")
        self.assertEqual(b["level"], "red")
        self.assertEqual(b["regressions"][0]["page_type"], "Карточка товара")
        self.assertTrue(b["regressions"][0]["priority"].startswith("P1"))
        self.assertIn("изображение", b["regressions"][0]["cause"])

    def test_ne_bolee_tryoh_problem(self):
        old = [page(path=f"/p{i}", perf=95) for i in range(5)]
        new = [page(path=f"/p{i}", perf=80) for i in range(5)]
        (self.hist / "2026-09-04.json").write_text(
            json.dumps(measurement(date="2026-09-04", pages=old)), encoding="utf-8")
        self.write(measurement(pages=new))
        self.assertEqual(len(technical.build("2026-09-05")["regressions"]), 3)

    def test_posledniy_polnyy_audit_schitaet_svetofor(self):
        self.write(measurement(mode="weekly", pages=[
            page(path="/a", perf=95), page(path="/b", perf=85),
            page(path="/c", perf=70)]))
        full = technical.build("2026-09-05")["last_full"]
        self.assertEqual((full["green"], full["yellow"], full["red"]), (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
