"""Исчерпанная квота Google не роняет сбор данных.

04.09.2026 суточная квота инспекции URL кончилась, скрипт вышел с кодом 1,
и ежедневное письмо не вышло вовсе — хотя все прочие источники собрались,
а страницы сохраняли статус прошлой инспекции. Проверяем разделение:
квота при наличии унаследованных статусов — ограничение, любая другая
ошибка и квота без унаследованных данных — по-прежнему поломка.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import index_coverage as ic  # noqa: E402

QUOTA_ERROR = ('ни один URL не проинспектирован: /blog/x: HTTP 429: '
               '{"error": {"code": 429, "message": "Quota exceeded for '
               'sc-domain:biz-soft.pro.", "status": "RESOURCE_EXHAUSTED"}}')


class QuotaLimitedTest(unittest.TestCase):
    def test_kvota_s_unasledovannymi_eto_ogranichenie(self):
        self.assertTrue(ic.quota_limited({"error": QUOTA_ERROR, "inherited": 454}))

    def test_kvota_bez_unasledovannyh_ostayotsya_polomkoy(self):
        self.assertFalse(ic.quota_limited({"error": QUOTA_ERROR, "inherited": 0}))

    def test_drugaya_oshibka_ostayotsya_polomkoy(self):
        self.assertFalse(ic.quota_limited(
            {"error": "секрет GSC_SERVICE_ACCOUNT_JSON не задан", "inherited": 454}))

    def test_uspeshnyy_srez_ne_ogranichenie(self):
        self.assertFalse(ic.quota_limited({"inspected": 120, "inherited": 300}))

    def test_otkaz_dostupa_403_ne_kvota(self):
        self.assertFalse(ic.quota_limited(
            {"error": "HTTP 403: Forbidden", "inherited": 454}))


if __name__ == "__main__":
    unittest.main()
