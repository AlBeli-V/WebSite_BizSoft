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
    def card(self, **kw):
        base = {"домен": "x.ru", "доля": 0.10, "топ3": 40, "топ10": 60}
        base.update(kw)
        return base

    def test_больше_доля_больше_угроза(self):
        мал = threat.score(self.card(доля=0.02), queries_total=150).score
        вел = threat.score(self.card(доля=0.12), queries_total=150).score
        self.assertGreater(вел, мал)

    def test_без_истории_confidence_low(self):
        """Неполный расчёт не выдаётся за полный."""
        t = threat.score(self.card(), queries_total=150)
        self.assertEqual(t.confidence, "LOW")
        self.assertNotIn("рост_доли", t.breakdown)
        self.assertIn("динамика недоступна", t.explanation)

    def test_с_историей_учитывается_рост(self):
        t = threat.score(self.card(доля=0.13), previous=self.card(доля=0.10),
                         queries_total=150)
        self.assertEqual(t.confidence, "MEDIUM")
        self.assertIn("рост_доли", t.breakdown)
        self.assertGreater(t.breakdown["рост_доли"], 0)

    def test_потолок_сто(self):
        t = threat.score(self.card(доля=0.9, топ3=150, топ10=150),
                         previous=self.card(доля=0.0), queries_total=150)
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

    def test_неизвестный_спрос_нейтрален(self):
        self.assertEqual(opportunity.demand_factor(None), 0.5)

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

    def test_только_маркетплейсы_выше_не_кандидат(self):
        """С B2C мы не конкурируем за сделку."""
        rows = [row("купить figma юрлицу", [
            {"domain": "ozon.ru", "url": "https://ozon.ru/x"},
            {"domain": "dzen.ru", "url": "https://dzen.ru/a"},
            {"domain": "avito.ru", "url": "https://avito.ru/x"},
            {"domain": "biz-soft.pro", "url": "https://biz-soft.pro/f"},
        ])]
        self.assertEqual(strike_list.build(rows, vendor_hosts=self.hosts), [])

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


if __name__ == "__main__":
    unittest.main()
