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
import webreport  # noqa: E402


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

    def test_bystryy_lcp_ne_daet_zheltogo_signala(self):
        # Случай 07.09.2026: карточка 939 → 1201 мс, это +28%, но обе цифры
        # отличные. Письмо ушло жёлтым — так быть не должно.
        now = measurement(pages=[page(lcp=1201)])
        was = measurement(date="2026-09-06", pages=[page(lcp=939)])
        self.assertEqual(technical.compare(now, was, self.cfg), [])

    def test_medlennyy_lcp_daet_zheltyy_signal(self):
        # Тот же относительный сдвиг, но за границей зоны «хорошо».
        now = measurement(pages=[page(lcp=3200)])
        was = measurement(date="2026-09-06", pages=[page(lcp=2400)])
        r = technical.compare(now, was, self.cfg)
        self.assertEqual(r[0]["issues"][0]["kind"], "lcp")

    def test_krohotnyy_cls_ne_daet_signala(self):
        # Прыжок 0,001 → 0,055 формально больше порога 0,05, но итог остаётся
        # в зоне «хорошо» по Core Web Vitals (граница 0,1) — это не новость.
        now = measurement(pages=[page(cls=0.055)])
        was = measurement(date="2026-09-06", pages=[page(cls=0.001)])
        self.assertEqual(technical.compare(now, was, self.cfg), [])

    def test_zametnyy_cls_daet_signal(self):
        # За границей зоны «хорошо» тот же по величине сдвиг — уже новость.
        now = measurement(pages=[page(cls=0.13)])
        was = measurement(date="2026-09-06", pages=[page(cls=0.06)])
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

    def test_neudachnaya_popytka_nazyvaet_prichinu(self):
        # Удачных замеров нет, но попытка была: «файла нет» — не та новость.
        (self.hist / "2026-09-05.json").write_text(json.dumps({
            "date": "2026-09-05", "mode": "daily", "status": "unavailable",
            "reason": "HTTP 429: Quota exceeded",
            "pages": [{"path": "/", "pageType": "homepage",
                       "strategy": "mobile", "error": "HTTP 429"}]},
            ensure_ascii=False), encoding="utf-8")
        b = technical.build("2026-09-05")
        self.assertEqual(b["reason_code"], "api_error")
        self.assertEqual(b["last_attempt"], "2026-09-05")
        self.assertIn("429", b["reason"])
        self.assertIn("не удалась", technical.email_line(b))

    def test_pri_sboe_ostayotsya_proshlyy_udachnyy_zamer(self):
        # latest.json перезаписывается только удачным замером, поэтому
        # вчерашние цифры остаются на месте с честным возрастом.
        self.write(measurement(date="2026-09-04", pages=[page(perf=93)]))
        (self.hist / "2026-09-05.json").write_text(json.dumps({
            "date": "2026-09-05", "mode": "daily", "status": "unavailable",
            "reason": "HTTP 429", "pages": []}, ensure_ascii=False),
            encoding="utf-8")
        b = technical.build("2026-09-05")
        self.assertTrue(b["available"])
        self.assertEqual(b["as_of"], "2026-09-04")
        self.assertEqual(b["age_days"], 1)

    def test_pervyy_zamer_govorit_chto_sravnivat_ne_s_chem(self):
        # Первый замер контура: строка сравнения не должна печататься
        # обрывком «сравнение с предыдущим замером нет» (05.09.2026).
        self.write(measurement(pages=[page(perf=99)]))
        b = technical.build("2026-09-05")
        self.assertIsNone(b["previous_date"])
        html = webreport._technical_section(b)
        self.assertIn("предыдущего замера для сравнения нет", html)
        self.assertNotIn("сравнение с предыдущим", html)

    def test_posledniy_polnyy_audit_schitaet_svetofor(self):
        self.write(measurement(mode="weekly", pages=[
            page(path="/a", perf=95), page(path="/b", perf=85),
            page(path="/c", perf=70)]))
        full = technical.build("2026-09-05")["last_full"]
        self.assertEqual((full["green"], full["yellow"], full["red"]), (1, 1, 1))


class TestTechnicalSectionTypography(unittest.TestCase):
    """Блок письма: текст мельче 14 px допустим только как метаданные.

    Браузерная проверка uxlint (rendered_font_sizes) берёт минимальный
    размер по всем элементам без data-meta; 05.09.2026 подпись о последней
    расширенной проверке в 13,5 px без пометки заблокировала выпуск.
    """

    def test_melkiy_tekst_tolko_s_pometkoy_metadannykh(self):
        import importlib.util
        import re
        spec = importlib.util.spec_from_file_location(
            "report_v4", pathlib.Path(__file__).resolve().parents[1] / "report_v4.py")
        r = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(r)
        html = r._technical_html({
            "available": True, "level": "green", "mobile_performance": 96,
            "pages_checked": 3, "pages": [{"page_type": "Главная", "performance": 96}],
            "lcp_ms": 2100, "cls": 0.01, "regressions": [],
            "last_full": {"date": "2026-09-05", "urls": 12, "green": 10,
                          "yellow": 2, "red": 0}})
        for m in re.finditer(r"<div([^>]*)>", html):
            attrs = m.group(1)
            size = re.search(r"font-size:([\d.]+)px", attrs)
            if size and float(size.group(1)) < 14:
                self.assertIn('data-meta="1"', attrs, attrs)


if __name__ == "__main__":
    unittest.main()
