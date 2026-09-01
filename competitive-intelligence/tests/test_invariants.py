"""Инвариант-тесты модели: свойства, которые обязаны выполняться всегда.

Обычный unit-тест проверяет один пример: «при таких входных данных выходит
такое число». Инвариант-тест проверяет утверждение обо всей модели: «эта
величина не может убывать», «результат не зависит от порядка», «неизвестное
никогда не превращается в ноль». Внешний аудит методики (четвёртый раунд,
31.08.2026) справедливо заметил, что именно такие свойства и составляют
методику — а проверялись до сих пор только примеры.

Каждый тест ниже соответствует утверждению из docs/competitive/methodology.md.
Если тест падает — это не сломанный код, а нарушенное обещание документа, и
чинить нужно то из двух, что неверно.
"""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from attack_engine import work_packages  # noqa: E402
from competitors import classifier  # noqa: E402
from decision_engine import kpi as kpi_mod  # noqa: E402
from decision_engine import signal as signal_mod  # noqa: E402
from discovery import query_set, registry, run_discovery, serp_source  # noqa: E402
from scoring import opportunity as opp  # noqa: E402
from scoring import threat as threat_mod  # noqa: E402
from scoring import visibility  # noqa: E402


def base_args(**over):
    args = dict(commercial=0.8, b2b=0.6, our_position=7, has_page=True,
                frequency=400, demand_source="wordstat", vulnerability=0.5,
                vendor_priority=0.5)
    args.update(over)
    return args


# --- 1. Правило недоступных факторов ---------------------------------------

class TestMissingFactors(unittest.TestCase):
    """Одно правило на любое число недоступных факторов, порядок не важен."""

    def test_1_исключение_факторов_коммутативно(self):
        """Результат не зависит от порядка, в котором факторы стали неизвестны.

        Главная претензия четвёртой рецензии: пока правил было два (ручное
        перераспределение веса уязвимости и пропорциональная нормализация для
        остальных), итог зависел от того, какой фактор пропал первым.
        """
        сначала_спрос = opp.normalize_weights(
            {"commercial", "b2b", "proximity", "page_improvement", "vendor"})
        сначала_уязвимость = opp.normalize_weights(
            {"vendor", "page_improvement", "proximity", "b2b", "commercial"})
        self.assertEqual(сначала_спрос, сначала_уязвимость)

    def test_2_веса_активного_набора_всегда_дают_сто(self):
        for available in (
                set(opp.WEIGHTS),
                {"commercial", "b2b"},
                {"commercial", "b2b", "proximity", "demand"},
                {"vendor"}):
            with self.subTest(available=sorted(available)):
                weights = opp.normalize_weights(available)
                self.assertAlmostEqual(sum(weights.values()), 100, places=6)

    def test_3_недоступный_фактор_не_подменяется_средним(self):
        """Неизвестный спрос ≠ спрос 0,5 и ≠ спрос 0."""
        неизвестен = opp.score(**base_args(frequency=None))
        средний = opp.score(**base_args(frequency=500))
        нулевой = opp.score(**base_args(frequency=0))
        self.assertNotEqual(неизвестен.score, средний.score)
        self.assertNotEqual(неизвестен.score, нулевой.score)
        self.assertIn("demand", неизвестен.missing)

    def test_4_каждый_недоступный_фактор_понижает_уверенность(self):
        полный = opp.score(**base_args())
        без_одного = opp.score(**base_args(vulnerability=None))
        без_двух = opp.score(**base_args(vulnerability=None, frequency=None))
        self.assertEqual(полный.confidence, "HIGH")
        self.assertEqual(без_одного.confidence, "MEDIUM")
        self.assertEqual(без_двух.confidence, "LOW")

    def test_5_ключ_сравнимости_различает_наборы_факторов(self):
        полный = opp.score(**base_args())
        без_уязвимости = opp.score(**base_args(vulnerability=None))
        без_спроса = opp.score(**base_args(vulnerability=None, frequency=None))
        ключи = {полный.comparable_key, без_уязвимости.comparable_key,
                 без_спроса.comparable_key}
        self.assertEqual(len(ключи), 3)

    def test_6_оценка_монотонна_по_спросу(self):
        ряд = [opp.score(**base_args(frequency=f)).score
               for f in (10, 100, 400, 900, 5000)]
        self.assertEqual(ряд, sorted(ряд))

    def test_7_оценка_монотонна_по_близости_позиции(self):
        ряд = [opp.score(**base_args(our_position=p)).score
               for p in (18, 12, 8, 5)]
        self.assertEqual(ряд, sorted(ряд))


# --- 2. Компоненты Threat ---------------------------------------------------

class TestThreatComponents(unittest.TestCase):
    """Явные формулы компонентов и заданное поведение на краях."""

    def test_8_присутствие_монотонно_и_насыщается(self):
        ряд = [threat_mod.presence_component(s)
               for s in (0.0, 0.02, 0.07, 0.15, 0.4)]
        self.assertEqual(ряд, sorted(ряд))
        self.assertEqual(ряд[-1], threat_mod.WEIGHT_PRESENCE)
        self.assertEqual(ряд[-2], threat_mod.WEIGHT_PRESENCE)

    def test_9_превосходство_ограничено_своим_весом(self):
        self.assertEqual(threat_mod.superiority_component(0, 100), 0.0)
        self.assertEqual(threat_mod.superiority_component(100, 100),
                         threat_mod.WEIGHT_SUPERIORITY)
        self.assertEqual(threat_mod.superiority_component(500, 100),
                         threat_mod.WEIGHT_SUPERIORITY)

    def test_10_падение_не_даёт_баллов_но_сохраняется_числом(self):
        """Отрицательная динамика = 0 баллов, но само значение не теряется."""
        self.assertEqual(threat_mod.momentum_component(-5.0), 0.0)
        self.assertEqual(threat_mod.momentum_component(0.0), 0.0)
        self.assertGreater(threat_mod.momentum_component(1.0), 0.0)
        card = {"домен": "x", "доля": 0.05, "топ3": 3, "топ10": 8}
        падение = threat_mod.score(card, queries_total=100,
                                   history=[0.06] * 3 + [0.04] * 3)
        self.assertEqual(падение.breakdown["динамика"], 0.0)
        self.assertLess(падение.momentum_pp, 0)
        self.assertIn("падение", падение.explanation)

    def test_11_шкала_режима_не_превышается(self):
        card = {"домен": "x", "доля": 0.9, "топ3": 100, "топ10": 100}
        базовый = threat_mod.score(card, queries_total=10)
        полный = threat_mod.score(card, queries_total=10,
                                  history=[0.1] * 3 + [0.9] * 3)
        self.assertLessEqual(базовый.score, threat_mod.MAX_BASE)
        self.assertLessEqual(полный.score, threat_mod.MAX_FULL)
        self.assertEqual(базовый.scale_max, threat_mod.MAX_BASE)
        self.assertEqual(полный.scale_max, threat_mod.MAX_FULL)

    def test_12_появление_истории_меняет_режим_а_не_положение(self):
        """Оценки разных режимов не сравниваются: у них разные знаменатели."""
        card = {"домен": "x", "доля": 0.05, "топ3": 3, "топ10": 8}
        без_истории = threat_mod.score(card, queries_total=100)
        с_историей = threat_mod.score(card, queries_total=100,
                                      history=[0.05] * 6)
        self.assertNotEqual(без_истории.comparable_key, с_историей.comparable_key)
        # Компоненты, не зависящие от истории, при этом неизменны
        self.assertEqual(без_истории.breakdown["присутствие"],
                         с_историей.breakdown["присутствие"])

    def test_13_смена_состава_ядра_отменяет_динамику(self):
        card = {"домен": "x", "доля": 0.05, "топ3": 3, "топ10": 8}
        нестабильное = threat_mod.score(card, queries_total=100,
                                        history=[0.01] * 3 + [0.05] * 3,
                                        core_stable=False)
        self.assertEqual(нестабильное.mode, threat_mod.MODE_BASE)
        self.assertIn("состав ядра", нестабильное.explanation)


# --- 3. Индекс потенциала и покрытие спроса ---------------------------------

def attack(query, url, position, demand, source="wordstat"):
    return {"attack_id": "ATT-001", "query": query, "our_url": url,
            "our_position": position, "demand": demand,
            "rival_domain": "raketapay.ru", "rival_position": 1,
            "opportunity": 60, "confidence": "MEDIUM", "demand_source": source}


class TestPotentialIndex(unittest.TestCase):
    def test_14_без_измеренного_спроса_индекса_нет(self):
        packages = work_packages.build([
            attack("q1", "https://biz-soft.pro/vendors/x", 6, None, "none"),
            attack("q2", "https://biz-soft.pro/vendors/x", 8, None, "none"),
        ])
        pkg = packages[0]
        self.assertIsNone(pkg.potential_index)
        self.assertEqual(pkg.potential_label, "не оценён")
        self.assertEqual(pkg.demand_coverage, "0/2")

    def test_15_частичное_покрытие_подписано_и_не_считается_нулём(self):
        """Запрос с неизвестным спросом не входит в индекс и не обнуляет его."""
        частично = work_packages.build([
            attack("q1", "https://biz-soft.pro/vendors/x", 6, 500),
            attack("q2", "https://biz-soft.pro/vendors/x", 8, None, "none"),
        ])[0]
        только_измеренный = work_packages.build([
            attack("q1", "https://biz-soft.pro/vendors/x", 6, 500),
        ])[0]
        self.assertEqual(частично.demand_coverage, "1/2")
        self.assertAlmostEqual(частично.potential_index,
                               только_измеренный.potential_index, places=6)
        self.assertIn("1 запросам из 2", частично.potential_note)

    def test_16_пакеты_без_индекса_уходят_в_конец_очереди(self):
        packages = work_packages.build([
            attack("q1", "https://biz-soft.pro/vendors/a", 6, None, "none"),
            attack("q2", "https://biz-soft.pro/vendors/b", 6, 800),
        ])
        self.assertIsNotNone(packages[0].potential_index)
        self.assertIsNone(packages[-1].potential_index)


# --- 4. Сравнимость ядра ----------------------------------------------------

def snapshot(date, core, ours, field, *, core_hash=None):
    """Снимок с по-запросной видимостью: ours и field — словари по запросам."""
    queries = sorted(core)
    return {
        "дата": date,
        "ядро_запросов": {"хеш": core_hash or query_set.fingerprint(queries),
                          "версия": "v1", "запросов": len(queries),
                          "запросы": queries},
        "по_запросам": {q: {"наша": ours.get(q, 0.0), "поле": field.get(q, 1.0)}
                        for q in queries},
        "наши_показатели": {"доля_видимости": (sum(ours.values())
                                               / sum(field.get(q, 1.0)
                                                     for q in queries)),
                            "топ3": 1, "топ10": 3, "запросов_в_поле": len(queries)},
        "покрытие": {"яндекс_запросов_всего": len(queries),
                     "яндекс_запросов_с_данными": len(queries), "google": None},
    }


class TestComparableCore(unittest.TestCase):
    def test_17_отпечаток_ядра_не_зависит_от_порядка_и_регистра(self):
        a = query_set.fingerprint(["Купить Figma", "zoom для юрлиц"])
        b = query_set.fingerprint(["zoom  ДЛЯ  юрлиц", "купить figma"])
        self.assertEqual(a, b)
        self.assertNotEqual(a, query_set.fingerprint(["купить figma"]))

    def test_18_смена_состава_ядра_не_создаёт_ложной_динамики(self):
        """Добавили запросы, где нас нет, — сравнимая доля не изменилась."""
        вчера = snapshot("2026-09-01", ["a", "b"], {"a": 0.2, "b": 0.2},
                         {"a": 1.0, "b": 1.0})
        сегодня = snapshot("2026-09-02", ["a", "b", "c"],
                           {"a": 0.2, "b": 0.2, "c": 0.0},
                           {"a": 1.0, "b": 1.0, "c": 1.0})
        kpi = kpi_mod.build_kpi(сегодня, вчера)
        self.assertTrue(kpi.core_changed)
        # Доля в текущем поле упала (добавились запросы, где нас нет)…
        self.assertLess(сегодня["наши_показатели"]["доля_видимости"],
                        вчера["наши_показатели"]["доля_видимости"])
        # …а сравнимая доля не изменилась: в выдаче ничего не произошло.
        self.assertEqual(kpi.share_delta_pp, 0.0)
        self.assertIn("пересечение ядер", kpi.delta_basis)

    def test_19_при_неизменном_ядре_дельта_совпадает_с_разницей_долей(self):
        вчера = snapshot("2026-09-01", ["a", "b"], {"a": 0.2, "b": 0.2},
                         {"a": 1.0, "b": 1.0})
        сегодня = snapshot("2026-09-02", ["a", "b"], {"a": 0.3, "b": 0.2},
                           {"a": 1.0, "b": 1.0})
        kpi = kpi_mod.build_kpi(сегодня, вчера)
        self.assertFalse(kpi.core_changed)
        ожидаемо = round(100 * (сегодня["наши_показатели"]["доля_видимости"]
                                - вчера["наши_показатели"]["доля_видимости"]), 2)
        self.assertEqual(kpi.share_delta_pp, ожидаемо)
        self.assertEqual(kpi.delta_basis, "то же ядро")

    def test_20_слишком_малое_пересечение_отменяет_ряд(self):
        дни = [snapshot("2026-09-01", ["a", "b", "c", "d"], {}, {}),
               snapshot("2026-09-02", ["a", "x", "y", "z"], {}, {})]
        ряд, meta = kpi_mod.comparable_series(дни)
        self.assertEqual(ряд, [])
        self.assertIn("меньше порога", meta["причина"])

    def test_21_ряд_считается_по_общему_подмножеству(self):
        дни = [snapshot(f"2026-09-0{i}", ["a", "b", "c"],
                        {"a": 0.1 * i, "b": 0.1, "c": 0.1},
                        {"a": 1.0, "b": 1.0, "c": 1.0}) for i in range(1, 7)]
        ряд, meta = kpi_mod.comparable_series(дни)
        self.assertEqual(len(ряд), 6)
        self.assertEqual(meta["пересечение"], 3)
        self.assertIsNotNone(kpi_mod.trend_change(ряд))

    def test_22_версия_ядра_присваивается_один_раз(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "query-sets.json")
            первый = query_set.describe(["a", "b"], "2026-09-01", path)
            повтор = query_set.describe(["b", "a"], "2026-09-02", path)
            другой = query_set.describe(["a", "b", "c"], "2026-09-03", path)
            self.assertEqual(первый["версия"], повтор["версия"])
            self.assertNotEqual(первый["версия"], другой["версия"])


# --- 5. Покрытие данных и NO DATA ------------------------------------------

class TestCoverageAndNoData(unittest.TestCase):
    def test_23_двойной_гейт_покрытия(self):
        """Много запросов и мало спроса — это тоже непригодный день."""
        снимок = {"покрытие": {"яндекс_запросов_всего": 100,
                               "яндекс_запросов_с_данными": 95,
                               "взвешенное_покрытие": {"wordstat": 0.42},
                               "google": None}}
        состояние, why = kpi_mod.coverage_state(снимок)
        self.assertEqual(состояние, "критическое")
        self.assertIn("объёму спроса", why)

    def test_24_нет_данных_не_равно_нулю(self):
        self.assertIsNone(visibility.share(0.0, 0.0))
        self.assertIsNone(opp.demand_factor(None))
        self.assertIsNone(kpi_mod.trend_change([0.1] * 5))
        self.assertEqual(kpi_mod.format_share(None), "NO DATA")

    def test_25_неклассифицированный_домен_не_конкурент_за_сделку(self):
        """За клик — да, за сделку — нет: несимметрично и намеренно."""
        self.assertFalse(classifier.in_main_ranking("?"))
        self.assertFalse(classifier.in_main_ranking("E"))
        self.assertTrue(classifier.in_main_ranking("A"))


class TestSnapshotConsistency(unittest.TestCase):
    """Снимок обязан быть согласован сам с собой."""

    def setUp(self):
        self.config = visibility.load_config()
        self.rows = [
            serp_source.SerpRow(
                date="2026-09-01", query="купить figma юрлицу", region="213",
                top=[{"domain": "raketapay.ru", "url": "https://raketapay.ru/f"},
                     {"domain": "www.biz-soft.pro",
                      "url": "https://biz-soft.pro/vendors/figma"},
                     {"domain": "dzen.ru", "url": "https://dzen.ru/a/x"}]),
            serp_source.SerpRow(
                date="2026-09-01", query="figma для компании счёт", region="213",
                top=[{"domain": "biz-soft.pro",
                      "url": "https://biz-soft.pro/product/figma"},
                     {"domain": "raketapay.ru", "url": "https://raketapay.ru/g"}]),
        ]

    def test_26_по_запросная_видимость_даёт_ту_же_долю(self):
        """Сумма по запросам обязана совпасть с долей в карточке домена.

        Это тот инвариант, на котором держится сравнимая доля: если два
        расчёта расходятся, «сравнимая доля» перестаёт быть той же величиной,
        что показана в письме.
        """
        cards = {c.domain: c for c in registry.build(self.rows, self.config)}
        per_query = run_discovery.per_query_visibility(self.rows, self.config)
        наша = sum(v["наша"] for v in per_query.values())
        поле = sum(v["поле"] for v in per_query.values())
        self.assertAlmostEqual(наша / поле, cards["biz-soft.pro"].share,
                               places=5)

    def test_27_наш_домен_не_попадает_в_конкуренты(self):
        cards = registry.build(self.rows, self.config)
        snapshot = run_discovery.build_snapshot(
            "2026-09-01", cards, self.rows, self.config,
            query_sets_path=os.path.join(tempfile.mkdtemp(), "qs.json"))
        домены = [l["домен"] for l in snapshot["лидеры"]]
        self.assertNotIn("biz-soft.pro", домены)
        self.assertIsNotNone(snapshot["наши_показатели"]["доля_видимости"])

    def test_28_метаданные_снимка_описывают_условия_расчёта(self):
        cards = registry.build(self.rows, self.config)
        snapshot = run_discovery.build_snapshot(
            "2026-09-01", cards, self.rows, self.config,
            query_sets_path=os.path.join(tempfile.mkdtemp(), "qs.json"))
        meta = snapshot["метаданные"]
        for key in ("версия_методики", "хеш_конфига", "ядро_версия",
                    "ядро_хеш", "запросов_в_ядре", "покрытие_запросов",
                    "взвешенное_покрытие", "состав_источников_спроса"):
            self.assertIn(key, meta)
        self.assertEqual(meta["ядро_хеш"], kpi_mod.core_hash(snapshot))


class TestConfigContract(unittest.TestCase):
    """Конфиг — опубликованный контракт модели, а не справка рядом с кодом."""

    def setUp(self):
        self.config = visibility.load_config()

    def test_29_веса_opportunity_в_конфиге_совпадают_с_кодом(self):
        объявлено = self.config["opportunity"]["веса"]
        self.assertEqual({k: int(v) for k, v in объявлено.items()}, opp.WEIGHTS)

    def test_30_пороги_нормировки_спроса_берутся_из_конфига(self):
        насыщение = self.config["спрос"]["насыщение"]
        self.assertEqual(opp.demand_scale("wordstat", self.config),
                         float(насыщение["wordstat"]))
        self.assertEqual(opp.demand_scale("webmaster", self.config),
                         float(насыщение["webmaster"]))

    def test_31_кривая_ctr_задана_явно_на_все_двадцать_позиций(self):
        кривая = self.config["ctr_кривая"]
        веса = [visibility.ctr_weight(p, self.config) for p in range(1, 21)]
        self.assertEqual(len([k for k in кривая if k.isdigit()]), 20)
        self.assertEqual(веса, sorted(веса, reverse=True))
        self.assertEqual(visibility.ctr_weight(21, self.config), 0.0)

    def test_32_коэффициент_serp_берётся_самый_сильный_а_не_произведение(self):
        """Два крупных элемента не давят выдачу вдвое сильнее одного."""
        оба = visibility.feature_factor(["ai_ответ", "товарная_галерея"],
                                        self.config)
        один = visibility.feature_factor(["ai_ответ"], self.config)
        self.assertEqual(оба, один)

    def test_33_веса_threat_в_конфиге_совпадают_с_кодом(self):
        веса = self.config["threat"]["веса"]
        self.assertEqual(int(веса["присутствие"]), threat_mod.WEIGHT_PRESENCE)
        self.assertEqual(int(веса["превосходство_над_нами"]),
                         threat_mod.WEIGHT_SUPERIORITY)
        self.assertEqual(int(веса["динамика"]), threat_mod.WEIGHT_MOMENTUM)
        self.assertEqual(float(self.config["покрытие"]["критический_порог_ядра"]),
                         kpi_mod.CRITICAL_COVERAGE_RATIO)
        self.assertEqual(
            float(self.config["покрытие"]["минимальное_пересечение_ядра"]),
            kpi_mod.MIN_COMPARABLE_CORE_RATIO)


class TestSerpSourceRobustness(unittest.TestCase):
    """Чтение срезов не должно зависеть от каталога запуска и от переезда.

    Обе проверки написаны после реального сбоя 01.09.2026: базовый контур
    перенёс срезы из reports/seo/data/serp в reports/seo/serp, а вызов
    git ls-tree без --full-tree отсчитывал путь от текущего каталога.
    В результате прогон не нашёл ни одного среза, письмо не ушло, и никто
    об этом не узнал.
    """

    def test_34_ls_tree_вызывается_от_корня_дерева(self):
        calls = []

        def fake_git(*args):
            calls.append(args)
            return ""

        original = serp_source._git
        serp_source._git = fake_git
        try:
            serp_source.available_dates()
        finally:
            serp_source._git = original
        self.assertTrue(calls, "ls-tree не вызывался вовсе")
        for args in calls:
            self.assertIn("--full-tree", args)

    def test_35_даты_объединяются_по_всем_каталогам(self):
        новый, старый = serp_source.SERP_DIRS

        def fake_git(*args):
            directory = args[-1].rstrip("/")
            if directory == новый:
                return f"{новый}/2026-09-01-serp.jsonl\n"
            return f"{старый}/2026-08-30-serp.jsonl\n"

        original = serp_source._git
        serp_source._git = fake_git
        try:
            self.assertEqual(serp_source.available_dates(),
                             ["2026-08-30", "2026-09-01"])
        finally:
            serp_source._git = original

    def test_36_срез_ищется_и_в_старом_каталоге(self):
        новый, старый = serp_source.SERP_DIRS
        row = ('{"date": "2026-08-30", "query": "q", "region": "213", '
               '"top": [{"domain": "biz-soft.pro"}]}')

        def fake_git(*args):
            if args[0] != "show":
                return ""
            if новый in args[1]:
                raise subprocess.CalledProcessError(128, "git")
            return row

        original = serp_source._git
        serp_source._git = fake_git
        try:
            rows = serp_source.read_snapshot("2026-08-30")
        finally:
            serp_source._git = original
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].has_data)


class TestMainSignalHonesty(unittest.TestCase):
    """Главный сигнал не сообщает о движении, которого не было."""

    def _snapshot(self, date, core_size, share, core_hash):
        return {
            "дата": date,
            "ядро_запросов": {"хеш": core_hash, "версия": "v1",
                              "запросов": core_size},
            "доли_по_категориям": {"H": 0.3},
            "наши_показатели": {"доля_видимости": 0.03},
            "лидеры": [{"домен": "raketapay.ru", "категория": "H",
                        "доля": share, "топ3": 70, "топ10": 120}],
        }

    def test_37_смена_ядра_отменяет_сигнал_об_изменении(self):
        вчера = self._snapshot("2026-08-31", 150, 0.10, "aaa")
        сегодня = self._snapshot("2026-09-01", 369, 0.056, "bbb")
        self.assertIsNone(signal_mod.change_signal(сегодня, вчера))
        выбран = signal_mod.pick(сегодня, вчера)
        self.assertEqual(выбран.kind, "структура")
        self.assertIn("ядро выросло с 150 до 369", выбран.text)
        self.assertIn("несопоставимы", выбран.text)
        self.assertNotIn("просел", выбран.text)

    def test_38_при_том_же_ядре_изменение_сообщается(self):
        вчера = self._snapshot("2026-08-31", 150, 0.10, "aaa")
        сегодня = self._snapshot("2026-09-01", 150, 0.056, "aaa")
        выбран = signal_mod.pick(сегодня, вчера)
        self.assertEqual(выбран.kind, "падение_конкурента")
        self.assertIn("просел", выбран.text)


if __name__ == "__main__":
    unittest.main()
