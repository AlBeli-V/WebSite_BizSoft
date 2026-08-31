"""Threat Score 0–100 — «насколько этот конкурент опасен сейчас».

Раздел 11 задания различает три разных вопроса, и смешивать их нельзя:
Relevance («наш ли это конкурент вообще»), Threat («опасен ли сейчас») и
Vulnerability («можно ли отобрать позицию»). Здесь — только Threat.

Threat складывается из уровня и динамики:
  * уровень — доля видимости, присутствие в топ-3 и топ-10;
  * динамика — рост доли за последние дни.

Пока истории меньше двух дней, динамическая часть недоступна. Её вес не
раздаётся молча остальным слагаемым: он честно отражается в поле
`confidence`, чтобы письмо не выдавало неполный расчёт за полный.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Веса слагаемых. Сумма уровня — 70, динамики — 30: конкурент, который уже
# держит поле, опаснее того, кто быстро растёт с нуля, но пока мал.
WEIGHT_SHARE = 40
WEIGHT_TOP3 = 20
WEIGHT_TOP10 = 10
WEIGHT_GROWTH = 30

# Доля видимости, при которой слагаемое «доля» набирает максимум. 15% в
# нашем поле — это уровень безусловного лидера: у текущего первого места
# около 10%, у BIZSoft — около 5%.
SHARE_AT_MAX = 0.15
# Рост доли за сутки, при котором динамическая часть набирает максимум.
GROWTH_AT_MAX_PP = 2.0


@dataclass
class Threat:
    score: int
    confidence: str  # HIGH | MEDIUM | LOW
    breakdown: dict[str, float] = field(default_factory=dict)
    explanation: str = ""


def _clamp(value: float, limit: float) -> float:
    return max(0.0, min(value, limit))


def score(card: dict, *, previous: dict | None = None,
          queries_total: int | None = None) -> Threat:
    """Threat одного конкурента.

    `card` — запись домена из снимка (доля, топ-3, топ-10);
    `previous` — та же запись за прошлый сравнимый день, если он есть.
    """
    share = card.get("доля") or 0.0
    top3 = card.get("топ3") or 0
    top10 = card.get("топ10") or 0
    total = queries_total or max(top10, 1)

    share_part = _clamp(WEIGHT_SHARE * share / SHARE_AT_MAX, WEIGHT_SHARE)
    top3_part = _clamp(WEIGHT_TOP3 * top3 / total, WEIGHT_TOP3)
    top10_part = _clamp(WEIGHT_TOP10 * top10 / total, WEIGHT_TOP10)

    breakdown = {
        "доля_видимости": round(share_part, 1),
        "присутствие_топ3": round(top3_part, 1),
        "присутствие_топ10": round(top10_part, 1),
    }

    prev_share = (previous or {}).get("доля")
    if prev_share is None:
        # Динамика недоступна: не раздаём её вес остальным и не выдаём
        # неполный расчёт за полный — понижаем confidence.
        confidence = "LOW"
        growth_part = 0.0
        explanation = ("динамика недоступна: нет сравнимого прошлого, "
                       "оценён только текущий уровень")
    else:
        delta_pp = 100 * (share - prev_share)
        growth_part = _clamp(WEIGHT_GROWTH * delta_pp / GROWTH_AT_MAX_PP,
                             WEIGHT_GROWTH)
        breakdown["рост_доли"] = round(growth_part, 1)
        confidence = "MEDIUM"
        explanation = f"рост доли {delta_pp:+.2f} п.п. к прошлому срезу"

    total_score = int(round(share_part + top3_part + top10_part + growth_part))
    return Threat(score=min(100, total_score), confidence=confidence,
                  breakdown=breakdown, explanation=explanation)


def rank(cards: list[dict], *, previous_cards: list[dict] | None = None,
         queries_total: int | None = None) -> list[tuple[dict, Threat]]:
    """Конкуренты по убыванию Threat. В расчёт идут только те, кто в рейтинге."""
    was = {c["домен"]: c for c in (previous_cards or [])}
    scored = [(card, score(card, previous=was.get(card["домен"]),
                           queries_total=queries_total))
              for card in cards]
    scored.sort(key=lambda pair: pair[1].score, reverse=True)
    return scored
