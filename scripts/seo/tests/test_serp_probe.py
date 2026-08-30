#!/usr/bin/env python3
"""Разбор XML веб-поиска: результаты, ошибка сервиса кодом 200, мусор."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402

SERP_XML = """<?xml version="1.0" encoding="utf-8"?>
<yandexsearch version="1.0">
 <response date="20260830T000000">
  <found priority="all">1234</found>
  <results><grouping>
   <group><doc>
     <url>https://biz-soft.pro/product/figma-org</url>
     <domain>biz-soft.pro</domain>
     <title>Купить <hlword>Figma</hlword> для юрлиц</title>
   </doc></group>
   <group><doc>
     <url>https://example.com/figma</url>
     <domain>example.com</domain>
     <title>Figma</title>
   </doc></group>
  </grouping></results>
 </response>
</yandexsearch>"""

ERROR_XML = """<?xml version="1.0" encoding="utf-8"?>
<yandexsearch version="1.0">
 <response><error code="32">Превышен лимит запросов</error></response>
</yandexsearch>"""


class TestParseSerp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = mocks.load("serp_probe")

    def test_docs_and_found(self):
        out = self.p.parse_serp(SERP_XML)
        self.assertEqual(out["found"], 1234)
        self.assertEqual(len(out["docs"]), 2)
        self.assertEqual(out["docs"][0]["domain"], "biz-soft.pro")
        # hlword-подсветка не рвёт заголовок
        self.assertEqual(out["docs"][0]["title"], "Купить Figma для юрлиц")

    def test_service_error_in_200(self):
        out = self.p.parse_serp(ERROR_XML)
        self.assertIn("code=32", out["error"])
        self.assertIn("лимит", out["error"])

    def test_garbage_is_error_not_crash(self):
        out = self.p.parse_serp("<html>not xml serp")
        self.assertIn("не является XML", out["error"])


if __name__ == "__main__":
    unittest.main()
