#!/usr/bin/env python3
"""Замер глубины выдачи GetTop: сколько фраз запрашивать за один вызов.

Глубина не тарифицируется отдельно — один вызов стоит одинаково при любом
numPhrases. Значит, вопрос не в цене вызова, а в том, что мы получаем на рубль:
больше уникальных и коммерческих фраз или больше мусора и дублей.

Замеряется на нескольких seed разной ёмкости: 100, 500, 1000, 2000.
Максимум брать нельзя только потому, что он максимум — решение принимается
по соотношению полезности, стоимости и дублирования.

Запуск: python3 scripts/seo/wordstat/benchmark.py [--phrases a,b,c]
Результат: reports/seo/wordstat/gettop-depth-benchmark.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import budget as budget_mod    # noqa: E402
import client as client_mod    # noqa: E402
import config                  # noqa: E402
import normalize as N          # noqa: E402

OUT = pathlib.Path("reports/seo/wordstat")
DEPTHS = (100, 500, 1000, 2000)
# Seed разной ёмкости: крупный бренд, средний, узкий продукт, тематический запрос.
DEFAULT_PHRASES = ["adobe", "wondershare", "marmoset toolbag", "оплата зарубежных сервисов"]


def measure(client, phrase: str, depth: int, cfg: dict) -> dict:
    started = time.time()
    res = client.top(phrase, reason="benchmark", cluster=None, num_phrases=depth)
    latency = round(time.time() - started, 3)
    if res["status"] != "ok":
        return {"phrase": phrase, "depth": depth, "status": res["status"],
                "latency_sec": latency}
    rows = (res["data"] or {}).get("results") or []
    raw = len(rows)
    keys = {N.morph_key(r.get("phrase", "")) for r in rows}
    commercial = [r for r in rows
                  if N.classify_intent(r.get("phrase", "")) == "commercial"
                  and N.in_scope(r.get("phrase", ""))]
    price = config.price_of("getTop", cfg=cfg)
    return {
        "phrase": phrase, "depth": depth, "status": "ok", "latency_sec": latency,
        "raw_phrases": raw,
        "unique_phrases": len(keys),
        "duplicate_rate": round(1 - len(keys) / raw, 4) if raw else None,
        "commercial_phrases": len(commercial),
        "truncated": raw >= depth,
        "cost_rub": price,
        "cost_per_1000_unique_rub": round(price / len(keys) * 1000, 4) if keys else None,
        "cost_per_1000_commercial_rub": (round(price / len(commercial) * 1000, 4)
                                         if commercial else None),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phrases", default=",".join(DEFAULT_PHRASES))
    ap.add_argument("--date", default=dt.date.today().isoformat())
    args = ap.parse_args()
    phrases = [p.strip() for p in args.phrases.split(",") if p.strip()]

    cfg = config.load()
    bud = budget_mod.BudgetController(cfg, today=args.date)
    client = client_mod.WordstatClient(bud, cfg)

    rows, stopped = [], None
    for phrase in phrases:
        for depth in DEPTHS:
            r = measure(client, phrase, depth, cfg)
            rows.append(r)
            print(f"  {phrase[:26]:28} глубина {depth:5}: {r['status']}"
                  + (f", уникальных {r['unique_phrases']:4}, "
                     f"коммерческих {r['commercial_phrases']:3}, "
                     f"дублей {r['duplicate_rate']:.1%}, "
                     f"{'обрезано' if r['truncated'] else 'полностью'}"
                     if r["status"] == "ok" else ""))
            if r["status"] in ("quota_exceeded", "budget_blocked"):
                stopped = r["status"]
                break
        if stopped:
            break

    ok = [r for r in rows if r["status"] == "ok"]
    by_depth: dict[int, dict] = {}
    for r in ok:
        d = by_depth.setdefault(r["depth"], {"calls": 0, "unique": 0, "commercial": 0,
                                             "raw": 0, "truncated": 0, "latency": 0.0})
        d["calls"] += 1
        d["unique"] += r["unique_phrases"]
        d["commercial"] += r["commercial_phrases"]
        d["raw"] += r["raw_phrases"]
        d["truncated"] += 1 if r["truncated"] else 0
        d["latency"] += r["latency_sec"]

    price = config.price_of("getTop", cfg=cfg)
    summary = []
    for depth in sorted(by_depth):
        d = by_depth[depth]
        cost = d["calls"] * price
        summary.append({
            "depth": depth, "calls": d["calls"], "raw": d["raw"],
            "unique": d["unique"], "commercial": d["commercial"],
            "duplicate_rate": round(1 - d["unique"] / d["raw"], 4) if d["raw"] else None,
            "truncated_calls": d["truncated"],
            "avg_latency_sec": round(d["latency"] / d["calls"], 3),
            "cost_rub": round(cost, 4),
            "cost_per_1000_unique_rub": round(cost / d["unique"] * 1000, 4) if d["unique"] else None,
            "cost_per_1000_commercial_rub": (round(cost / d["commercial"] * 1000, 4)
                                             if d["commercial"] else None),
        })

    result = {"date": args.date, "phrases": phrases, "depths": list(DEPTHS),
              "stopped": stopped, "measurements": rows, "summary": summary,
              "spent_rub": round(bud.cost_month(), 4)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gettop-depth-benchmark.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    L = ["# Замер глубины выдачи GetTop", "",
         f"Дата: {args.date}. Фразы: {', '.join(phrases)}.", "",
         "Глубина не тарифицируется отдельно: один вызов стоит одинаково при любом "
         "`numPhrases`. Поэтому сравнивается не цена вызова, а полезность на рубль.", "",
         "| Глубина | Вызовов | Уникальных фраз | Коммерческих | Дублей | Обрезано | "
         "Задержка | ₽/1000 уникальных | ₽/1000 коммерческих |",
         "|---|---|---|---|---|---|---|---|---|"]
    for s in summary:
        L.append(f"| {s['depth']} | {s['calls']} | {s['unique']} | {s['commercial']} | "
                 f"{s['duplicate_rate']:.1%} | {s['truncated_calls']} | "
                 f"{s['avg_latency_sec']} с | {s['cost_per_1000_unique_rub']} | "
                 f"{s['cost_per_1000_commercial_rub'] or '—'} |")
    L += ["", f"Израсходовано на замер: {len(ok)} вызовов, "
          f"{round(len(ok) * price, 2)} ₽.", ""]
    if stopped:
        L.append(f"Замер остановлен: {stopped}. Часть глубин не измерена.")
    (OUT / "gettop-depth-benchmark.md").write_text("\n".join(L), encoding="utf-8")
    print(f"\nзамер: {OUT / 'gettop-depth-benchmark.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
