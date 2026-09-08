#!/usr/bin/env python3
"""google_authority: типология топа, слабость выдачи, диагноз кластера.

Главное, что проверяется, — разделение двух диагнозов. Запрос, по которому
Яндекс держит нас в топ-10, а Google не показывает, значит разное в
зависимости от того, есть ли ранжирующая страница в индексе Google: в одном
случае работа над индексацией, в другом — над самим документом. Перепутать
их — потратить бюджет не туда.
"""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mocks  # noqa: E402

DATE = "2026-09-08"


def docs(*specs):
    """specs: ("домен", "заголовок") или просто "домен"."""
    out = []
    for s in specs:
        dom, title = s if isinstance(s, tuple) else (s, s)
        out.append({"domain": dom, "url": f"https://{dom}/page", "title": title})
    return out


class Base(unittest.TestCase):
    def setUp(self):
        self.m = mocks.load("google_authority")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = pathlib.Path(self.tmp.name)

    def write(self, name, rows):
        (self.dir / name).write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
            encoding="utf-8")


class TestClassification(Base):
    def test_domain_classes(self):
        self.assertEqual(self.m.classify_domain("biz-soft.pro"), "OURS")
        self.assertEqual(self.m.classify_domain("www.atlassian.com"), "OFFICIAL")
        self.assertEqual(self.m.classify_domain("vc.ru"), "UGC")
        self.assertEqual(self.m.classify_domain("reddit.com"), "FORUM")
        self.assertEqual(self.m.classify_domain("plati.market"), "MARKETPLACE")
        self.assertEqual(self.m.classify_domain("syssoft.ru"), "RESELLER")
        self.assertEqual(self.m.classify_domain("oplata.guru"), "INTERMEDIARY")
        # Неизвестное остаётся неизвестным, а не приписывается удобному классу.
        self.assertEqual(self.m.classify_domain("nechto-novoe.ru"), "OTHER")

    def test_document_types(self):
        self.assertEqual(
            self.m.classify_document("https://vc.ru/a", "Как оплатить Framer из России", "UGC"),
            "HOW_TO")
        self.assertEqual(
            self.m.classify_document("https://vc.ru/b", "Аналоги Figma для России", "UGC"),
            "ALTERNATIVES")
        # Маркетплейс — всегда товарная витрина, что бы ни было в заголовке.
        self.assertEqual(
            self.m.classify_document("https://plati.market/x", "Как купить", "MARKETPLACE"),
            "PRODUCT_LISTING")

    def test_query_intent(self):
        self.assertEqual(self.m.query_intent("купить heygen юридическим лицом"), "B2B_LEGAL")
        self.assertEqual(self.m.query_intent("купить подписку runway"), "BUY")
        self.assertEqual(self.m.query_intent("оплатить cloudflare"), "PAY")
        self.assertEqual(self.m.query_intent("figma аналоги"), "ALTERNATIVES")
        self.assertTrue(self.m.is_b2b("оплата postman юридическим лицом"))
        self.assertFalse(self.m.is_b2b("suno подписка"))

    def test_vendor_and_hub(self):
        self.assertEqual(self.m.query_vendor("как оплатить фреймер из россии"), "framer")
        self.assertEqual(self.m.query_vendor("claude team купить"), "anthropic")
        self.assertIsNone(self.m.query_vendor("оплата зарубежного по для юрлица"))
        self.assertEqual(self.m.VENDOR_HUB["gitlab"], "dev-tools")


class TestWeakness(Base):
    def test_ugc_serp_scores_higher_than_normal_one(self):
        ugc = self.m.weakness(docs("vc.ru", "dtf.ru", "reddit.com", "pikabu.ru",
                                   "vc.ru", "dtf.ru", "habr.com", "sostav.ru",
                                   "klerk.ru", "dzen.ru"), "купить x")
        strong = self.m.weakness(docs("atlassian.com", "syssoft.ru", "softline.ru",
                                      "migsoft.ru", "allsoft.ru", "vc.ru",
                                      "softmagazin.ru", "itshop.ru", "iesoft.ru",
                                      "ml-soft.ru"), "купить x")
        self.assertGreater(ugc["score"], strong["score"])
        self.assertIn("нет официального сайта вендора", ugc["reasons"])

    def test_b2b_intent_without_b2b_documents(self):
        w = self.m.weakness(docs("vc.ru", "dtf.ru", "plati.market", "ggsel.net",
                                 "funpay.com", "pikabu.ru", "reddit.com",
                                 "playerok.com", "dzen.ru", "habr.com"),
                            "купить x юридическим лицом")
        self.assertIn("запрос про юрлицо, а документов для юрлица в топе нет",
                      w["reasons"])

    def test_empty_serp(self):
        self.assertEqual(self.m.weakness([], "x")["score"], 0)


class TestBuild(Base):
    def setUp(self):
        super().setUp()
        self.write(f"{DATE}-serp-google.jsonl", [
            {"query": "оплата framer юридическим лицом", "region": "2643",
             "top": docs("vc.ru", "dtf.ru", "oplata.guru", "raketapay.ru",
                         "reddit.com", "pikabu.ru", "habr.com", "sostav.ru",
                         "klerk.ru", "plati.market")},
            {"query": "купить artlist", "region": "2643",
             "top": docs("ggsel.net", "plati.market", "vc.ru", "dtf.ru",
                         "syssoft.ru", "migsoft.ru", "artlist.io", "habr.com",
                         "oplata.guru", "funpay.com")},
        ])
        self.write(f"{DATE}-serp.jsonl", [
            {"query": "оплата framer юридическим лицом", "region": "213",
             "top": docs("raketapay.ru") + [
                 {"domain": "biz-soft.pro",
                  "url": "https://biz-soft.pro/blog/kak-oplatit-framer-dlya-yurlica",
                  "title": "Framer"}]},
            {"query": "купить artlist", "region": "213",
             "top": [{"domain": "biz-soft.pro",
                      "url": "https://biz-soft.pro/vendors/artlist",
                      "title": "Artlist"}] + docs("ggsel.net")},
        ])

    def test_gap_counted(self):
        a = self.m.build(self.dir, DATE)
        self.assertEqual(a["queries_google"], 2)
        self.assertEqual(a["gap_queries"], 2)
        self.assertEqual(a["google_top10"], 0)
        self.assertEqual(a["yandex_top10"], 2)
        # Наш домен не попадает в список конкурентов.
        self.assertNotIn("biz-soft.pro", [r["domain"] for r in a["link_gap"]])

    def test_link_gap_marks_google_only_domains(self):
        a = self.m.build(self.dir, DATE)
        gap = {r["domain"]: r for r in a["link_gap"]}
        self.assertTrue(gap["vc.ru"]["google_only"])
        self.assertFalse(gap["ggsel.net"]["google_only"])

    def test_content_map_separates_two_diagnoses(self):
        a = self.m.build(self.dir, DATE)
        index = {"/blog/kak-oplatit-framer-dlya-yurlica": "Discovered - currently not indexed",
                 "/vendors/artlist": "Submitted and indexed"}
        cm = self.m.content_map(a, self.dir, DATE, index)
        by = {c["cluster"]: c for c in cm["clusters"]}
        self.assertIn("вне индекса Google", by["framer"]["diagnosis"])
        self.assertIn("индексация", by["framer"]["action"])
        self.assertEqual(by["artlist"]["diagnosis"],
                         "страница в индексе, проигрывает выдаче")
        # Тип страницы выводится из интента, а не назначается статьёй.
        self.assertEqual(by["framer"]["recommended_page_type"], "PROCUREMENT_GUIDE")
        self.assertEqual(by["artlist"]["recommended_page_type"], "COMMERCIAL_LANDING")

    def test_content_map_without_index_data(self):
        """Нет данных о покрытии — диагноз не выдумывается."""
        a = self.m.build(self.dir, DATE)
        cm = self.m.content_map(a, self.dir, DATE, {})
        self.assertEqual(cm["index_source"], "нет данных о покрытии индекса")
        for c in cm["clusters"]:
            self.assertEqual(c["google_index_state"], "не измерялась")


    def test_page_demand_counts_only_held_queries(self):
        """Спрос считается по запросам, которые страница реально держит в
        топ-10 Яндекса: остальные к потерям от отсутствия в Google не
        относятся."""
        a = self.m.build(self.dir, DATE)
        d = self.m.page_demand(a, self.dir, DATE)
        self.assertEqual(sorted(d), ["/blog/kak-oplatit-framer-dlya-yurlica",
                                     "/vendors/artlist"])
        framer = d["/blog/kak-oplatit-framer-dlya-yurlica"]
        self.assertEqual(framer["queries_held"], 1)
        self.assertEqual(framer["best_yandex_position"], 2)
        self.assertGreater(framer["weakness_avg"], 0)

    def test_page_demand_ignores_pages_outside_yandex_top10(self):
        """Страница на 11-й позиции Яндекса спроса не удерживает."""
        self.write(f"{DATE}-serp.jsonl", [
            {"query": "оплата framer юридическим лицом", "region": "213",
             "top": docs(*[f"d{i}.ru" for i in range(10)]) + [
                 {"domain": "biz-soft.pro",
                  "url": "https://biz-soft.pro/blog/kak-oplatit-framer-dlya-yurlica",
                  "title": "Framer"}]},
        ])
        a = self.m.build(self.dir, DATE)
        self.assertEqual(self.m.page_demand(a, self.dir, DATE), {})

    def test_demand_by_path_is_silent_without_google_slice(self):
        """Потребитель приоритета не должен падать из-за отсутствия среза:
        без него надбавка просто не начисляется."""
        (self.dir / f"{DATE}-serp-google.jsonl").unlink()
        self.assertEqual(self.m.demand_by_path(self.dir, self.dir, DATE), {})

    def test_no_second_crawl_queue(self):
        """Очередь на обход одна — GIPS в google_gap.py (решение 08.09.2026).
        Второй список «что подавать первым» здесь не заводится."""
        self.assertFalse(hasattr(self.m, "crawl_queue"))


if __name__ == "__main__":
    unittest.main()
