#!/usr/bin/env python3
"""Чтение инвентаря URL (sitemap) и страниц с показами — слой этапа 2.

Инвентарь пишет sitemap_inventory.py (workflow seo-data-collect); здесь —
загрузка последней выгрузки, реестра first-seen и множества страниц, у
которых есть показы в Google (пары + разрез page). Поверх этого работают
zero_impression.py и lifecycle.py.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib

import pairs

DATA_DIR = pathlib.Path("reports/seo/data")
LOOKBACK_DAYS = 7


def load_latest(date_s: str) -> dict | None:
    """Последний инвентарь sitemap не старше LOOKBACK_DAYS."""
    date = dt.date.fromisoformat(date_s)
    for back in range(LOOKBACK_DAYS + 1):
        d = (date - dt.timedelta(days=back)).isoformat()
        p = DATA_DIR / f"sitemap-{d}.json"
        if not p.exists():
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if raw.get("error") or not raw.get("urls"):
            continue
        return {"date": d, "urls": raw["urls"], "count": raw.get("count")}
    return None


def first_seen() -> dict:
    """Реестр «путь → дата первой фиксации в инвентаре»."""
    p = DATA_DIR / "url-first-seen.json"
    if not p.exists():
        return {"paths": {}, "started": None}
    try:
        reg = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"paths": {}, "started": None}
    reg.setdefault("paths", {})
    return reg


def pages_with_impressions(date_s: str) -> set[str]:
    """Страницы с показами Google за окно 28 дней: пары + разрез page.

    Оба источника — выборки одного GSC; объединение даёт самое полное из
    доступного. Яндекс разбивку по страницам не отдаёт — покрытие считается
    только по Google, и потребители обязаны называть это явно.
    """
    seen: set[str] = set()
    data = pairs.load_latest(date_s)
    if data:
        seen |= {r["page"] for r in data["rows"] if r["impressions"] > 0}
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
        for r in ((raw.get("analytics") or {}).get("page") or {}).get("rows", []):
            if (r.get("impressions") or 0) > 0 and r.get("keys"):
                seen.add((r["keys"][0] or "").replace(pairs.SITE, "") or "/")
        break
    return seen
