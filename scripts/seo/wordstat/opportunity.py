#!/usr/bin/env python3
"""Модель возможностей: прозрачная, с раздельно хранимыми компонентами.

Opportunity = NormalizedDemand × CommercialIntent × CoverageGap × TrendFactor
              × Confidence / EstimatedEffort

Итоговое число — способ упорядочить список, а не основание решения. Поэтому
каждая составляющая сохраняется отдельно и показывается рядом с результатом:
руководитель должен видеть, что именно даёт высокий балл — спрос, разрыв
покрытия или дешевизна работы.
"""

from __future__ import annotations

# Во что обходится закрытие разрыва: относительная трудоёмкость, не часы.
EFFORT = {
    "GAP-A": 5.0,   # новая страница с текстами и разметкой
    "GAP-B": 2.0,   # техническая правка индексации
    "GAP-C": 3.0,   # переработка существующей страницы
    "GAP-D": 1.0,   # заголовок и описание
    "GAP-E": 4.0,   # предложение и форма
    "GAP-F": 3.0,   # исследование платного канала
    "GAP-G": 4.0,   # ранняя страница под растущий спрос
    "GAP-H": 8.0,   # снижающийся спрос: работа окупается плохо
    "GAP-N": 1.0,   # проверка индексации и позиции — замер, не правка
}
TREND_FACTOR = {"growing": 1.3, "stable": 1.0, "unknown": 0.9, "declining": 0.5}


def coverage_gap(gap: dict) -> float:
    """Насколько велик разрыв: 1.0 — нас нет вовсе, 0.1 — почти всё хорошо."""
    if not gap["page_exists"]:
        return 1.0
    if gap["indexed"] is False:
        return 0.85
    pos = gap["best_position"]
    if gap["indexed"] is None or pos is None:
        return 0.8      # размер разрыва не измерен — не самый большой и не малый
    if pos > 30:
        return 0.7
    if pos > 10:
        return 0.5
    if (gap["ctr"] or 0) < 0.01:
        return 0.35
    return 0.1


def confidence_of(gap: dict) -> tuple[float, str]:
    if gap["commercial_phrases"] >= 5 and gap["commercial_demand"] >= 1000:
        return 0.9, "достаточная: кластер измерен несколькими фразами"
    if gap["commercial_demand"] >= 300:
        return 0.7, "средняя: спрос заметен, фраз немного"
    return 0.45, "низкая: малый кластер"


def score(gap: dict, max_demand: int) -> dict:
    demand = round(min(1.0, gap["commercial_demand"] / max_demand), 4) if max_demand else 0
    intent = round(min(1.0, gap["commercial_phrases"] / 10), 4)
    intent = max(intent, 0.3) if gap["commercial_demand"] else intent
    cov = coverage_gap(gap)
    trend = TREND_FACTOR.get(gap["trend"], 1.0)
    conf, conf_note = confidence_of(gap)
    effort = EFFORT[gap["gap"]]
    value = round(demand * intent * cov * trend * conf / effort, 5)
    return {
        "opportunity_score": value,
        "components": {
            "normalized_demand": demand,
            "commercial_intent": intent,
            "coverage_gap": cov,
            "trend_factor": trend,
            "confidence": conf,
            "estimated_effort": effort,
        },
        "confidence_note": conf_note,
    }


def rank(gaps: list[dict], limit: int = 5) -> list[dict]:
    if not gaps:
        return []
    max_demand = max(g["commercial_demand"] for g in gaps)
    scored = []
    for g in gaps:
        s = score(g, max_demand)
        scored.append({**g, **s})
    scored.sort(key=lambda g: -g["opportunity_score"])
    return scored[:limit]
