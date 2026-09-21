"""Привязка фразы к каталогу: продаём ли мы то, о чём спрашивают (21.09.2026).

База семантики маппит все фразы на страницы вендоров, поэтому «google pixel
купить» и «apple watch цена» выглядели в ней рекламопригодными. Решение
руководителя — рекламировать только карточки, которые есть на витрине.

Каталог в тестах синтетический: правила проверяются на устройстве привязки,
а не на сегодняшнем ассортименте, который меняется каждую неделю.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "wordstat"))
import catalog_match as C  # noqa: E402

LEXICON = {
    "hardware_stop": ["pixel", "watch", "наушник"],
    "generic_tokens": ["pro", "plus", "business", "gift", "card", "win", "mac"],
    "class_synonyms": {"gift-card": ["подарочн", "сертификат", "пополнен"]},
    "vendor_aliases": {"apple": ["apple", "эпл"]},
}
VENDORS = {"apple": "Apple", "adobe": "Adobe", "google": "Google", "narrow": "Narrow"}
CARDS = [
    "app-store-itunes-gift-card",
    "adobe-ps", "adobe-ai", "adobe-cc-std",
    "gemini-workspace-standard",
    "narrow-one",
]
TITLES = {
    "app-store-itunes-gift-card": "Цифровая подарочная карта Apple",
    "adobe-ps": "Adobe Photoshop",
    "adobe-ai": "Adobe Illustrator",
    "adobe-cc-std": "Adobe Creative Cloud",
    "gemini-workspace-standard": "Google Workspace с Gemini для бизнеса",
    "narrow-one": "Narrow Single",
}


def catalog() -> C.Catalog:
    return C.Catalog(lexicon=LEXICON, vendors=VENDORS, cards=CARDS,
                     sku_names={}, titles=TITLES)


class HardwareTest(unittest.TestCase):
    def test_железо_отсекается_до_всего_остального(self):
        m = catalog().match("google pixel купить")
        self.assertEqual(m["kind"], "none")
        self.assertIn("железо", m["why"])

    def test_железо_отсекается_даже_у_вендора_с_карточками(self):
        self.assertEqual(catalog().match("apple watch цена")["kind"], "none")


class ProductMatchTest(unittest.TestCase):
    def test_фраза_садится_на_свою_карточку_а_не_на_соседнюю(self):
        m = catalog().match("adobe photoshop купить")
        self.assertEqual(m["slug"], "adobe-ps")

    def test_имя_вендора_само_по_себе_карточку_не_выбирает(self):
        # Иначе «adobe ... купить» село бы на первую попавшуюся из 22 карточек.
        cat = catalog()
        self.assertNotIn("adobe", cat.card_tokens("adobe-ps"))

    def test_русский_синоним_класса_находит_латинскую_карточку(self):
        m = catalog().match("купить подарочную карту apple")
        self.assertEqual(m["slug"], "app-store-itunes-gift-card")

    def test_товар_без_бренда_ищется_по_всем_карточкам(self):
        self.assertEqual(catalog().match("купить illustrator")["slug"], "adobe-ai")

    def test_выбор_карточки_повторяем(self):
        cat = catalog()
        first = cat.match("adobe купить illustrator")
        for _ in range(3):
            self.assertEqual(cat.match("adobe купить illustrator"), first)


class VendorMatchTest(unittest.TestCase):
    def test_брендовый_запрос_ведёт_на_вендора(self):
        m = catalog().match("adobe купить")
        self.assertEqual(m["kind"], "vendor")
        self.assertEqual(m["url"], "/vendors/adobe")

    def test_постороннее_слово_снимает_брендовую_привязку(self):
        # «google pro купить» — это Pixel Pro, а не Google Workspace.
        m = catalog().match("google pro купить")
        self.assertEqual(m["kind"], "none")
        self.assertIn("посторонним словом", m["why"])

    def test_линейка_из_одних_подарочных_карт_брендовый_запрос_не_ловит(self):
        m = catalog().match("apple купить")
        self.assertEqual(m["kind"], "none")
        self.assertIn("подарочные карты", m["why"])

    def test_вендор_без_карточек_отсекается(self):
        cat = C.Catalog(lexicon=LEXICON, vendors=dict(VENDORS, empty="Empty"),
                        cards=CARDS, sku_names={}, titles=TITLES)
        m = cat.match("empty купить")
        self.assertEqual(m["kind"], "none")
        self.assertIn("продавать нечего", m["why"])


class GroupingTest(unittest.TestCase):
    def test_карточка_привязана_по_названию_а_не_по_слагу(self):
        # `gemini-workspace-standard` — это Google, хотя слаг об этом молчит.
        cat = catalog()
        self.assertIn("gemini-workspace-standard", cat._by_vendor.get("google", []))

    def test_карточка_без_описания_идёт_за_соседями_по_префиксу(self):
        cards = CARDS + ["adobe-lr"]
        cat = C.Catalog(lexicon=LEXICON, vendors=VENDORS, cards=cards,
                        sku_names={}, titles=TITLES)
        self.assertIn("adobe-lr", cat._by_vendor["adobe"])


if __name__ == "__main__":
    unittest.main()
