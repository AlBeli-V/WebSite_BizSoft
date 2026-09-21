"""Целевой замер корпоративного спроса: формы и состав вендоров (21.09.2026).

Прогон тратит квоту Wordstat по три вызова на вендора, поэтому проверяется
главное: формы те самые, которыми к нам приходят заявки, и берутся они по
якорю вендора из каталога, а не по произвольному имени.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "wordstat"))
import corporate_demand as C  # noqa: E402
import discovery as D  # noqa: E402


class FormsTest(unittest.TestCase):
    def test_формы_взяты_из_запросов_с_заявками(self):
        # Каждая форма встречалась в Вебмастере у запросов, приведших заявку.
        self.assertIn("оплата {vendor} юридическим лицом", C.FORMS)
        self.assertIn("купить {vendor} для компании", C.FORMS)
        self.assertEqual(len(C.FORMS), 3)

    def test_мёртвая_форма_не_используется(self):
        # «{vendor} для юридических лиц» — 35 пустых ответов из 37.
        self.assertNotIn("{vendor} для юридических лиц", C.FORMS)

    def test_фраза_строится_по_якорю_вендора(self):
        vendor = {"anchor": "capture one", "slug": "capture-one"}
        made = [f.format(vendor=vendor["anchor"]) for f in C.FORMS]
        self.assertIn("оплата capture one юридическим лицом", made)


class VendorsTest(unittest.TestCase):
    def test_список_вендоров_совпадает_с_каталогом(self):
        # Тот же источник, что у основного сбора: иначе замер разойдётся с сайтом.
        vendors = D.site_vendors() + D.bespoke_landings()
        self.assertGreater(len(vendors), 50)
        for v in vendors[:20]:
            self.assertTrue(v.get("anchor"), v)
            self.assertTrue(v.get("slug"), v)


class WiringTest(unittest.TestCase):
    """Проверка сборки прогона без единого вызова в сеть.

    Холостой режим выходит раньше, чем скрипт открывает базу семантики, и
    первый боевой прогон упал именно там: у Universe нет метода load(),
    база читается конструктором. Тест повторяет тот же путь.
    """

    def test_база_и_индекс_вендоров_открываются(self):
        import universe as U
        vendors = D.site_vendors() + D.bespoke_landings()
        index = D.vendor_index(vendors)
        # Непустоты базы тест не требует: файл живёт в ветке seo-data и
        # появляется в рабочем каталоге только после data_sync pull.
        uni = U.Universe(vendors=index)
        self.assertIsInstance(len(uni), int)
        self.assertTrue(callable(getattr(uni, "observe", None)))
        self.assertTrue(callable(getattr(uni, "save", None)))
        self.assertFalse(hasattr(uni, "load"), "метода load() у базы нет")


if __name__ == "__main__":
    unittest.main()
