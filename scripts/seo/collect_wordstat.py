#!/usr/bin/env python3
"""Сбор рыночного спроса из Вордстата (Yandex Cloud Search API v2).

Контракт проверен на живом ключе 19.08.2026:
  POST https://searchapi.api.cloud.yandex.net/v2/wordstat/topRequests
       {phrase, numPhrases 1..2000, regions:[id], devices:[DEVICE_ALL|...]}
       → {results:[{phrase,count}], associations:[{phrase,count}], totalCount}
  POST .../regions   {phrase} → {results:[{region,count,share,affinityIndex}]}
  POST .../dynamics  {phrase, period, fromDate, toDate} — даты в RFC3339
  POST .../getRegionsTree {} → справочник регионов
Авторизация: Authorization: Api-Key <ключ> (секрет WORDSTAT_API_KEY).

Единица — показы в поиске Яндекса за 30 дней: это спрос, не покупки и не выручка.
Пустой ответ {} означает «частотность ниже порога выдачи», а не ноль.

Бюджет запросов согласован руководителем 19.08.2026: до 10 000 запросов в месяц.
Скрипт держит жёсткий потолок на прогон и пишет фактический расход в артефакт.

Запуск: python3 scripts/seo/collect_wordstat.py [YYYY-MM-DD] [--max-requests N]
Результат: reports/seo/semantics/core-<дата>.json
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import time

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from snapshot import classify_intent  # noqa: E402

SCHEMA_VERSION = "2.0.0"
BASE = "https://searchapi.api.cloud.yandex.net/v2/wordstat"
PLAN = pathlib.Path("reports/seo/semantics/plan.json")
DISCOVERY = pathlib.Path("reports/seo/semantics/discovery.json")
OUT_DIR = pathlib.Path("reports/seo/semantics")

MONTHLY_BUDGET = 10_000   # согласованный потолок запросов в месяц
MAX_REQUESTS = 3_000      # потолок одного прогона
NUM_PHRASES = 300         # глубина выдачи бесплатна: это один и тот же запрос
PAUSE_SEC = 0.25
LOW_DEMAND_LIMIT = 30
DYNAMICS_CLUSTERS = 30    # сезонность по стольким верхним кластерам
REGION_CLUSTERS = 15      # региональный срез по стольким верхним кластерам


class Budget:
    def __init__(self, cap: int):
        self.cap = cap
        self.used = 0
        self.failures = 0
        self.quota_hit = False

    def spend(self) -> bool:
        if self.used >= self.cap or self.quota_hit:
            return False
        self.used += 1
        return True


def headers() -> dict:
    token = os.environ.get("WORDSTAT_API_KEY", "").strip()
    if not token:
        raise SystemExit("WORDSTAT_API_KEY не задан")
    return {"Authorization": f"Api-Key {token}", "Content-Type": "application/json"}


def call(path: str, body: dict, h: dict, budget: Budget) -> tuple[dict | None, str]:
    if not budget.spend():
        return None, "budget_exhausted"
    try:
        r = requests.post(BASE + path, json=body, headers=h, timeout=40)
    except requests.RequestException as e:
        budget.failures += 1
        return None, f"network_error: {type(e).__name__}"
    time.sleep(PAUSE_SEC)
    if r.status_code == 429:
        budget.quota_hit = True
        return None, "quota_exceeded"
    if r.status_code != 200:
        budget.failures += 1
        return None, f"http_{r.status_code}"
    try:
        data = r.json()
    except ValueError:
        budget.failures += 1
        return None, "not_json"
    if not data:
        return None, "below_threshold"
    return data, "ok"


def phrase_row(row: dict) -> dict:
    text = row.get("phrase", "")
    count = row.get("count")
    return {
        "phrase": text,
        "impressions_wordstat": int(count) if count is not None else None,
        "intent": classify_intent(text),
    }


def collect_phrase(phrase: str, region: str, h: dict, budget: Budget) -> dict:
    data, status = call("/topRequests",
                        {"phrase": phrase, "numPhrases": NUM_PHRASES, "regions": [region]},
                        h, budget)
    out = {"phrase": phrase, "status": status, "total_impressions": None,
           "results": [], "associations": []}
    if status != "ok":
        return out
    total = data.get("totalCount")
    out["total_impressions"] = int(total) if total is not None else None
    out["results"] = [phrase_row(r) for r in (data.get("results") or [])]
    out["associations"] = [phrase_row(r) for r in (data.get("associations") or [])]
    return out


def dedupe(rows: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for r in rows:
        prev = best.get(r["phrase"])
        if prev is None or (r["impressions_wordstat"] or 0) > (prev["impressions_wordstat"] or 0):
            best[r["phrase"]] = r
    return sorted(best.values(), key=lambda r: -(r["impressions_wordstat"] or 0))


def collect_cluster(item: dict, region: str, h: dict, budget: Budget) -> dict:
    probes = [collect_phrase(p, region, h, budget) for p in item["phrases"]]
    measured = [p for p in probes if p["status"] == "ok"]
    all_rows = dedupe([r for p in measured for r in p["results"]])
    commercial = [r for r in all_rows if r["intent"] == "commercial"]
    seed_total = next((p["total_impressions"] for p in probes
                       if p["phrase"] == item["phrases"][0]), None)
    return {
        "cluster": item["cluster"],
        "vendor": item.get("vendor"),
        "page": item.get("page"),
        "priority": item.get("priority"),
        "status": "ok" if measured else (probes[0]["status"] if probes else "no_probes"),
        "seed_impressions": seed_total,
        "probes": [{"phrase": p["phrase"], "status": p["status"],
                    "total_impressions": p["total_impressions"]} for p in probes],
        "phrases": all_rows[:400],
        "associations": dedupe([r for p in measured for r in p["associations"]])[:40],
        "commercial_phrases": len(commercial),
        "commercial_impressions": sum(r["impressions_wordstat"] or 0 for r in commercial) or None,
        "confidence": "sufficient" if (seed_total or 0) >= LOW_DEMAND_LIMIT else "low",
    }


def collect_dynamics(phrase: str, region: str, h: dict, budget: Budget) -> dict:
    today = dt.date.today()
    start = (today - dt.timedelta(days=365)).isoformat()
    body = {"phrase": phrase, "period": "PERIOD_MONTHLY", "regions": [region],
            "fromDate": f"{start}T00:00:00Z", "toDate": f"{today.isoformat()}T00:00:00Z"}
    data, status = call("/dynamics", body, h, budget)
    return {"phrase": phrase, "status": status,
            "series": data if status == "ok" else None}


def collect_regions(phrase: str, h: dict, budget: Budget) -> dict:
    data, status = call("/regions", {"phrase": phrase}, h, budget)
    rows = (data or {}).get("results") or []
    rows = sorted(rows, key=lambda r: -int(r.get("count") or 0))[:25]
    return {"phrase": phrase, "status": status, "regions": rows}


def collect_discovery(region: str, h: dict, budget: Budget) -> list[dict]:
    if not DISCOVERY.exists():
        return []
    cfg = json.loads(DISCOVERY.read_text(encoding="utf-8"))
    template = cfg.get("template", "{brand} купить для юридических лиц")
    out = []
    for brand in cfg.get("brands", []):
        probe = collect_phrase(template.format(brand=brand), region, h, budget)
        commercial = [r for r in probe["results"] if r["intent"] == "commercial"]
        out.append({
            "brand": brand,
            "status": probe["status"],
            "demand": probe["total_impressions"],
            "top_commercial": commercial[:5],
        })
        if budget.quota_hit or budget.used >= budget.cap:
            break
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    date = args[0] if args else dt.date.today().isoformat()
    cap = MAX_REQUESTS
    if "--max-requests" in sys.argv:
        cap = int(sys.argv[sys.argv.index("--max-requests") + 1])

    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    region = plan.get("region_id", "225")
    h = headers()
    budget = Budget(cap)

    clusters = [collect_cluster(c, region, h, budget) for c in plan["clusters"]]

    ranked = sorted([c for c in clusters if c["status"] == "ok"],
                    key=lambda c: -(c["seed_impressions"] or 0))
    dynamics = [collect_dynamics(c["cluster"] if c["vendor"] is None else c["vendor"].lower(),
                                 region, h, budget)
                for c in ranked[:DYNAMICS_CLUSTERS]]
    regions = [collect_regions(c["cluster"] if c["vendor"] is None else c["vendor"].lower(),
                               h, budget)
               for c in ranked[:REGION_CLUSTERS]]
    discovery = collect_discovery(region, h, budget)

    snap = {
        "schema_version": SCHEMA_VERSION,
        "report_date": date,
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "source_name": "yandex_wordstat",
            "endpoint": f"{BASE}/topRequests",
            "region_id": region,
            "region_name": plan.get("region_name", "Россия"),
            "devices": "DEVICE_ALL",
            "match_type": "broad",
            "window": "последние 30 дней",
            "unit": "показы в поиске Яндекса",
            "num_phrases_requested": NUM_PHRASES,
            "modifiers": plan.get("modifiers", []),
            "notes": "Показы Вордстата — объём поисковых запросов в Яндексе, не покупки "
                     "и не выручка. На Google не переносятся. Пустой ответ означает "
                     "частотность ниже порога выдачи, а не ноль.",
        },
        "quota": {
            "monthly_budget": MONTHLY_BUDGET,
            "run_cap": cap,
            "requests_made": budget.used,
            "failures": budget.failures,
            "quota_exceeded": budget.quota_hit,
        },
        "clusters": clusters,
        "seasonality": dynamics,
        "geography": regions,
        "discovery": discovery,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"core-{date}.json"
    out.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for c in clusters if c["status"] == "ok")
    print(f"wordstat: {out} — кластеров {ok}/{len(clusters)}, "
          f"сезонность {sum(1 for d in dynamics if d['status'] == 'ok')}/{len(dynamics)}, "
          f"регионы {sum(1 for r in regions if r['status'] == 'ok')}/{len(regions)}, "
          f"разведка {len(discovery)}, запросов {budget.used}, ошибок {budget.failures}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
