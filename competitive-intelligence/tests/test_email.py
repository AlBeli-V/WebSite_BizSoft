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
             categories=None, date="2026-08-30", coverage=150,
             core_hash="ядро-150"):
    return {
        "дата": date,
        "зрелость_скоринга": "базовый",
        # Отпечаток состава ядра: сравнение долей допустимо только внутри
        # одного состава, поэтому фикстуры по умолчанию описывают одно и то
        # же ядро. Тест на смену состава задаёт core_hash явно.
        "ядро_запросов": {"хеш": core_hash, "версия": "v1", "запросов": 150},
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
    """Версия 1.1.0: динамический вердикт требует шести сравнимых измерений.

    В 1.0.0 была коллизия, найденная внешним аудитом: методика декларировала
    сглаживание медианами 3×3, а вердикт менялся уже на втором дне по
    разнице двух соседних точек.
    """

    def test_без_истории_недостаточно_данных(self):
        k = kpi_mod.build_kpi(snapshot())
        mark, why = kpi_mod.verdict(k, [])
        self.assertEqual(mark, kpi_mod.VERDICT_NO_DATA)
        self.assertIn("динамики", why)

    def test_пяти_измерений_недостаточно(self):
        """Пять точек — окно 3×3 не собирается, тренда не существует."""
        k = kpi_mod.build_kpi(snapshot())
        mark, why = kpi_mod.verdict(k, [0.05] * 5)
        self.assertEqual(mark, kpi_mod.VERDICT_NO_DATA)
        self.assertIn("не хватает 1", why)

    def test_нет_покрытия_даёт_серый_вердикт(self):
        k = kpi_mod.build_kpi(snapshot(coverage=0))
        mark, _ = kpi_mod.verdict(k, [0.05] * 6)
        self.assertEqual(mark, kpi_mod.VERDICT_NO_DATA)

    def test_значимый_рост_по_окнам(self):
        k = kpi_mod.build_kpi(snapshot())
        mark, why = kpi_mod.verdict(k, [0.05, 0.05, 0.05, 0.07, 0.07, 0.07])
        self.assertEqual(mark, kpi_mod.VERDICT_GROWTH)
        self.assertIn("выросла", why)

    def test_значимое_падение_по_окнам(self):
        k = kpi_mod.build_kpi(snapshot())
        mark, _ = kpi_mod.verdict(k, [0.07, 0.07, 0.07, 0.05, 0.05, 0.05])
        self.assertEqual(mark, kpi_mod.VERDICT_DECLINE)

    def test_шум_не_становится_сигналом(self):
        k = kpi_mod.build_kpi(snapshot())
        mark, _ = kpi_mod.verdict(k, [0.054, 0.054, 0.054, 0.056, 0.056, 0.056])
        self.assertEqual(mark, kpi_mod.VERDICT_NEUTRAL)

    def test_выброс_сглаживается_медианой(self):
        """Один аномальный день не должен переворачивать вердикт."""
        k = kpi_mod.build_kpi(snapshot())
        ровно, _ = kpi_mod.verdict(k, [0.05, 0.05, 0.05, 0.052, 0.052, 0.052])
        с_выбросом, _ = kpi_mod.verdict(k, [0.05, 0.05, 0.05, 0.052, 0.40, 0.052])
        self.assertEqual(ровно, с_выбросом)

    def test_структурный_вердикт_доступен_сразу(self):
        """Расстановка сил — не тренд, её можно называть с первого дня."""
        k = kpi_mod.build_kpi(snapshot())
        text = kpi_mod.structural_verdict(k, ("raketapay.ru", 0.0998))
        self.assertIn("5,4%", text)
        self.assertIn("raketapay.ru", text)

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


class TestStaleData(unittest.TestCase):
    """Поведение в день, когда свежий сбор не удался.

    Реальный случай 31.08.2026: сбор базового контура вернул ошибку по всем
    502 запросам. Требование раздела 24 задания — письмо в такой день всё
    равно уходит, но с вердиктом «недостаточно данных».
    """

    def test_вердикт_становится_серым(self):
        meta = build_email.build("2026-08-30", snapshot(share=0.09),
                                 snapshot(share=0.05),
                                 stale_notice="свежий сбор за 2026-08-31 не удался",
                                 history=[0.05] * 3 + [0.09] * 3)
        # Даже при росте доли на 4 п.п. вердикт не «усиливаемся»
        self.assertEqual(meta["вердикт"], kpi_mod.VERDICT_NO_DATA)

    def test_причина_названа_в_письме(self):
        meta = build_email.build("2026-08-30", snapshot(), None,
                                 stale_notice="свежий сбор за 2026-08-31 не удался")
        self.assertIn("2026-08-31", meta["текст"])
        self.assertIn("не удался", meta["текст"])

    def test_предупреждение_в_метаданных(self):
        meta = build_email.build("2026-08-30", snapshot(), None,
                                 stale_notice="сбор не удался")
        self.assertEqual(meta["предупреждение_о_свежести"], "сбор не удался")

    def test_обычный_день_без_предупреждения(self):
        meta = build_email.build("2026-08-30", snapshot(), None)
        self.assertIsNone(meta["предупреждение_о_свежести"])

    def test_лимит_соблюдён_и_с_предупреждением(self):
        meta = build_email.build("2026-08-30", snapshot(), None,
                                 stale_notice="свежий сбор за 2026-08-31 не удался "
                                              "(502 запросов с ошибкой), "
                                              "показаны данные за 2026-08-30")
        self.assertTrue(meta["лимит_соблюдён"])


class TestPackageChoice(unittest.TestCase):
    """Выбор главного поручения не должен предпочитать неизученные цели.

    Замечание второй внешней рецензии: при нормализации весов пакет с
    отсутствующим спросом получает фору — неудобный фактор просто исчезает
    из расчёта.
    """

    def package(self, pid, potential, upside=None):
        return {"package_id": pid, "potential_index": potential,
                "traffic_upside": upside, "url": "https://biz-soft.pro/a",
                "action": "тест", "queries_count": 1, "demand_total": 10,
                "position_best": 5, "position_worst": 5, "effort": "S",
                "potential_label": "высокий"}

    def test_при_сопоставимом_потенциале_выбирается_измеренный(self):
        chosen = build_email.pick_package([
            self.package("WP-01", 0.11),                # спрос не измерен
            self.package("WP-02", 0.10, upside=12.0),   # спрос измерен
        ])
        self.assertEqual(chosen["package_id"], "WP-02")

    def test_явно_больший_потенциал_побеждает(self):
        """Запрет не абсолютный: заметно лучшая цель выигрывает."""
        chosen = build_email.pick_package([
            self.package("WP-01", 0.50),
            self.package("WP-02", 0.10, upside=12.0),
        ])
        self.assertEqual(chosen["package_id"], "WP-01")

    def test_без_измеренных_берётся_лучший(self):
        chosen = build_email.pick_package([
            self.package("WP-01", 0.20),
            self.package("WP-02", 0.10),
        ])
        self.assertEqual(chosen["package_id"], "WP-01")

    def test_пустой_список(self):
        self.assertIsNone(build_email.pick_package([]))
        self.assertIsNone(build_email.pick_package(None))


class TestCoverageClassification(unittest.TestCase):
    """Критический недостаток данных отделён от некритического.

    Замечание третьей рецензии: при формулировке «неполные данные → вердикт
    недостаточно данных» система с незапущенным Google обязана была бы вечно
    отвечать «недостаточно данных», а 149 валидных запросов из 150 и 20 из
    150 назывались бы одинаково.
    """

    def test_полное_покрытие_рабочее(self):
        state, note = kpi_mod.coverage_state(snapshot(coverage=150))
        self.assertEqual(state, "ок")

    def test_отсутствие_google_не_критично(self):
        """Необязательный источник снижает достоверность, но не блокирует."""
        state, note = kpi_mod.coverage_state(snapshot(coverage=150))
        self.assertEqual(state, "ок")
        self.assertIn("Google", note)

    def test_потеря_большей_части_ядра_критична(self):
        state, note = kpi_mod.coverage_state(snapshot(coverage=20))
        self.assertEqual(state, "критическое")
        self.assertIn("20", note)

    def test_почти_полное_покрытие_рабочее(self):
        """149 из 150 — рабочий день, а не сбой."""
        state, _ = kpi_mod.coverage_state(snapshot(coverage=149))
        self.assertEqual(state, "ок")

    def test_пустой_срез_критичен(self):
        state, note = kpi_mod.coverage_state(snapshot(coverage=0))
        self.assertEqual(state, "критическое")

    def test_порог_на_границе(self):
        """80% — граница: ровно на пороге данные ещё рабочие."""
        state, _ = kpi_mod.coverage_state(snapshot(coverage=120))
        self.assertEqual(state, "ок")
        state, _ = kpi_mod.coverage_state(snapshot(coverage=119))
        self.assertEqual(state, "критическое")


if __name__ == "__main__":
    unittest.main()


class TestGoogleBlock(unittest.TestCase):
    """Google по России (xmlriver, топ-10) в письме: раздел, KPI, честность."""

    def google(self):
        return {"дата_среза": "2026-09-03", "источник": "xmlriver",
                "гео": "Россия (loc 2643)", "глубина": 10,
                "запросов_всего": 480, "запросов_с_данными": 470,
                "наша_доля_видимости": 0.0, "наша_взвешенная_видимость": 0.0,
                "топ3": 0, "топ10": 0, "лучшая_позиция": None,
                "наши_запросы": [],
                "лидеры": [{"домен": "ggsel.net", "категория": "G",
                            "доля": 0.21, "топ3": 300, "топ10": 420}]}

    def test_без_среза_google_no_data(self):
        snap = snapshot()
        meta = build_email.build("2026-08-30", snap, None)
        html_page = build_email.render_html(meta, kpi=kpi_mod.build_kpi(snap, None),
                                            snapshot=snap)
        self.assertNotIn("Google по России", html_page)
        self.assertIn("Google-среза за эту дату нет", html_page)
        self.assertIn("NO DATA", html_page)

    def test_с_срезом_раздел_и_доля(self):
        snap = snapshot()
        snap["google"] = self.google()
        snap["покрытие"]["google"] = 0.0
        meta = build_email.build("2026-08-30", snap, None)
        html_page = build_email.render_html(meta, kpi=kpi_mod.build_kpi(snap, None),
                                            snapshot=snap)
        self.assertIn("Google по России", html_page)
        self.assertIn("ggsel.net", html_page)
        # ноль в Google — измеренный ноль, а не NO DATA
        self.assertIn("0,0%", html_page)
        self.assertIn("ни по одному из 470 запросов", html_page)
        self.assertIn("Россия, топ-10, 470 запросов", html_page)
        txt = build_email.render_txt(meta, snapshot=snap)
        self.assertIn("GOOGLE ПО РОССИИ", txt)
        self.assertIn("ggsel.net", txt)
        self.assertTrue(meta["лимит_соблюдён"])
