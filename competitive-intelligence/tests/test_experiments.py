"""Тесты цикла экспериментов: предложение → внедрение → мораторий → оценка.

Цикл существует, чтобы контур перестал быть генератором предложений: помнил
судьбу своих поручений, не требовал переделать только что сделанное и учился
на исходах. Тесты проверяют именно эти обещания.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from attack_engine import page_audit  # noqa: E402
from experiments import journal as jr  # noqa: E402
from experiments import learning  # noqa: E402
from experiments import lifecycle  # noqa: E402


def page(*, title="", headings=(), body="", available=True):
    return page_audit.PageContent(
        url="https://biz-soft.pro/blog/x", kind="blog", available=available,
        title=title, headings=list(headings), body=body)


def package(**over):
    data = {
        "package_id": "WP-01",
        "url": "https://biz-soft.pro/blog/x",
        "page_kind": "blog",
        "queries": ["оплата figma юрлицом", "купить figma на компанию"],
        "действия": [
            {"kind": "текст", "steps": ["«оплата figma юрлицом» — не хватает слов: figma"]},
            {"kind": "заголовки", "steps": ["«купить figma на компанию»"]},
            {"kind": "индексация", "steps": ["urls = https://biz-soft.pro/blog/x"]},
        ],
    }
    data.update(over)
    return data


def snapshot(date, positions: dict, extra: dict | None = None):
    """Снимок с позициями по запросам; extra — контрольные запросы."""
    per_query = {page_audit.normalize(q): {"наша": 0.1, "поле": 1.0, "позиция": p}
                 for q, p in positions.items()}
    for q, p in (extra or {}).items():
        per_query[page_audit.normalize(q)] = {"наша": 0.1, "поле": 1.0, "позиция": p}
    return {"дата": date, "по_запросам": per_query}


class TestRegister(unittest.TestCase):
    def test_эксперимент_заводится_на_пакет_с_требованиями(self):
        experiments = []
        created = lifecycle.register(experiments, [package()], "2026-09-01")
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].state, jr.STATE_PROPOSED)
        # Требования разной природы: дописать в текст и вынести в заголовок
        needs = {r["нужно"] for r in created[0].requirements}
        self.assertEqual(needs, {page_audit.COVER_BODY, page_audit.COVER_PROMINENT})

    def test_без_проверяемых_требований_эксперимента_нет(self):
        """Пакет «проверить вручную» измерить нечем — опыт не заводится."""
        пустой = package(действия=[{"kind": "текст", "steps": ["проверить руками"]}])
        experiments = []
        self.assertEqual(lifecycle.register(experiments, [пустой], "2026-09-01"), [])

    def test_повторный_прогон_не_дублирует(self):
        experiments = []
        lifecycle.register(experiments, [package()], "2026-09-01")
        lifecycle.register(experiments, [package()], "2026-09-02")
        self.assertEqual(len(experiments), 1)


class TestDetectImplementation(unittest.TestCase):
    def setUp(self):
        self.experiments = []
        lifecycle.register(self.experiments, [package()], "2026-09-01")
        self.snapshots = {"2026-09-01": snapshot("2026-09-01",
                                                 {"оплата figma юрлицом": 8,
                                                  "купить figma на компанию": 9})}

    def test_фраза_в_тексте_не_считается_вынесенной_в_заголовок(self):
        """Регресс: контур однажды засчитал внедрение, где ничего не меняли.

        Поручению «вынести фразу в заголовок» недостаточно того, что фраза и
        так была в тексте абзацем ниже. Именно на этом контур ошибся 01.09.2026,
        отправив пять страниц под мораторий без единой правки.
        """
        только_заголовки = package(действия=[
            {"kind": "заголовки", "steps": ["«купить figma на компанию»"]}])
        experiments = []
        lifecycle.register(experiments, [только_заголовки], "2026-09-01")
        в_тексте = page(body="здесь можно купить figma на компанию по счёту")
        moved = lifecycle.detect_implementation(
            experiments, self.snapshots, "2026-09-05",
            loader=lambda url, kind: в_тексте)
        self.assertEqual(moved, [])
        self.assertEqual(experiments[0].state, jr.STATE_PROPOSED)

        # А вынесенная в подзаголовок — считается.
        в_заголовке = page(headings=["Купить figma на компанию"],
                           body="здесь можно купить figma на компанию")
        moved = lifecycle.detect_implementation(
            experiments, self.snapshots, "2026-09-05",
            loader=lambda url, kind: в_заголовке)
        self.assertEqual(len(moved), 1)

    def test_выполнение_требований_переводит_в_наблюдение(self):
        сделано = page(body="оплата figma юрлицом теперь описана",
                       headings=["Купить figma на компанию"])
        moved = lifecycle.detect_implementation(
            self.experiments, self.snapshots, "2026-09-05",
            loader=lambda url, kind: сделано)
        self.assertEqual(len(moved), 1)
        exp = self.experiments[0]
        self.assertEqual(exp.state, jr.STATE_WATCH)
        self.assertEqual(exp.implemented_at, "2026-09-05")
        self.assertEqual(exp.watch_until, "2026-09-19")
        self.assertIsNotNone(exp.baseline.get("медиана_позиций"))

    def test_недоступная_страница_не_даёт_ложного_внедрения(self):
        moved = lifecycle.detect_implementation(
            self.experiments, self.snapshots, "2026-09-05",
            loader=lambda url, kind: page(available=False))
        self.assertEqual(moved, [])


class TestMoratorium(unittest.TestCase):
    def test_страница_на_замере_под_мораторием(self):
        experiments = []
        lifecycle.register(experiments, [package()], "2026-09-01")
        experiments[0].state = jr.STATE_WATCH
        experiments[0].watch_until = "2026-09-19"
        frozen = lifecycle.moratorium(experiments)
        self.assertIn("https://biz-soft.pro/blog/x", frozen)

    def test_оценённый_эксперимент_мораторий_снимает(self):
        experiments = []
        lifecycle.register(experiments, [package()], "2026-09-01")
        experiments[0].state = jr.STATE_DONE
        self.assertEqual(lifecycle.moratorium(experiments), {})


class TestEvaluate(unittest.TestCase):
    def _experiment(self):
        experiments = []
        lifecycle.register(experiments, [package()], "2026-09-01")
        exp = experiments[0]
        exp.state = jr.STATE_WATCH
        exp.implemented_at = "2026-09-05"
        exp.watch_until = "2026-09-19"
        exp.baseline = {"дата": "2026-09-05",
                        "дни": ["2026-09-03", "2026-09-04"],
                        "медиана_позиций": 9.0}
        return experiments, exp

    def _snapshots(self, before_exp, after_exp, before_ctl, after_ctl):
        return {
            "2026-09-03": snapshot("2026-09-03",
                                   {"оплата figma юрлицом": before_exp,
                                    "купить figma на компанию": before_exp},
                                   {"контрольный запрос": before_ctl}),
            "2026-09-04": snapshot("2026-09-04",
                                   {"оплата figma юрлицом": before_exp,
                                    "купить figma на компанию": before_exp},
                                   {"контрольный запрос": before_ctl}),
            "2026-09-18": snapshot("2026-09-18",
                                   {"оплата figma юрлицом": after_exp,
                                    "купить figma на компанию": after_exp},
                                   {"контрольный запрос": after_ctl}),
            "2026-09-19": snapshot("2026-09-19",
                                   {"оплата figma юрлицом": after_exp,
                                    "купить figma на компанию": after_exp},
                                   {"контрольный запрос": after_ctl}),
        }

    def test_эффект_очищен_от_общего_сдвига_выдачи(self):
        """Выдача сама поднялась на 2 позиции — в заслугу правке не идёт."""
        experiments, exp = self._experiment()
        snapshots = self._snapshots(before_exp=9, after_exp=4,
                                    before_ctl=10, after_ctl=8)
        lifecycle.evaluate_due(experiments, snapshots, "2026-09-19")
        outcome = exp.outcome
        self.assertEqual(outcome["дельта"], -5.0)
        self.assertEqual(outcome["контроль_дельта"], -2.0)
        self.assertEqual(outcome["чистый_эффект"], -3.0)
        self.assertEqual(outcome["вердикт"], jr.VERDICT_BETTER)

    def test_движение_вместе_со_всей_выдачей_не_считается_успехом(self):
        experiments, exp = self._experiment()
        snapshots = self._snapshots(before_exp=9, after_exp=7,
                                    before_ctl=9, after_ctl=7)
        lifecycle.evaluate_due(experiments, snapshots, "2026-09-19")
        self.assertEqual(exp.outcome["чистый_эффект"], 0.0)
        self.assertEqual(exp.outcome["вердикт"], jr.VERDICT_FLAT)

    def test_ухудшение_фиксируется(self):
        experiments, exp = self._experiment()
        snapshots = self._snapshots(before_exp=5, after_exp=12,
                                    before_ctl=9, after_ctl=9)
        lifecycle.evaluate_due(experiments, snapshots, "2026-09-19")
        self.assertEqual(exp.outcome["вердикт"], jr.VERDICT_WORSE)

    def test_окно_ещё_не_истекло_итога_нет(self):
        experiments, exp = self._experiment()
        snapshots = self._snapshots(9, 4, 10, 10)
        self.assertEqual(lifecycle.evaluate_due(experiments, snapshots,
                                                "2026-09-10"), [])
        self.assertEqual(exp.state, jr.STATE_WATCH)

    def test_вылет_из_топ20_не_улучшает_среднее(self):
        """Нет в выдаче — это позиция 21, а не отсутствие данных."""
        snap = snapshot("2026-09-19", {"запрос": None})
        self.assertEqual(lifecycle.positions_on(snap, ["запрос"])["запрос"],
                         jr.OUT_OF_TOP)

    def test_старый_снимок_без_позиций_не_считается_вылетом_из_топа(self):
        """Регресс: база показывала 21 и любой опыт выглядел успешным.

        Снимки до 01.09.2026 позиций не хранили. Отсутствие поля — это
        «не измеряли», а не «нас там не было».
        """
        старый = {"дата": "2026-08-30",
                  "по_запросам": {"запрос": {"наша": 0.1, "поле": 1.0}}}
        self.assertEqual(lifecycle.positions_on(старый, ["запрос"]), {})

        новый = snapshot("2026-09-01", {"запрос": None})
        self.assertEqual(lifecycle.positions_on(новый, ["запрос"])["запрос"],
                         jr.OUT_OF_TOP)

    def test_база_берёт_день_внедрения_если_прошлых_замеров_нет(self):
        snapshots = {"2026-08-30": {"дата": "2026-08-30",
                                    "по_запросам": {"запрос": {"наша": 0.1,
                                                               "поле": 1.0}}},
                     "2026-09-01": snapshot("2026-09-01", {"запрос": 7})}
        base = lifecycle.baseline_for(snapshots, "2026-09-01", ["запрос"], 3)
        self.assertEqual(base["медиана_позиций"], 7)
        self.assertIn("ещё не была на проде", base["_оговорка"])

    def test_контроль_не_включает_запросы_эксперимента(self):
        snapshots = self._snapshots(9, 4, 10, 8)
        control = lifecycle._control_queries(
            snapshots, ["2026-09-19"], ["оплата figma юрлицом"])
        self.assertIn("контрольный запрос", control)
        self.assertNotIn("оплата figma юрлицом", control)


class TestFairComparison(unittest.TestCase):
    """Нивелирование искажений, найденных при первом выполненном объёме работ.

    Правки вносились по одной версии методики, а замер пойдёт по другой; при
    этом часть правок была шаблонной и задела все страницы своего типа —
    включая те, что служат контролем. Без учёта обоих обстоятельств сравнение
    «было → стало» было бы сравнением разными линейками на загрязнённой
    контрольной группе.
    """

    def test_условия_базы_сохраняются(self):
        снимок = {"метаданные": {"версия_методики": "1.6.0",
                                 "хеш_конфига": "abc123",
                                 "ядро_хеш": "core1", "ядро_версия": "v2"}}
        experiments = []
        lifecycle.register(experiments, [package()], "2026-09-01", снимок)
        self.assertEqual(experiments[0].conditions["хеш_конфига"], "abc123")

    def test_смена_модели_помечает_сравнимость_ограниченной(self):
        база = {"версия_методики": "1.6.0", "хеш_конфига": "abc",
                "ядро_хеш": "core1"}
        сейчас = {"версия_методики": "1.7.0", "хеш_конфига": "xyz",
                  "ядро_хеш": "core1"}
        оценка, why = lifecycle.comparability(база, сейчас)
        self.assertEqual(оценка, "ограничена")
        self.assertIn("конфигурация модели", why)
        self.assertIn("приписывать всю разницу правке нельзя", why)

    def test_одинаковые_условия_дают_полную_сравнимость(self):
        одно = {"версия_методики": "1.6.0", "хеш_конфига": "abc",
                "ядро_хеш": "core1"}
        оценка, _ = lifecycle.comparability(одно, dict(одно))
        self.assertEqual(оценка, "полная")

    def test_шаблонная_правка_исключает_свой_тип_из_контроля(self):
        """Страницы, задетые той же правкой, контролем быть не могут."""
        snapshots = {"2026-09-01": {
            "дата": "2026-09-01",
            "по_запросам": {
                "запрос вендора": {"наша": 0.1, "поле": 1.0, "позиция": 5,
                                   "наш_url": "https://biz-soft.pro/vendors/x"},
                "запрос статьи": {"наша": 0.1, "поле": 1.0, "позиция": 6,
                                  "наш_url": "https://biz-soft.pro/blog/y"},
            }}}
        весь = lifecycle._control_queries(snapshots, ["2026-09-01"], [], [])
        чистый = lifecycle._control_queries(snapshots, ["2026-09-01"], [],
                                            ["vendor"])
        self.assertIn("запрос вендора", весь)
        self.assertNotIn("запрос вендора", чистый)
        self.assertIn("запрос статьи", чистый)

    def test_запрос_без_нашей_позиции_не_идёт_в_контроль(self):
        """Иначе сотни неподвижных 21 сделают контроль всегда нулевым."""
        snapshots = {"2026-09-01": {
            "дата": "2026-09-01",
            "по_запросам": {
                "нас нет": {"наша": 0.0, "поле": 1.0, "позиция": None,
                            "наш_url": None},
                "мы есть": {"наша": 0.1, "поле": 1.0, "позиция": 8,
                            "наш_url": "https://biz-soft.pro/blog/y"},
            }}}
        control = lifecycle._control_queries(snapshots, ["2026-09-01"], [], [])
        self.assertEqual(control, ["мы есть"])


class TestLearning(unittest.TestCase):
    def _done(self, kind, net, verdict=jr.VERDICT_BETTER):
        return jr.Experiment(id="EXP", created="2026-09-01", url="/x",
                             page_kind="blog", package_id="WP",
                             action_kinds=[kind], state=jr.STATE_DONE,
                             outcome={"чистый_эффект": net, "вердикт": verdict})

    def test_вывод_не_делается_на_малой_выборке(self):
        rows = learning.by_action_kind([self._done("текст", -3.0)])
        self.assertEqual(rows[0]["надёжность"], "предварительная")
        self.assertIn("наблюдений мало", rows[0]["вывод"])

    def test_порядок_действий_не_меняется_пока_данных_мало(self):
        self.assertEqual(learning.ranking([self._done("текст", -3.0)]), {})

    def test_после_порога_появляется_вывод(self):
        rows = learning.by_action_kind([self._done("текст", -2.0)] * 5)
        self.assertEqual(rows[0]["надёжность"], "рабочая")
        self.assertIn("работает", rows[0]["вывод"])
        self.assertEqual(learning.ranking([self._done("текст", -2.0)] * 5),
                         {"текст": -2.0})

    def test_воронка_считает_состояния(self):
        data = learning.funnel([self._done("текст", -2.0),
                                jr.Experiment(id="E2", created="", url="/y",
                                              page_kind="blog", package_id="WP")])
        self.assertEqual(data["по_состояниям"][jr.STATE_DONE], 1)
        self.assertEqual(data["по_состояниям"][jr.STATE_PROPOSED], 1)


if __name__ == "__main__":
    unittest.main()
