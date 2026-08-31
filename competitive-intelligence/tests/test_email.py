"""Тесты KPI, вердикта, главного сигнала и сборки письма.

Проверяются в первую очередь гейты качества из раздела 24 задания: лимит
символов, честность при отсутствии данных, ровно один главный сигнал.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from decision_engine import kpi as kpi_mod  # noqa: E402
from decision_engine import signal as signal_mod  # noqa: E402
from mailer import build_email  # noqa: E402


def snapshot(*, share=0.054, top3=28, top10=94, queries=150, leaders=None,
             categories=None, date="2026-08-30", coverage=150):
    return {
        "дата": date,
        "зрелость_скоринга": "базовый",
        "покрытие": {"яндекс_запросов_всего": 150,
                     "яндекс_запросов_с_данными": coverage,
                     "яндекс_ошибок": 150 - coverage, "google": None},
        "наши_показатели": {"доля_видимости": share, "топ3": top3,
                            "топ10": top10, "запросов_в_поле": queries,
                            "взвешенная_видимость": 6.4},
        "доли_по_категориям": categories or {"H": 0.32, "G": 0.24, "A": 0.18},
        "лидеры": leaders if leaders is not None else [
            {"домен": "raketapay.ru", "категория": "H", "доля": 0.0998,
             "топ3": 44, "топ10": 63},
            {"домен": "pipl.io", "категория": "H", "доля": 0.06,
             "топ3": 38, "топ10": 63},
        ],
        "конкурентов_в_основном_рейтинге": 34,
        "не_классифицировано": 137,
    }


class TestVerdict(unittest.TestCase):
    def test_без_прошлого_всегда_недостаточно_данных(self):
        """На второй день наблюдений объявлять рост нельзя."""
        k = kpi_mod.build_kpi(snapshot())
        mark, why = kpi_mod.verdict(k)
        self.assertEqual(mark, kpi_mod.VERDICT_NO_DATA)
        self.assertIn("сравнивать", why)

    def test_нет_покрытия_даёт_серый_вердикт(self):
        k = kpi_mod.build_kpi(snapshot(coverage=0))
        mark, _ = kpi_mod.verdict(k)
        self.assertEqual(mark, kpi_mod.VERDICT_NO_DATA)

    def test_значимый_рост(self):
        k = kpi_mod.build_kpi(snapshot(share=0.070), snapshot(share=0.054))
        mark, why = kpi_mod.verdict(k)
        self.assertEqual(mark, kpi_mod.VERDICT_GROWTH)
        self.assertIn("выросла", why)

    def test_значимое_падение(self):
        k = kpi_mod.build_kpi(snapshot(share=0.040), snapshot(share=0.054))
        mark, _ = kpi_mod.verdict(k)
        self.assertEqual(mark, kpi_mod.VERDICT_DECLINE)

    def test_шум_не_становится_сигналом(self):
        """Движение меньше порога — нейтрально, а не «рост»."""
        k = kpi_mod.build_kpi(snapshot(share=0.0562), snapshot(share=0.054))
        mark, _ = kpi_mod.verdict(k)
        self.assertEqual(mark, kpi_mod.VERDICT_NEUTRAL)

    def test_дельты_считаются(self):
        k = kpi_mod.build_kpi(snapshot(top3=28, top10=94),
                              snapshot(top3=20, top10=80))
        self.assertEqual(k.top3_delta, 8)
        self.assertEqual(k.top10_delta, 14)


class TestFormatting(unittest.TestCase):
    def test_доля_с_запятой(self):
        self.assertEqual(kpi_mod.format_share(0.054287), "5,4%")

    def test_no_data_не_ноль(self):
        self.assertEqual(kpi_mod.format_share(None), "NO DATA")

    def test_дельта_со_знаком(self):
        self.assertEqual(kpi_mod.format_delta(0.9, unit=" п.п."), "+0,90 п.п.")
        self.assertEqual(kpi_mod.format_delta(None), "н/д")


class TestSignal(unittest.TestCase):
    def test_без_истории_структурный_сигнал(self):
        s = signal_mod.pick(snapshot())
        self.assertEqual(s.kind, "структура")
        self.assertIn("платёжные посредники", s.text)

    def test_значимое_движение_конкурента(self):
        now = snapshot(leaders=[{"домен": "raketapay.ru", "категория": "H",
                                 "доля": 0.13, "топ3": 50, "топ10": 70}])
        was = snapshot(leaders=[{"домен": "raketapay.ru", "категория": "H",
                                 "доля": 0.10, "топ3": 44, "топ10": 63}])
        s = signal_mod.pick(now, was)
        self.assertEqual(s.kind, "рост_конкурента")
        self.assertIn("raketapay.ru", s.text)

    def test_малое_движение_не_сигнал(self):
        """Тихий день даёт структурный сигнал, а не выдуманное движение."""
        now = snapshot(leaders=[{"домен": "raketapay.ru", "категория": "H",
                                 "доля": 0.1005, "топ3": 44, "топ10": 63}])
        was = snapshot(leaders=[{"домен": "raketapay.ru", "категория": "H",
                                 "доля": 0.10, "топ3": 44, "топ10": 63}])
        self.assertEqual(signal_mod.pick(now, was).kind, "структура")

    def test_категории_вне_рейтинга_не_становятся_главными(self):
        """Информационные площадки держат много видимости, но не они конкурент."""
        s = signal_mod.pick(snapshot(categories={"G": 0.50, "H": 0.20, "A": 0.10}))
        self.assertIn("платёжные посредники", s.text)
        self.assertNotIn("информационные", s.text)


class TestBuildEmail(unittest.TestCase):
    def test_лимит_символов_соблюдён(self):
        meta = build_email.build("2026-08-30", snapshot(), None)
        self.assertTrue(meta["лимит_соблюдён"])
        self.assertLessEqual(meta["видимых_символов"], build_email.TEXT_LIMIT)

    def test_тема_с_датой_и_вердиктом(self):
        meta = build_email.build("2026-08-30", snapshot(), None)
        self.assertIn("30.08.2026", meta["тема"])
        self.assertIn("⚪", meta["тема"])

    def test_ровно_один_главный_сигнал(self):
        meta = build_email.build("2026-08-30", snapshot(), None)
        self.assertEqual(meta["текст"].count("Главный сигнал:"), 1)

    def test_хэш_сигнала_для_анти_повтора(self):
        """Одинаковый сигнал даёт одинаковый хэш — основа проверки повторов."""
        a = build_email.build("2026-08-30", snapshot(), None)
        b = build_email.build("2026-08-31", snapshot(date="2026-08-31"), None)
        self.assertEqual(a["сигнал_хэш"], b["сигнал_хэш"])

    def test_html_экранирует_и_содержит_кнопку(self):
        meta = build_email.build("2026-08-30", snapshot(), None)
        page = build_email.render_html(meta)
        self.assertIn("Открыть полную конкурентную аналитику", page)
        self.assertNotIn("<script", page.lower())

    def test_текстовая_версия_самодостаточна(self):
        """Письмо обязано читаться без картинок и без HTML."""
        meta = build_email.build("2026-08-30", snapshot(), None)
        txt = build_email.render_txt(meta)
        self.assertIn("B2B Share", txt)
        self.assertIn("Scoring:", txt)
        self.assertIn("NO DATA", txt)


class TestDoNextAndWatch(unittest.TestCase):
    """DO NEXT и WATCH — блоки полного формата письма (Phase 2)."""

    def attack(self, **kw):
        base = {"attack_id": "ATT-001", "query": "купить figma юрлицу",
                "our_position": 5, "rival_domain": "raketapay.ru",
                "rival_position": 1, "opportunity": 72, "confidence": "MEDIUM"}
        base.update(kw)
        return base

    def test_нет_кандидатов_честная_строка(self):
        """Пустота лучше выдуманного задания."""
        text = build_email.do_next_text(None)
        self.assertIn("подтверждённых точек атаки нет", text)

    def test_действие_названо_конкретно(self):
        text = build_email.do_next_text(self.attack())
        self.assertIn("ATT-001", text)
        self.assertIn("raketapay.ru", text)
        self.assertIn("72", text)

    def test_низкая_уверенность_не_становится_действием(self):
        """Opportunity HIGH при Confidence LOW главным действием не делаем."""
        chosen = build_email.pick_attack([self.attack(opportunity=95,
                                                      confidence="LOW")])
        self.assertIsNone(chosen)

    def test_выбирается_максимальный_opportunity(self):
        chosen = build_email.pick_attack([
            self.attack(attack_id="ATT-001", opportunity=60),
            self.attack(attack_id="ATT-002", opportunity=80),
        ])
        self.assertEqual(chosen["attack_id"], "ATT-002")

    def test_watch_без_угроз(self):
        self.assertIn("не зафиксировано", build_email.watch_text(None))

    def test_watch_называет_домен_и_threat(self):
        from scoring import threat as threat_mod
        card = {"домен": "raketapay.ru", "доля": 0.0998, "топ3": 44, "топ10": 63}
        t = threat_mod.score(card, queries_total=150)
        text = build_email.watch_text((card, t))
        self.assertIn("raketapay.ru", text)
        self.assertIn("10,0%", text)

    def test_полное_письмо_содержит_все_пять_блоков(self):
        meta = build_email.build("2026-08-30", snapshot(), None,
                                 attacks=[self.attack()])
        text = meta["текст"]
        self.assertIn("Главный сигнал:", text)
        self.assertIn("Что делать:", text)
        self.assertIn("Следим:", text)
        self.assertTrue(meta["лимит_соблюдён"])

    def test_хэш_действия_для_анти_повтора(self):
        """Тот же DO NEXT второй день подряд должен опознаваться."""
        a = build_email.build("2026-08-30", snapshot(), None,
                              attacks=[self.attack()])
        b = build_email.build("2026-08-31", snapshot(date="2026-08-31"), None,
                              attacks=[self.attack()])
        self.assertEqual(a["действие_хэш"], b["действие_хэш"])


if __name__ == "__main__":
    unittest.main()
