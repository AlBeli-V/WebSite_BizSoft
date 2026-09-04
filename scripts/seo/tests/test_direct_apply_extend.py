"""Правка существующей кампании Директа (plan_kind=extend_campaign).

Раунд 2 рекламы не создаёт кампанию заново: старые группы ставятся на
паузу, новые добавляются внутрь работающей кампании. Проверяем то, что
дороже всего стоит ошибиться: dry-run ничего не пишет в API, повторный
прогон не плодит дубли групп, расхождение спецификации с кабинетом
останавливает прогон, а тексты объявлений и фразы проверяются до записи.
"""

import io
import contextlib
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ppc"))
import direct_apply as da  # noqa: E402

LIVE_GROUPS = ["Старая группа A", "Старая группа B"]


def _spec(groups=None, pause=None, keep=None):
    return {
        "plan_kind": "extend_campaign",
        "campaign": {
            "name": "bs-test-2026-09",
            "utm_template": "utm_source=yandex&utm_content={group}",
        },
        "pause": pause if pause is not None else [
            {"group": "Старая группа A", "facts": "77 кликов", "reason": "нет заявок"}],
        "keep": keep if keep is not None else [
            {"group": "Старая группа B", "facts": "40 кликов", "reason": "дешёвый трафик"}],
        "groups": groups if groups is not None else [_group()],
    }


def _group(title="Новая группа", gid="r2-k1"):
    return {
        "id": gid,
        "title": title,
        "share": 0.35,
        "max_bid_rub": 60,
        "cpa_limit_rub": 3000,
        "landing": "https://biz-soft.pro/vendors/atlassian",
        "why": "транзакционный интент",
        "stop_rule": "40 кликов без заявки — пауза",
        "keywords": [{"keyword": '"оплата confluence в рублях"', "our_impressions": 10,
                      "our_position": 5.2}],
        "minus_words": ["обучение"],
        "ads": [{"title1": "Confluence юрлицам", "title2": "Счёт и ЭДО",
                 "text": "Оплата в рублях по счёту. Закрывающие документы."}],
    }


class FakeApi:
    """Кабинет-заглушка: помнит все вызовы, чтобы отличить чтение от записи."""

    def __init__(self, groups=LIVE_GROUPS, ads_per_group=2):
        self.groups = list(groups)
        self.ads_per_group = ads_per_group
        self.calls = []

    def __call__(self, service, method, params, token):
        self.calls.append(f"{service}.{method}")
        if service == "campaigns" and method == "get":
            camp = {"Id": 713927850, "Name": "bs-test-2026-09", "State": "ON"}
            if "Ids" in params.get("SelectionCriteria", {}):
                camp["TextCampaign"] = {"BiddingStrategy": {"Search": {"WbMaximumClicks": {
                    "WeeklySpendLimit": 4098 * 10 ** 6, "BidCeiling": 60 * 10 ** 6}}}}
            return {"Campaigns": [camp]}
        if service == "adgroups" and method == "get":
            return {"AdGroups": [{"Id": 100 + i, "Name": n, "Status": "ACCEPTED"}
                                 for i, n in enumerate(self.groups)]}
        if service == "ads" and method == "get":
            ads = []
            for i in range(len(self.groups)):
                for j in range(self.ads_per_group):
                    ads.append({"Id": 900 + i * 10 + j, "AdGroupId": 100 + i,
                                "State": "ON", "Status": "ACCEPTED"})
            return {"Ads": ads}
        if service == "keywords" and method == "get":
            return {"Keywords": [{"Id": 555, "Keyword": "---autotargeting"}]}
        if method in ("add", "suspend", "moderate", "update"):
            key = {"add": "AddResults", "suspend": "SuspendResults",
                   "moderate": "ModerateResults", "update": "UpdateResults"}[method]
            return {key: [{"Id": 777}]}
        raise AssertionError(f"неожиданный вызов {service}.{method}")


def run(spec, api, apply=False):
    da.call = api
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        da.mode_extend(spec, "token", apply=apply)
    return buf.getvalue()


class ExtendPlanTest(unittest.TestCase):
    def test_dry_run_ne_pishet_v_api(self):
        api = FakeApi()
        out = run(_spec(), api)
        self.assertEqual([c for c in api.calls if not c.endswith(".get")], [])
        self.assertIn("остановить объявлений: 2 из 2", out)
        self.assertIn("к остановке объявлений — 2, новых групп — 1", out)

    def test_plan_pokazyvaet_dengi_i_doli(self):
        out = run(_spec(), FakeApi())
        self.assertIn("недельный лимит в кабинете: 4098 ₽", out)
        self.assertIn("доли бюджета (share) в кабинет не переносятся", out)
        self.assertIn("бюджет, стратегия, расписание и корректировки не меняются", out)

    def test_sushchestvuyushchaya_gruppa_ne_dublitsya(self):
        api = FakeApi(groups=LIVE_GROUPS + ["Новая группа"])
        out = run(_spec(), api)
        self.assertIn("пропуск «Новая группа»", out)
        self.assertIn("новых групп — 0", out)

    def test_gruppa_pause_ne_naydena_ostanavlivaet(self):
        spec = _spec(pause=[{"group": "Нет такой", "facts": "-", "reason": "-"}])
        with self.assertRaises(SystemExit) as e:
            run(spec, FakeApi())
        self.assertIn("Нет такой", str(e.exception))

    def test_gruppy_vne_spetsifikatsii_ne_trogayutsya(self):
        api = FakeApi(groups=LIVE_GROUPS + ["Чужая группа"])
        out = run(_spec(), api)
        self.assertIn("не упомянуты в спецификации и остаются как есть: «Чужая группа»", out)

    def test_apply_posledovatelnost_vyzovov(self):
        api = FakeApi()
        run(_spec(), api, apply=True)
        pisali = [c for c in api.calls if not c.endswith(".get")]
        self.assertEqual(pisali, ["ads.suspend", "adgroups.add", "keywords.add",
                                  "ads.add", "ads.moderate", "keywords.update"])

    def test_kampaniya_ne_naydena(self):
        class NoCamp(FakeApi):
            def __call__(self, service, method, params, token):
                if service == "campaigns":
                    return {"Campaigns": []}
                return super().__call__(service, method, params, token)
        with self.assertRaises(SystemExit):
            run(_spec(), NoCamp())


class TextLimitsTest(unittest.TestCase):
    def test_summa_zagolovkov_oshibka_v_novom_plane(self):
        ad = {"title1": "Ы" * 40, "title2": "Ы" * 20, "text": "коротко"}
        with self.assertRaises(SystemExit) as e:
            da.check_ad_texts(ad, "r2-k1", strict_sum=True)
        self.assertIn("Директ отбросит второй заголовок", str(e.exception))

    def test_summa_zagolovkov_preduprezhdenie_v_starom_plane(self):
        ad = {"title1": "Ы" * 40, "title2": "Ы" * 20, "text": "коротко"}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            da.check_ad_texts(ad, "k1", strict_sum=False)
        self.assertIn("предупреждение", buf.getvalue())

    def test_dlinnyy_tekst_oshibka_vsegda(self):
        ad = {"title1": "коротко", "title2": "коротко", "text": "Ы" * 82}
        with self.assertRaises(SystemExit):
            da.check_ad_texts(ad, "k1", strict_sum=False)

    def test_fraza_dlinnee_semi_slov(self):
        with self.assertRaises(SystemExit) as e:
            da.check_keyword('"оплата зарубежного по для юр лица документы срочно"', "r2-k1")
        self.assertIn("лимите 7", str(e.exception))

    def test_fraza_semi_slov_prohodit(self):
        da.check_keyword('"оплата зарубежного по для юр лица документы"', "r2-k1")


if __name__ == "__main__":
    unittest.main()
