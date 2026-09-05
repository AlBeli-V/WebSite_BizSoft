"""Достоверность плана работ: четыре причины, по которым отчёт советовал сделанное.

Разбор отчёта за 04.09.2026 по замечанию руководителя. Проверка показала, что
пять из восемнадцати утверждений «не хватает слов» ложны, а пять пакетов из
девятнадцати стоят на страницах, написанных накануне. Причины оказались
разными, и каждая закрыта отдельно:

  1. сравнение слов по обрезке фиксированной длины давало три разные основы
     одному корню («оплата», «оплатой», «оплатить»);
  2. проверка заголовка искала слово подстрокой, вообще без учёта формы;
  3. мораторий срабатывал только на собственные поручения контура, а работа
     по тикетам и решениям руководителя была для него невидима;
  4. бренд конкурента из запроса превращался в требование вписать чужое
     название в свой текст.

Каждый тест ниже держит одно из этих обещаний.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from attack_engine import page_audit  # noqa: E402
from attack_engine import recommendations as rec  # noqa: E402
from experiments import page_changes  # noqa: E402


def page(**over) -> page_audit.PageContent:
    args = dict(url="/blog/x", kind="blog", available=True, title="",
                headings=[], faq_questions=[], body="", internal_links=[])
    args.update(over)
    return page_audit.PageContent(**args)


class TestWordForms(unittest.TestCase):
    """Формы одного слова — одно слово."""

    def test_оплата_и_оплатить_одно_слово(self):
        self.assertTrue(page_audit.same_word("оплатить", "оплата"))
        self.assertTrue(page_audit.same_word("оплатить", "оплаты"))
        self.assertTrue(page_audit.same_word("оплата", "оплатой"))

    def test_россии_и_россиян_одно_слово(self):
        self.assertTrue(page_audit.same_word("россиян", "россии"))

    def test_короткие_формы_сходятся(self):
        self.assertTrue(page_audit.same_word("лицом", "лицам"))
        self.assertTrue(page_audit.same_word("цена", "цены"))

    def test_разные_корни_не_сливаются(self):
        self.assertFalse(page_audit.same_word("покупка", "подписка"))
        self.assertFalse(page_audit.same_word("тариф", "трафик"))
        self.assertFalse(page_audit.same_word("мо", "москва"))

    def test_страница_с_формой_слова_не_требует_дописывания(self):
        # Ровно случай /vendors/depositphotos из отчёта за 04.09: на странице
        # одиннадцать вхождений «оплата» и «оплаты», а отчёт требовал
        # дописать «оплатить».
        p = page(body="Оплата в рублях, оплаты по счёту для юридических лиц")
        state, missing = page_audit.coverage(p, "как оплатить depositphotos")
        self.assertNotIn("оплатить", missing)

    def test_подстрока_внутри_другого_слова_вхождением_не_считается(self):
        # Прежняя проверка искала основу подстрокой по всему тексту: основа
        # «счет» находилась внутри «расчетный», и запрос про счёт считался
        # раскрытым страницей, где слова «счёт» нет.
        p = page(body="расчетный период и условия сотрудничества")
        state, missing = page_audit.coverage(p, "выставление счета компании")
        self.assertIn("счета", missing)

    def test_спорная_пара_решается_в_пользу_пропуска(self):
        # Порог сознательно мягкий: лишнее поручение дороже пропущенного.
        # «картой» и «карточки» считаются одним словом, и поручение не выдаётся.
        self.assertTrue(page_audit.same_word("картой", "карточки"))


class TestTitleCheck(unittest.TestCase):
    """Заголовок проверяется по формам слова, а не подстрокой."""

    def test_заголовок_с_другой_формой_слова_не_пересобирается(self):
        p = page(title="Как оплатить CorelDRAW для юридического лица в России",
                 body="оплата coreldraw для россиян")
        package = {"url": "https://biz-soft.pro/blog/x", "page_kind": "blog",
                   "queries": ["оплата coreldraw для россиян"],
                   "position_best": 6, "position_worst": 8, "rivals": []}
        actions, done, skip = rec.build(package, p)
        self.assertNotIn("мета", [a.kind for a in actions])

    def test_заголовок_без_ведущего_запроса_пересобирается(self):
        p = page(title="Графический редактор для дизайнеров",
                 body="оплата coreldraw для россиян тариф")
        package = {"url": "https://biz-soft.pro/blog/x", "page_kind": "blog",
                   "queries": ["оплата coreldraw для россиян"],
                   "position_best": 6, "position_worst": 8, "rivals": []}
        actions, done, skip = rec.build(package, p)
        self.assertIn("мета", [a.kind for a in actions])


class TestRivalBrands(unittest.TestCase):
    """Чужой бренд не дописывается в свой текст."""

    def test_бренд_конкурента_распознаётся_через_транслитерацию(self):
        self.assertEqual(["миру"],
                         rec.rival_brand_words(["миру"], ["platipomiru.com"]))
        self.assertEqual(["плати"],
                         rec.rival_brand_words(["плати"], ["platipomiru.com"]))

    def test_обычное_слово_брендом_не_становится(self):
        self.assertEqual([], rec.rival_brand_words(["тариф", "оплата"],
                                                   ["platipomiru.com"]))

    def test_короткое_слово_к_домену_не_примеряется(self):
        # «pay» внутри raketapay.ru — не повод запрещать слово.
        self.assertEqual([], rec.rival_brand_words(["pay"], ["raketapay.ru"]))

    def test_запрос_с_брендом_конкурента_уходит_в_не_рекомендуем(self):
        p = page(body="windsurf для юридических лиц, покупка из России")
        package = {"url": "https://biz-soft.pro/blog/x", "page_kind": "blog",
                   "queries": ["windsurf pro купить плати по миру"],
                   "position_best": 8, "position_worst": 8,
                   "rivals": ["platipomiru.com"]}
        actions, done, skip = rec.build(package, p)
        self.assertTrue(any("миру" in line for line in skip))
        self.assertNotIn("текст", [a.kind for a in actions])

    def test_заголовок_пакета_называет_настоящую_причину(self):
        skip = ["«windsurf pro купить плати по миру» — не дописываем: «миру» "
                "входит в название конкурента"]
        self.assertIn("дописывать нельзя", rec.headline([], {}, skip))
        self.assertIn("уже раскрыты", rec.headline([], {}, []))


class TestPageChanges(unittest.TestCase):
    """Мораторий — по факту правки, а не по авторству поручения."""

    def setUp(self):
        self.pages = {f"/vendors/v{i}": page(url=f"/vendors/v{i}", kind="vendor",
                                             body=f"текст вендора {i}")
                      for i in range(6)}

    def test_первый_прогон_моратория_не_создаёт(self):
        state = {"страницы": {}}
        report = page_changes.update(state, self.pages, "2026-09-05")
        self.assertEqual([], report["под_мораторием_с_сегодня"])
        self.assertEqual({}, page_changes.frozen(state, "2026-09-05"))

    def test_правка_одной_страницы_снимает_её_с_поручений(self):
        state = {"страницы": {}}
        page_changes.update(state, self.pages, "2026-09-05")
        self.pages["/vendors/v0"].body = "текст вендора 0, дописан абзац"
        report = page_changes.update(state, self.pages, "2026-09-06")
        self.assertEqual(["/vendors/v0"], report["под_мораторием_с_сегодня"])
        self.assertIn("/vendors/v0", page_changes.frozen(state, "2026-09-06"))

    def test_мораторий_истекает(self):
        state = {"страницы": {}}
        page_changes.update(state, self.pages, "2026-09-05")
        self.pages["/vendors/v0"].body = "иначе"
        page_changes.update(state, self.pages, "2026-09-06")
        self.assertEqual({}, page_changes.frozen(state, "2026-09-30"))

    def test_правка_шаблона_не_обнуляет_очередь(self):
        # Шаблон входит в проверяемый текст всех страниц типа: если бы его
        # правка ставила мораторий, очередь поручений опустела бы целиком.
        state = {"страницы": {}}
        page_changes.update(state, self.pages, "2026-09-05")
        for p in self.pages.values():
            p.body += " общий блок из шаблона"
        report = page_changes.update(state, self.pages, "2026-09-06")
        self.assertEqual(["vendor"], report["правка_шаблона"])
        self.assertEqual([], report["под_мораторием_с_сегодня"])

    def test_невидимая_аудиту_правка_поручений_не_блокирует(self):
        state = {"страницы": {}}
        page_changes.update(state, self.pages, "2026-09-05")
        report = page_changes.update(state, self.pages, "2026-09-06")
        self.assertEqual([], report["изменились"])


if __name__ == "__main__":
    unittest.main()
