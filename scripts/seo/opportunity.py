#!/usr/bin/env python3
"""Радар возможностей: где рост наиболее вероятен при наименьших усилиях.

opportunity_score = commercial_intent × observable_demand × confidence
                    × expected_impact / effort

Источники сигнала разделены и не смешиваются:

  наши показы по запросу  — свидетельство нашей видимости, НЕ рыночный спрос;
  частотность Вордстата   — рыночный спрос, доступен только после замера.

Формулировка «рыночный спрос» разрешена лишь при наличии замера Вордстата.
Показы сайта рыночным спросом не называются ни при каких условиях.
"""

from __future__ import annotations

INTENT_WEIGHT = {"commercial": 1.0, "unknown": 0.5, "informational": 0.3,
                 "navigational": 0.15}
CONFIDENCE_WEIGHT = {"sufficient": 1.0, "low": 0.6, "very_low": 0.3, "unknown": 0.4}

# Полоса позиций → ожидаемый эффект и трудоёмкость типового действия.
BANDS = [
    (0.0, 10.0, "в первой десятке, но без переходов", 0.9, 1,
     "переписать заголовок и описание страницы под запрос",
     "переходы при том же объёме показов — платить за них не нужно"),
    (10.0, 20.0, "на второй странице", 0.7, 2,
     "усилить страницу под запрос: заголовок, ответ на вопрос, внутренняя ссылка",
     "выход на первую страницу открывает основной объём показов"),
    (20.0, 40.0, "далеко от первой страницы", 0.4, 3,
     "отдельный блок или страница под кластер запроса",
     "новая точка входа там, где сейчас нас практически не видно"),
]
MIN_IMPRESSIONS = 8


def band_for(position: float | None):
    if position is None:
        return None
    for lo, hi, label, impact, effort, action, upside in BANDS:
        if lo < position <= hi:
            return {"label": label, "impact": impact, "effort": effort,
                    "action": action, "upside": upside}
    return None


def normalise(value: float, scale: float) -> float:
    if not scale:
        return 0.0
    return min(1.0, value / scale)


def from_queries(snap: dict, engine: str) -> list[dict]:
    block = snap.get(engine) or {}
    if not block.get("available"):
        return []
    rows = [e for e in (block.get("entities") or []) if e.get("entity_type") == "query"]
    if not rows:
        return []
    scale = max((r.get("impressions") or 0) for r in rows) or 1
    out = []
    for r in rows:
        imp = r.get("impressions") or 0
        if imp < MIN_IMPRESSIONS:
            continue
        band = band_for(r.get("average_position"))
        if not band:
            continue
        if band["impact"] == 0.9 and (r.get("clicks") or 0) > 0:
            continue    # в топе и клики есть — возможности нет, всё работает
        intent = INTENT_WEIGHT.get(r.get("intent", "unknown"), 0.4)
        conf = CONFIDENCE_WEIGHT.get(r.get("confidence", "unknown"), 0.4)
        demand = normalise(imp, scale)
        score = intent * demand * conf * band["impact"] / band["effort"]
        out.append({
            "cluster": r["entity_id"],
            "engine": engine,
            "evidence": f"{imp} показов по запросу за период, средняя позиция "
                        f"{r['average_position']} — {band['label']}",
            "evidence_kind": "our_impressions",
            "potential": band["upside"],
            "confidence": r.get("confidence", "unknown"),
            "recommended_action": band["action"],
            "effort": band["effort"],
            "score": round(score, 4),
        })
    return out


def from_market_demand(snap: dict) -> list[dict]:
    md = snap.get("market_demand") or {}
    if not md.get("available"):
        return []
    gaps = md.get("gaps") or {}
    flat = [(c, r) for c, rows in gaps.items() for r in rows]
    if not flat:
        return []
    scale = max((r["impressions"] or 0) for _, r in flat) or 1
    out = []
    for cluster, r in flat:
        demand = normalise(r["impressions"] or 0, scale)
        score = 1.0 * demand * 0.8 * 0.8 / 2
        out.append({
            "cluster": cluster,
            "engine": "yandex",
            "evidence": f"«{r['phrase']}» — {r['impressions']} запросов в месяц "
                        f"(рыночный спрос, замер {md['source']['measured_at']}), "
                        "наша страница по этим словам не видна",
            "evidence_kind": "market_demand",
            "potential": "запрос с подтверждённым спросом, по которому нас нет",
            "confidence": "sufficient" if md.get("complete") else "low",
            "recommended_action": "довести карточку до запроса: заголовок, описание, ответ в FAQ",
            "effort": 2,
            "score": round(score, 4),
        })
    return out


def build(snap: dict, decision_date: str, limit: int = 3) -> dict:
    items = from_market_demand(snap) + from_queries(snap, "yandex") + from_queries(snap, "google")
    if not items:
        return {"available": False,
                "reason": "сигналов, достаточных для приоритизации, пока нет",
                "items": []}
    items.sort(key=lambda i: -i["score"])
    seen, top = set(), []
    for i in items:
        key = i["cluster"].lower()
        if key in seen:
            continue
        seen.add(key)
        i["decision_date"] = decision_date
        top.append(i)
        if len(top) >= limit:
            break
    return {"available": True, "reason": None, "items": top,
            "considered": len(items),
            "market_demand_used": any(i["evidence_kind"] == "market_demand" for i in top)}
