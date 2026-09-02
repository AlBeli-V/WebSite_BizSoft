"""Тесты полноты проверки вендорской страницы.

Разбор плана работ 02.09.2026. Проверка страницы читала только tagline и
about из src/data/vendors.ts плюс текст типового шаблона — и не видела
bespoke-контент вендора (scripts/content/<slug>.json), из которого на
странице рендерятся сравнение тарифов, матрица выбора, сценарии (H3) и
СВОЙ блок FAQ. Из-за этого семь запросов дня получили поручение «вынести в
подзаголовок или вопрос FAQ» то, что уже стояло вопросом FAQ.

Обратная сторона той же слепоты: шаблонные вопросы FAQ попадали в тело
страницы всегда — даже когда шаблонный блок не рендерится, потому что его
вытеснил свой FAQ вендора или эксперимент со сниппетами. Запрос считался
раскрытым текстом, которого посетитель не видит.

Тесты стерегут обе стороны.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from attack_engine import page_audit, recommendations as rec  # noqa: E402

VENDORS_TS = """export const VENDORS = [
  { slug: 'testvendor', vendor: 'TestVendor', legalName: 'Test Inc.',
    tagline: 'Инструмент для команд.',
    about: 'TestVendor — сервис для совместной работы над макетами.' },
];
"""
BESPOKE = {
    "summary": "TestVendor — сервис для команд. Оформим на юрлицо.",
    "scenarios": [{"title": "Годовая подписка для отдела",
                   "text": "Отдел покупает годовую подписку одним счётом."}],
    "faq": [{"q": "Как оплатить TestVendor в рублях из России?",
             "a": "По счёту на организацию, закрывающие через ЭДО."}],
}
EXPERIMENTS_TS = """export const SEO_EXPERIMENTS = {
  busyvendor: {
    title: 'Оплата BusyVendor для юрлиц | BIZSoft',
    description: 'описание',
    faqTitle: 'Как купить BusyVendor на юрлицо',
    faq: faqFor('BusyVendor'),
  },
  addvendor: {
    title: 'Оплата AddVendor юридическим лицом | BIZSoft',
    description: 'описание',
    faqTitle: 'Оплата AddVendor юридическим лицом',
    faqAdd: faqLegalPay('AddVendor'),
  },
};
"""


class VendorFixture(unittest.TestCase):
    """Подменяет источники страницы на временный каталог."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.content_dir = os.path.join(self.tmp, "content")
        os.makedirs(self.content_dir)
        self.vendors_ts = os.path.join(self.tmp, "vendors.ts")
        with open(self.vendors_ts, "w", encoding="utf-8") as fh:
            fh.write(VENDORS_TS)
        self.experiments_ts = os.path.join(self.tmp, "seo-experiments.ts")
        with open(self.experiments_ts, "w", encoding="utf-8") as fh:
            fh.write(EXPERIMENTS_TS)
        self._saved = (page_audit.VENDORS_TS, page_audit.VENDOR_CONTENT_DIR,
                       page_audit.SEO_EXPERIMENTS_TS, page_audit.VENDOR_PAGES)
        page_audit.VENDORS_TS = self.vendors_ts
        page_audit.VENDOR_CONTENT_DIR = self.content_dir
        page_audit.SEO_EXPERIMENTS_TS = self.experiments_ts
        page_audit.VENDOR_PAGES = os.path.join(self.tmp, "нет-таких-страниц")

    def tearDown(self):
        (page_audit.VENDORS_TS, page_audit.VENDOR_CONTENT_DIR,
         page_audit.SEO_EXPERIMENTS_TS, page_audit.VENDOR_PAGES) = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_bespoke(self, slug, data):
        with open(os.path.join(self.content_dir, f"{slug}.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)

    def load(self, slug="testvendor"):
        return page_audit.load(f"https://biz-soft.pro/vendors/{slug}", "vendor")


class TestBespokeVisible(VendorFixture):
    def test_свой_faq_вендора_виден_проверке(self):
        self.write_bespoke("testvendor", BESPOKE)
        page = self.load()
        self.assertIn("Как оплатить TestVendor в рублях из России?",
                      page.faq_questions)

    def test_заголовок_сценария_считается_заголовком(self):
        self.write_bespoke("testvendor", BESPOKE)
        page = self.load()
        self.assertIn("Годовая подписка для отдела", page.headings)

    def test_запрос_из_вопроса_faq_раскрыт_в_заголовке(self):
        """Ровно та ошибка дня: поручение «вынести в FAQ» уже сделанного."""
        self.write_bespoke("testvendor", BESPOKE)
        page = self.load()
        state, _ = page_audit.coverage(page, "оплатить testvendor в рублях")
        self.assertEqual(state, page_audit.COVER_PROMINENT)

    def test_без_bespoke_остаётся_шаблонный_faq(self):
        page = self.load()
        self.assertTrue(any("для юридического лица" in q
                            for q in page.faq_questions))

    def test_граница_проверки_называет_bespoke(self):
        self.write_bespoke("testvendor", BESPOKE)
        page = self.load()
        self.assertIn("scripts/content/testvendor.json", page.scope_note)


class TestExperimentOverride(VendorFixture):
    """Эксперимент со сниппетами подменяет FAQ — это надо учитывать."""

    def setUp(self):
        super().setUp()
        with open(self.vendors_ts, "w", encoding="utf-8") as fh:
            fh.write(VENDORS_TS.replace("testvendor", "busyvendor")
                     .replace("TestVendor", "BusyVendor"))

    def test_faq_вытеснен_экспериментом_и_не_считается_раскрытием(self):
        self.write_bespoke("busyvendor", {
            "faq": [{"q": "Поддерживаются ли форматы вывода в вектор?",
                     "a": "Да."}]})
        page = self.load("busyvendor")
        # Свой вопрос про вектор на странице не рендерится: блок заменён.
        self.assertNotIn("Поддерживаются ли форматы вывода в вектор?",
                         page.faq_questions)
        state, missing = page_audit.coverage(page, "busyvendor вектор экспорт")
        self.assertEqual(state, page_audit.COVER_NONE)

    def test_режим_подмены_определяется_по_файлу(self):
        self.assertEqual(page_audit.experiment_faq_mode("busyvendor"), "faq")
        self.assertEqual(page_audit.experiment_faq_mode("addvendor"), "faqAdd")
        self.assertEqual(page_audit.experiment_faq_mode("testvendor"), "")


class TestProductHeadings(unittest.TestCase):
    """На карточке товара подзаголовок под запрос завести негде."""

    def test_вместо_заголовков_предлагается_проверка(self):
        page = page_audit.PageContent(
            url="https://biz-soft.pro/product/spine-pro", kind="product",
            available=True, edit_hint="data/seo/product-descriptions.json",
            title="Spine Pro", headings=["Тарифы"],
            body="spine pro купить лицензию", scope_note="шаблон карточки")
        actions, _, _ = rec.build(
            {"package_id": "WP-01", "url": "https://biz-soft.pro/product/spine-pro",
             "queries": ["spine pro купить"], "position_best": 7,
             "position_worst": 7, "rivals": ["syssoft.ru"]}, page)
        kinds = [a.kind for a in actions]
        self.assertIn("проверка", kinds)
        self.assertNotIn("заголовки", kinds)
        проверка = next(a for a in actions if a.kind == "проверка")
        self.assertIn("Directus", проверка.where)


class TestEmptyPackageHeadline(unittest.TestCase):
    """Пакет без действий не получает расплывчатого поручения 1.3.0."""

    def test_без_действий_печатается_результат_проверки(self):
        text = rec.headline([], {"action": "довести условия для юрлиц до "
                                           "уровня конкурентов из выдачи"})
        self.assertNotIn("довести условия", text)
        self.assertIn("правок по репозиторию не требуется", text)


if __name__ == "__main__":
    unittest.main()
