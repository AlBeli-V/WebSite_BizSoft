#!/usr/bin/env python3
"""Региональное распределение спроса топ-кластеров (месячный срез).

«Зелёный свет» руководителя 30.08.2026: GetRegionsDistribution
(50 ₽/1000 = 0,05 ₽/запрос) по верху коммерческого ядра раз в месяц —
карта регионов для гео-настроек Директа и региональных посадочных.

Вызовы — через штатный WordstatClient (кэш regions_ttl_days, бюджет,
квота). Стоимость прогона: ≤50 фраз × 0,05 ₽ ≈ 2,5 ₽.

Запуск: python3 scripts/seo/wordstat/region_demand.py [YYYY-MM-DD]
Выход:  reports/seo/wordstat/region-demand-<ГГГГ-ММ>.json
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import budget as budget_mod    # noqa: E402
import client as client_mod    # noqa: E402
import config as config_mod    # noqa: E402

OUT_DIR = pathlib.Path("reports/seo/wordstat")
PHRASES_CAP = 50
TOP_REGIONS = 15


def parse_regions(data: dict) -> list[dict]:
    rows = (data or {}).get("regions") or []
    out = []
    for r in rows:
        out.append({"region_id": r.get("regionId") or r.get("region_id"),
                    "name": r.get("regionName") or r.get("name"),
                    "count": int(r.get("count") or r.get("value") or 0),
                    "share": r.get("share") or r.get("percent")})
    out.sort(key=lambda x: -x["count"])
    return out[:TOP_REGIONS]


def run(date_s: str) -> dict:
    import serp_watchlist
    phrases = serp_watchlist.build(date_s, cap=PHRASES_CAP)
    if not phrases:
        return {"available": False, "reason": "ядро фраз пусто"}
    cfg = config_mod.load()
    bud = budget_mod.BudgetController(cfg, today=date_s)
    cli = client_mod.WordstatClient(bud, cfg)
    items, errors, stopped = [], 0, None
    region_totals: dict[str, dict] = {}
    for phrase in phrases:
        res = cli.regions(phrase, reason="region-demand-monthly")
        if res["status"] in ("budget_blocked", "quota_exceeded"):
            stopped = res.get("reason") or cli.stopped_by or res["status"]
            break
        if res["status"] != "ok" or not res.get("data"):
            errors += 1
            continue
        rows = parse_regions(res["data"])
        items.append({"phrase": phrase, "regions": rows})
        for r in rows:
            key = str(r["region_id"])
            agg = region_totals.setdefault(
                key, {"region_id": r["region_id"], "name": r["name"],
                      "count": 0})
            agg["count"] += r["count"]
    top = sorted(region_totals.values(), key=lambda x: -x["count"])[:TOP_REGIONS]
    return {
        "available": bool(items),
        "date": date_s,
        "phrases_planned": len(phrases),
        "collected": len(items),
        "errors": errors,
        "stopped_by": stopped,
        "top_regions": top,
        "items": items,
        "note": ("региональное распределение спроса Вордстата по верху "
                 "коммерческого ядра; агрегат по регионам — сумма счётчиков "
                 "фраз выборки, не весь рынок"),
    }


def main() -> int:
    date_s = sys.argv[1] if len(sys.argv) > 1 else dt.datetime.now(
        dt.timezone(dt.timedelta(hours=3))).date().isoformat()
    res = run(date_s)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"region-demand-{date_s[:7]}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    top = ", ".join(f"{r['name']} ({r['count']})"
                    for r in res.get("top_regions", [])[:5])
    print(f"регионы спроса: {res.get('collected', 0)} фраз; топ: {top or '—'}"
          + (f"; остановлено: {res['stopped_by']}" if res.get("stopped_by")
             else "") + f" -> {out}")
    return 0 if res.get("available") else 1


if __name__ == "__main__":
    sys.exit(main())
