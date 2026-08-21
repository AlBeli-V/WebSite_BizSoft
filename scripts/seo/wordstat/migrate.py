#!/usr/bin/env python3
"""Перенос уже собранных данных Вордстата в Semantic Universe.

За прежние 270 вызовов уже заплачено. Импорт превращает их в базу семантики
и в статистику продуктивности шаблонов, поэтому пилот не платит второй раз
за то же самое и сразу видит, какие шаблоны дают пустые ответы.

Запуск: python3 scripts/seo/wordstat/migrate.py
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import config  # noqa: E402
import discovery as D  # noqa: E402
import universe as U  # noqa: E402

OLD_CACHE = pathlib.Path("reports/seo/semantics/cache-2026-08.json")
PRICE_PER_CALL = 0.02


def pattern_of(seed: str, anchors: list[str]) -> str | None:
    """Восстановить шаблон, из которого получен seed."""
    low = seed.lower()
    for anchor in sorted(anchors, key=len, reverse=True):
        if anchor in low:
            tpl = low.replace(anchor, "{vendor}").strip()
            return tpl if tpl else "{vendor}"
    return None


def main() -> int:
    if not OLD_CACHE.exists():
        print(f"нет прежнего кэша {OLD_CACHE}", file=sys.stderr)
        return 1
    cfg = config.load()
    vendors = D.site_vendors()
    vendor_by_anchor = {v["anchor"]: v for v in vendors}
    anchors = list(vendor_by_anchor)
    index = D.vendor_index(vendors)

    cache = json.loads(OLD_CACHE.read_text(encoding="utf-8"))
    uni = U.Universe()
    stats = D.PatternStats()
    date = "2026-08-20"
    imported = new_phrases = calls = empty = 0

    for key, entry in cache.items():
        kind, seed = key.split("|", 1)
        if kind != "top":
            continue
        calls += 1
        status = entry.get("status")
        tpl = pattern_of(seed, anchors)
        vendor = next((v for a, v in vendor_by_anchor.items() if a in seed.lower()), None)
        rows = entry.get("results") or []
        before = len(uni)
        for r in rows:
            _, is_new = uni.observe(
                phrase=r["phrase"], frequency=r.get("impressions_wordstat"),
                date=date, source_seed=seed, region=cfg["collection"]["region_id"],
                period="последние 30 дней", method="getTop",
                cost_rub=PRICE_PER_CALL / max(1, len(rows)), vendors=index,
                vendor=(vendor or {}).get("vendor"),
                category=(vendor or {}).get("category"))
            imported += 1
            new_phrases += 1 if is_new else 0
        if status != "ok":
            empty += 1
        if tpl:
            stats.record(tpl, ok=status == "ok", unique_new=len(uni) - before)

    uni.save()
    stats.save()
    s = uni.stats()
    print(f"импортировано наблюдений: {imported}, уникальных фраз: {new_phrases}")
    print(f"перенесено вызовов: {calls}, из них пустых: {empty} "
          f"({empty / calls * 100:.0f}%)")
    print(f"база: {s['phrases']} фраз, {s['commercial_phrases']} коммерческих, "
          f"{s['clusters']} кластеров, спрос {s['total_commercial_demand']:,}"
          .replace(",", " "))
    print("продуктивность шаблонов:")
    for tpl, d in sorted(stats.data.items(), key=lambda kv: -kv[1]["calls"])[:10]:
        ok_rate = 1 - d["empty"] / d["calls"]
        print(f"  {tpl:36} вызовов {d['calls']:3}  непустых {ok_rate:5.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
