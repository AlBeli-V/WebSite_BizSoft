"""Изъяны отчёта за 10.09.2026: занятые страницы в поручениях и ноль вместо «нет данных».

Разбор веб-отчёта и письма того дня. Ни один из пяти дефектов ниже не был
покрыт тестами — все 326 существующих проверок проходили. Каждый тест здесь
падает на прежнем поведении.

  1. `mark()` возвращает готовое разделение пакетов на свободные и занятые,
     но run_daily брал только занятых, а packages оставлял нетронутым. Из 22
     пакетов раздела «План работ» 16 стояли на страницах, занятых замером
     базового SEO-контура; письмо поставило поручением дня WP-01 — страницу,
     занятую до 30.09. Правка там лишила бы оценки оба эксперимента сразу.
  2. `_leaderboard` звал `threat_mod.rank()` без `core_stable`, а у того
     значение по умолчанию True. Ядро выросло с 431 до 489 запросов, и из
     одного прогона вышли два ответа: письмо «Threat 36 из 70», отчёт —
     «полный режим (шкала 0–100)» с динамикой по разным ядрам, которую
     подвал того же отчёта запрещает.
  3. Строка плана складывала `traffic_upside or 0` и печатала «+0 переходов»
     там, где переходы не посчитаны ни по одному пакету. Ноль на месте
     отсутствия данных запрещён методикой самого отчёта.
  4. Счётчик состояний точек атаки ловил четыре статуса из шести; «снято с
     поручений» и «не поручение — проверка» падали в else с подписью «вне
     плана работ: запрос не сведён в пакет» — ложной для всех десяти.
  5. Статус контрольной группы начинается со слов «в очереди», и общий
     префикс засчитывал его в доступную работу.
"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from attack_engine import occupancy  # noqa: E402
from mailer import build_email, sections  # noqa: E402
from reports import deep_report  # noqa: E402
from scoring import threat as threat_mod  # noqa: E402

DATE = "2026-09-10"

SNAPSHOT = {
    "дата": DATE,
    "наши_показатели": {"доля_видимости": 0.058, "топ3": 8, "топ10": 27,
                        "запросов_в_поле": 60},
    "доли_по_категориям": {"H": 0.2, "A": 0.1},
    "лидеры": [{"домен": "raketapay.ru", "категория": "H", "доля": 0.093,
                "топ3": 16, "топ10": 31},
               {"домен": "biz-soft.pro", "категория": "A", "доля": 0.058,
                "топ3": 8, "топ10": 27}],
    "покрытие": {"яндекс_запросов_с_данными": 60},
    "метаданные": {"версия_методики": "1.9.0"},
}


def attack(query: str, attack_id: str = "ATT-001") -> dict:
    return {"attack_id": attack_id, "query": query, "opportunity": 57,
            "confidence": "MEDIUM", "our_position": 4,
            "our_url": "https://biz-soft.pro/blog/framer",
            "rival_domain": "raketapay.ru", "rival_position": 1,
            "demand": 7, "demand_source": "webmaster",
            "commercial_intent": 0.7, "b2b_intent": 0.6,
            "breakdown": {"commercial": 16.5}, "notes": []}


def package(package_id: str, query: str, **over) -> dict:
    pkg = {"package_id": package_id,
           "url": f"https://biz-soft.pro/blog/{package_id.lower()}",
           "page_kind": "blog", "action": "Дописать текст",
           "queries": [query], "queries_count": 1,
           "demand_by_source": {"webmaster": 7},
           "demand_queries_by_source": {"webmaster": 1},
           "demand_coverage": "1/1", "potential_index": 0.06,
           "potential_label": "высокий", "traffic_upside": None,
           "upside_note": "перевод в переходы невозможен",
           "position_best": 4, "position_worst": 10, "effort": "L",
           "rivals": ["raketapay.ru"], "confidence": "MEDIUM",
           "действия": [], "уже_сделано": [], "не_рекомендуем": [],
           "checklist": []}
    pkg.update(over)
    return pkg


ЗАНЯТОСТЬ = {"степень": occupancy.BUSY_PAGE,
             "эксперимент": "content-6-clusters", "до": "2026-09-30"}
КОНТРОЛЬ = {"степень": occupancy.BUSY_CONTROL,
            "эксперимент": "money-a1-query-phrase", "до": "2026-10-06"}


class TestЗанятаяСтраницаНеПоручается(unittest.TestCase):
    """Дефект 1. Пакет по занятой странице — не работа сегодня."""

    def test_split_takeable_выводит_занятых_и_оставляет_контроль(self):
        занят = package("WP-01", "framer оплата", занятость=ЗАНЯТОСТЬ)
        контроль = package("WP-22", "hailuo оплата", занятость=КОНТРОЛЬ)
        свободен = package("WP-31", "recraft оплата")
        free, busy = occupancy.split_takeable([занят, контроль, свободен])
        self.assertEqual([занят], busy)
        self.assertEqual([контроль, свободен], free)

    def test_занятый_пакет_не_попадает_в_план_работ_отчёта(self):
        занят = package("WP-01", "framer оплата", занятость=ЗАНЯТОСТЬ)
        свободен = package("WP-31", "recraft оплата")
        html = deep_report.build(DATE, SNAPSHOT, None,
                                 [attack("framer оплата")], [], [],
                                 packages=[занят, свободен], core_stable=True)
        план = html.split('id="plan"')[1].split('id="blocked"')[0]
        self.assertNotIn("WP-01", план)
        self.assertIn("WP-31", план)

    def test_занятый_пакет_назван_в_своём_разделе_со_сроком(self):
        занят = package("WP-01", "framer оплата", занятость=ЗАНЯТОСТЬ)
        html = deep_report.build(DATE, SNAPSHOT, None,
                                 [attack("framer оплата")], [], [],
                                 packages=[package("WP-31", "recraft оплата")],
                                 blocked=[занят], core_stable=True)
        self.assertIn('id="blocked"', html)
        блок = html.split('id="blocked"')[1]
        self.assertIn("WP-01", блок)
        self.assertIn("content-6-clusters", блок)
        self.assertIn("2026-09-30", блок)

    def test_занятый_пакет_не_становится_поручением_дня_в_письме(self):
        занят = package("WP-01", "framer оплата", занятость=ЗАНЯТОСТЬ,
                        potential_index=0.9)
        свободен = package("WP-31", "recraft оплата", potential_index=0.01)
        meta = build_email.build(DATE, SNAPSHOT, None,
                                 attacks=[attack("framer оплата")],
                                 packages=[занят, свободен])
        self.assertNotIn("WP-01", meta["текст"])

    def test_занятый_пакет_не_попадает_в_текстовое_письмо(self):
        занят = package("WP-01", "framer оплата", занятость=ЗАНЯТОСТЬ,
                        potential_index=0.9)
        свободен = package("WP-31", "recraft оплата", potential_index=0.01)
        meta = build_email.build(DATE, SNAPSHOT, None,
                                 attacks=[attack("framer оплата")],
                                 packages=[свободен])
        txt = build_email.render_txt(meta, snapshot=SNAPSHOT,
                                     attacks=[attack("framer оплата")],
                                     packages=[занят, свободен])
        поручения = txt.split("ЧТО ПОРУЧИТЬ")[1]
        self.assertNotIn("WP-01", поручения)
        self.assertIn("WP-31", поручения)

    def test_письмо_называет_сколько_пакетов_ждёт_освобождения(self):
        занят = package("WP-01", "framer оплата", занятость=ЗАНЯТОСТЬ)
        note = sections.blocked_note([занят])
        self.assertIn("1", note)
        self.assertIn("2026-09-30", note)

    def test_условие_едет_вместе_с_поручением_дня(self):
        """Ограничение на том же уровне, где даётся поручение.

        Верхнюю часть письма читают полностью, карточку ниже — не всегда.
        Условие только в карточке значит работу, начатую молча.
        """
        контроль = package("WP-22", "hailuo оплата", занятость=КОНТРОЛЬ,
                           действия=[{"what": "Вынести запрос в подзаголовки",
                                      "effort": "S", "owner": "редактор",
                                      "steps": ["«купить аккаунт hailuo»"]}])
        meta = build_email.build(DATE, SNAPSHOT, None,
                                 attacks=[attack("hailuo оплата")],
                                 packages=[контроль])
        строка = [l for l in meta["текст"].split("\n")
                  if l.startswith("Что делать")][0]
        self.assertIn("WP-22", строка)
        self.assertIn("Условие", строка)
        self.assertIn("2026-10-06", строка)
        self.assertTrue(meta["лимит_соблюдён"])

    def test_свободный_пакет_условия_не_получает(self):
        свободен = package("WP-31", "recraft оплата",
                           действия=[{"what": "Дописать текст", "effort": "S",
                                      "owner": "редактор", "steps": ["«x»"]}])
        meta = build_email.build(DATE, SNAPSHOT, None,
                                 attacks=[attack("recraft оплата")],
                                 packages=[свободен])
        строка = [l for l in meta["текст"].split("\n")
                  if l.startswith("Что делать")][0]
        self.assertNotIn("Условие", строка)

    def test_контрольная_группа_остаётся_в_очереди_но_с_условием(self):
        контроль = package("WP-22", "hailuo оплата", занятость=КОНТРОЛЬ)
        note = sections.control_note(контроль)
        self.assertIn("money-a1-query-phrase", note)
        self.assertIn("2026-10-06", note)
        self.assertEqual("", sections.control_note(package("WP-31", "x")))


class TestРежимThreatОдинНаПрогон(unittest.TestCase):
    """Дефект 2. Отчёт и письмо не могут расходиться в режиме шкалы."""

    def test_leaderboard_требует_core_stable_явно(self):
        with self.assertRaises(TypeError):
            deep_report._leaderboard([], 60, {})

    def test_при_сменившемся_ядре_отчёт_не_уходит_в_полный_режим(self):
        история = {"raketapay.ru": [0.10, 0.10, 0.10, 0.09, 0.09, 0.09]}
        html = deep_report.build(DATE, SNAPSHOT, None, [], [], [],
                                 histories=история, core_stable=False)
        self.assertIn("базовый режим", html)
        self.assertNotIn("полный режим", html)

    def test_шкала_отчёта_совпадает_со_шкалой_письма(self):
        история = {"raketapay.ru": [0.10, 0.10, 0.10, 0.09, 0.09, 0.09]}
        rivals = [c for c in SNAPSHOT["лидеры"] if c["домен"] != "biz-soft.pro"]
        for core_stable in (True, False):
            ranked = threat_mod.rank(rivals, histories=история,
                                     queries_total=60, core_stable=core_stable)
            письмо = sections.threat_scale_hint(ranked)
            html = deep_report.build(DATE, SNAPSHOT, None, [], [], [],
                                     histories=история, core_stable=core_stable)
            шкала = ranked[0][1].scale_max
            self.assertIn(f"0–{шкала}", письмо)
            self.assertIn(f"шкала 0–{шкала}", html)


class TestНольНеСтоитНаМестеНетДанных(unittest.TestCase):
    """Дефект 3. Собственное правило отчёта: нет данных — не ноль."""

    def test_без_измеренных_переходов_ноль_не_печатается(self):
        строка = deep_report._upside_total(
            [package("WP-01", "x"), package("WP-02", "y")])
        self.assertNotIn("+0", строка)
        self.assertIn("не считается", строка)

    def test_измеренные_переходы_складываются(self):
        строка = deep_report._upside_total(
            [package("WP-01", "x", traffic_upside=1.2),
             package("WP-02", "y", traffic_upside=0.4)])
        self.assertIn("+2 перехода", строка.replace("переходов", "перехода"))

    def test_в_плане_работ_нет_нуля_переходов(self):
        html = deep_report.build(DATE, SNAPSHOT, None,
                                 [attack("framer оплата")], [], [],
                                 packages=[package("WP-31", "framer оплата")],
                                 core_stable=True)
        self.assertNotIn("+0\nпереходов", html)
        self.assertNotIn("+0 переходов", html)


class TestСчётчикСостоянийНеВрёт(unittest.TestCase):
    """Дефекты 4 и 5. Каждое состояние названо своим именем."""

    def сводка(self, packages, attacks):
        html = deep_report._attack_summary(attacks, packages, [])
        числа = dict(re.findall(
            r'<tr><td>([^<]+)</td>\s*<td class="num">(\d+)</td>', html))
        return {k.strip(): int(v) for k, v in числа.items()}

    def test_проверка_и_мораторий_не_числятся_вне_плана(self):
        packages = [
            package("WP-38", "notion business купить", очередь=False,
                    action="правок по репозиторию не требуется"),
            package("WP-04", "claude team купить",
                    причина_моратория="страница правилась вне контура",
                    мораторий_до="2026-09-19"),
        ]
        attacks = [attack("notion business купить", "ATT-028"),
                   attack("claude team купить", "ATT-026")]
        числа = self.сводка(packages, attacks)
        self.assertEqual(0, числа["Вне плана работ"])
        self.assertEqual(1, числа["Проверка, а не поручение"])
        self.assertEqual(
            1, числа["Снято с поручений: страницу правили вне контура"])

    def test_контрольная_группа_не_числится_очередью(self):
        packages = [package("WP-22", "hailuo оплата", занятость=КОНТРОЛЬ),
                    package("WP-31", "recraft оплата")]
        attacks = [attack("hailuo оплата", "ATT-050"),
                   attack("recraft оплата", "ATT-051")]
        числа = self.сводка(packages, attacks)
        self.assertEqual(1, числа["В очереди на работу"])
        self.assertEqual(
            1, числа["Кластер — контрольная группа чужого замера"])

    def test_сумма_состояний_равна_числу_точек(self):
        packages = [package("WP-01", "framer оплата", занятость=ЗАНЯТОСТЬ),
                    package("WP-22", "hailuo оплата", занятость=КОНТРОЛЬ),
                    package("WP-31", "recraft оплата"),
                    package("WP-38", "notion купить", очередь=False)]
        attacks = [attack("framer оплата", "ATT-001"),
                   attack("hailuo оплата", "ATT-002"),
                   attack("recraft оплата", "ATT-003"),
                   attack("notion купить", "ATT-004"),
                   attack("чужой запрос", "ATT-005")]
        числа = self.сводка(packages, attacks)
        self.assertEqual(len(attacks), sum(числа.values()))
        self.assertEqual(1, числа["Вне плана работ"])


if __name__ == "__main__":
    unittest.main()


class TestПревосходствоИзмеряетсяАНеПриближается(unittest.TestCase):
    """Дефект 6. Компонент весом 20 из 100 ни разу не был измерен.

    `above_us` — «по скольким запросам домен стоит выше нас» — не передавал
    ни один вызов, и Threat всегда подменял его числом ТОП-3. Приближение не
    просто занижало оценку: оно меняло порядок. Конкурент, который редко
    берёт ТОП-3, но стабильно стоит выше нас, уходил вниз рейтинга —
    10.09.2026 aifory.pro при ТОП-3 по 4 запросам стоял выше нас по 67.
    """

    def test_registry_считает_выше_нас(self):
        from discovery import registry, serp_source

        def строка(query, *domains):
            return serp_source.SerpRow(
                date=DATE, query=query, region="213",
                top=[{"domain": d, "url": f"https://{d}/p", "title": d}
                     for d in domains])

        rows = [строка("q1", "rival.ru", "biz-soft.pro"),
                строка("q2", "biz-soft.pro", "rival.ru"),
                строка("q3", "rival.ru")]
        from scoring import visibility
        cards = {c.domain: c
                 for c in registry.build(rows, visibility.load_config())}
        # q1 — выше, q2 — ниже, q3 — нас нет вовсе, значит выше.
        self.assertEqual(2, cards["rival.ru"].above_us)
        self.assertEqual(0, cards["biz-soft.pro"].above_us)

    def test_threat_берёт_величину_из_карточки(self):
        карточка = {"домен": "r.ru", "доля": 0.09, "топ3": 4, "топ10": 100,
                    "выше_нас": 67}
        оценка = threat_mod.score(карточка, queries_total=639,
                                  core_stable=False)
        self.assertIn("по запросам выше BIZSoft", оценка.explanation)
        self.assertNotIn("приближение", оценка.explanation)

    def test_без_величины_приближение_помечено(self):
        карточка = {"домен": "r.ru", "доля": 0.09, "топ3": 4, "топ10": 100}
        оценка = threat_mod.score(карточка, queries_total=639,
                                  core_stable=False)
        self.assertIn("приближение по ТОП-3", оценка.explanation)

    def test_приближение_делало_тихого_конкурента_неразличимым(self):
        """Ради чего правка: цифры с реального прогона 10.09.2026.

        aifory.pro берёт ТОП-3 всего по 4 запросам, но стоит выше нас по 67.
        migsoft.ru берёт ТОП-3 по 13, а выше нас стоит по 32. Приближение по
        ТОП-3 даёт обоим одинаковую оценку — тихий конкурент неотличим от
        шумного. Измерение их разводит.
        """
        тихий = {"домен": "aifory.pro", "доля": 0.011, "топ3": 4,
                 "топ10": 100, "выше_нас": 67}
        шумный = {"домен": "migsoft.ru", "доля": 0.010, "топ3": 13,
                  "топ10": 60, "выше_нас": 32}
        без = [{k: v for k, v in c.items() if k != "выше_нас"}
               for c in (тихий, шумный)]
        оценка = lambda c: threat_mod.score(c, queries_total=639,
                                            core_stable=False).score
        self.assertEqual(оценка(без[0]), оценка(без[1]))
        self.assertGreater(оценка(тихий), оценка(шумный))


class TestЧитабельность(unittest.TestCase):
    """Повтор, который читатель пролистывает, ничего из него не узнавая.

    Блок «не рекомендуем» состоит из общих ограничений (ссылки, поведенческие
    факторы, общие формулировки) и адресных — тех, что начинаются с самой
    формулировки запроса. Общие одинаковы у всех пакетов: на 22 пакетах это
    66 одинаковых строк внутри карточек. Сказать их надо один раз.
    """

    def пакет(self, package_id, *адресные):
        общие = ["внешние ссылки и их закупка: ссылочный профиль этим "
                 "контуром не измеряется",
                 "поведенческие факторы: данные Метрики не заведены"]
        return package(package_id, f"запрос {package_id}",
                       не_рекомендуем=[*общие, *адресные])

    def test_общее_ограничение_названо_один_раз(self):
        packages = [self.пакет(f"WP-{i:02d}") for i in range(1, 6)]
        html = deep_report.build(DATE, SNAPSHOT, None, [], [], [],
                                 packages=packages, core_stable=True)
        self.assertEqual(1, html.count("ссылочный профиль этим контуром"))

    def test_адресное_ограничение_остаётся_в_карточке(self):
        адресное = "«framer оплата»: бренд конкурента в свой текст не вписываем"
        packages = [self.пакет("WP-01", адресное), self.пакет("WP-02")]
        html = deep_report.build(DATE, SNAPSHOT, None, [], [], [],
                                 packages=packages, core_stable=True)
        карточка = html.split('id="pkg-wp-01"')[1].split("</details>")[0]
        self.assertIn("бренд конкурента", карточка)
        вторая = html.split('id="pkg-wp-02"')[1].split("</details>")[0]
        self.assertNotIn("бренд конкурента", вторая)

    def test_без_общих_ограничений_блока_нет(self):
        self.assertEqual("", deep_report._общие_ограничения_блок(
            [package("WP-01", "x", не_рекомендуем=[])]))


class TestСтрокаЭкспериментов(unittest.TestCase):
    """Запас по состояниям — не поток через воронку.

    «предложено 22, на наблюдении 23, оценено 0» читается как «22, из которых
    23», то есть как невозможное. Опыт стоит ровно в одном состоянии, и
    строка обязана называть общее число, а доли — текущими состояниями.
    """

    def опыты(self, предложено, наблюдение):
        from experiments import journal as jr
        def опыт(идентификатор, url, состояние):
            return jr.Experiment(id=идентификатор, created=DATE, url=url,
                                 page_kind="blog", package_id="WP-01",
                                 state=состояние)
        return ([опыт(f"EXP-{i:04d}", f"/p{i}", jr.STATE_PROPOSED)
                 for i in range(предложено)]
                + [опыт(f"EXP-9{i:03d}", f"/w{i}", jr.STATE_WATCH)
                   for i in range(наблюдение)])

    def test_названо_общее_число_и_состояния(self):
        from experiments import learning as lr
        строка = lr.summary_line(self.опыты(22, 23))
        self.assertIn("всего 45", строка)
        self.assertIn("ждут внедрения 22", строка)
        self.assertIn("на замере 23", строка)

    def test_пустой_журнал_говорит_прямо(self):
        from experiments import learning as lr
        self.assertIn("журнал пуст", lr.summary_line([]))


class TestПеререраспределениеВесаНазваноТочно(unittest.TestCase):
    """Дефект 7. Утверждение о методе, которое метод опровергает.

    Отчёт писал «недоступные факторы не заменяются средним». Арифметически
    перераспределение веса ТОЖДЕСТВЕННО подстановке недоступному фактору
    взвешенного среднего измеренных. Формулировка была верна против прежнего
    поведения (общая константа 0,5) и неверна как утверждение о нынешнем
    методе — причём вводила в заблуждение ровно там, где нужна осторожность:
    у цели, сильной по всем измеренным факторам, недоступная уязвимость
    считается такой же сильной.
    """

    def test_перераспределение_равно_подстановке_среднего(self):
        from scoring import opportunity as op
        знач = {"commercial": 0.9, "b2b": 0.8, "proximity": 0.4,
                "demand": 0.2, "page_improvement": 0.6, "vendor": 0.5}
        измеренные = {k: op.WEIGHTS[k] for k in знач}
        норм = op.normalize_weights(set(знач))
        с_перераспределением = sum(норм[k] * знач[k] for k in знач)
        среднее = (sum(измеренные[k] * знач[k] for k in знач)
                   / sum(измеренные.values()))
        с_подстановкой = (sum(op.WEIGHTS[k] * знач[k] for k in знач)
                          + op.WEIGHTS["vulnerability"] * среднее)
        self.assertAlmostEqual(с_перераспределением, с_подстановкой, places=9)

    def test_отчёт_больше_не_утверждает_обратное(self):
        html = deep_report.build(DATE, SNAPSHOT, None,
                                 [attack("framer оплата")], [], [],
                                 core_stable=True)
        self.assertNotIn("не заменяются средним", html)
        self.assertIn("тоже подстановка", html)

    def test_смещение_названо_направленным(self):
        html = deep_report._opportunity_caveat()
        self.assertIn("Смещение направленное", html)
        self.assertIn("уверенность", html.lower())


class TestШтрафЗаОтсутствиеПоГлубинеСреза(unittest.TestCase):
    """Дефект 8. Штраф за отсутствие не соответствовал глубине выдачи.

    Константа была 21 при реальной глубине среза Яндекса 10: страница на
    11-м месте получала штраф как за 21-е. Эффект правки считается по
    изменению медианной позиции, поэтому пересечение границы топ-10
    перевешивало всё остальное — уход с 9-го на 11-е выглядел падением на 12
    позиций вместо двух.
    """

    def test_штраф_берётся_из_глубины_снимка(self):
        from experiments import journal as jr
        снимок = {"покрытие": {"глубина_яндекс": 10}}
        self.assertEqual(11, jr.out_of_top(снимок))
        self.assertEqual(21, jr.out_of_top({"покрытие": {"глубина_яндекс": 20}}))

    def test_без_глубины_остаётся_запасное_значение(self):
        from experiments import journal as jr
        self.assertEqual(jr.OUT_OF_TOP, jr.out_of_top({}))
        self.assertEqual(jr.OUT_OF_TOP, jr.out_of_top(None))

    def test_позиции_дня_используют_глубину(self):
        from experiments import lifecycle as lc
        снимок = {"покрытие": {"глубина_яндекс": 10},
                  "по_запросам": {"framer оплата": {"позиция": None},
                                  "recraft оплата": {"позиция": 4}}}
        позиции = lc.positions_on(снимок, ["framer оплата", "recraft оплата"])
        self.assertEqual(11, позиции["framer оплата"])
        self.assertEqual(4, позиции["recraft оплата"])

    def test_отчёт_называет_настоящую_глубину(self):
        html = deep_report.build(DATE, SNAPSHOT, None, [], [], [],
                                 core_stable=True)
        self.assertNotIn("Отсутствие в ТОП-20 считается позицией 21", html)


class TestРядДинамикиДостижим(unittest.TestCase):
    """Дефект 10. Вердикт был недостижим по построению, и отчёт молчал.

    Строгий ряд требует ОДНУ корзину запросов на все дни. Ядро контура росло
    почти ежедневно, и общее пересечение по построению только сжималось: на
    11 снимках оно упало до 59 из 489 — 12% при пороге 70%. Ряд оказывался
    пустым, а вердикт сообщал «не хватает 6 измерений», что читалось как
    «подождите». Ждать было бесполезно.

    При этом соседние дни сравнимы отлично — попарные пересечения 86–100%.
    Отсюда сцепление: каждая пара сравнивается по своему пересечению.
    """

    def снимок(self, дата, запросы, доли):
        return {"дата": дата,
                "по_запросам": {q: {"наша": доли.get(q, 0.0), "поле": 1.0}
                                for q in запросы}}

    def test_растущее_ядро_убивает_строгий_ряд(self):
        from decision_engine import kpi as k
        снимки = [self.снимок(f"2026-09-0{i}",
                              [f"q{n}" for n in range(i * 10)],
                              {f"q{n}": 0.05 for n in range(i * 10)})
                  for i in range(1, 8)]
        строгий, _ = k.comparable_series(снимки)
        self.assertEqual([], строгий)

    def test_сцепление_даёт_ряд_там_где_строгий_пуст(self):
        from decision_engine import kpi as k
        # Ядро растёт на 10% в день, как в жизни: соседние дни сравнимы
        # (91%), а общее пересечение падает до 56% и строгий ряд гибнет.
        снимки = []
        размер = 100
        for i in range(1, 8):
            запросы = [f"q{n}" for n in range(размер)]
            снимки.append(self.снимок(f"2026-09-0{i}", запросы,
                                      {q: 0.05 + i * 0.001 for q in запросы}))
            размер = int(размер * 1.10)
        ряд, вид, _ = k.trend_basis(снимки)
        self.assertEqual("сцепленный", вид)
        self.assertGreaterEqual(len(ряд), 2)

    def test_строгий_ряд_предпочитается_когда_есть(self):
        from decision_engine import kpi as k
        запросы = [f"q{n}" for n in range(100)]
        снимки = [self.снимок(f"2026-09-0{i}", запросы,
                              {q: 0.05 for q in запросы}) for i in range(1, 8)]
        _, вид, _ = k.trend_basis(снимки)
        self.assertEqual("строгий", вид)

    def test_разрыв_цепи_обрезает_отрезок(self):
        from decision_engine import kpi as k
        общие = [f"q{n}" for n in range(100)]
        чужие = [f"z{n}" for n in range(100)]
        снимки = [self.снимок("2026-09-01", общие, {q: 0.05 for q in общие}),
                  self.снимок("2026-09-02", чужие, {q: 0.05 for q in чужие}),
                  self.снимок("2026-09-03", чужие, {q: 0.06 for q in чужие}),
                  self.снимок("2026-09-04", чужие, {q: 0.07 for q in чужие})]
        ряд, мета = k.chained_series(снимки)
        self.assertEqual("2026-09-02", мета["отрезок_с"])
        self.assertEqual(3, len(ряд))

    def test_вердикт_называет_сколько_измерений_есть(self):
        from decision_engine import kpi as k
        показатели = k.build_kpi(SNAPSHOT, None)
        _, почему = k.verdict(показатели, [0.05] * 4)
        self.assertIn("есть 4", почему)
        self.assertIn("не хватает 2", почему)


class TestПолосаКандидатаПоДанным(unittest.TestCase):
    """Дефект 11. Отчёт обещал охват, которого не было.

    Полоса кандидата объявлена «мы на 4–20», а срез Яндекса собирается
    глубиной 10: позиций 11–20 в данных нет ни одной. Запрос, где мы
    одиннадцатые, попадал не в «есть куда расти», а в «нас нет в выдаче
    вовсе» — контур был слеп к полосе, которую считал своей.
    """

    def строка(self, query, *domains):
        from discovery import serp_source
        return serp_source.SerpRow(
            date=DATE, query=query, region="213",
            top=[{"domain": d, "url": f"https://{d}/p", "title": d}
                 for d in domains])

    def test_полоса_ограничена_глубиной_среза(self):
        from attack_engine import strike_list as sl
        десять = [self.строка("q", *[f"r{i}.ru" for i in range(10)])]
        self.assertEqual((4, 10), sl.band(десять))

    def test_при_глубокой_выдаче_полоса_шире(self):
        from attack_engine import strike_list as sl
        двадцать = [self.строка("q", *[f"r{i}.ru" for i in range(20)])]
        self.assertEqual((4, 20), sl.band(двадцать))

    def test_потолок_не_превышается(self):
        from attack_engine import strike_list as sl
        глубокая = [self.строка("q", *[f"r{i}.ru" for i in range(40)])]
        self.assertEqual(sl.OUR_POSITION_MAX, sl.band(глубокая)[1])

    def test_отчёт_печатает_фактическую_полосу(self):
        точки = [attack("q1"), dict(attack("q2"), our_position=9)]
        self.assertEqual("4–9", deep_report._полоса(точки))

    def test_без_точек_полоса_не_выдумывается(self):
        self.assertEqual("4–10", deep_report._полоса([]))
