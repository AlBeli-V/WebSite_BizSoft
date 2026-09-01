#!/usr/bin/env python3
"""Тесты блока «Заявки за сутки»: канал, путь клиента, сводка и деградация.

Проверяется главное свойство блока — он не выдаёт догадку за измерение.
Канал по визитам Метрики и канал по метке браузера — разной силы
утверждения, и письмо обязано называть основание. Отдельно проверено, что
реклама не попадает в органику: именно эта ошибка делает бесполезным весь
расчёт окупаемости.
"""

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "seo"))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / "seo" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


leads = load("leads")

DATE = "2026-09-02"   # отчёт за 2 сентября рассказывает про сутки 1 сентября
DAY = "2026-09-01"


def lead(**kw):
    base = {"id": 1, "created_at": f"{DAY}T09:15:00", "company": "ООО «Ромашка»",
            "form_source": "pricing", "product_ref": "Figma Organization"}
    base.update(kw)
    return base


def raw(*items):
    return {"date": DATE, "leads_available": True, "leads": list(items),
            "metrika": {"available": True, "error": None}}


class TestChannelFromTouch(unittest.TestCase):
    """Метка браузера: реклама, фид и переход по ссылке различимы."""

    def test_yclid_is_direct_ads(self):
        ch = leads.channel_from_touch(lead(yclid="12345",
                                           last_touch_source="yandex.ru / referral"))
        self.assertEqual(ch["key"], "ad_direct")

    def test_paid_medium_wins_over_referrer(self):
        ch = leads.channel_from_touch(lead(utm_source="yandex", utm_medium="cpc",
                                           last_touch_source="yandex.ru / referral"))
        self.assertTrue(ch["key"].startswith("ad"))

    def test_feed_marker_is_not_referral(self):
        ch = leads.channel_from_touch(lead(utm_source="yandex_market"))
        self.assertEqual(ch["key"], "feed")

    def test_search_host_is_not_called_organic(self):
        # Реферер поисковика не отличает выдачу от сервисов — формулировка
        # обязана оставаться двусмысленной, пока Метрика не уточнит.
        ch = leads.channel_from_touch(lead(last_touch_source="www.google.com / referral"))
        self.assertEqual(ch["key"], "google")
        self.assertNotIn("органик", ch["label"].lower())

    def test_referral_host_is_named(self):
        ch = leads.channel_from_touch(lead(last_touch_source="bitrix.informatic.ru / referral"))
        self.assertEqual(ch["key"], "referral")
        self.assertIn("bitrix.informatic.ru", ch["label"])

    def test_no_marks_is_unknown_not_direct(self):
        # Отсутствие метки — отсутствие сведений, а не канал «прямой заход».
        ch = leads.channel_from_touch(lead())
        self.assertEqual(ch["key"], "unknown")


class TestChannelFromMetrika(unittest.TestCase):
    """Визиты счётчика сильнее метки и называют поисковую систему."""

    def test_metrika_overrides_touch(self):
        item = lead(last_touch_source="www.google.com / referral", ym_client_id="42",
                    journey={"available": True, "visits": 3, "steps": [
                        {"date": "2026-08-30", "source": "organic", "engine": "Yandex",
                         "landing": "/vendors/freepik"},
                        {"date": DAY, "source": "organic", "engine": "Google",
                         "landing": "/vendors/freepik"}]})
        ch = leads.channel_of(item)
        self.assertEqual(ch["basis"], "Метрика")
        self.assertEqual(ch["label"], "поиск Google")

    def test_basis_named_when_metrika_silent(self):
        ch = leads.channel_of(lead(last_touch_source="bitrix.informatic.ru / referral"))
        self.assertEqual(ch["basis"], "метка браузера")

    def test_engine_named_in_russian(self):
        item = lead(ym_client_id="3", journey={"available": True, "visits": 1, "steps": [
            {"date": DAY, "source": "organic", "engine": "Yandex", "landing": "/"}]})
        self.assertEqual(leads.channel_of(item)["label"], "поиск Яндекса")

    def test_last_visit_decides_not_first(self):
        item = lead(ym_client_id="7", journey={"available": True, "visits": 2, "steps": [
            {"date": "2026-08-31", "source": "ad", "engine": "Yandex", "landing": "/"},
            {"date": DAY, "source": "referral", "referer_host": "bitrix.informatic.ru",
             "landing": "/product/x"}]})
        self.assertIn("bitrix.informatic.ru", leads.channel_of(item)["label"])


class TestJourney(unittest.TestCase):
    """Путь читается как рассказ, а пробел в данных назван причиной."""

    def test_journey_mentions_first_visit_and_count(self):
        item = lead(ym_client_id="9", journey={"available": True, "visits": 4, "steps": [
            {"date": "2026-08-30", "source": "organic", "engine": "Yandex",
             "phrase": "купить figma для юрлица", "landing": "/vendors/freepik"},
            {"date": DAY, "source": "direct", "landing": "/vendors/freepik"}]})
        line = leads.journey_line(item)
        self.assertIn("первый визит 30.08", line)
        self.assertIn("купить figma для юрлица", line)
        self.assertIn("4 визита", line)

    def test_missing_client_id_explained(self):
        line = leads.journey_line(lead(last_touch_source="mail.ru / referral"))
        self.assertIn("не опознан", line)

    def test_api_error_is_shown(self):
        item = lead(ym_client_id="5", journey={"available": False, "error": "HTTP 403"})
        self.assertIn("HTTP 403", leads.journey_line(item))


class TestBuild(unittest.TestCase):
    """Сборка блока: сутки, сводка недели, мусор и пустой день."""

    def test_only_previous_day_in_items(self):
        block = leads.build(raw(lead(created_at=f"{DAY}T10:00:00"),
                                lead(id=2, created_at=f"{DATE}T08:00:00")), DATE)
        self.assertEqual(block["count"], 1)
        self.assertEqual(block["day"], DAY)

    def test_spam_excluded(self):
        block = leads.build(raw(lead(status="spam"), lead(id=2)), DATE)
        self.assertEqual(block["count"], 1)

    def test_empty_day_is_not_missing_data(self):
        block = leads.build(raw(lead(created_at="2026-08-20T10:00:00")), DATE)
        self.assertTrue(block["available"])
        self.assertEqual(block["count"], 0)
        self.assertIn("не поступило", leads.summary_line(block))

    def test_no_export_says_so(self):
        block = leads.build(None, DATE)
        self.assertFalse(block["available"])
        self.assertIn("ops-leads-collect", block["reason"])

    def test_summary_counts_week_by_channel(self):
        block = leads.build(raw(
            lead(created_at=f"{DAY}T09:00:00", last_touch_source="yandex.ru / referral"),
            lead(id=2, created_at="2026-08-28T09:00:00",
                 last_touch_source="yandex.ru / referral")), DATE)
        self.assertEqual(block["week_count"], 2)
        self.assertEqual(block["channels"][0]["count"], 2)

    def test_amount_and_quote_in_request_line(self):
        block = leads.build(raw(lead(amount=66469, quote_no="BZ-20260901-85535",
                                     product_ref="Magnific Premium+ (годовая)")), DATE)
        request = block["items"][0]["request"]
        self.assertIn("66 469 ₽", request)
        self.assertIn("BZ-20260901-85535", request)

    def test_detailed_limit_and_more(self):
        block = leads.build(raw(*[lead(id=i, created_at=f"{DAY}T0{i}:00:00")
                                  for i in range(1, 6)]), DATE)
        self.assertEqual(len(block["items"]), leads.DETAILED)
        self.assertEqual(block["more"], 5 - leads.DETAILED)

    def test_note_names_method_and_gaps(self):
        block = leads.build(raw(lead()), DATE)
        self.assertIn("Метрики", block["note"])
        self.assertIn("метке источника", block["note"])


class TestCollectorNormalization(unittest.TestCase):
    """Витрина не должна нести персональные данные клиента."""

    def test_personal_fields_dropped(self):
        collect = load("leads_collect")
        rows = collect.normalize([{
            "id": 1, "created_at": f"{DAY}T09:00:00", "company": "ООО «Ромашка»",
            "inn": "7703606133", "name": "Иван Петров", "email": "i@example.com",
            "phone": "+7 900 000-00-00", "message": "текст обращения",
            "last_touch_source": "yandex.ru / referral"}])
        self.assertEqual(rows[0]["company"], "ООО «Ромашка»")
        self.assertEqual(rows[0]["inn"], "7703606133")
        for forbidden in ("name", "email", "phone", "message"):
            self.assertNotIn(forbidden, rows[0])

    def test_steps_sorted_by_date(self):
        collect = load("leads_collect")
        steps = collect.parse_steps({"data": [
            {"dimensions": [{"name": "2026-09-01"}, {"id": "direct", "name": "Direct traffic"},
                            {"name": "N/A"}, {"name": "/vendors/freepik"}],
             "metrics": [1.0]},
            {"dimensions": [{"name": "2026-08-30"}, {"id": "organic", "name": "Search engine"},
                            {"name": "Yandex"}, {"name": "/vendors/freepik"}],
             "metrics": [2.0]}]})
        self.assertEqual([s["date"] for s in steps], ["2026-08-30", "2026-09-01"])
        # «N/A» — не название поисковой системы, а её отсутствие.
        self.assertEqual(steps[1]["engine"], "")


class TestEmailIntegration(unittest.TestCase):
    """Блок доезжает до письма — и в HTML, и в текстовую версию.

    Проверка сквозная намеренно: блок собирается в snapshot, а рисуется в
    report_v4, и рассинхрон этих двух мест виден только на полном письме.
    Фикстура — фактический срез 19.08 из ветки seo-data, как в
    test_report_v4.
    """

    FIX = pathlib.Path(__file__).resolve().parent / "fixtures"
    FIX_DATE = "2026-08-19"
    ACTIONS = {"roles": {}, "actions": []}

    @classmethod
    def setUpClass(cls):
        import json
        cls.s, cls.q, cls.r = load("snapshot"), load("quality"), load("report_v4")
        cls.snap = json.loads(
            (cls.FIX / f"reports/seo/intelligence/snapshots/{cls.FIX_DATE}.json")
            .read_text(encoding="utf-8"))

    def _email(self, crm):
        snap = dict(self.snap, crm=crm)
        dq = self.q.run_checks(snap, None)
        b = self.r.assemble(snap, None, dq, self.ACTIONS, None)
        return dq, self.r.html_email(b, {}, cid_mode=False), self.r.plain_text(b)

    def _crm(self, *items):
        day = (__import__("datetime").date.fromisoformat(self.FIX_DATE)
               - __import__("datetime").timedelta(days=1)).isoformat()
        rows = [dict(i, created_at=f"{day}T{i.pop('at', '10:00')}:00") for i in items]
        block = leads.build({"leads_available": True, "leads": rows,
                             "metrika": {"available": True}}, self.FIX_DATE)
        return {"connected": True, "qualified_leads": block["count"],
                "revenue": None, "deals": None, "block": block}

    def test_section_present_with_leads(self):
        _, html, text = self._email(self._crm(
            {"id": 1, "company": "ООО «Информатик»", "product_ref": "Toon Boom Studio",
             "last_touch_source": "bitrix.informatic.ru / referral",
             "landing_path": "/product/mrmst-tb5-studio"}))
        self.assertIn("Заявки за сутки", html)
        self.assertIn("ООО «Информатик»", html)
        self.assertIn("bitrix.informatic.ru", html)
        self.assertIn("ЗАЯВКИ ЗА СУТКИ", text)
        self.assertIn("основание: метка браузера", text)

    def test_no_section_without_export(self):
        _, html, text = self._email({"connected": False,
                                     "block": leads.build(None, self.FIX_DATE)})
        self.assertNotIn("Заявки за сутки", html)
        self.assertNotIn("ЗАЯВКИ ЗА СУТКИ", text)

    def test_kpi_card_switches_to_leads(self):
        dq, html, text = self._email(self._crm(
            {"id": 1, "company": "ООО «Ромашка»", "amount": 66469}))
        self.assertIn("Обращения", html)
        self.assertIn("1 заявка за сутки", html)
        # NO_CRM снят, но выручка по-прежнему не измеряется — и это сказано.
        codes = [f["code"] for f in dq["findings"]]
        self.assertNotIn("NO_CRM", codes)
        self.assertIn("NO_CRM_REVENUE", codes)


if __name__ == "__main__":
    unittest.main()
