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

import passport
INTENT_WEIGHT = {"commercial": 1.0, "unknown": 0.5, "informational": 0.3,
                 "navigational": 0.15}
CONFIDENCE_WEIGHT = {"sufficient": 1.0, "low": 0.6, "very_low": 0.3, "unknown": 0.4}

# Полоса позиций → ожидаемый эффект и трудоёмкость типового действия.
#
# Зоны разделены по типу проблемы, а не только по номеру страницы: топ-3 без
# переходов — задача сниппета (CTR-аномалия), 4–10 и 10–20 — «низко висящие»
# позиции, где небольшое усиление страницы даёт непропорциональный эффект
# (главная рабочая зона радара — позиции 4–20).
BANDS = [
    (0.0, 3.0, "top3", "в топ-3, но без переходов", 0.85, 1,
     "сравнить сниппет с соседями по выдаче и переписать заголовок и описание",
     "запрос уже выигран — не хватает только клика"),
    (3.0, 10.0, "first_page", "в первой десятке, но без переходов", 0.9, 1,
     "переписать заголовок и описание страницы под запрос",
     "переходы при том же объёме показов — платить за них не нужно"),
    (10.0, 20.0, "second_page", "на второй странице", 0.7, 2,
     "усилить страницу под запрос: заголовок, ответ на вопрос, внутренняя ссылка",
     "выход на первую страницу открывает основной объём показов"),
    (20.0, 40.0, "far", "далеко от первой страницы", 0.4, 3,
     "отдельный блок или страница под кластер запроса",
     "новая точка входа там, где сейчас нас практически не видно"),
]
MIN_IMPRESSIONS = 8

# Зона «низко висящих» позиций: страница уже ранжируется, усиление дёшево.
SWEET_SPOT_ZONES = ("first_page", "second_page")


def band_for(position: float | None):
    if position is None:
        return None
    for lo, hi, zone, label, impact, effort, action, upside in BANDS:
        if lo < position <= hi:
            return {"zone": zone, "label": label, "impact": impact,
                    "effort": effort, "action": action, "upside": upside}
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
        if band["zone"] in ("top3", "first_page") and (r.get("clicks") or 0) > 0:
            continue    # в топе и клики есть — возможности нет, всё работает
        intent = INTENT_WEIGHT.get(r.get("intent", "unknown"), 0.4)
        conf = CONFIDENCE_WEIGHT.get(r.get("confidence", "unknown"), 0.4)
        demand = normalise(imp, scale)
        score = intent * demand * conf * band["impact"] / band["effort"]
        out.append({
            "cluster": r["entity_id"],
            "engine": engine,
            "zone": band["zone"],
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


def under_experiment(cluster: str, snap: dict) -> str | None:
    """Тикет действующего эксперимента, который меряет этот кластер.

    Пока опыт идёт, его страницы под мораторием: правка заголовка и описания
    обнуляет замер. 09.09.2026 радар предлагал «переписать заголовок и
    описание страницы под запрос» по кластерам «оплата coreldraw для россиян»
    (CONTENT-003) и «оплата artlist юридическим лицом» (SEO-EXP-004), а в
    таблице money-запросов таких строк было шесть из девяти верхних.
    """
    low = (cluster or "").lower()
    if not low:
        return None
    for e in snap.get("experiments") or []:
        if e.get("status") not in ("running", "observing"):
            continue
        markers = [m.lower() for m in (e.get("query_markers") or []) if m]
        if any(m in low for m in markers):
            return e.get("ticket") or e.get("id")
    return None


def money_radar(snap: dict, limit: int = 15) -> dict:
    """Money-запросы: коммерческий интент на позициях 3–20.

    Витрина веб-отчёта (в письме её нет — там общий радар): запросы со словами
    покупки, по которым сайт уже ранжируется, но не в топ-3. Именно здесь
    небольшое усиление страницы даёт непропорциональный коммерческий эффект.
    Брендовые запросы исключены: по ним позиция — не заслуга SEO.
    """
    items = []
    for engine in ("yandex", "google"):
        block = snap.get(engine) or {}
        if not block.get("available"):
            continue
        for e in block.get("entities") or []:
            if e.get("entity_type") != "query" or e.get("branded"):
                continue
            if e.get("intent") != "commercial":
                continue
            if (e.get("impressions") or 0) < MIN_IMPRESSIONS:
                continue
            band = band_for(e.get("average_position"))
            if not band or band["zone"] not in SWEET_SPOT_ZONES:
                continue
            ticket = under_experiment(e["entity_id"], snap)
            items.append({
                "query": e["entity_id"],
                "engine": engine,
                "impressions": e.get("impressions"),
                "clicks": e.get("clicks") or 0,
                "position": e.get("average_position"),
                "zone_label": band["label"],
                "recommended_action": (
                    f"под замером {ticket} — правку не вносить до вердикта"
                    if ticket else band["action"]),
                "experiment": ticket,
                "confidence": e.get("confidence", "unknown"),
            })
    if not items:
        return passport.unavailable(
            "no_signal", detail="коммерческих запросов в зоне позиций 4–20 "
                                "с достаточными показами нет", items=[])
    items.sort(key=lambda i: -(i["impressions"] or 0))
    return {"available": True, "items": items[:limit],
            "considered": len(items),
            "note": "показы сайта по выборке запросов; рыночным спросом не являются"}


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


def build(snap: dict, decision_date: str | None = None, limit: int = 3) -> dict:
    """Три ближайшие возможности роста.

    decision_date — срок решения, если он назначен руководителем. Зашитой
    даты здесь больше нет: письмо две недели печатало «решение к 26.08»,
    когда этот день давно прошёл (аудит 03.09.2026). Без срока строка
    честно говорит «решение за вами».
    """
    items = from_market_demand(snap) + from_queries(snap, "yandex") + from_queries(snap, "google")
    if not items:
        return passport.unavailable("no_signal", detail="сигналов для приоритизации",
                                    items=[])
    items.sort(key=lambda i: -i["score"])
    seen, top, held = set(), [], []
    for i in items:
        key = i["cluster"].lower()
        if key in seen:
            continue
        seen.add(key)
        # Кластер под действующим экспериментом возможностью не является:
        # рекомендованная правка обнулила бы чужой замер. Такие кластеры
        # не занимают места в тройке, но и не пропадают — их перечисляет
        # отдельная строка, чтобы отсутствие кластера в радаре не читалось
        # как отсутствие спроса.
        ticket = under_experiment(i["cluster"], snap)
        if ticket:
            held.append({"cluster": i["cluster"], "experiment": ticket})
            continue
        i["decision_date"] = decision_date
        top.append(i)
        if len(top) >= limit:
            break
    return {"available": True, "reason": None, "items": top,
            "considered": len(items), "held_by_experiment": held,
            "market_demand_used": any(i["evidence_kind"] == "market_demand" for i in top)}
