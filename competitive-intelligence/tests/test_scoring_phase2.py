"""Тесты Threat, Opportunity, интента и Strike List (Phase 2)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from attack_engine import strike_list  # noqa: E402
from discovery import serp_source  # noqa: E402
from scoring import intent, opportunity, threat  # noqa: E402


class TestIntent(unittest.TestCase):
    def test_коммерческий_растёт_с_маркерами(self):
        слабый = intent.commercial_intent("figma")
        средний = intent.commercial_intent("figma купить")
        сильный = intent.commercial_intent("купить figma цена")
        self.assertEqual(слабый, 0.0)
        self.assertLess(средний, сильный)

    def test_информационный_запрос_понижает_коммерческий(self):
        прямой = intent.commercial_intent("купить figma лицензия")
        вопрос = intent.commercial_intent("как купить figma лицензия")
        self.assertLess(вопрос, прямой)

    def test_b2b_сильные_маркеры_дают_максимум(self):
        self.assertEqual(intent.b2b_intent("оплата по счёту для юридических лиц"), 1.0)

    def test_слабые_маркеры_не_дают_полного_b2b(self):
        """«business» часто про название тарифа, а не про покупателя."""
        self.assertLess(intent.b2b_intent("github copilot business"), 0.5)

    def test_некоммерческий_запрос(self):
        self.assertEqual(intent.commercial_intent("figma это что"), 0.0)
        self.assertEqual(intent.b2b_intent("figma обзор"), 0.0)

    def test_брендовый_запрос_распознан(self):
        """Бренд исключается из конкурентного Share (раздел 6 задания)."""
        self.assertTrue(intent.is_branded("bizsoft отзывы"))
        self.assertFalse(intent.is_branded("купить figma"))

    def test_разбор_объясним(self):
        d = intent.describe("купить figma юридическим лицам с ндс")
        self.assertIn("купить", d["маркеры_коммерческие"])
        self.assertTrue(d["маркеры_b2b"])


class TestThreat(unittest.TestCase):
    """Версия 1.1.0: три ортогональных компонента вместо тройного учёта позиций."""

    def card(self, **kw):
        base = {"домен": "x.ru", "доля": 0.10, "топ3": 40, "топ10": 60}
        base.update(kw)
        return base

    def test_больше_доля_больше_угроза(self):
        мал = threat.score(self.card(доля=0.02), queries_total=150).score
        вел = threat.score(self.card(доля=0.12), queries_total=150).score
        self.assertGreater(вел, мал)

    def test_позиции_не_учитываются_трижды(self):
        """Дефект 1.0.0: доля, ТОП-3 и ТОП-10 давали баллы за одно и то же.

        Теперь компонентов два (присутствие и превосходство над нами), и
        отдельного слагаемого за ТОП-10 нет.
        """
        t = threat.score(self.card(), queries_total=150)
        self.assertIn("присутствие", t.breakdown)
        self.assertIn("превосходство_над_нами", t.breakdown)
        self.assertNotIn("присутствие_топ10", t.breakdown)

    def test_без_шести_измерений_динамики_нет(self):
        """Динамика требует того же окна, что и общий фильтр значимости."""
        t = threat.score(self.card(), history=[0.05] * 5, queries_total=150)
        self.assertEqual(t.confidence, "LOW")
        self.assertNotIn("динамика", t.breakdown)
        self.assertIn("динамика требует", t.explanation)

    def test_с_шестью_измерениями_динамика_считается(self):
        history = [0.05, 0.05, 0.05, 0.09, 0.09, 0.09]
        t = threat.score(self.card(доля=0.09), history=history, queries_total=150)
        self.assertEqual(t.confidence, "MEDIUM")
        self.assertIn("динамика", t.breakdown)
        self.assertGreater(t.breakdown["динамика"], 0)

    def test_динамика_сглажена_медианой(self):
        """Одиночный выброс не должен раздувать угрозу."""
        ровно = [0.05] * 3 + [0.06] * 3
        с_выбросом = [0.05] * 3 + [0.06, 0.30, 0.06]
        a = threat.score(self.card(), history=ровно, queries_total=150)
        b = threat.score(self.card(), history=с_выбросом, queries_total=150)
        self.assertEqual(a.breakdown["динамика"], b.breakdown["динамика"])

    def test_превосходство_считается_по_запросам_выше_нас(self):
        свой = threat.score(self.card(), queries_total=150, above_us=100)
        чужой = threat.score(self.card(), queries_total=150, above_us=10)
        self.assertGreater(свой.breakdown["превосходство_над_нами"],
                           чужой.breakdown["превосходство_над_нами"])

    def test_приближение_помечается(self):
        """Если счётчик «выше нас» не передан, это указывается явно."""
        t = threat.score(self.card(), queries_total=150)
        self.assertIn("приближение", t.explanation)

    def test_потолок_сто(self):
        t = threat.score(self.card(доля=0.9, топ3=150, топ10=150),
                         history=[0.0] * 3 + [0.9] * 3,
                         queries_total=150, above_us=150)
        self.assertLessEqual(t.score, 100)

    def test_ранжирование_по_убыванию(self):
        cards = [self.card(домен="a.ru", доля=0.02),
                 self.card(домен="b.ru", доля=0.12)]
        ranked = threat.rank(cards, queries_total=150)
        self.assertEqual(ranked[0][0]["домен"], "b.ru")


class TestOpportunity(unittest.TestCase):
    def test_режим_деградации_включён_без_vulnerability(self):
        o = opportunity.score(commercial=1.0, b2b=1.0, our_position=5,
                              has_page=True, frequency=500)
        self.assertTrue(o.degraded)
        self.assertEqual(o.confidence, "MEDIUM")
        self.assertIn("Vulnerability недоступен", " ".join(o.notes))

    def test_confidence_не_выше_medium_при_деградации(self):
        """Требование раздела 12: неполный скоринг не даёт HIGH."""
        o = opportunity.score(commercial=1.0, b2b=1.0, our_position=4,
                              has_page=True, frequency=100000)
        self.assertNotEqual(o.confidence, "HIGH")

    def test_близость_позиции(self):
        близко = opportunity.proximity_factor(4)
        далеко = opportunity.proximity_factor(18)
        нет = opportunity.proximity_factor(None)
        self.assertEqual(близко, 1.0)
        self.assertLess(далеко, близко)
        self.assertEqual(нет, 0.0)

    def test_вне_топ20_близость_ноль(self):
        self.assertEqual(opportunity.proximity_factor(25), 0.0)

    def test_шкала_спроса_зависит_от_источника(self):
        """Сотня показов и сотня частотности — разный спрос."""
        по_показам = opportunity.demand_factor(100, "webmaster")
        по_частотности = opportunity.demand_factor(100, "wordstat")
        self.assertGreater(по_показам, по_частотности)

    def test_неизвестный_спрос_не_подменяется_средним(self):
        """Дефект 1.0.0: незнание превращалось в 0,5 — то есть в «средний
        спрос», хотя за ним могло стоять и 5 запросов, и 50 000."""
        self.assertIsNone(opportunity.demand_factor(None))

    def test_отсутствие_признака_нормализует_веса_и_снижает_уверенность(self):
        со_спросом = opportunity.score(commercial=1.0, b2b=1.0, our_position=5,
                                       has_page=True, frequency=500)
        без_спроса = opportunity.score(commercial=1.0, b2b=1.0, our_position=5,
                                       has_page=True, frequency=None)
        self.assertIn("demand", без_спроса.missing)
        self.assertEqual(без_спроса.confidence, "LOW")
        self.assertEqual(со_спросом.confidence, "MEDIUM")

    def test_нет_двойного_счёта_спроса_и_интента(self):
        """Дефект 1.0.0: revenue считался как спрос × интент и входил
        отдельным фактором, из-за чего оба признака учитывались дважды."""
        o = opportunity.score(commercial=1.0, b2b=1.0, our_position=5,
                              has_page=True, frequency=500)
        self.assertNotIn("revenue", o.breakdown)
        self.assertIn("экономический фактор не участвует", " ".join(o.notes))

    def test_страница_в_топ3_почти_нечего_улучшать(self):
        верх = opportunity.page_improvement_factor(2, True)
        середина = opportunity.page_improvement_factor(8, True)
        self.assertLess(верх, середина)

    def test_без_страницы_потенциал_ниже_чем_у_слабой(self):
        нет = opportunity.page_improvement_factor(None, False)
        слабая = opportunity.page_improvement_factor(8, True)
        self.assertLess(нет, слабая)


def row(query, top, region="213"):
    return serp_source.SerpRow(date="2026-08-30", query=query, region=region, top=top)


class TestStrikeList(unittest.TestCase):
    def setUp(self):
        self.hosts = set()

    def test_кандидат_найден(self):
        rows = [row("купить figma юридическим лицам", [
            {"domain": "raketapay.ru", "url": "https://raketapay.ru/f"},
            {"domain": "dzen.ru", "url": "https://dzen.ru/a"},
            {"domain": "x.ru", "url": "https://x.ru"},
            {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/vendors/figma"},
        ])]
        cands = strike_list.build(rows, vendor_hosts=self.hosts)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0].our_position, 4)
        self.assertEqual(cands[0].rival_domain, "raketapay.ru")
        self.assertEqual(cands[0].attack_id, "ATT-001")

    def test_топ3_не_кандидат(self):
        """Где мы уже наверху, отбирать нечего."""
        rows = [row("купить figma юрлицу", [
            {"domain": "raketapay.ru", "url": "https://raketapay.ru/f"},
            {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/f"},
        ])]
        self.assertEqual(strike_list.build(rows, vendor_hosts=self.hosts), [])

    def test_маркетплейсы_выше_это_конкуренция_за_клик(self):
        """Версия 1.1.0: раньше такой запрос выпадал из поля зрения целиком.

        Сделку маркетплейс у нас не заберёт, а переход заберёт — и это тоже
        потеря. Теперь запрос остаётся кандидатом с пометкой вида конкуренции.
        """
        rows = [row("купить figma юрлицу", [
            {"domain": "ozon.ru", "url": "https://ozon.ru/x"},
            {"domain": "dzen.ru", "url": "https://dzen.ru/a"},
            {"domain": "avito.ru", "url": "https://avito.ru/x"},
            {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/f"},
        ])]
        cands = strike_list.build(rows, vendor_hosts=self.hosts)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0].competition_kind, "клик")

    def test_деловой_конкурент_важнее_площадки_за_клик(self):
        """Если выше есть и площадка, и продавец, — на кону сделка."""
        rows = [row("купить figma юрлицу", [
            {"domain": "dzen.ru", "url": "https://dzen.ru/a"},
            {"domain": "raketapay.ru", "url": "https://raketapay.ru/f"},
            {"domain": "x.ru", "url": "https://x.ru"},
            {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/f"},
        ])]
        cand = strike_list.build(rows, vendor_hosts=self.hosts)[0]
        self.assertEqual(cand.competition_kind, "сделка")
        self.assertEqual(cand.rival_domain, "raketapay.ru")

    def test_сделка_приоритетнее_клика_при_сортировке(self):
        rows = [
            row("оплата canva юрлицом по счёту", [
                {"domain": "ozon.ru", "url": "https://ozon.ru/x"},
                {"domain": "dzen.ru", "url": "https://dzen.ru/a"},
                {"domain": "avito.ru", "url": "https://avito.ru/x"},
                {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/c"},
            ]),
            row("figma тариф", [
                {"domain": "raketapay.ru", "url": "https://raketapay.ru/f"},
                {"domain": "dzen.ru", "url": "https://dzen.ru/a"},
                {"domain": "x.ru", "url": "https://x.ru"},
                {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/f"},
            ]),
        ]
        cands = strike_list.build(rows, vendor_hosts=self.hosts)
        self.assertEqual(cands[0].competition_kind, "сделка")

    def test_брендовый_запрос_исключён(self):
        rows = [row("bizsoft купить figma", [
            {"domain": "raketapay.ru", "url": "https://raketapay.ru/f"},
            {"domain": "dzen.ru", "url": "https://dzen.ru/a"},
            {"domain": "x.ru", "url": "https://x.ru"},
            {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/f"},
        ])]
        self.assertEqual(strike_list.build(rows, vendor_hosts=self.hosts), [])

    def test_некоммерческий_запрос_исключён(self):
        rows = [row("figma это что такое", [
            {"domain": "raketapay.ru", "url": "https://raketapay.ru/f"},
            {"domain": "dzen.ru", "url": "https://dzen.ru/a"},
            {"domain": "x.ru", "url": "https://x.ru"},
            {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/f"},
        ])]
        self.assertEqual(strike_list.build(rows, vendor_hosts=self.hosts), [])

    def test_чужой_регион_исключён(self):
        rows = [row("купить figma юрлицу", [
            {"domain": "raketapay.ru", "url": "https://raketapay.ru/f"},
            {"domain": "dzen.ru", "url": "https://dzen.ru/a"},
            {"domain": "x.ru", "url": "https://x.ru"},
            {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/f"},
        ], region="2")]
        self.assertEqual(strike_list.build(rows, vendor_hosts=self.hosts), [])

    def test_сортировка_по_opportunity(self):
        rows = [
            row("оплата canva для юридических лиц по счёту", [
                {"domain": "raketapay.ru", "url": "https://raketapay.ru/c"},
                {"domain": "dzen.ru", "url": "https://dzen.ru/a"},
                {"domain": "x.ru", "url": "https://x.ru"},
                {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/c"},
            ]),
            row("figma тариф", [
                {"domain": "raketapay.ru", "url": "https://raketapay.ru/f"},
                {"domain": "dzen.ru", "url": "https://dzen.ru/a"},
                {"domain": "x.ru", "url": "https://x.ru"},
                {"domain": "y.ru", "url": "https://y.ru"},
                {"domain": "z.ru", "url": "https://z.ru"},
                {"domain": "w.ru", "url": "https://w.ru"},
                {"domain": "v.ru", "url": "https://v.ru"},
                {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/f"},
            ]),
        ]
        cands = strike_list.build(rows, vendor_hosts=self.hosts)
        self.assertEqual(len(cands), 2)
        self.assertGreaterEqual(cands[0].opportunity, cands[1].opportunity)
        self.assertEqual(cands[0].attack_id, "ATT-001")


class TestMaturityModes(unittest.TestCase):
    """Оценки из разных режимов зрелости несравнимы между собой.

    Замечание третьей рецензии: без разделения шкал одно и то же положение
    конкурента давало 32 «из 70» и 62 «из 100» — руководитель увидел бы
    удвоение угрозы при неизменной доле.
    """

    def card(self):
        return {"домен": "x.ru", "доля": 0.08, "топ3": 40, "топ10": 60}

    def test_базовый_режим_ограничен_семьюдесятью(self):
        t = threat.score({"домен": "x.ru", "доля": 0.9, "топ3": 150,
                          "топ10": 150}, queries_total=150, above_us=150)
        self.assertEqual(t.mode, threat.MODE_BASE)
        self.assertEqual(t.scale_max, 70)
        self.assertLessEqual(t.score, 70)

    def test_полный_режим_до_ста(self):
        t = threat.score(self.card(), history=[0.05] * 3 + [0.08] * 3,
                         queries_total=150, above_us=40)
        self.assertEqual(t.mode, threat.MODE_FULL)
        self.assertEqual(t.scale_max, 100)

    def test_режимы_помечены_как_несравнимые(self):
        base = threat.score(self.card(), queries_total=150, above_us=40)
        full = threat.score(self.card(), history=[0.05] * 3 + [0.08] * 3,
                            queries_total=150, above_us=40)
        self.assertNotEqual(base.comparable_key, full.comparable_key)

    def test_шкала_указана_в_объяснении(self):
        base = threat.score(self.card(), queries_total=150)
        self.assertIn("0–70", base.explanation)

    def test_opportunity_режим_в_оценке(self):
        degraded = opportunity.score(commercial=1.0, b2b=1.0, our_position=5,
                                     has_page=True, frequency=500)
        full = opportunity.score(commercial=1.0, b2b=1.0, our_position=5,
                                 has_page=True, frequency=500, vulnerability=0.5)
        self.assertEqual(degraded.mode, opportunity.MODE_DEGRADED)
        self.assertEqual(full.mode, opportunity.MODE_FULL)
        self.assertNotEqual(degraded.comparable_key, full.comparable_key)

    def test_отсутствующие_факторы_входят_в_ключ_сравнимости(self):
        со_спросом = opportunity.score(commercial=1.0, b2b=1.0, our_position=5,
                                       has_page=True, frequency=500)
        без_спроса = opportunity.score(commercial=1.0, b2b=1.0, our_position=5,
                                       has_page=True, frequency=None)
        self.assertNotEqual(со_спросом.comparable_key, без_спроса.comparable_key)


class TestSignificantParticipant(unittest.TestCase):
    """Значимый участник выдачи — машинно проверяемое условие."""

    def test_технические_домены_поисковика_не_участники(self):
        self.assertFalse(strike_list.is_significant("yandex.ru", set()))
        self.assertFalse(strike_list.is_significant("ya.ru", set()))

    def test_наш_домен_не_участник(self):
        self.assertFalse(strike_list.is_significant("biz-soft.pro", set()))

    def test_повтор_домена_не_удваивает_конкуренцию(self):
        seen = {"raketapay.ru"}
        self.assertFalse(strike_list.is_significant("raketapay.ru", seen))
        self.assertTrue(strike_list.is_significant("pipl.io", seen))

    def test_обычный_домен_значим(self):
        self.assertTrue(strike_list.is_significant("syssoft.ru", set()))


if __name__ == "__main__":
    unittest.main()


class TestМаркерыБезПерекрытий(unittest.TestCase):
    """Одно слово — один голос.

    Маркеры интента — подстроки, и часть вложена друг в друга: «цен» целиком
    лежит внутри «лицензи». Прямой подсчёт давал слову «лицензия» два голоса
    из двух нужных для насыщения, и «лицензия adobe» получала полный
    коммерческий интент 1.0 — больше, чем «тариф recraft» с его 0.7.
    """

    def test_вложенный_маркер_не_добавляет_голос(self):
        from scoring import intent
        self.assertEqual(0.7, intent.commercial_intent("лицензия adobe"))

    def test_два_разных_маркера_насыщают(self):
        from scoring import intent
        self.assertEqual(1.0, intent.commercial_intent("купить лицензию"))

    def test_один_маркер_даёт_семь_десятых(self):
        from scoring import intent
        self.assertEqual(0.7, intent.commercial_intent("тариф recraft"))

    def test_отбор_маркеров_общий_а_не_точечный(self):
        from scoring import intent
        self.assertEqual(["длинный"],
                         intent._hits("длинный", ("длин", "длинный", "нет")))

    def test_мёртвый_b2b_маркер_убран(self):
        """«корпоративн» всегда перекрыт сильным «корпоратив»."""
        from scoring import intent
        self.assertNotIn("корпоративн", intent.B2B_WEAK)
        self.assertIn("корпоратив", intent.B2B_STRONG)

    def test_сильный_b2b_маркер_работает(self):
        from scoring import intent
        self.assertEqual(0.7, intent.b2b_intent("корпоративные лицензии"))
