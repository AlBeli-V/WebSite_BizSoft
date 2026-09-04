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
UNIVERSE = OUT_DIR / "semantic-universe.jsonl"
PHRASES_CAP = 50
TOP_REGIONS = 15
# Ниже этой месячной частотности региональное распределение не существует:
# замер 01.09.2026 дал 43 из 50 ответов below_threshold — длинные хвосты
# из ядра тратят вызовы впустую. Отбираем частотные фразы, хвосты — добор.
MIN_FREQUENCY = 100


def _frequency_map() -> dict[str, int]:
    freq: dict[str, int] = {}
    if not UNIVERSE.exists():
        return freq
    for line in UNIVERSE.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        f = row.get("wordstat_frequency")
        if isinstance(f, (int, float)) and f > 0:
            freq[row.get("phrase", "").lower()] = int(f)
    return freq


def pick_phrases(core: list[str], cap: int = PHRASES_CAP) -> list[str]:
    """Частотные фразы ядра вперёд; хвосты — только если частотных мало."""
    freq = _frequency_map()
    frequent = [p for p in core if freq.get(p.lower(), 0) >= MIN_FREQUENCY]
    frequent.sort(key=lambda p: -freq.get(p.lower(), 0))
    rest = [p for p in core if p not in frequent]
    return (frequent + rest)[:cap]


# Имена по геобазе Яндекса даём только для регионов, в которых уверены;
# остальные честно остаются числовым id (ответ API имён не содержит).
REGION_NAMES = {
    "225": "Россия", "1": "Москва и область", "213": "Москва",
    "2": "Санкт-Петербург", "10174": "Санкт-Петербург и область",
}


def parse_regions(data: dict) -> list[dict]:
    """Строки из ответа getRegionsDistribution.

    Фактическая форма (кэш 21.08.2026): {"results": [{"region": "1",
    "count": "580", "share": ..., "affinityIndex": ...}]}; region — id
    геобазы строкой, имени нет, count — строка. Прежний ключ regions
    оставлен запасным.
    """
    rows = (data or {}).get("results") or (data or {}).get("regions") or []
    out = []
    for r in rows:
        rid = (r.get("region") or r.get("regionId") or r.get("region_id"))
        out.append({"region_id": rid,
                    "name": (r.get("regionName") or r.get("name")
                             or REGION_NAMES.get(str(rid)) or str(rid)),
                    "count": int(r.get("count") or r.get("value") or 0),
                    "share": r.get("share") or r.get("percent"),
                    "affinity": r.get("affinityIndex")})
    out.sort(key=lambda x: -x["count"])
    return out[:TOP_REGIONS]


def run(date_s: str) -> dict:
    import serp_watchlist
    core = serp_watchlist.build(date_s, cap=PHRASES_CAP * 6)
    phrases = pick_phrases(core)
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
    date_s = sys.argv[1] if len(sys.argv) > 1 else config_mod.today_msk()
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
