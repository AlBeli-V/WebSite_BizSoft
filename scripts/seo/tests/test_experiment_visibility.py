"""Видимость эксперимента: сниппет в выдаче и «старый → новый» до вердикта.

Разбор руководителя 31.08.2026: письмо писало «нет данных», хотя ответы
лежали в собственных данных (site-check, SERP-замеры, выгрузки Вебмастера).
Тесты закрепляют: SERP-замер сопоставляется со страницами эксперимента,
предварительное сравнение считается до чистого окна и честно оговаривается,
свежая проверка сайта подхватывается и за вчера.
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
import report_v4  # noqa: E402
import serp_snippets  # noqa: E402

TODAY = dt.date(2026, 8, 31)
LIVE = "Оплата Canva для юридических лиц из России — счёт, договор, ЭДО | BIZSoft"


class TitlesMatchTest(unittest.TestCase):
    def test_усечённый_заголовок_выдачи_совпадает_с_живым(self):
        self.assertTrue(serp_snippets.titles_match(
            "Оплата Canva для юридических лиц из России — счёт... | BIZSoft", LIVE))

    def test_старый_заголовок_не_совпадает(self):
        self.assertFalse(serp_snippets.titles_match(
            "Купить Canva для юрлица — тарифы, счёт и КП — BIZSoft", LIVE))

    def test_слишком_короткий_префикс_не_считается_совпадением(self):
        self.assertFalse(serp_snippets.titles_match("Оплата Canva...", LIVE))


class SerpStatusTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.old = serp_snippets.SERP_DIR
        serp_snippets.SERP_DIR = self.tmp

    def tearDown(self):
        serp_snippets.SERP_DIR = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, date, rows):
        p = self.tmp / f"{date}-serp.jsonl"
        p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows),
                     encoding="utf-8")

    def test_страница_найдена_и_сниппет_распознан_как_новый(self):
        self._write("2026-08-30", [{
            "date": "2026-08-30", "query": "оплата canva",
            "top": [
                {"domain": "other.ru", "url": "https://other.ru/x", "title": "x"},
                {"domain": "biz-soft.pro",
                 "url": "https://biz-soft.pro/vendors/canva",
                 "title": "Оплата Canva для юридических лиц из России — счёт..."},
            ]}])
        s = serp_snippets.serp_status(["/vendors/canva"],
                                      {"/vendors/canva": LIVE}, TODAY)
        self.assertEqual(s["measured_at"], "2026-08-30")
        self.assertEqual(s["pages_seen"], 1)
        self.assertEqual(s["pages_with_new_snippet"], 1)
        self.assertEqual(s["pages"]["/vendors/canva"]["best_position"], 2)

    def test_файл_из_одних_ошибок_пропускается_в_пользу_старшего(self):
        self._write("2026-08-31", [{"date": "2026-08-31", "query": "q",
                                    "error": "ConnectionError"}])
        self._write("2026-08-30", [{
            "date": "2026-08-30", "query": "оплата canva",
            "top": [{"domain": "biz-soft.pro",
                     "url": "https://biz-soft.pro/vendors/canva",
                     "title": LIVE}]}])
        s = serp_snippets.serp_status(["/vendors/canva"],
                                      {"/vendors/canva": LIVE}, TODAY)
        self.assertEqual(s["measured_at"], "2026-08-30")

    def test_замер_старше_недели_не_используется(self):
        self._write("2026-08-20", [{
            "date": "2026-08-20", "query": "оплата canva",
            "top": [{"domain": "biz-soft.pro",
                     "url": "https://biz-soft.pro/vendors/canva",
                     "title": LIVE}]}])
        self.assertIsNone(serp_snippets.serp_status(
            ["/vendors/canva"], {"/vendors/canva": LIVE}, TODAY))

    def test_без_живого_заголовка_новизна_не_утверждается(self):
        self._write("2026-08-30", [{
            "date": "2026-08-30", "query": "оплата canva",
            "top": [{"domain": "biz-soft.pro",
                     "url": "https://biz-soft.pro/vendors/canva",
                     "title": LIVE}]}])
        s = serp_snippets.serp_status(["/vendors/canva"], {}, TODAY)
        self.assertEqual(s["pages_seen"], 1)
        self.assertIsNone(s["pages_with_new_snippet"])


def _dump(dirpath, file_date, w_from, w_to, queries):
    (dirpath / f"yandex-{file_date}.json").write_text(json.dumps({
        "popular_queries": {"date_from": w_from, "date_to": w_to,
                            "queries": queries}}, ensure_ascii=False),
        encoding="utf-8")


def _q(text, shows, clicks, pos=5.0):
    return {"query_text": text,
            "indicators": {"TOTAL_SHOWS": shows, "TOTAL_CLICKS": clicks,
                           "AVG_SHOW_POSITION": pos}}


class InterimComparisonTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.old = experiment_stats.DATA_DIR
        experiment_stats.DATA_DIR = self.tmp

    def tearDown(self):
        experiment_stats.DATA_DIR = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_сравнение_считается_до_чистого_окна_с_оговорками(self):
        start = dt.date(2026, 8, 19)
        _dump(self.tmp, "2026-08-18", "2026-08-05", "2026-08-18",
              [_q("canva оплата", 100, 1)])
        # Текущее окно пересекает период до внедрения: 17.08 < старта.
        _dump(self.tmp, "2026-08-31", "2026-08-17", "2026-08-29",
              [_q("canva оплата", 200, 4)])
        i = experiment_stats.interim_comparison(["canva"], start, TODAY)
        self.assertTrue(i["preliminary"])
        self.assertEqual(i["baseline"]["impressions"], 100)
        self.assertEqual(i["current"]["impressions"], 200)
        self.assertAlmostEqual(i["relative_uplift"], 1.0)
        self.assertEqual(i["current"]["post_days"], 10)
        self.assertEqual(i["current"]["window_days"], 13)
        joined = " ".join(i["caveats"])
        self.assertIn("пересекает период до внедрения", joined)
        self.assertIn("усечённой выгрузки", joined)

    def test_без_базового_окна_сравнения_нет(self):
        _dump(self.tmp, "2026-08-31", "2026-08-20", "2026-08-29",
              [_q("canva оплата", 200, 4)])
        self.assertIsNone(experiment_stats.interim_comparison(
            ["canva"], dt.date(2026, 8, 19), TODAY))


class SiteCheckFallbackTest(unittest.TestCase):
    """Гонка пушей 31.08 стёрла сегодняшний site-check — письмо берёт свежайший."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.old = report_v4.BASE
        report_v4.BASE = self.tmp

    def tearDown(self):
        report_v4.BASE = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, date):
        (self.tmp / f"site-check-{date}.json").write_text(json.dumps(
            {"experiments": {"x": {"pages_recrawled": 5}}}), encoding="utf-8")

    def test_сегодняшний_файл_в_приоритете(self):
        self._write("2026-08-30")
        self._write("2026-08-31")
        sc = report_v4.load_site_check("2026-08-31")
        self.assertEqual(sc["date"], "2026-08-31")

    def test_вчерашний_подхватывается_с_честной_датой(self):
        self._write("2026-08-30")
        sc = report_v4.load_site_check("2026-08-31")
        self.assertEqual(sc["date"], "2026-08-30")
        self.assertEqual(sc["experiments"]["x"]["pages_recrawled"], 5)

    def test_старше_трёх_дней_не_подхватывается(self):
        self._write("2026-08-27")
        self.assertIsNone(report_v4.load_site_check("2026-08-31"))


if __name__ == "__main__":
    unittest.main()
