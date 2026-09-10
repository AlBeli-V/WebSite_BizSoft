"""Business Opportunity Score 0–100 — основной показатель выбора цели.

Версия 1.3.0 (после четвёртой внешней рецензии, 31.08.2026).

История правок математики:

1. **1.1.0: убран revenue-прокси как отдельный фактор.** В 1.0.0 он считался
   как спрос × коммерческий интент и получал 20% веса, при этом спрос и
   коммерческий интент входили в сумму ещё и напрямую. Один и тот же признак
   давал баллы дважды. Экономический фактор вернётся, когда появится
   измеренная выручка из Метрики и GA4, а не её подобие.

2. **1.1.0: отсутствующий признак не заменяется общей константой.** В 1.0.0
   неизвестный спрос давал 0,5 — незнание превращалось в «средний спрос» по
   всему полю. Теперь недоступный фактор исключается, веса нормализуются,
   уверенность понижается.

   Точная формулировка важна, и до 1.9.6 она была неточной (см. пункт 5).

3. **1.3.0: одно правило вместо двух.** До 1.3.0 недоступность уязвимости
   обрабатывалась вручную заранее заданной таблицей WEIGHTS_DEGRADED (вес
   уязвимости раздавался трём выбранным факторам), а недоступность любого
   другого фактора — пропорциональной нормализацией. Два механизма на одну
   ситуацию давали результат, зависящий от того, какой фактор пропал: при
   двух и более отсутствующих факторах итог зависел от порядка их обработки.
   Теперь правило одно и универсальное, и оно инвариантно к порядку:

       активный набор = факторы с известным значением и ненулевым весом
       масштаб        = 100 / сумма весов активного набора
       оценка         = Σ (вес × масштаб × значение) по активному набору

   Ни один вес не «передаётся» конкретному фактору: недостающая масса
   распределяется пропорционально между всеми оставшимися, а перечень
   недоступных факторов хранится рядом с оценкой и входит в ключ
   сравнимости.

4. **1.9.6: что перераспределение веса делает на самом деле.** Методика
   говорила «недоступный фактор не заменяется средним». Арифметически это
   неверно, и проверяется в одну строку: пропорциональное перераспределение
   веса ТОЖДЕСТВЕННО подстановке недоступному фактору взвешенного среднего
   измеренных.

       S  = 100 · Σ wᵢxᵢ / Σ wᵢ                (перераспределение)
       S' = Σ wᵢxᵢ + w_k·x_k, Σw = 100          (полная модель)
       S' = S  ⟺  x_k = Σ wᵢxᵢ / Σ wᵢ          (взвешенное среднее)

   Разница с 1.0.0 остаётся, и она существенна: там подставлялась общая
   константа 0,5 — «средний спрос по полю» независимо от цели. Здесь
   подставляется среднее самой цели по её же измеренным факторам.

   Но допущение никуда не делось, и его надо называть: у цели, сильной по
   всем измеренным факторам, недоступный фактор считается таким же сильным.
   Для уязвимости страницы конкурента это ровно то, чего утверждать нельзя —
   и смещает оценку сильнее всего наверху Strike List, там, где решения и
   принимаются. Занижать уверенность до MEDIUM недостаточно: уверенность
   говорит о надёжности, а здесь смещение направленное.

Базовые веса (до подключения измеренной выручки):
  коммерческий интент 20% · B2B-интент 20% · близость позиции 15% ·
  спрос 15% · уязвимость страницы конкурента 15% ·
  запас улучшения страницы 10% · приоритет вендора 5%.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Единственная таблица весов. Веса недоступных факторов не раздаются вручную:
# см. правило нормализации в docstring модуля.
WEIGHTS = {
    "commercial": 20, "b2b": 20, "proximity": 15,
    "demand": 15, "vulnerability": 15, "page_improvement": 10, "vendor": 5,
}
# Историческое имя для читаемости внешних ссылок на методику.
WEIGHTS_FULL = WEIGHTS

# Позиция, ближе которой считаем, что мы «уже рядом» и дожать легко.
PROXIMITY_BEST = 4
# Позиция, дальше которой близость обнуляется: с 20-го места до топ-3 не
# доходят одной правкой страницы.
PROXIMITY_WORST = 20
# Значение спроса, при котором фактор набирает максимум. Шкалы источников
# разные и смешивать их нельзя: частотность Wordstat меряет рынок за месяц,
# показы Вебмастера — только видимую нам часть за две недели. Числа —
# параметр калибровки, а не константа природы: они вынесены в
# scoring/config.json (раздел «спрос»), здесь оставлено значение по умолчанию
# на случай вызова функций без конфига.
DEMAND_AT_MAX = {
    "wordstat": 1000,
    "webmaster": 200,
}

# Режим доступности факторов. Оценки из разных режимов между собой
# несравнимы: при недоступном факторе веса остальных нормализуются, и то же
# самое число получено по другой формуле.
MODE_FULL = "full"
MODE_DEGRADED = "degraded"


@dataclass
class Opportunity:
    score: int
    confidence: str
    mode: str = MODE_DEGRADED
    breakdown: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    degraded: bool = True
    missing: list[str] = field(default_factory=list)

    @property
    def comparable_key(self) -> str:
        """Ключ сравнимости: режим плюс перечень недоступных факторов.

        Opportunity 82 сегодня и 82 после подключения обхода конкурентов —
        математически разные числа: они получены нормализацией по разным
        наборам весов. Сравнивать их как динамику возможности нельзя; при
        смене режима начинается новая базовая линия.
        """
        return f"{self.mode}|{','.join(sorted(self.missing))}"


def proximity_factor(our_position: int | None) -> float:
    """Насколько мы близки к вершине. Нет в выдаче — ноль, а не «далеко»."""
    if our_position is None or our_position > PROXIMITY_WORST:
        return 0.0
    if our_position <= PROXIMITY_BEST:
        return 1.0
    span = PROXIMITY_WORST - PROXIMITY_BEST
    return round((PROXIMITY_WORST - our_position) / span, 3)


def page_improvement_factor(our_position: int | None, has_page: bool) -> float:
    """Запас улучшения страницы.

    Максимум там, где страница уже есть, но стоит невысоко: правка даёт
    эффект быстрее, чем создание новой. Если страницы нет вовсе — потенциал
    есть, но он дороже, поэтому ниже.
    """
    if not has_page:
        return 0.5
    if our_position is None:
        return 0.6
    if our_position <= 3:
        return 0.2   # уже наверху, улучшать почти нечего
    return 1.0


def demand_scale(source: str, config: dict | None = None) -> float:
    """Точка насыщения фактора спроса для источника.

    Берётся из конфига, если он передан: значение — параметр калибровки,
    и держать его только в коде значит прятать допущение.
    """
    table = dict(DEMAND_AT_MAX)
    if config:
        table.update((config.get("спрос") or {}).get("насыщение") or {})
    return float(table.get(source, table["wordstat"]))


def demand_factor(value: int | None, source: str = "wordstat",
                  config: dict | None = None) -> float | None:
    """Спрос с нормировкой по источнику.

    Возвращает None при отсутствии данных — не 0,5 и не ноль. Дальше такой
    фактор исключается из расчёта: незнание не является ни нулём, ни заранее
    выбранной серединой шкалы.
    """
    if value is None:
        return None
    return round(min(1.0, value / demand_scale(source, config)), 3)


def _downgrade(confidence: str) -> str:
    order = ["HIGH", "MEDIUM", "LOW"]
    index = order.index(confidence) if confidence in order else 1
    return order[min(index + 1, len(order) - 1)]


def normalize_weights(available: set[str], weights: dict[str, int] | None = None
                      ) -> dict[str, float]:
    """Веса активного набора, нормализованные к 100.

    Одна операция для любого числа недоступных факторов: сначала определяется
    активный набор целиком, потом веса масштабируются один раз. Поэтому
    результат не зависит ни от порядка исключения, ни от того, исключались
    факторы поштучно или сразу — это проверяется инвариант-тестом
    (tests/test_invariants.py, «коммутативность исключения факторов»).
    """
    weights = weights or WEIGHTS
    active = {name: weights[name] for name in available
              if weights.get(name, 0) > 0}
    total = sum(active.values())
    if total <= 0:
        return {}
    scale = 100 / total
    return {name: weight * scale for name, weight in active.items()}


def score(*, commercial: float, b2b: float, our_position: int | None,
          has_page: bool, frequency: int | None = None,
          demand_source: str = "wordstat",
          vulnerability: float | None = None,
          vendor_priority: float = 0.5,
          config: dict | None = None) -> Opportunity:
    """Opportunity одной цели атаки.

    Все факторы вычисляются, недоступные помечаются None, затем один раз
    применяется правило нормализации. Отсутствие признака честно уменьшает
    надёжность оценки и не искажает её значение.
    """
    demand = demand_factor(frequency, demand_source, config)
    factors: dict[str, float | None] = {
        "commercial": commercial,
        "b2b": b2b,
        "proximity": proximity_factor(our_position),
        "demand": demand,
        "vulnerability": vulnerability,
        "page_improvement": page_improvement_factor(our_position, has_page),
        "vendor": vendor_priority,
    }

    known = {name: value for name, value in factors.items()
             if value is not None and WEIGHTS.get(name, 0) > 0}
    missing = sorted(name for name, value in factors.items()
                     if value is None and WEIGHTS.get(name, 0) > 0)
    degraded = bool(missing)

    weights = normalize_weights(set(known), WEIGHTS)
    if not weights:
        return Opportunity(score=0, confidence="LOW", mode=MODE_DEGRADED,
                           breakdown={},
                           notes=["ни один фактор не измерен — оценка невозможна"],
                           degraded=True, missing=missing)

    parts = {name: weights[name] * value for name, value in known.items()}

    notes = []
    if "vulnerability" in missing:
        notes.append("Vulnerability недоступен до обхода страниц конкурентов: "
                     "его вес пропорционально распределён между измеренными "
                     "факторами, а не передан выбранным")
    if "demand" in missing:
        notes.append("спрос по запросу неизвестен — фактор исключён из расчёта, "
                     "веса остальных нормализованы, уверенность понижена")
    elif demand_source == "webmaster":
        notes.append(f"спрос оценён по показам Вебмастера ({frequency}) — это "
                     "видимая нам часть спроса за две недели, а не рынок за месяц")
    notes.append("экономический фактор не участвует: измеренной выручки нет, "
                 "а её оценка через спрос и интент дублировала бы эти факторы")

    # Уверенность: каждое отсутствующее измерение понижает на ступень.
    confidence = "HIGH"
    for _ in missing:
        confidence = _downgrade(confidence)

    return Opportunity(
        score=min(100, int(round(sum(parts.values())))),
        confidence=confidence,
        mode=MODE_DEGRADED if degraded else MODE_FULL,
        breakdown={k: round(v, 1) for k, v in parts.items()},
        notes=notes,
        degraded=degraded,
        missing=missing,
    )
