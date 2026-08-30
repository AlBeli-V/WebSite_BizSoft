#!/usr/bin/env python3
"""Пары «запрос × страница × день» из выгрузки GSC — общий слой детекторов.

Сенсор пишет collect.py (ключ `pairs` в gsc-<дата>.json, окно 28 дней,
измерения query+page+date). Здесь — загрузка последней выгрузки и агрегация
по запросам; поверх этого работают детекторы каннибализации
(cannibalization.py) и query-page mismatch (mismatch.py).

Правила методики наследуются: пары — выборка GSC (Google), не «весь поиск»;
отсутствие выгрузки — честное «данных нет», а не пустой список находок.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib

DATA_DIR = pathlib.Path("reports/seo/data")
SITE = "https://biz-soft.pro"

# Сколько дней назад искать последнюю выгрузку с парами: сенсор ежедневный,
# но выходной сбоя не должен выключать детекторы.
LOOKBACK_DAYS = 7


def normalize_rows(rows: list[dict]) -> list[dict]:
    """Строки GSC → плоские записи. Переживает оба формата ключей:
    [query, page] (первые дни сенсора) и [query, page, date]."""
    out = []
    for r in rows or []:
        keys = r.get("keys") or []
        if len(keys) < 2:
            continue
        page = (keys[1] or "").replace(SITE, "") or "/"
        out.append({
            "query": keys[0],
            "page": page,
            "date": keys[2] if len(keys) > 2 else None,
            "impressions": int(r.get("impressions") or 0),
            "clicks": int(r.get("clicks") or 0),
            "position": r.get("position"),
        })
    return out


def load_latest(date_s: str) -> dict | None:
    """Последняя выгрузка пар не старше LOOKBACK_DAYS от даты отчёта."""
    date = dt.date.fromisoformat(date_s)
    for back in range(LOOKBACK_DAYS + 1):
        d = (date - dt.timedelta(days=back)).isoformat()
        p = DATA_DIR / f"gsc-{d}.json"
        if not p.exists():
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        pairs = raw.get("pairs")
        if not isinstance(pairs, dict) or pairs.get("error"):
            continue
        rows = normalize_rows(pairs.get("rows"))
        if not rows:
            continue
        return {"date": d, "window": pairs.get("window") or {},
                "truncated": bool(pairs.get("truncated")), "rows": rows}
    return None


def by_query(rows: list[dict]) -> dict[str, dict]:
    """Агрегация по запросу: суммы, страницы с долями, дневные лидеры.

    Лидер дня — страница с наибольшими показами в этот день; серия лидеров
    строится только по дням с показами. Для строк без даты (старый формат)
    дневная серия не строится — нестабильность честно неизмерима.
    """
    agg: dict[str, dict] = {}
    for r in rows:
        q = agg.setdefault(r["query"], {"impressions": 0, "clicks": 0,
                                        "pages": {}, "daily": {}})
        q["impressions"] += r["impressions"]
        q["clicks"] += r["clicks"]
        p = q["pages"].setdefault(r["page"], {"impressions": 0, "clicks": 0,
                                              "pos_sum": 0.0, "pos_w": 0})
        p["impressions"] += r["impressions"]
        p["clicks"] += r["clicks"]
        if r["position"] is not None and r["impressions"]:
            p["pos_sum"] += float(r["position"]) * r["impressions"]
            p["pos_w"] += r["impressions"]
        if r["date"] and r["impressions"]:
            day = q["daily"].setdefault(r["date"], {})
            day[r["page"]] = day.get(r["page"], 0) + r["impressions"]
    for q in agg.values():
        total = q["impressions"] or 1
        for page, p in q["pages"].items():
            p["share"] = p["impressions"] / total
            p["avg_position"] = (round(p["pos_sum"] / p["pos_w"], 2)
                                 if p["pos_w"] else None)
            del p["pos_sum"], p["pos_w"]
        leaders = [max(day.items(), key=lambda kv: kv[1])[0]
                   for _, day in sorted(q["daily"].items())]
        q["leader_series"] = leaders
        q["leader_changes"] = sum(1 for a, b in zip(leaders, leaders[1:])
                                  if a != b)
        q["days_observed"] = len(leaders)
        del q["daily"]
    return agg
