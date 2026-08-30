#!/usr/bin/env python3
"""Радар каннибализации: несколько страниц сайта делят один запрос.

Сам факт двух URL по запросу проблемой не считается — ищется расщепление
показов (ни одна страница не собирает запрос) и нестабильность лидера
(выдача перебирает страницы день ото дня). Детектор только наблюдает и
формирует карточку возможности; canonical, склейка и перелинковка — решения,
которые готовятся отдельно и проходят обычный цикл PR.

Источник — пары «запрос × страница × день» GSC (pairs.py). Это данные
Google; по Яндексу разбивка запрос×страница источником не отдаётся.
"""

from __future__ import annotations

import pairs

MIN_IMPRESSIONS = 10     # ниже — расщепление неотличимо от шума
MIN_SHARE = 0.2          # страница «участвует» в запросе с этой доли показов
UNSTABLE_CHANGES = 2     # смен лидера за окно, с которых начинается нестабильность
LIMIT = 15

VERDICT_LABEL = {
    "unstable": "нестабильность: выдача перебирает страницы",
    "split": "расщепление показов между страницами",
}


def build(date_s: str) -> dict:
    data = pairs.load_latest(date_s)
    if not data:
        return {"available": False,
                "reason": "сенсор пар «запрос × страница» ещё не накопил данных",
                "items": []}
    agg = pairs.by_query(data["rows"])
    items = []
    for query, q in agg.items():
        if q["impressions"] < MIN_IMPRESSIONS:
            continue
        contenders = {p: v for p, v in q["pages"].items()
                      if v["share"] >= MIN_SHARE}
        if len(contenders) < 2:
            continue
        unstable = q["leader_changes"] >= UNSTABLE_CHANGES
        top_pages = sorted(q["pages"].items(),
                           key=lambda kv: -kv[1]["impressions"])[:3]
        items.append({
            "query": query,
            "impressions": q["impressions"],
            "clicks": q["clicks"],
            "pages": [{"page": p, "share": round(v["share"], 2),
                       "impressions": v["impressions"],
                       "avg_position": v["avg_position"]}
                      for p, v in top_pages],
            "leader_changes": q["leader_changes"],
            "days_observed": q["days_observed"],
            "verdict": "unstable" if unstable else "split",
            "verdict_label": VERDICT_LABEL["unstable" if unstable else "split"],
            "recommended_action": (
                "выбрать основную страницу и усилить её: canonical или "
                "склейка содержимого, внутренние ссылки со второстепенной"
                if unstable else
                "проверить, не отвечают ли страницы на разные интенты; "
                "при одном интенте — сослать второстепенную на основную"),
        })
    if not items:
        return {"available": True, "items": [],
                "reason": "запросов с расщеплением между страницами не найдено",
                "as_of": data["date"], "window": data["window"]}
    items.sort(key=lambda i: (i["verdict"] != "unstable", -i["impressions"]))
    return {"available": True, "items": items[:LIMIT],
            "considered": len(items),
            "unstable_count": sum(1 for i in items if i["verdict"] == "unstable"),
            "as_of": data["date"], "window": data["window"],
            "truncated": data["truncated"],
            "note": ("данные Google Search Console (пары запрос × страница × "
                     "день, окно 28 дней); Яндекс такой разбивки не отдаёт")}
