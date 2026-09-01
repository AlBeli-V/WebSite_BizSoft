"""Тесты категоризации доменов и B2B Confidence.

Отдельно проверяется требование раздела 32 задания: маркетплейсы и B2C не
должны становиться главными B2B-конкурентами.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from competitors import classifier  # noqa: E402
from scoring import visibility  # noqa: E402


class TestCategorize(unittest.TestCase):
    def test_наш_домен(self):
        self.assertEqual(classifier.categorize("biz-soft.pro"), "A")

    def test_www_и_регистр_не_мешают(self):
        self.assertEqual(classifier.categorize("WWW.Syssoft.RU"), "A")

    def test_платёжные_посредники(self):
        for d in ("raketapay.ru", "pipl.io", "finteka.io"):
            self.assertEqual(classifier.categorize(d), "H", d)

    def test_маркетплейсы_и_b2c(self):
        for d in ("ozon.ru", "avito.ru", "ggsel.net", "plati.market"):
            self.assertEqual(classifier.categorize(d), "E", d)

    def test_информационные(self):
        for d in ("dzen.ru", "vc.ru", "habr.com"):
            self.assertEqual(classifier.categorize(d), "G", d)

    def test_вендор_из_реестра_сайта(self):
        hosts = classifier.vendor_domains()
        self.assertIn("adobe.com", hosts)
        self.assertEqual(classifier.categorize("adobe.com", vendor_hosts=hosts), "F")

    def test_неизвестный_домен_не_попадает_в_рейтинг_молча(self):
        self.assertEqual(classifier.categorize("совершенно-новый-домен.ру"), "?")
        self.assertFalse(classifier.in_main_ranking("?"))

    def test_пустой_домен(self):
        self.assertEqual(classifier.categorize(""), "?")
        self.assertEqual(classifier.categorize(None), "?")

    def test_признак_статьи_в_url_слабее_списка(self):
        """Статья на домене-маркетплейсе не делает его информационным."""
        self.assertEqual(
            classifier.categorize("ozon.ru", sample_urls=["https://ozon.ru/blog/x"]),
            "E")

    def test_имя_домена_как_последний_признак(self):
        self.assertEqual(classifier.categorize("nukapay.ru"), "H")


class TestMainRanking(unittest.TestCase):
    def test_b2c_информационные_и_официальные_вне_рейтинга(self):
        """Ключевая защита от ложных срабатываний (раздел 32 задания)."""
        for cat in ("E", "G", "F", "?"):
            self.assertFalse(classifier.in_main_ranking(cat), cat)

    def test_b2b_и_посредники_в_рейтинге(self):
        for cat in ("A", "B", "C", "D", "H"):
            self.assertTrue(classifier.in_main_ranking(cat), cat)


class TestB2BConfidence(unittest.TestCase):
    def setUp(self):
        self.config = visibility.load_config()

    def test_пустая_страница_даёт_ноль(self):
        v = classifier.b2b_confidence("", self.config)
        self.assertEqual(v.confidence, 0)
        self.assertEqual(v.signals, [])
        self.assertFalse(v.in_main_pool)

    def test_сильная_b2b_страница_проходит_порог(self):
        текст = ("Оплата по счёту для юридических лиц, договор, НДС, "
                 "закрывающие документы через ЭДО, ИНН и ОГРН, "
                 "корпоративное лицензирование")
        v = classifier.b2b_confidence(текст, self.config)
        self.assertGreaterEqual(v.confidence, 60)
        self.assertTrue(v.in_main_pool)
        self.assertIn("оплата_по_счёту", v.signals)
        self.assertIn("эдо", v.signals)

    def test_score_объясним(self):
        """Число без оснований доверия не заслуживает."""
        v = classifier.b2b_confidence("работаем с юридическими лицами",
                                      self.config,
                                      evidence_urls=["https://x.ru/payment"])
        self.assertTrue(v.signals)
        self.assertEqual(v.evidence_urls, ["https://x.ru/payment"])

    def test_потолок_сто(self):
        текст = " ".join(w for group in classifier.B2B_SIGNALS.values() for w in group)
        v = classifier.b2b_confidence(текст, self.config)
        self.assertLessEqual(v.confidence, 100)

    def test_b2c_страница_не_проходит_порог(self):
        текст = "Купить ключ активации мгновенно, оплата картой, скидка 50%"
        v = classifier.b2b_confidence(текст, self.config)
        self.assertLess(v.confidence, 60)


if __name__ == "__main__":
    unittest.main()
