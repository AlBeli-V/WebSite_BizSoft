"""Блок «Аудитория»: разрез устройств и каналов из дневной витрины.

Проверяется то, из-за чего блок может соврать: неполное окно выдаётся за
данные, доли считаются не от того целого, отсутствующий ряд превращается в
ноль, а переход с незнакомого домена молча записывается в каталоги.
"""

import datetime as dt
import json
import pathlib
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import audience_block as audience  # noqa: E402
import collect_daily as cd  # noqa: E402

REPORT_DATE = "2026-09-14"


def _days(end: str, count: int) -> list[str]:
    last = dt.date.fromisoformat(end)
    return [(last - dt.timedelta(days=i)).isoformat() for i in range(count)]


def _store(source: str, series: dict) -> dict:
    return {"source": source, "scope": "site", "series": series,
            "updated_at": "2026-09-14T06:00:00+00:00"}


def _flat(metric_values: dict, dates: list[str]) -> dict:
    """Ряды «метрика → день → значение»: одно значение на все дни окна."""
    return {metric: {d: value for d in dates} for metric, value in metric_values.items()}


class AudienceCase(unittest.TestCase):
    """Витрина с полными рядами: 20 дней хватает на оба окна любого лага."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        dates = _days(REPORT_DATE, 25)
        search = _flat({
            "impressions": 100, "clicks": 5,
            "impressions_desktop": 30, "impressions_mobile": 60,
            "impressions_tablet": 10,
            "clicks_desktop": 2, "clicks_mobile": 3, "clicks_tablet": 0,
        }, dates)
        (self.dir / "yandex.json").write_text(
            json.dumps(_store("yandex", search)), encoding="utf-8")
        (self.dir / "gsc.json").write_text(
            json.dumps(_store("gsc", {**search, "position": {d: 12.0 for d in dates}})),
            encoding="utf-8")
        visits = {}
        for channel, per_day in (("organic", (4, 6, 1, 0)), ("ads", (2, 3, 0, 0)),
                                 ("links", (1, 1, 0, 0)), ("catalogs", (1, 0, 0, 0)),
                                 ("platforms", (0, 2, 0, 0)), ("other", (1, 1, 0, 0))):
            for device, value in zip(cd.DEVICES, per_day):
                visits[f"visits_{channel}_{device}"] = {d: value for d in dates}
        sessions = {m.replace("visits_", "sessions_"): days
                    for m, days in visits.items()}
        (self.dir / "metrika.json").write_text(
            json.dumps(_store("metrika", visits)), encoding="utf-8")
        (self.dir / "ga4.json").write_text(
            json.dumps(_store("ga4", sessions)), encoding="utf-8")
        self.block = audience.build(REPORT_DATE, self.dir)

    def tearDown(self):
        self.tmp.cleanup()

    def test_block_available_with_both_families(self):
        self.assertTrue(self.block["available"])
        self.assertTrue(self.block["impressions"]["available"])
        self.assertTrue(self.block["visits"]["available"])

    def test_impressions_total_matches_base_series(self):
        """Итог показов — тот же ряд, что у карточки видимости: 7 дней × 100."""
        row = self.block["impressions"]["rows"][0]
        self.assertEqual(row["total"], 700)
        self.assertEqual(row["devices"], {"desktop": 210, "mobile": 420, "tablet": 70})
        self.assertAlmostEqual(row["shares"]["mobile"], 0.6)
        self.assertAlmostEqual(row["coverage"], 1.0)

    def test_impressions_window_is_mature_and_paired(self):
        """Окна поиска — семь зрелых дней встык, лаг созревания три дня."""
        period = self.block["impressions"]["rows"][0]["period"]
        self.assertEqual(period["current"], {"from": "2026-09-05", "to": "2026-09-11"})
        self.assertEqual(period["previous"], {"from": "2026-08-29", "to": "2026-09-04"})

    def test_visits_channels_and_devices(self):
        blk = self.block["visits"]["blocks"][0]
        self.assertEqual(blk["label"], "Яндекс")
        self.assertEqual(blk["source_label"], "Яндекс.Метрика")
        # 11 визитов в день × 7 дней окна.
        self.assertEqual(blk["total"], 161)
        organic = next(c for c in blk["channels"] if c["key"] == "organic")
        self.assertEqual(organic["total"], 77)
        self.assertEqual(organic["devices"]["mobile"], 42)
        self.assertAlmostEqual(organic["shares"]["desktop"], 28 / 77)
        self.assertEqual([c["key"] for c in blk["channels"]], list(audience.CHANNELS))

    def test_visits_window_is_shorter_lag_than_search(self):
        period = self.block["visits"]["blocks"][0]["period"]
        self.assertEqual(period["current"], {"from": "2026-09-07", "to": "2026-09-13"})

    def test_devices_hide_empty_other_column(self):
        self.assertEqual(self.block["devices"], ["desktop", "mobile", "tablet"])

    def test_tiles_are_four_in_fixed_order(self):
        self.assertEqual([t["title"] for t in self.block["tiles"]],
                         ["Показы · Яндекс", "Показы · Google",
                          "Визиты · Яндекс.Метрика", "Визиты · GA4"])

    def test_headline_speaks_only_of_measured_numbers(self):
        line = self.block["headline"]
        self.assertIn("с телефонов 60% показов", line)
        self.assertIn("органика", line)


class AudienceGapsCase(unittest.TestCase):
    """Дыры и отсутствие рядов: блок обязан сказать «нет данных»."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_store_is_no_data_not_zero(self):
        block = audience.build(REPORT_DATE, self.dir)
        self.assertFalse(block["available"])
        row = block["impressions"]["rows"][0]
        self.assertFalse(row["available"])
        self.assertEqual(row["reason_code"], "no_file")
        self.assertNotIn("total", row)

    def test_incomplete_window_is_not_published(self):
        dates = _days(REPORT_DATE, 25)
        del dates[5]  # один день окна отсутствует
        series = _flat({"impressions": 100, "clicks": 5, "impressions_desktop": 30,
                        "impressions_mobile": 60, "impressions_tablet": 10,
                        "clicks_desktop": 2, "clicks_mobile": 3, "clicks_tablet": 0},
                       dates)
        (self.dir / "yandex.json").write_text(
            json.dumps(_store("yandex", series)), encoding="utf-8")
        block = audience.build(REPORT_DATE, self.dir)
        row = block["impressions"]["rows"][0]
        self.assertFalse(row["available"])
        self.assertEqual(row["reason_code"], "no_rows")
        self.assertIn("окно неполное", row["reason"])

    def test_device_cut_absent_while_base_series_present(self):
        """Разрез по устройствам не собран — строка показов не публикуется."""
        dates = _days(REPORT_DATE, 25)
        series = _flat({"impressions": 100, "clicks": 5}, dates)
        (self.dir / "yandex.json").write_text(
            json.dumps(_store("yandex", series)), encoding="utf-8")
        row = audience.build(REPORT_DATE, self.dir)["impressions"]["rows"][0]
        self.assertFalse(row["available"])
        self.assertEqual(row["reason_code"], "no_rows")


class ReferralClassesCase(unittest.TestCase):
    """Реестр классов внешних переходов: домен вне реестра — обычная ссылка."""

    def setUp(self):
        self.classes = cd.load_referral_classes()

    def test_registry_has_both_classes(self):
        self.assertIn("catalogs", self.classes)
        self.assertIn("platforms", self.classes)

    def test_subdomain_matches_but_lookalike_does_not(self):
        self.assertEqual(cd.classify_referral("m.vc.ru", self.classes), "platforms")
        self.assertEqual(cd.classify_referral("myvc.ru", self.classes), "links")

    def test_unknown_domain_is_plain_link(self):
        self.assertEqual(cd.classify_referral("example.com", self.classes), "links")
        self.assertEqual(cd.classify_referral("", self.classes), "links")

    def test_registry_entry_with_path(self):
        self.assertEqual(cd.classify_referral("yandex.ru/maps/org/1", self.classes),
                         "catalogs")
        self.assertEqual(cd.classify_referral("yandex.ru", self.classes), "links")


class ChannelParsersCase(unittest.TestCase):
    """Парсеры разрезов: двойного счёта нет, незнакомое не выдумывается."""

    def setUp(self):
        self.classes = {"catalogs": ("soware.ru",), "platforms": ("vc.ru",)}

    def test_metrika_skips_referral_in_plain_cut(self):
        payload = {"data": [
            {"dimensions": [{"name": "2026-09-10"}, {"id": "organic"}, {"id": "mobile"}],
             "metrics": [7]},
            {"dimensions": [{"name": "2026-09-10"}, {"id": "referral"}, {"id": "desktop"}],
             "metrics": [3]},
            {"dimensions": [{"name": "2026-09-10"}, {"id": "qr"}, {"id": "tv"}],
             "metrics": [1]},
        ]}
        series = cd.parse_metrika_channel_rows(payload, self.classes)
        self.assertEqual(series["visits_organic_mobile"]["2026-09-10"], 7)
        self.assertEqual(series["visits_links_desktop"], {})
        self.assertEqual(series["visits_other_other"]["2026-09-10"], 1)

    def test_metrika_referral_cut_classifies_domains(self):
        payload = {"data": [
            {"dimensions": [{"name": "2026-09-10"}, {"name": "soware.ru"}, {"id": "desktop"}],
             "metrics": [2]},
            {"dimensions": [{"name": "2026-09-10"}, {"name": "vc.ru"}, {"id": "mobile"}],
             "metrics": [4]},
            {"dimensions": [{"name": "2026-09-10"}, {"name": "nowhere.io"}, {"id": "desktop"}],
             "metrics": [1]},
        ]}
        series = cd.parse_metrika_channel_rows(payload, self.classes, referral=True)
        self.assertEqual(series["visits_catalogs_desktop"]["2026-09-10"], 2)
        self.assertEqual(series["visits_platforms_mobile"]["2026-09-10"], 4)
        self.assertEqual(series["visits_links_desktop"]["2026-09-10"], 1)

    def test_ga4_channel_groups_and_dates(self):
        payload = {"rows": [
            {"dimensionValues": [{"value": "20260910"}, {"value": "Organic Search"},
                                 {"value": "desktop"}],
             "metricValues": [{"value": "5"}]},
            {"dimensionValues": [{"value": "20260910"}, {"value": "Paid Search"},
                                 {"value": "mobile"}],
             "metricValues": [{"value": "2"}]},
            {"dimensionValues": [{"value": "20260910"}, {"value": "Referral"},
                                 {"value": "desktop"}],
             "metricValues": [{"value": "9"}]},
        ]}
        series = cd.parse_ga4_channel_rows(payload, self.classes)
        self.assertEqual(series["sessions_organic_desktop"]["2026-09-10"], 5)
        self.assertEqual(series["sessions_ads_mobile"]["2026-09-10"], 2)
        self.assertEqual(series["sessions_links_desktop"], {})

    def test_gsc_device_rows_fill_measured_zero(self):
        payload = {"rows": [
            {"keys": ["2026-09-10", "DESKTOP"], "impressions": 12, "clicks": 1},
            {"keys": ["2026-09-10", "MOBILE"], "impressions": 20, "clicks": 2},
        ]}
        series = cd.parse_gsc_device_rows(payload)
        self.assertEqual(series["impressions_desktop"]["2026-09-10"], 12)
        # Планшетов в ответе нет, но день в ответе есть — это измеренный ноль.
        self.assertEqual(series["impressions_tablet"]["2026-09-10"], 0)

    def test_yandex_device_history_renames_series(self):
        payload = {"indicators": {
            "TOTAL_SHOWS": [{"date": "2026-09-10T00:00:00.000+03:00", "value": 40.0}],
            "TOTAL_CLICKS": [{"date": "2026-09-10T00:00:00.000+03:00", "value": 1.0}]}}
        series = cd.parse_yandex_device_history(payload, "mobile")
        self.assertEqual(series["impressions_mobile"]["2026-09-10"], 40.0)
        self.assertEqual(series["clicks_mobile"]["2026-09-10"], 1.0)


class RenderCase(unittest.TestCase):
    """Подача блока: письмо и веб-отчёт печатают то же, что в данных."""

    @classmethod
    def setUpClass(cls):
        import report_v4  # noqa: E402 — тяжёлый импорт, один раз на класс
        import webreport  # noqa: E402
        cls.r4, cls.web = report_v4, webreport

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        dates = _days(REPORT_DATE, 25)
        search = _flat({"impressions": 100, "clicks": 5, "impressions_desktop": 30,
                        "impressions_mobile": 60, "impressions_tablet": 10,
                        "clicks_desktop": 2, "clicks_mobile": 3, "clicks_tablet": 0},
                       dates)
        (self.dir / "yandex.json").write_text(json.dumps(_store("yandex", search)),
                                              encoding="utf-8")
        (self.dir / "gsc.json").write_text(
            json.dumps(_store("gsc", {**search, "position": {d: 12.0 for d in dates}})),
            encoding="utf-8")
        visits = {}
        for channel, per_day in (("organic", (4, 6, 1, 0)), ("ads", (2, 3, 0, 0)),
                                 ("links", (1, 1, 0, 0)), ("catalogs", (1, 0, 0, 0)),
                                 ("platforms", (0, 2, 0, 0)), ("other", (1, 1, 0, 0))):
            for device, value in zip(cd.DEVICES, per_day):
                visits[f"visits_{channel}_{device}"] = {d: value for d in dates}
        (self.dir / "metrika.json").write_text(json.dumps(_store("metrika", visits)),
                                               encoding="utf-8")
        (self.dir / "ga4.json").write_text(
            json.dumps(_store("ga4", {m.replace("visits_", "sessions_"): v
                                      for m, v in visits.items()})), encoding="utf-8")
        self.block = audience.build(REPORT_DATE, self.dir)

    def tearDown(self):
        self.tmp.cleanup()

    def test_email_section_names_every_channel(self):
        html = self.r4._audience_html(self.block)
        for channel in audience.CHANNELS:
            self.assertIn(audience.CHANNEL_LABEL[channel], html)
        self.assertIn("Показы · Яндекс", html)
        self.assertIn("Визиты · GA4", html)

    def test_email_section_has_no_unresolved_placeholders(self):
        html = self.r4._audience_html(self.block)
        self.assertNotIn("None", html)
        self.assertNotIn("нет данных", html)

    def test_email_meta_font_sizes_are_marked(self):
        """Мелкий шрифт письма обязан быть помечен data-meta — правило uxlint."""
        html = self.r4._audience_html(self.block)
        sizes = [float(v) for v in re.findall(r"font-size:([\d.]+)px", html)]
        self.assertTrue(sizes)
        self.assertGreaterEqual(min(sizes), 12.5)

    def test_email_period_line_names_both_windows(self):
        line = self.r4._audience_period(self.block)
        self.assertIn("показы", line)
        self.assertIn("визиты", line)

    def test_web_section_renders_tables(self):
        html = self.web._audience_section(self.block)
        self.assertIn("Показы поиска по устройствам", html)
        self.assertIn("визиты по каналам", html)
        self.assertIn("Итого", html)

    def test_web_section_without_data_says_so(self):
        html = self.web._audience_section(audience.build(REPORT_DATE, pathlib.Path(
            tempfile.mkdtemp())))
        self.assertIn("Нет данных", html)


class HistoryWindowCase(unittest.TestCase):
    """Новый ряд дозаполняется историей, а не начинается с сегодняшнего дня."""

    def test_missing_expected_metric_asks_for_history(self):
        store = {"series": {"impressions": {"2026-09-01": 10}}}
        date_from, _ = cd.window_for(store, ("impressions", "impressions_mobile"))
        self.assertEqual(date_from, cd.HISTORY_START)

    def test_present_metrics_read_only_tail(self):
        store = {"series": {"impressions": {"2026-09-01": 10}, "impressions_mobile": {}}}
        date_from, date_to = cd.window_for(store, ("impressions", "impressions_mobile"))
        self.assertEqual((date_to - date_from).days, cd.TAIL_DAYS)


if __name__ == "__main__":
    unittest.main()
