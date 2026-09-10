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
        self.assertEqual((ours["топ3"], ours["топ10"], ours["в_выдаче"]), (2, 2, 2))
        self.assertEqual(ours["лучшая_позиция"], 1)
        self.assertEqual(block["глубина"], 10)
        self.assertEqual(block["наши_запросы"],
                         [{"запрос": "наоборот", "позиция": 1},
                          {"запрос": "zoom для юрлиц", "позиция": 3}])
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
        ya = gap["яндекс_топ10_google_нет"]
        self.assertEqual([i["запрос"] for i in ya], ["купить figma"])
        self.assertEqual(ya[0]["позиция_яндекс"], 1)
        self.assertEqual(ya[0]["google_топ3"], ["softline.ru", "allsoft.ru", "syssoft.ru"])
        g = gap["google_топ10_яндекс_нет"]
        self.assertEqual([i["запрос"] for i in g], ["наоборот"])
        self.assertEqual(gap["яндекс_топ10_google_нет_всего"], 1)

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
            "глубина": 10,
            "наши_показатели": {"доля_видимости": share, "топ3": 1, "топ10": 1,
                                "в_выдаче": 2, "лучшая_позиция": 1,
                                "запросов_в_поле": 2,
                                "взвешенная_видимость": 0.2},
            "наши_запросы": [{"запрос": "zoom", "позиция": 1}],
            "по_запросам": per_query,
            "доли_по_категориям": {},
            "лидеры": [{"домен": "softline.ru", "категория": "A", "доля": 0.3,
                        "топ3": 1, "топ10": 2}],
            "конкурентов_в_основном_рейтинге": 1,
            "разрыв_с_яндексом": {"сопоставлено": 2, "в_обеих_топ10": 1,
                                  "яндекс_топ10_google_нет": [
                                      {"запрос": "купить figma", "позиция_яндекс": 2,
                                       "google_топ3": ["softline.ru"]}],
                                  "яндекс_топ10_google_нет_всего": 1,
                                  "google_топ10_яндекс_нет": [],
                                  "google_топ10_яндекс_нет_всего": 0},
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
        self.assertIn("Google по России", html)
        self.assertIn("softline.ru", html)
        self.assertIn("biz-soft.pro (мы)", html)
        self.assertIn("Где Google нас не показывает", html)
        self.assertIn("GOOGLE ПО РОССИИ", txt)
        self.assertIn("глубина 10", html)
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


class TestAbsenceProfile(unittest.TestCase):
    """Разрыв с Google, разложенный до проверяемой гипотезы.

    Разбор 10.09.2026: отчёт называл разрыв главным вопросом, перечислял три
    гипотезы и не проверял ни одной. Разводит их величина, которая уже
    собрана: встречается ли наша страница в Google-срезе хоть где-нибудь.
    Страница, проигрывающая по релевантности, стоит на 11–20 и в срез
    попадает; страница, которой нет ни разу, проигрывает не конкурентам.
    """

    def строка(self, query, *domains, engine="yandex", region=None):
        region = region or ("213" if engine == "yandex" else "2643")
        top = [{"domain": d, "url": f"https://{d}/page", "title": d}
               for d in domains]
        return serp_source.SerpRow(date="2026-09-07", query=query,
                                   region=region, engine=engine, top=top)

    def test_страница_не_встречается_нигде(self):
        y = [self.строка("q1", "biz-soft.pro"), self.строка("q2", "biz-soft.pro")]
        g = [self.строка("q1", "rival.ru", engine="google"),
             self.строка("q2", "rival.ru", engine="google")]
        p = google_ru.absence_profile(g, y, "2643")
        self.assertEqual(1, p["страниц_в_разрыве"])
        self.assertEqual(1, p["страниц_нет_в_срезе"])
        self.assertEqual(0, p["страниц_есть_в_срезе"])
        self.assertEqual(2, p["первые"][0]["запросов"])

    def test_страница_видна_по_другому_запросу(self):
        """Присутствие ищется по всему срезу, а не по запросам разрыва."""
        y = [self.строка("q1", "biz-soft.pro"), self.строка("q2", "biz-soft.pro")]
        g = [self.строка("q1", "rival.ru", engine="google"),
             self.строка("q2", "rival.ru", "biz-soft.pro", engine="google")]
        p = google_ru.absence_profile(g, y, "2643")
        # q2 не в разрыве: там мы в Google есть. q1 в разрыве, но страница
        # та же и в срезе встречается — значит видимость не под вопросом.
        self.assertEqual(1, p["страниц_в_разрыве"])
        self.assertEqual(1, p["страниц_есть_в_срезе"])
        self.assertEqual(0, p["страниц_нет_в_срезе"])

    def test_запросы_не_измеренные_в_обеих_системах_не_в_счёт(self):
        y = [self.строка("q1", "biz-soft.pro"), self.строка("только-яндекс",
                                                            "biz-soft.pro")]
        g = [self.строка("q1", "rival.ru", engine="google")]
        p = google_ru.absence_profile(g, y, "2643")
        self.assertEqual(1, p["страниц_в_разрыве"])
        self.assertEqual(1, p["первые"][0]["запросов"])

    def test_страницы_ранжированы_по_весу(self):
        y = ([self.строка(f"лёгкий {i}", "rival.ru", "biz-soft.pro")
              for i in range(1)]
             + [self.строка(f"тяжёлый {i}", "biz-soft.pro") for i in range(3)])
        g = [self.строка(r.query, "rival.ru", engine="google") for r in y]
        # Разные страницы: url берётся из выдачи, поэтому подменяем домен.
        for i, r in enumerate(y):
            for item in r.top:
                if item["domain"] == "biz-soft.pro":
                    item["url"] = ("https://biz-soft.pro/тяжёлая" if "тяжёлый"
                                   in r.query else "https://biz-soft.pro/лёгкая")
        p = google_ru.absence_profile(g, y, "2643")
        self.assertEqual(2, p["страниц_в_разрыве"])
        self.assertEqual("https://biz-soft.pro/тяжёлая", p["первые"][0]["url"])
        self.assertEqual(3, p["первые"][0]["запросов"])


class TestGoogleHypothesisBlock(unittest.TestCase):
    """Вывод выбирается статусом индексации, а не догадкой.

    Первая версия блока (1.9.3) меряла только присутствие страницы в
    Google-срезе и делала один вывод на всех — «проверять надо видимость».
    На срезе 09.09 он был верен для 41 страницы из 64 и неверен для 23:
    те в индексе и просто проигрывают в ранжировании. Статус, разводящий эти
    случаи, базовый контур снимает ежедневно, и разведка теперь его читает.
    """

    def профиль(self, **по_индексу):
        всего = sum(по_индексу.values())
        return {"страниц_в_разрыве": всего,
                "страниц_нет_в_срезе": всего,
                "страниц_есть_в_срезе": 0,
                "наших_url_в_срезе_всего": 0,
                "индекс_доступен": True,
                "индекс_дата": "2026-09-09",
                "по_индексу": по_индексу,
                "первые": [{"url": "https://biz-soft.pro/x", "запросов": 3,
                            "лучшая_позиция_яндекс": 1,
                            "есть_в_google_срезе": False,
                            "индекс": "не знает адреса",
                            "индекс_дословно": "URL is unknown to Google"}]}

    def test_три_группы_названы_порознь(self):
        html = deep_report._google_hypothesis(self.профиль(**{
            "не знает адреса": 11,
            "знает, но не индексирует": 30,
            "в индексе, проигрывает в выдаче": 23}))
        self.assertIn("три, и работа у них разная", html)
        self.assertIn("Google не знает адреса", html)
        self.assertIn("Google знает адрес и в индекс не берёт", html)
        self.assertIn("Страница в индексе и проигрывает", html)

    def test_только_видимость_говорит_про_видимость(self):
        html = deep_report._google_hypothesis(self.профиль(**{
            "не знает адреса": 5, "знает, но не индексирует": 7}))
        self.assertIn("Дело в видимости, а не в текстах", html)

    def test_только_индекс_говорит_про_ранжирование(self):
        html = deep_report._google_hypothesis(self.профиль(**{
            "в индексе, проигрывает в выдаче": 9}))
        self.assertIn("вопрос в ранжировании", html)

    def test_без_статусов_вывод_не_делается(self):
        """Молчаливый переход к догадке — то, ради чего блок и переписан."""
        профиль = self.профиль(**{"статуса нет": 9})
        профиль["индекс_доступен"] = False
        html = deep_report._google_hypothesis(профиль)
        self.assertIn("гипотезы не разведены", html)
        self.assertNotIn("Дело в видимости", html)

    def test_источник_статусов_назван(self):
        html = deep_report._google_hypothesis(self.профиль(**{
            "не знает адреса": 3, "в индексе, проигрывает в выдаче": 3}))
        self.assertIn("URL Inspection API", html)
        self.assertIn("2026-09-09", html)

    def test_без_разрыва_блока_нет(self):
        self.assertEqual("", deep_report._google_hypothesis(
            {"страниц_в_разрыве": 0}))


class TestIndexStatus(unittest.TestCase):
    """Статус индексации читается из выгрузки, а не запрашивается заново."""

    def setUp(self):
        from discovery import index_status
        self.ix = index_status
        self.ix.load.cache_clear()
        self._load = self.ix.load
        self.ix.load = lambda *a, **k: {
            "date": "2026-09-09",
            "pages": {
                "/blog/framer": {"coverage_state": "URL is unknown to Google"},
                "/blog/postman": {"coverage_state":
                                  "Discovered - currently not indexed"},
                "/vendors/recraft": {"coverage_state": "Submitted and indexed"},
                "/vendors/пусто": {},
            }}

    def tearDown(self):
        self.ix.load = self._load
        self.ix.load.cache_clear()

    def test_три_класса_разводятся(self):
        S = "https://biz-soft.pro"
        self.assertEqual(self.ix.UNKNOWN, self.ix.state(f"{S}/blog/framer")[0])
        self.assertEqual(self.ix.NOT_INDEXED,
                         self.ix.state(f"{S}/blog/postman")[0])
        self.assertEqual(self.ix.INDEXED,
                         self.ix.state(f"{S}/vendors/recraft")[0])

    def test_страницы_нет_в_выгрузке(self):
        класс, дословно = self.ix.state("https://biz-soft.pro/нет-такой")
        self.assertEqual(self.ix.NO_DATA, класс)
        self.assertEqual("", дословно)

    def test_пустой_статус_не_подменяется(self):
        self.assertEqual(self.ix.NO_DATA,
                         self.ix.state("https://biz-soft.pro/vendors/пусто")[0])

    def test_завершающий_слеш_не_мешает(self):
        self.assertEqual(self.ix.INDEXED,
                         self.ix.state("https://biz-soft.pro/vendors/recraft/")[0])

    def test_неизвестный_статус_считается_непроиндексированным(self):
        """Незнакомая формулировка Search Console не становится «в индексе»."""
        self.ix.load = lambda *a, **k: {
            "date": "2026-09-09",
            "pages": {"/x": {"coverage_state": "Что-то новое от Google"}}}
        self.assertEqual(self.ix.NOT_INDEXED,
                         self.ix.state("https://biz-soft.pro/x")[0])


class TestОчередьОбходаОтличаетсяОтПриговора(unittest.TestCase):
    """Страницу, которую Google не скачивал, переписывать бесполезно.

    Разбор индексации 10.09.2026: из 363 страниц в статусе «Discovered —
    currently not indexed» Google скачал ровно одну, а по сайту не скачано
    493 из 732. Статус в общем случае может означать «посмотрел и не взял»,
    здесь означает «знаю адрес, руки не дошли». Разница определяет работу.
    """

    def setUp(self):
        from discovery import index_status
        self.ix = index_status
        self.ix.load.cache_clear()
        self._load = self.ix.load
        self.ix.load = lambda *a, **k: {
            "date": "2026-09-09",
            "pages": {
                "/скачан": {"coverage_state": "Submitted and indexed",
                            "last_crawl": "2026-09-08T00:00:00Z"},
                "/в-очереди": {"coverage_state":
                               "Discovered - currently not indexed"},
                "/неизвестен": {"coverage_state": "URL is unknown to Google"},
            }}

    def tearDown(self):
        self.ix.load = self._load
        self.ix.load.cache_clear()

    def test_скачанность_видна_отдельно_от_статуса(self):
        S = "https://biz-soft.pro"
        self.assertTrue(self.ix.crawled(f"{S}/скачан"))
        self.assertFalse(self.ix.crawled(f"{S}/в-очереди"))
        self.assertFalse(self.ix.crawled(f"{S}/неизвестен"))

    def test_сводка_по_обходу_считает_сайт_целиком(self):
        сводка = self.ix.crawl_summary()
        self.assertEqual(3, сводка["страниц"])
        self.assertEqual(1, сводка["скачано"])
        self.assertEqual(2, сводка["не скачано"])
        self.assertEqual("2026-09-08", сводка["последний_обход"])

    def test_отчёт_называет_очередь_обхода(self):
        профиль = {"страниц_в_разрыве": 64, "страниц_нет_в_срезе": 41,
                   "страниц_есть_в_срезе": 23, "наших_url_в_срезе_всего": 23,
                   "индекс_доступен": True, "индекс_дата": "2026-09-09",
                   "не_скачано": 41,
                   "обход_по_сайту": {"страниц": 732, "скачано": 239,
                                      "не скачано": 493,
                                      "последний_обход": "2026-09-08"},
                   "по_индексу": {"не знает адреса": 11,
                                  "знает, но не индексирует": 30,
                                  "в индексе, проигрывает в выдаче": 23},
                   "первые": []}
        html = deep_report._google_hypothesis(профиль)
        self.assertIn("ни разу не скачивал 41 из 64", html)
        self.assertIn("493 из 732", html)
        self.assertIn("переписывать бесполезно", html)

    def test_без_данных_об_обходе_строки_нет(self):
        профиль = {"страниц_в_разрыве": 5, "страниц_нет_в_срезе": 5,
                   "страниц_есть_в_срезе": 0, "индекс_доступен": True,
                   "по_индексу": {"не знает адреса": 5}, "первые": []}
        html = deep_report._google_hypothesis(профиль)
        self.assertNotIn("очередь обхода", html)
