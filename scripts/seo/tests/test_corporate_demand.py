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


if __name__ == "__main__":
    unittest.main()
