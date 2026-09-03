#!/usr/bin/env python3
"""xmlriver: разбор XML Google-выдачи, параметры запроса, баланс, повторы."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402

SERP_XML = """<?xml version="1.0" encoding="utf-8"?>
<yandexsearch version="1.0">
 <response date="20260903T000000">
  <found priority="all">4560000</found>
  <results><grouping>
   <group><doc>
     <url>https://ads.example.com/figma</url>
     <title>Реклама</title>
     <contentType>ads</contentType>
   </doc></group>
   <group><doc>
     <url>https://www.biz-soft.pro/product/figma-org</url>
     <title>Купить <hlword>Figma</hlword> для юрлиц</title>
     <contentType>organic</contentType>
   </doc></group>
   <group><doc>
     <url>https://example.com/figma</url>
     <domain>Example.com</domain>
     <title>Figma</title>
   </doc></group>
  </grouping></results>
 </response>
</yandexsearch>"""

ERROR_XML = """<?xml version="1.0" encoding="utf-8"?>
<yandexsearch version="1.0">
 <response><error code="101">Недостаточно средств</error></response>
</yandexsearch>"""

RETRY_XML = """<?xml version="1.0" encoding="utf-8"?>
<yandexsearch version="1.0">
 <response><error code="500">Выполните перезапрос. Ответ от поисковой системы не получен.</error></response>
</yandexsearch>"""

EMPTY_XML = """<?xml version="1.0" encoding="utf-8"?>
<yandexsearch version="1.0">
 <response><error code="15">Искомая комбинация слов нигде не встречается</error></response>
</yandexsearch>"""


class TestParse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x = mocks.load("xmlriver")

    def test_organic_only_domain_fallback_and_hlword(self):
        out = self.x.parse_google_xml(SERP_XML)
        self.assertEqual(out["found"], 4560000)
        # реклама в топ не попадает, но считается в блоках
        self.assertEqual([d["domain"] for d in out["top"]],
                         ["biz-soft.pro", "example.com"])
        self.assertEqual(out["blocks"], {"ads": 1, "organic": 2})
        # домен — из URL без www, если узла <domain> нет; подсветка не рвёт title
        self.assertEqual(out["top"][0]["title"], "Купить Figma для юрлиц")

    def test_top_n_cut(self):
        out = self.x.parse_google_xml(SERP_XML, top_n=1)
        self.assertEqual(len(out["top"]), 1)

    def test_no_results_is_empty_not_error(self):
        out = self.x.parse_google_xml(EMPTY_XML)
        self.assertNotIn("error", out)
        self.assertEqual((out["found"], out["top"]), (0, []))

    def test_service_error_in_200(self):
        out = self.x.parse_google_xml(ERROR_XML)
        self.assertIn("code=101", out["error"])
        self.assertIn("средств", out["error"])

    def test_garbage_is_error(self):
        out = self.x.parse_google_xml("<html>captcha")
        self.assertIn("не является XML", out["error"])


class TestParams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x = mocks.load("xmlriver")

    def test_null_settings_are_not_sent(self):
        p = self.x.build_params("u", "k", "купить figma",
                                {"loc": 2643, "device": "desktop",
                                 "groupby": 20, "lr": None, "domain": ""})
        self.assertEqual(p, {"user": "u", "key": "k", "query": "купить figma",
                             "loc": 2643, "device": "desktop", "groupby": 20})

    def test_page_param_only_from_second_page(self):
        """Нумерация xmlriver — с единицы: первая страница без параметра,
        вторая — page=2 (ответ поддержки 03.09.2026)."""
        first = self.x.build_params("u", "k", "q", {"loc": 2643}, page=1)
        default = self.x.build_params("u", "k", "q", {"loc": 2643})
        second = self.x.build_params("u", "k", "q", {"loc": 2643}, page=2)
        self.assertNotIn("page", first)
        self.assertNotIn("page", default)
        self.assertEqual(second["page"], 2)

    def test_config_defaults_and_comment_keys_dropped(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "x.json"
            p.write_text(json.dumps({"_описание": "…", "cadence": "daily",
                                     "query": {"loc": 1, "_loc": "…",
                                               "lr": None}}),
                         encoding="utf-8")
            cfg = self.x.load_config(p)
        self.assertEqual(cfg["cadence"], "daily")
        self.assertEqual(cfg["query"], {"loc": 1})
        self.assertEqual(cfg["monthly_cap"], 15000)   # значение по умолчанию
        self.assertNotIn("_описание", cfg)
        # отсутствующий файл — значения по умолчанию, не сбой
        self.assertEqual(self.x.load_config(pathlib.Path("/nonexistent"))
                         ["query"]["loc"], 2643)

    def test_repo_config_is_valid(self):
        cfg = self.x.load_config(
            pathlib.Path(__file__).resolve().parents[3]
            / "data" / "seo" / "xmlriver.json")
        self.assertIn(cfg["cadence"], ("weekly", "daily"))
        self.assertGreater(cfg["daily_cap"], 0)
        self.assertGreaterEqual(cfg["monthly_cap"], cfg["daily_cap"])
        self.assertTrue(cfg["query"].get("loc"))
        # groupby сервис принимает только 10 — топ-20 берётся страницами
        self.assertNotIn("groupby", cfg["query"])
        # page сервис игнорирует (проба 03.09.2026) — страницы выключены,
        # пока поддержка xmlriver не подтвердит способ получить 11–20
        self.assertEqual(cfg["pages"], 1)
        self.assertGreaterEqual(cfg["daily_cap"], cfg["core_cap"] * cfg["pages"])
        # учётные данные в конфиг не кладут — только секреты
        for k in cfg:
            self.assertNotIn("key", k.lower())


class TestHttp(unittest.TestCase):
    def setUp(self):
        self.x = mocks.load("xmlriver")
        self.x.RETRY_PAUSE_S = 0

    def test_retries_on_5xx_then_ok(self):
        calls = []

        class S:
            def get(self, url, params=None, timeout=None):
                calls.append(params)
                if len(calls) == 1:
                    return mocks.FakeResponse(502, text="bad gateway")
                return mocks.FakeResponse(200, text=SERP_XML)
        out = self.x.search_google(S(), "u", "k", "q", {"loc": 2643})
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["loc"], 2643)
        self.assertEqual(len(out["top"]), 2)

    def test_service_code_500_is_retried(self):
        """Сервис сам просит перезапрос — это помеха, а не вердикт."""
        calls = []

        class S:
            def get(self, url, params=None, timeout=None):
                calls.append(1)
                if len(calls) == 1:
                    return mocks.FakeResponse(200, text=RETRY_XML)
                return mocks.FakeResponse(200, text=SERP_XML)
        out = self.x.search_google(S(), "u", "k", "q")
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(out["top"]), 2)

    def test_service_code_500_exhausts_retries(self):
        class S:
            def get(self, url, params=None, timeout=None):
                return mocks.FakeResponse(200, text=RETRY_XML)
        out = self.x.search_google(S(), "u", "k", "q")
        self.assertIn("после 4 попыток", out["error"])
        self.assertIn("code=500", out["error"])

    def test_4xx_not_retried(self):
        calls = []

        class S:
            def get(self, url, params=None, timeout=None):
                calls.append(1)
                return mocks.FakeResponse(403, text="forbidden")
        out = self.x.search_google(S(), "u", "k", "q")
        self.assertEqual(len(calls), 1)
        self.assertIn("HTTP 403", out["error"])

    def test_network_failure_exhausts_retries(self):
        class S:
            def get(self, url, params=None, timeout=None):
                raise ConnectionError("reset")
        out = self.x.search_google(S(), "u", "k", "q")
        self.assertIn("после 4 попыток", out["error"])

    def test_no_free_channels_is_retried_with_growing_pause(self):
        """code=111 «Нет свободных каналов» — повтор с растущей паузой."""
        pauses = []
        self.x.time.sleep = pauses.append
        self.x.RETRY_PAUSE_S = 3.0
        calls = []
        busy = RETRY_XML.replace('code="500"', 'code="111"').replace(
            "Выполните перезапрос. Ответ от поисковой системы не получен.",
            "Нет свободных каналов для сбора данных")

        class S:
            def get(self, url, params=None, timeout=None):
                calls.append(1)
                if len(calls) < 3:
                    return mocks.FakeResponse(200, text=busy)
                return mocks.FakeResponse(200, text=SERP_XML)
        out = self.x.search_google(S(), "u", "k", "q")
        self.assertEqual(len(calls), 3)
        self.assertEqual(pauses, [3.0, 6.0])
        self.assertEqual(len(out["top"]), 2)

    def test_balance(self):
        class S:
            def get(self, url, params=None, timeout=None):
                return mocks.FakeResponse(200, text=" 1234,50 ")
        self.assertEqual(self.x.get_balance(S(), "u", "k"),
                         {"balance_rub": 1234.5})

        class Bad:
            def get(self, url, params=None, timeout=None):
                return mocks.FakeResponse(200, text="Wrong key")
        self.assertIn("не является числом", self.x.get_balance(Bad(), "u", "k")["error"])


if __name__ == "__main__":
    unittest.main()
