"""Тесты исполнимости рекомендаций.

Проверяют не форму, а обещание: поручение из отчёта можно отдать в работу и
принять по названному признаку, оно не советует сделанное и не опирается на
то, чего контур не измеряет.
"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from attack_engine import page_audit, recommendations as rec  # noqa: E402

ARTICLE = """---
title: "Как оплатить Depositphotos для юридического лица"
description: "Счёт в рублях, договор и закрывающие документы через ЭДО."
faq:
  - q: "Можно ли оплатить с расчётного счёта компании?"
    a: "Да, счёт выставляется в рублях."
---

Оплатить Depositphotos для юридического лица можно через российского поставщика.

## Что нужно для оплаты Depositphotos на юрлицо

Счёт в рублях, договор, закрывающие документы. Подробнее — в [каталоге](/catalog),
карточка [подписки](/product/deposit-unl-year) и страница [вендора](/vendors/depositphotos).
"""


def package(**over):
    data = {
        "package_id": "WP-01",
        "url": "https://biz-soft.pro/blog/test-article",
        "page_kind": "blog",
        "queries": ["как оплатить depositphotos на юрлицо",
                    "оплатить подписку depositphotos в россии"],
        "position_best": 5, "position_worst": 10,
        "rivals": ["card-open.ru", "finteka.io"],
        "action": "старый шаблонный заголовок",
    }
    data.update(over)
    return data


def page_from(text, kind="blog", url="https://biz-soft.pro/blog/test-article"):
    """Страница из текста статьи — без обращения к репозиторию."""
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "test-article.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    original = page_audit.BLOG_DIR
    page_audit.BLOG_DIR = tmp
    try:
        return page_audit.load(url, kind)
    finally:
        page_audit.BLOG_DIR = original


class TestPageAudit(unittest.TestCase):
    def test_читается_текст_заголовки_faq_и_ссылки(self):
        page = page_from(ARTICLE)
        self.assertTrue(page.available)
        self.assertIn("Что нужно для оплаты Depositphotos на юрлицо", page.headings)
        self.assertEqual(len(page.faq_questions), 1)
        self.assertIn("/product/deposit-unl-year", page.internal_links)
        self.assertIn("/vendors/depositphotos", page.internal_links)

    def test_запрос_из_заголовка_считается_раскрытым(self):
        page = page_from(ARTICLE)
        state, missing = page_audit.coverage(page, "оплата depositphotos на юрлицо")
        self.assertEqual(state, page_audit.COVER_PROMINENT)
        self.assertEqual(missing, [])

    def test_отсутствующее_слово_названо(self):
        page = page_from(ARTICLE)
        state, missing = page_audit.coverage(
            page, "оплатить подписку депозитфотос в россии")
        self.assertEqual(state, page_audit.COVER_NONE)
        self.assertIn("депозитфотос", missing)

    def test_недоступная_страница_не_притворяется_проверенной(self):
        page = page_audit.load("https://biz-soft.pro/blog/нет-такой", "blog")
        self.assertFalse(page.available)
        self.assertIn("не найден", page.scope_note)


class TestActions(unittest.TestCase):
    def setUp(self):
        self.page = page_from(ARTICLE)
        self.actions, self.done, self.skip = rec.build(package(), self.page)

    def test_каждое_действие_отвечает_на_четыре_вопроса(self):
        """Что, где, почему и как принять — иначе поручить нельзя."""
        self.assertTrue(self.actions)
        for action in self.actions:
            self.assertTrue(action.what.strip(), action)
            self.assertTrue(action.where.strip(), action)
            self.assertTrue(action.why.strip(), action)
            self.assertTrue(action.check.strip(), action)

    def test_не_советует_сделанное(self):
        """Ссылки на товар и вендора уже стоят — добавлять их не предлагаем."""
        тексты = " ".join(a.what for a in self.actions)
        self.assertNotIn("коммерческий переход", тексты)
        self.assertTrue(any("коммерческая связка на месте" in d for d in self.done))

    def test_отсутствие_связки_превращается_в_действие(self):
        без_ссылок = page_from(ARTICLE.replace(
            "[каталоге](/catalog),\nкарточка [подписки](/product/deposit-unl-year) "
            "и страница [вендора](/vendors/depositphotos)", "каталоге"))
        actions, done, _ = rec.build(package(), без_ссылок)
        self.assertTrue(any("коммерческий переход" in a.what for a in actions))

    def test_нет_общих_формулировок(self):
        """«Улучшить SEO» нельзя ни поручить, ни принять."""
        запрещено = ("улучшить", "усилить", "оптимизировать", "проработать",
                     "поработать над")
        for action in self.actions:
            for слово in запрещено:
                self.assertNotIn(слово, action.what.lower(), action.what)

    def test_действие_называет_конкретные_фразы(self):
        первое = self.actions[0]
        self.assertTrue(первое.steps)
        self.assertTrue(any("подписку" in s for s in первое.steps))

    def test_недоступная_страница_даёт_ручную_проверку_а_не_совет(self):
        page = page_audit.load("https://biz-soft.pro/blog/нет-такой", "blog")
        actions, done, _ = rec.build(package(), page)
        self.assertEqual(len(actions), 1)
        self.assertIn("Проверить вручную", actions[0].what)
        self.assertIn("не хранится в репозитории", actions[0].why)

    def test_не_рекомендуем_объясняет_причину(self):
        self.assertTrue(self.skip)
        self.assertTrue(any("ссылочный профиль" in s for s in self.skip))

    def test_переобход_идёт_последним_и_с_конкретным_url(self):
        последнее = self.actions[-1]
        self.assertEqual(последнее.kind, "индексация")
        self.assertTrue(any("biz-soft.pro/blog/test-article" in s
                            for s in последнее.steps))

    def test_заголовок_пакета_это_первое_действие(self):
        pkg = package()
        headline = rec.headline(self.actions, pkg)
        self.assertEqual(headline, self.actions[0].what)
        self.assertNotEqual(headline, pkg["action"])


class TestGeoAndPlural(unittest.TestCase):
    def test_гео_действие_только_при_разрыве(self):
        близко = rec.geo_gap(["запрос"], {"запрос": (5, 6)})
        далеко = rec.geo_gap(["запрос"], {"запрос": (5, 12)})
        self.assertIsNone(близко)
        self.assertEqual(далеко["разрыв_позиций"], 7.0)

    def test_гео_не_считается_по_одному_региону(self):
        self.assertIsNone(rec.geo_gap(["запрос"], {"запрос": (5, None)}))

    def test_числительные_согласованы(self):
        self.assertEqual(rec.queries_word(1), "1 запрос")
        self.assertEqual(rec.queries_word(2), "2 запроса")
        self.assertEqual(rec.queries_word(5), "5 запросов")
        self.assertEqual(rec.queries_word(11), "11 запросов")
        self.assertEqual(rec.queries_word(21), "21 запрос")


if __name__ == "__main__":
    unittest.main()
