"""Автотаргетинг новых групп: режим из спецификации (21.09.2026).

Решение руководителя: платим только за строгие совпадения заданных фраз.
Даже EXACT-режим оставляет Директу право подбирать похожие запросы, а
разбор трёх недель показал цену этого права — 24% расхода на классы C и D.

Первая редакция гасила автотаргетинг остановкой условия и считала этот
путь единственным. Прогон 21.09.2026 по кампании bs-catalog-2026-09 ответил
кодом 8305 «Автотаргетинг не может быть остановлен»: кампания осталась
наполненной, но прогон упал, не дойдя до модерации объявлений. Поэтому
режим «off» — лестница попыток от строгой к мягкой, а обещание в журнале
соответствует тому, что кабинет принял.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ppc"))
import direct_apply  # noqa: E402

SRC = (pathlib.Path(__file__).resolve().parents[2] / "ppc" / "direct_apply.py").read_text(encoding="utf-8")


class AutotargetingTest(unittest.TestCase):
    def test_режим_берётся_из_спецификации(self):
        self.assertIn('spec.get("campaign") or {}).get("autotargeting", "exact")', SRC)

    def test_лестница_начинается_с_остановки_условия(self):
        self.assertIn('"keywords", "suspend"', SRC)

    def test_умолчание_прежнее(self):
        # Спецификации без поля продолжают работать в режиме EXACT-only.
        self.assertIn('"AutotargetingCategories": EXACT_ONLY', SRC)

    def test_exact_only_разрешает_ровно_одну_категорию(self):
        yes = [c for c in direct_apply.EXACT_ONLY if c["Value"] == "YES"]
        self.assertEqual([c["Category"] for c in yes], ["EXACT"])

    def test_all_off_не_оставляет_ни_одной_категории(self):
        self.assertEqual(len(direct_apply.ALL_OFF), len(direct_apply.EXACT_ONLY))
        self.assertEqual([c["Value"] for c in direct_apply.ALL_OFF],
                         ["NO"] * len(direct_apply.ALL_OFF))

    def test_автотаргетинг_гасится_во_всех_ветках(self):
        # Создание кампании, добавление групп в существующую и доводка.
        self.assertEqual(SRC.count("apply_autotargeting("), 4)


class LadderTest(unittest.TestCase):
    """Лестница попыток: применяется первая принятая, отказ не молчит."""

    def setUp(self):
        self.calls = []
        self.spec = {"campaign": {"autotargeting": "off"}}
        self.orig_soft = direct_apply.call_soft
        self.orig_state = direct_apply.autotargeting_state
        direct_apply.autotargeting_state = lambda ids, token: "проверка отключена в тесте"

    def tearDown(self):
        direct_apply.call_soft = self.orig_soft
        direct_apply.autotargeting_state = self.orig_state

    def _run(self, verdicts):
        """verdicts — ответы кабинета по порядку попыток."""
        answers = list(verdicts)

        def fake(service, method, params, token, key):
            self.calls.append((service, method, params))
            return answers.pop(0)

        direct_apply.call_soft = fake
        direct_apply.apply_autotargeting([1, 2], self.spec, "t")

    def test_принятая_остановка_дальше_не_идёт(self):
        self._run([(True, "")])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][1], "suspend")

    def test_отказ_8305_ведёт_к_обнулению_категорий(self):
        self._run([(False, "код 8305 Автотаргетинг не может быть остановлен"), (True, "")])
        self.assertEqual([c[1] for c in self.calls], ["suspend", "update"])
        sent = self.calls[1][2]["Keywords"][0]["AutotargetingCategories"]
        self.assertEqual([c["Value"] for c in sent], ["NO"] * 5)

    def test_последняя_ступень_оставляет_точные_совпадения(self):
        self._run([(False, "нельзя"), (False, "нельзя"), (True, "")])
        sent = self.calls[2][2]["Keywords"][0]["AutotargetingCategories"]
        self.assertEqual(sent, direct_apply.EXACT_ONLY)

    def test_полный_отказ_останавливает_прогон(self):
        with self.assertRaises(SystemExit) as e:
            self._run([(False, "нельзя"), (False, "нельзя"), (False, "нельзя")])
        # Показы с неуправляемым автоподбором запускать нельзя — и об этом
        # должно быть сказано прямо, а не «применено частично».
        self.assertIn("показы запускать нельзя", str(e.exception))


class CampaignSettingsTest(unittest.TestCase):
    """Помощники кабинета выключаются поимённо и по одному."""

    def setUp(self):
        self.calls = []
        self.orig = direct_apply.call_soft
        direct_apply.call_soft = lambda s, m, p, t, k: (self.calls.append((s, m, p)), (True, ""))[1]

    def tearDown(self):
        direct_apply.call_soft = self.orig

    def test_каждая_опция_идёт_своим_вызовом(self):
        direct_apply.apply_campaign_settings(7, {"campaign": {
            "settings_off": ["ALTERNATIVE_TEXTS_ENABLED", "ENABLE_AREA_OF_INTEREST_TARGETING"],
            "settings_on": ["ENABLE_SITE_MONITORING"]}}, "t")
        self.assertEqual(len(self.calls), 3)
        values = [c[2]["Campaigns"][0]["TextCampaign"]["Settings"][0] for c in self.calls]
        self.assertEqual([v["Value"] for v in values], ["YES", "NO", "NO"])

    def test_без_поля_ничего_не_трогается(self):
        direct_apply.apply_campaign_settings(7, {"campaign": {}}, "t")
        self.assertEqual(self.calls, [])


class NegativesSyncTest(unittest.TestCase):
    """Минус-слова кампании приводятся к спецификации, а не дополняются вслепую."""

    def setUp(self):
        self.sent = []
        self.have = []
        self.orig_call = direct_apply.call
        self.orig_check = direct_apply.check_add_results

        def fake_call(service, method, params, token):
            if (service, method) == ("campaigns", "get"):
                return {"Campaigns": [{"Id": 7, "NegativeKeywords": {"Items": self.have}}]}
            self.sent.append((service, method, params))
            return {"UpdateResults": [{"Id": 7}]}

        direct_apply.call = fake_call
        direct_apply.check_add_results = lambda *a, **k: []

    def tearDown(self):
        direct_apply.call = self.orig_call
        direct_apply.check_add_results = self.orig_check

    def test_совпадающий_список_не_трогается(self):
        self.have = ["бесплатно", "торрент"]
        direct_apply.sync_negatives(7, {"campaign": {
            "negative_keywords": ["торрент", "бесплатно"]}}, "t")
        self.assertEqual(self.sent, [])

    def test_расхождение_приводится_к_спецификации(self):
        self.have = ["бесплатно"]
        direct_apply.sync_negatives(7, {"campaign": {
            "negative_keywords": ["бесплатно", "студент"]}}, "t")
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0][2]["Campaigns"][0]["NegativeKeywords"]["Items"],
                         ["бесплатно", "студент"])

    def test_пустой_список_в_спецификации_ничего_не_снимает(self):
        # Спецификация без поля не повод стереть минус-слова кабинета.
        self.have = ["бесплатно"]
        direct_apply.sync_negatives(7, {"campaign": {}}, "t")
        self.assertEqual(self.sent, [])


if __name__ == "__main__":
    unittest.main()
