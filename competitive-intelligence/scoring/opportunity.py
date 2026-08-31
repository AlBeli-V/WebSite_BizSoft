"""Business Opportunity Score 0–100 — основной показатель выбора атаки.

Состав из раздела 12 задания:
  20% Revenue Potential · 15% Commercial Intent · 15% B2B Intent ·
  15% Ranking Proximity · 10% Search Demand · 10% Competitor Vulnerability ·
  10% Page Improvement Potential · 5% Strategic Vendor Priority

**Режим деградации** (обязателен до Phase 4). Vulnerability требует
краулинга страниц конкурента, которого ещё нет. Его вес перераспределяется
на Proximity и Page Improvement — то есть на факторы, которые мы измеряем
достоверно, — а Confidence принудительно не выше MEDIUM. Так письмо не
выдаёт неполный расчёт за полный.

Revenue Potential до калибровки по Метрике/GA4 (Phase 5) считается прокси:
спрос × коммерческий интент. Это честно помечено в breakdown, чтобы никто
не принял прокси за измеренную выручку.
"""
from __future__ import annotations

from dataclasses import dataclass, field

WEIGHTS_FULL = {
    "revenue": 20, "commercial": 15, "b2b": 15, "proximity": 15,
    "demand": 10, "vulnerability": 10, "page_improvement": 10, "vendor": 5,
}
# Деградация: 10 пунктов Vulnerability уходят туда, что мы реально измеряем.
WEIGHTS_DEGRADED = {
    "revenue": 20, "commercial": 15, "b2b": 15, "proximity": 21,
    "demand": 10, "vulnerability": 0, "page_improvement": 14, "vendor": 5,
}

# Позиция, ближе которой считаем, что мы «уже рядом» и дожать легко.
PROXIMITY_BEST = 4
# Позиция, дальше которой близость обнуляется: с 20-го места до топ-3 не
# доходят одной правкой страницы.
PROXIMITY_WORST = 20
# Значение спроса, при котором слагаемое набирает максимум. Шкалы источников
# разные и смешивать их нельзя: частотность Wordstat меряет весь рынок за
# месяц, показы Вебмастера — только ту его часть, где нас уже видно за две
# недели. Сотня показов и сотня частотности — совершенно разный спрос.
DEMAND_AT_MAX = {
    "wordstat": 1000,
    "webmaster": 200,
}


@dataclass
class Opportunity:
    score: int
    confidence: str
    breakdown: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    degraded: bool = True


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


def demand_factor(value: int | None, source: str = "wordstat") -> float:
    """Спрос с нормировкой по источнику.

    NO DATA даёт нейтральное значение, а не ноль: отсутствие данных о спросе
    — это незнание, а не отсутствие спроса.
    """
    if value is None:
        return 0.5
    scale = DEMAND_AT_MAX.get(source, DEMAND_AT_MAX["wordstat"])
    return round(min(1.0, value / scale), 3)


def score(*, commercial: float, b2b: float, our_position: int | None,
          has_page: bool, frequency: int | None = None,
          demand_source: str = "wordstat",
          vulnerability: float | None = None,
          vendor_priority: float = 0.5) -> Opportunity:
    """Opportunity одной цели атаки."""
    degraded = vulnerability is None
    weights = WEIGHTS_DEGRADED if degraded else WEIGHTS_FULL

    prox = proximity_factor(our_position)
    page = page_improvement_factor(our_position, has_page)
    demand = demand_factor(frequency, demand_source)
    # Прокси выручки до калибровки по фактическим конверсиям (Phase 5)
    revenue_proxy = round(demand * commercial, 3)

    parts = {
        "revenue": weights["revenue"] * revenue_proxy,
        "commercial": weights["commercial"] * commercial,
        "b2b": weights["b2b"] * b2b,
        "proximity": weights["proximity"] * prox,
        "demand": weights["demand"] * demand,
        "page_improvement": weights["page_improvement"] * page,
        "vendor": weights["vendor"] * vendor_priority,
    }
    if not degraded:
        parts["vulnerability"] = weights["vulnerability"] * (vulnerability or 0.0)

    notes = []
    if degraded:
        notes.append("Vulnerability недоступен до Phase 4: вес перераспределён "
                     "на близость позиции и запас улучшения страницы")
    if frequency is None:
        notes.append("спрос по запросу неизвестен — принят нейтральным")
    elif demand_source == "webmaster":
        notes.append(f"спрос оценён по показам Вебмастера ({frequency}), "
                     "а не по частотности Wordstat")
    notes.append("Revenue — прокси (спрос × коммерческий интент), "
                 "не измеренная выручка")

    # Confidence не может быть выше MEDIUM в режиме деградации — требование
    # раздела 12 задания. Полное незнание спроса опускает её ещё на ступень.
    if degraded:
        confidence = "LOW" if frequency is None else "MEDIUM"
    else:
        confidence = "MEDIUM" if frequency is None else "HIGH"

    return Opportunity(
        score=min(100, int(round(sum(parts.values())))),
        confidence=confidence,
        breakdown={k: round(v, 1) for k, v in parts.items()},
        notes=notes,
        degraded=degraded,
    )
