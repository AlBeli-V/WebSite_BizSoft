"""Google RU в снимке, KPI и письме: доля из среза xmlriver, разрыв с Яндексом,
NO DATA без свежего среза, дельта только между срезами разных дат."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from decision_engine import kpi as kpi_mod  # noqa: E402
from discovery import google_ru, run_discovery, serp_source  # noqa: E402
from mailer import build_email, sections  # noqa: E402
from reports import deep_report  # noqa: E402
from scoring import visibility  # noqa: E402

DATE = "2026-09-09"
G_DATE = "2026-09-07"


def top(*domains):
    return [{"domain": d, "url": f"https://{d}/x", "title": d} for d in domains]


def yrow(query, *domains, region="213"):
    return serp_source.SerpRow(date=DATE, query=query, region=region, top=top(*domains))


def grow(query, *domains, error=None):
    return serp_source.SerpRow(date=G_DATE, query=query, region="2643",
                               engine="google", top=top(*domains) if not error else [],
                               error=error)


class TestBlock(unittest.TestCase):
    def setUp(self):
        self.config = visibility.load_config()
        self.yandex = [
            yrow("купить figma", "biz-soft.pro", "softline.ru"),
            yrow("zoom для юрлиц", "raketapay.ru", "biz-soft.pro"),
            yrow("наоборот", "a.ru", "b.ru"),
            yrow("zoom для юрлиц", "biz-soft.pro", region="2"),
        ]
        self.google = [
            grow("Купить Figma", "softline.ru", "allsoft.ru", "syssoft.ru"),
            grow("zoom для юрлиц", "raketapay.ru", "pipl.io", "biz-soft.pro"),
            grow("наоборот", "biz-soft.pro", "a.ru"),
            grow("сбой", error="HTTP 500"),
        ]

    def test_недоступен_без_среза(self):
        block = google_ru.build_block(DATE, None, [], self.yandex, self.config)
        self.assertFalse(block["доступен"])
        self.assertIn("еженедельный", block["причина"])
        self.assertIsNone(google_ru.share(block))

    def test_блок_из_среза(self):
        block = google_ru.build_block(DATE, G_DATE, self.google, self.yandex,
                                      self.config)
        self.assertTrue(block["доступен"])
        self.assertEqual((block["провайдер"], block["серия"], block["регион"]),
                         ("xmlriver", "google_ru", "2643"))
        self.assertEqual(block["дата_среза"], G_DATE)
        self.assertEqual(block["возраст_дней"], 2)
        self.assertEqual(block["покрытие"]["запросов_с_данными"], 3)
        self.assertEqual(block["покрытие"]["ошибок"], 1)
        ours = block["наши_показатели"]
        self.assertGreater(ours["доля_видимости"], 0)
        self.assertLess(ours["доля_видимости"], 1)
        self.assertEqual((ours["топ3"], ours["топ10"], ours["топ20"]), (2, 2, 2))
        self.assertEqual(ours["запросов_в_поле"], 3)
        self.assertIn("купить figma", block["по_запросам"])
        self.assertIsNone(block["по_запросам"]["купить figma"]["позиция"])
        self.assertEqual(block["по_запросам"]["наоборот"]["позиция"], 1)

    def test_разрыв_с_яндексом_по_присутствию(self):
        block = google_ru.build_block(DATE, G_DATE, self.google, self.yandex,
                                      self.config)
        gap = block["разрыв_с_яндексом"]
        self.assertEqual(gap["сопоставлено"], 3)
        self.assertEqual(gap["в_обеих_топ10"], 1)
        ya = gap["яндекс_топ10_google_вне_топ20"]
        self.assertEqual([i["запрос"] for i in ya], ["купить figma"])
        self.assertEqual(ya[0]["позиция_яндекс"], 1)
        self.assertEqual(ya[0]["google_топ3"], ["softline.ru", "allsoft.ru", "syssoft.ru"])
        g = gap["google_топ10_яндекс_вне_топ20"]
        self.assertEqual([i["запрос"] for i in g], ["наоборот"])
        self.assertEqual(gap["яндекс_топ10_google_вне_топ20_всего"], 1)

    def test_наш_домен_отсутствует_везде_это_измеренный_ноль(self):
        rows = [grow("q", "a.ru", "b.ru")]
        block = google_ru.build_block(DATE, G_DATE, rows, [], self.config)
        self.assertEqual(block["наши_показатели"]["доля_видимости"], 0.0)
        self.assertEqual(google_ru.share(block), 0.0)

    def test_блок_в_снимке_и_kpi(self):
        from discovery import registry
        block = google_ru.build_block(DATE, G_DATE, self.google, self.yandex,
                                      self.config)
        cards = registry.build(self.yandex, self.config, date=DATE)
        snap = run_discovery.build_snapshot(DATE, cards, self.yandex, self.config,
                                            query_sets_path=os.devnull, google=block)
        self.assertTrue(snap["состояние_зрелости"]["google_собирается"])
        self.assertEqual(snap["покрытие"]["google"],
                         block["наши_показатели"]["доля_видимости"])
        self.assertIn(G_DATE, snap["покрытие"]["_google_пояснение"])
        kpi = kpi_mod.build_kpi(snap)
        self.assertEqual(kpi.share_google, block["наши_показатели"]["доля_видимости"])
        self.assertEqual(kpi.google_date, G_DATE)
        self.assertEqual(kpi.google_top10, 2)
        state, note = kpi_mod.coverage_state(snap)
        self.assertEqual(state, "ок")
        self.assertIn(G_DATE, note)

    def test_снимок_без_блока_остаётся_no_data(self):
        from discovery import registry
        cards = registry.build(self.yandex, self.config, date=DATE)
        snap = run_discovery.build_snapshot(DATE, cards, self.yandex, self.config,
                                            query_sets_path=os.devnull)
        self.assertFalse(snap["состояние_зрелости"]["google_собирается"])
        self.assertIsNone(snap["покрытие"]["google"])
        self.assertIsNone(kpi_mod.build_kpi(snap).share_google)
        state, note = kpi_mod.coverage_state(snap)
        self.assertEqual(state, "ок")
        self.assertIn("Google", note)


def snapshot_with_google(g_date, per_query, share, previous_yandex=None):
    return {
        "дата": DATE, "зрелость_скоринга": "базовый",
        "ядро_запросов": {"хеш": "h", "версия": "v1", "запросов": 2},
        "по_запросам": {"a": {"наша": 0.1, "поле": 1.0}},
        "покрытие": {"яндекс_запросов_всего": 2, "яндекс_запросов_с_данными": 2,
                     "яндекс_ошибок": 0, "google": share},
        "наши_показатели": {"доля_видимости": 0.1, "топ3": 1, "топ10": 1,
                            "запросов_в_поле": 2, "взвешенная_видимость": 0.1},
        "доли_по_категориям": {"H": 0.5}, "лидеры": [],
        "конкурентов_в_основном_рейтинге": 0, "не_классифицировано": 0,
        "google": {
            "доступен": True, "провайдер": "xmlriver", "серия": "google_ru",
            "название": "Россия", "регион": "2643", "дата_среза": g_date,
            "возраст_дней": 1,
            "покрытие": {"запросов_всего": 2, "запросов_с_данными": 2, "ошибок": 0},
            "наши_показатели": {"доля_видимости": share, "топ3": 1, "топ10": 1,
                                "топ20": 2, "запросов_в_поле": 2,
                                "взвешенная_видимость": 0.2},
            "по_запросам": per_query,
            "доли_по_категориям": {},
            "лидеры": [{"домен": "softline.ru", "категория": "A", "доля": 0.3,
                        "топ3": 1, "топ10": 2}],
            "конкурентов_в_основном_рейтинге": 1,
            "разрыв_с_яндексом": {"сопоставлено": 2, "в_обеих_топ10": 1,
                                  "яндекс_топ10_google_вне_топ20": [
                                      {"запрос": "купить figma", "позиция_яндекс": 2,
                                       "google_топ3": ["softline.ru"]}],
                                  "яндекс_топ10_google_вне_топ20_всего": 1,
                                  "google_топ10_яндекс_вне_топ20": [],
                                  "google_топ10_яндекс_вне_топ20_всего": 0},
            "точки_атаки": {"всего": 1, "первые": [
                {"запрос": "zoom", "наша_позиция": 5, "соперник": "softline.ru",
                 "позиция_соперника": 2, "вид": "сделка", "opportunity": 40}]},
        },
    }


class TestKpiDelta(unittest.TestCase):
    def test_дельта_только_между_срезами_разных_дат(self):
        today = snapshot_with_google("2026-09-07", {"a": {"наша": 0.2, "поле": 1.0}}, 0.2)
        same = snapshot_with_google("2026-09-07", {"a": {"наша": 0.1, "поле": 1.0}}, 0.1)
        older = snapshot_with_google("2026-08-31", {"a": {"наша": 0.1, "поле": 1.0}}, 0.1)
        self.assertIsNone(kpi_mod.build_kpi(today, same).google_delta_pp)
        kpi = kpi_mod.build_kpi(today, older)
        self.assertEqual(kpi.google_delta_pp, 10.0)
        self.assertEqual(kpi.google_compared_with, "2026-08-31")


class TestEmailAndReport(unittest.TestCase):
    def test_письмо_показывает_долю_google_и_дату_среза(self):
        snap = snapshot_with_google("2026-09-07", {"a": {"наша": 0.2, "поле": 1.0}}, 0.2)
        kpi = kpi_mod.build_kpi(snap)
        meta = build_email.build(DATE, snap, None)
        self.assertIn("Google 20,0%", meta["текст"])
        self.assertEqual(meta["kpi"]["google_date"], "2026-09-07")
        txt = build_email.render_txt(meta, snapshot=snap)
        self.assertIn("срез 2026-09-07", txt)
        html = build_email.render_html(meta, kpi=kpi, snapshot=snap)
        self.assertIn("Google, Россия", html)
        self.assertIn("softline.ru", html)
        self.assertIn("Где Google нас не показывает", html)
        self.assertNotIn("еженедельный сбор не запущен", html)
        self.assertIn("срез 2026-09-07", html)

    def test_секция_google_пуста_без_среза(self):
        snap = snapshot_with_google("2026-09-07", {}, 0.2)
        snap["google"] = {"доступен": False, "причина": "нет свежего среза"}
        snap["покрытие"]["google"] = None
        self.assertEqual(sections.google_section(snap), "")
        self.assertIn("нет свежего среза", sections.limits_section(snap, []))
        meta = build_email.build(DATE, snap, None)
        self.assertIn("Google NO DATA", meta["текст"])

    def test_deep_report_содержит_раздел_google(self):
        snap = snapshot_with_google("2026-09-07", {"a": {"наша": 0.2, "поле": 1.0}}, 0.2)
        page = deep_report.build(DATE, snap, None, [], [], [])
        self.assertIn("Google, Россия — срез 2026-09-07", page)
        self.assertIn("Разрыв с Яндексом", page)
        self.assertIn("Точки атаки в Google", page)
        self.assertNotIn("прокси-локацию", page)
        snap["google"] = {"доступен": False, "причина": "нет свежего среза"}
        page = deep_report.build(DATE, snap, None, [], [], [])
        self.assertIn("Нет данных: нет свежего среза", page)


if __name__ == "__main__":
    unittest.main()
