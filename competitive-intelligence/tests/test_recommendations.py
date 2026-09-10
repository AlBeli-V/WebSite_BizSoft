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


class TestGuardsAndSystemic(unittest.TestCase):
    """Уроки первого выполненного объёма работ (01.09.2026).

    Контур предлагал дописать в описание Postman слово «москва», в описание
    Depositphotos — «недорого», а на карточку товара — латинское название,
    которое и так стоит в её заголовке из Directus. И двадцать раз предлагал
    дописать одно и то же слово в двадцать разных описаний вместо одной
    правки шаблона.
    """

    def setUp(self):
        self.page = page_from(ARTICLE)

    def test_оценочное_слово_не_становится_поручением(self):
        pkg = package(queries=["недорого оплатить подписку figma"])
        actions, done, skip = rec.build(pkg, self.page)
        тексты = " ".join(a.what for a in actions)
        self.assertNotIn("недорого", тексты)
        self.assertTrue(any("недорого" in s and "оценочное" in s for s in skip))

    def test_город_не_дописывается_в_текст(self):
        pkg = package(queries=["москва figma оплата подписки"])
        actions, done, skip = rec.build(pkg, self.page)
        self.assertTrue(any("москва" in s and "город" in s for s in skip))

    def test_латинское_слово_на_карточке_проверяют_а_не_дописывают(self):
        """Название товара приходит из Directus и в проверку не попадает."""
        card = page_audit.PageContent(
            url="https://biz-soft.pro/product/ghcopilot-business",
            kind="product", available=True, body="как купить подписку")
        pkg = package(url=card.url, page_kind="product",
                      queries=["github copilot business купить"])
        actions, done, skip = rec.build(pkg, card)
        self.assertTrue(any("Directus" in s and "проверить" in s for s in skip))
        self.assertFalse(any("github" in a.what.lower() for a in actions))

    def test_общая_нехватка_становится_правкой_шаблона(self):
        """Три страницы одного типа с одним пробелом — это шаблон, а не текст."""
        pages, packages = {}, []
        for i in range(3):
            url = f"https://biz-soft.pro/vendors/v{i}"
            pages[url] = page_audit.PageContent(
                url=url, kind="vendor", available=True,
                body=f"Vendor{i} — инструмент для студий.")
            packages.append(package(package_id=f"WP-0{i}", url=url,
                                    page_kind="vendor",
                                    queries=[f"vendor{i} аккаунт оплата"]))
        systemic, words = rec.systemic_actions(packages, pages)
        self.assertEqual(len(systemic), 1)
        self.assertIn("аккаунт", systemic[0].what)
        self.assertIn("VendorLanding.astro", systemic[0].where)
        self.assertIn("аккаунт", words["vendor"])

    def test_слово_из_шаблонной_правки_не_дублируется_в_поручении(self):
        url = "https://biz-soft.pro/vendors/v1"
        page = page_audit.PageContent(url=url, kind="vendor", available=True,
                                      body="Vendor1 — инструмент для студий.")
        pkg = package(url=url, page_kind="vendor", queries=["vendor1 аккаунт"])
        actions, done, skip = rec.build(pkg, page, template_words={"аккаунт"})
        self.assertTrue(any("системной правкой" in d for d in done))
        self.assertFalse(any("аккаунт" in a.what for a in actions))

    def test_редкая_нехватка_остаётся_правкой_страницы(self):
        """Одна страница — это её текст, а не шаблон: порог не достигнут."""
        url = "https://biz-soft.pro/vendors/v1"
        pages = {url: page_audit.PageContent(url=url, kind="vendor",
                                             available=True,
                                             body="Vendor1 — инструмент.")}
        packages = [package(url=url, page_kind="vendor",
                            queries=["vendor1 уникальноеслово"])]
        systemic, words = rec.systemic_actions(packages, pages)
        self.assertEqual(systemic, [])


if __name__ == "__main__":
    unittest.main()


class TestСтопСловаПоручений(unittest.TestCase):
    """Дефекты 13 и 14: слова, которые нельзя дописывать в свой текст.

    Найдены сплошным разбором ТЗ за 10.09.2026 — проверялось не по коду, а по
    тому, что контур реально предлагал написать на страницах.
    """

    def test_гео_ловится_по_основе_а_не_по_написанию(self):
        """«московская область» проходила мимо списка из точных форм."""
        from attack_engine import recommendations as r
        self.assertTrue(r.is_geo("московская"))
        self.assertTrue(r.is_geo("область"))
        self.assertTrue(r.is_geo("москва"))
        self.assertTrue(r.is_geo("мск"))
        self.assertFalse(r.is_geo("инструкция"))
        self.assertFalse(r.is_geo("vpn"))

    def test_площадка_из_запроса_не_дописывается(self):
        """«как оплатить jira ... dtf» — dtf.ru медиаплощадка, не наш текст."""
        from attack_engine import recommendations as r
        поле = {"dtf.ru", "vc.ru", "companies.rbc.ru"}
        self.assertEqual(["dtf"], r.rival_brand_words(["dtf"], None, поле))
        self.assertEqual(["vc"], r.rival_brand_words(["vc"], None, поле))

    def test_русское_написание_площадки_ловится(self):
        """«рбк» транслитерируется в «rbk», а домен — rbc.ru."""
        from attack_engine import recommendations as r
        self.assertEqual(["рбк"], r.rival_brand_words(["рбк"], None, {"companies.rbc.ru"}))

    def test_короткое_слово_ловится_точным_совпадением(self):
        """Подстрочная проверка коротких слов запрещена, точная — безопасна."""
        from attack_engine import recommendations as r
        self.assertEqual([], r.rival_brand_words(["pay"], None, {"raketapay.ru"}))
        self.assertEqual(["dtf"], r.rival_brand_words(["dtf"], None, {"dtf.ru"}))

    def test_имя_вендора_разрешено_сильнее_запрета(self):
        """Регрессия, внесённая расширением фильтра и пойманная проверкой.

        Сквоттерский домен envato-access.ru попал в поле выдачи, и
        подстрочная проверка стала глушить слово «энвато» — имя вендора, ради
        которого страница и существует.
        """
        from attack_engine import recommendations as r
        поле = {"envato-access.ru", "envato.com.ru"}
        self.assertEqual(["энвато"], r.rival_brand_words(["энвато"], None, поле))
        self.assertEqual([], r.rival_brand_words(["энвато"], None, поле,
                                                 {"envato"}))

    def test_метки_домена_без_зоны(self):
        from attack_engine import recommendations as r
        self.assertEqual({"dtf"}, r.domain_labels({"dtf.ru"}))
        self.assertEqual({"companies", "rbc"}, r.domain_labels({"companies.rbc.ru"}))
        self.assertEqual({"gitlab"}, r.domain_labels({"www.gitlab.com"}))
