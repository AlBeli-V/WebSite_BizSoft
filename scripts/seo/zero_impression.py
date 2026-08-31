#!/usr/bin/env python3
"""Zero-impression: страницы инвентаря без показов Google.

1 000+ карточек не одинаково полезны: страница, месяцами не получающая ни
одного показа, — вопрос к индексации, спросу, названию или перелинковке.
Детектор не генерирует туда тексты вслепую (правило предложения №4): он
классифицирует и отдаёт список на разбор.

Возраст страницы считается от первой фиксации в инвентаре (url-first-seen):
у страниц старше самого сенсора возраст — нижняя оценка, это помечается.
Покрытие и показы — только Google (Яндекс разбивку по страницам не отдаёт).
"""

from __future__ import annotations

import datetime as dt

import inventory
from mismatch import page_type

YOUNG_DAYS = 14     # моложе — «рано судить», это не находка
OLD_DAYS = 30       # старше без показов — кандидат на разбор
LIMIT = 40


def build(date_s: str) -> dict:
    inv = inventory.load_latest(date_s)
    if not inv:
        return {"available": False,
                "reason": "инвентарь sitemap ещё не собран "
                          "(шаг workflow seo-data-collect)",
                "items": []}
    seen = inventory.pages_with_impressions(date_s)
    reg = inventory.first_seen()
    started = reg.get("started")
    date = dt.date.fromisoformat(date_s)

    items, young = [], 0
    for u in inv["urls"]:
        path = u["path"]
        if path in seen:
            continue
        first = reg["paths"].get(path)
        days = (date - dt.date.fromisoformat(first)).days if first else None
        floor = bool(first and started and first == started)
        if days is not None and days < YOUNG_DAYS and not floor:
            young += 1
            continue        # молодая страница без показов — норма, не находка
        if days is not None and days < OLD_DAYS and not floor:
            verdict = "наблюдение: показов нет, срок ещё не вышел"
        else:
            verdict = ("без показов Google — разобрать: индексация / спрос / "
                       "название / перелинковка")
        items.append({
            "path": path,
            "page_type": page_type(path),
            "known_days": days,
            "known_days_is_floor": floor,
            "lastmod": u.get("lastmod"),
            "verdict": verdict,
        })
    items.sort(key=lambda i: (i["page_type"], i["path"]))
    covered = len([u for u in inv["urls"] if u["path"] in seen])
    by_type: dict[str, int] = {}
    for i in items:
        by_type[i["page_type"]] = by_type.get(i["page_type"], 0) + 1
    return {
        "available": True,
        "as_of": inv["date"],
        "inventory_total": len(inv["urls"]),
        "with_impressions": covered,
        "coverage_google": round(covered / len(inv["urls"]), 3)
                           if inv["urls"] else None,
        "young_skipped": young,
        "zero_total": len(items),
        "by_type": by_type,
        "items": items[:LIMIT],
        "note": ("покрытие и показы — Google Search Console (окно 28 дней); "
                 "возраст — от первой фиксации в инвентаре, у страниц старше "
                 "сенсора это нижняя оценка"),
    }
