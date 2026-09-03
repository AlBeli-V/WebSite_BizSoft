#!/usr/bin/env python3
"""Жизненный цикл страниц по дневным рядам Google (пары query×page×day).

Статусы: new → gaining → stable → declining. Ранний детектор увядания
(Early Decay) — цель: заметить −30% недели к неделе до того, как страница
выпадет из выдачи. Статус описывает только Google-видимость страницы в
28-дневном окне пар; это выборка, а не «весь поиск».
"""

from __future__ import annotations

import datetime as dt

import pairs
import passport
from mismatch import page_type

NEW_WINDOW_DAYS = 10     # первая активность в последние N дней окна → new
GAIN_RATIO = 1.3
DECLINE_RATIO = 0.7
MIN_BASE = 10            # ниже — колебания не считаются трендом
LIMIT = 25

STATUS_LABEL = {
    "new": "новая: первые показы",
    "gaining": "растёт",
    "stable": "стабильна",
    "declining": "снижается — ранний сигнал увядания",
}


def _page_series(rows: list[dict]) -> dict[str, dict[str, int]]:
    series: dict[str, dict[str, int]] = {}
    for r in rows:
        if not r["date"] or r["impressions"] <= 0:
            continue
        series.setdefault(r["page"], {})
        series[r["page"]][r["date"]] = (series[r["page"]].get(r["date"], 0)
                                        + r["impressions"])
    return series


def _status(days: dict[str, int], window_end: dt.date) -> tuple[str, dict]:
    first = min(days)
    last7_start = (window_end - dt.timedelta(days=6)).isoformat()
    prev7_start = (window_end - dt.timedelta(days=13)).isoformat()
    last7 = sum(v for d, v in days.items() if d >= last7_start)
    prev7 = sum(v for d, v in days.items() if prev7_start <= d < last7_start)
    total = sum(days.values())
    meta = {"first_active": first, "last7": last7, "prev7": prev7,
            "total": total}
    if first >= (window_end - dt.timedelta(days=NEW_WINDOW_DAYS)).isoformat():
        return "new", meta
    if prev7 >= MIN_BASE and last7 <= prev7 * DECLINE_RATIO:
        return "declining", meta
    if last7 >= MIN_BASE and prev7 and last7 >= prev7 * GAIN_RATIO:
        return "gaining", meta
    return "stable", meta


def build(date_s: str) -> dict:
    data = pairs.load_latest(date_s)
    if not data:
        return passport.unavailable(
            "no_file", source="сенсор пар «запрос × страница»", items=[])
    window_end = dt.date.fromisoformat(
        (data.get("window") or {}).get("to") or data["date"])
    series = _page_series(data["rows"])
    if not series:
        return {"available": True, "items": [], "counts": {},
                "reason": "страниц с дневными показами в окне нет",
                "as_of": data["date"]}
    items, counts = [], {}
    for page, days in series.items():
        status, meta = _status(days, window_end)
        counts[status] = counts.get(status, 0) + 1
        items.append({"page": page, "page_type": page_type(page),
                      "status": status,
                      "status_label": STATUS_LABEL[status], **meta})
    order = {"declining": 0, "gaining": 1, "new": 2, "stable": 3}
    items.sort(key=lambda i: (order[i["status"]], -i["total"]))
    return {
        "available": True,
        "as_of": data["date"],
        "window": data.get("window"),
        "counts": counts,
        "items": items[:LIMIT],
        "pages_total": len(series),
        "note": ("статусы по дневным показам Google (окно 28 дней, выборка "
                 "пар); Яндекс дневных рядов по страницам не отдаёт"),
    }
