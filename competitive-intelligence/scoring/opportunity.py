"""Business Opportunity Score 0–100 — основной показатель выбора цели.

Версия 1.1.0 (после внешнего аудита методики, 31.08.2026). Две правки
математики против 1.0.0, обе — устранение реальных дефектов:

1. **Убран revenue-прокси как отдельный фактор.** В 1.0.0 он считался как
   спрос × коммерческий интент и получал 20% веса, при этом спрос и
   коммерческий интент входили в сумму ещё и напрямую. Один и тот же
   признак давал баллы дважды, и модель скрытно переоценивала
   высокочастотные запросы. Экономический фактор вернётся, когда появится
   измеренная выручка из Метрики и GA4, а не её подобие.

2. **Отсутствующий признак больше не заменяется средним значением.**
   В 1.0.0 неизвестный спрос давал 0,5 — то есть незнание превращалось в
   «средний спрос», хотя за ним могло стоять и 5 запросов, и 50 000. Это
   противоречило собственному правилу системы «нет данных не равно нулю»,
   просто в другую сторону. Теперь работает нормализация по доступным
   признакам: веса известных факторов масштабируются до 100%, а уверенность
   понижается на ступень.

Состав факторов до подключения измеренной выручки:
  коммерческий интент 20% · B2B-интент 20% · близость позиции 20% ·
  спрос 15% · запас улучшения страницы 15% · приоритет вендора 10%.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Веса без экономического фактора: измеренной выручки пока нет, а её
# подобие через спрос и интент — двойной счёт (аудит 31.08).
WEIGHTS_FULL = {
    "commercial": 20, "b2b": 20, "proximity": 15,
    "demand": 15, "vulnerability": 15, "page_improvement": 10, "vendor": 5,
}
# Деградация: вес уязвимости уходит на факторы, измеряемые достоверно.
WEIGHTS_DEGRADED = {
    "commercial": 20, "b2b": 20, "proximity": 20,
    "demand": 15, "vulnerability": 0, "page_improvement": 15, "vendor": 10,
}

# Позиция, ближе которой считаем, что мы «уже рядом» и дожать легко.
PROXIMITY_BEST = 4
# Позиция, дальше которой близость обнуляется: с 20-го места до топ-3 не
# доходят одной правкой страницы.
PROXIMITY_WORST = 20
# Значение спроса, при котором фактор набирает максимум. Шкалы источников
# разные и смешивать их нельзя: частотность Wordstat меряет рынок за месяц,
# показы Вебмастера — только видимую нам часть за две недели.
DEMAND_AT_MAX = {
    "wordstat": 1000,
    "webmaster": 200,
}


# Режим доступности факторов. Оценки из разных режимов между собой
# несравнимы: при недоступном факторе веса остальных нормализуются, и то же
# самое число получено по другой формуле. Режим хранится рядом с оценкой,
# чтобы изменение конфигурации модели нельзя было принять за изменение самой
# возможности.
MODE_FULL = "full"
MODE_DEGRADED = "degraded_no_vulnerability"


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
        математически разные числа. Сравнивать их как динамику возможности
        нельзя; при смене режима начинается новая базовая линия.
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


def demand_factor(value: int | None, source: str = "wordstat") -> float | None:
    """Спрос с нормировкой по источнику.

    Возвращает None при отсутствии данных — не 0,5 и не ноль. Дальше такой
    фактор исключается из расчёта, а не подменяется средним: незнание не
    является средним значением.
    """
    if value is None:
        return None
    scale = DEMAND_AT_MAX.get(source, DEMAND_AT_MAX["wordstat"])
    return round(min(1.0, value / scale), 3)


def _downgrade(confidence: str) -> str:
    order = ["HIGH", "MEDIUM", "LOW"]
    index = order.index(confidence) if confidence in order else 1
    return order[min(index + 1, len(order) - 1)]


def score(*, commercial: float, b2b: float, our_position: int | None,
          has_page: bool, frequency: int | None = None,
          demand_source: str = "wordstat",
          vulnerability: float | None = None,
          vendor_priority: float = 0.5) -> Opportunity:
    """Opportunity одной цели атаки.

    Известные факторы взвешиваются своими весами; веса недоступных факторов
    не раздаются молча — вместо этого сумма нормализуется по доступным, а
    уверенность понижается. Так отсутствие признака честно уменьшает
    надёжность оценки, не искажая её значение.
    """
    degraded = vulnerability is None
    weights = dict(WEIGHTS_DEGRADED if degraded else WEIGHTS_FULL)

    demand = demand_factor(frequency, demand_source)
    factors: dict[str, float | None] = {
        "commercial": commercial,
        "b2b": b2b,
        "proximity": proximity_factor(our_position),
        "demand": demand,
        "page_improvement": page_improvement_factor(our_position, has_page),
        "vendor": vendor_priority,
    }
    if not degraded:
        factors["vulnerability"] = vulnerability

    known = {name: value for name, value in factors.items()
             if value is not None and weights.get(name, 0) > 0}
    missing = [name for name, value in factors.items()
               if value is None and weights.get(name, 0) > 0]

    # Нормализация по доступным признакам: сумма весов известных факторов
    # приводится к 100, чтобы отсутствие признака не занижало итог механически.
    available_weight = sum(weights[name] for name in known)
    if available_weight <= 0:
        return Opportunity(score=0, confidence="LOW",
                           mode=MODE_DEGRADED if degraded else MODE_FULL,
                           breakdown={},
                           notes=["ни один фактор не измерен — оценка невозможна"],
                           degraded=degraded, missing=missing)
    scale = 100 / available_weight

    parts = {name: weights[name] * scale * value for name, value in known.items()}

    notes = []
    if degraded:
        notes.append("Vulnerability недоступен до обхода страниц конкурентов: "
                     "его вес перераспределён на близость позиции, запас "
                     "улучшения страницы и приоритет вендора")
    if "demand" in missing:
        notes.append("спрос по запросу неизвестен — фактор исключён из расчёта, "
                     "веса остальных нормализованы, уверенность понижена")
    elif demand_source == "webmaster":
        notes.append(f"спрос оценён по показам Вебмастера ({frequency}) — это "
                     "видимая нам часть спроса за две недели, а не рынок за месяц")
    notes.append("экономический фактор не участвует: измеренной выручки нет, "
                 "а её оценка через спрос и интент дублировала бы эти факторы")

    # Уверенность: деградация не даёт подняться выше средней, каждое
    # отсутствующее измерение понижает ещё на ступень.
    confidence = "MEDIUM" if degraded else "HIGH"
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
