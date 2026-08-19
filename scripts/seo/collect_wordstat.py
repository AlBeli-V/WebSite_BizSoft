#!/usr/bin/env python3
"""Сбор рыночного спроса из Вордстата (Yandex Cloud Search API v2).

Проверено 19.08.2026 на живом ключе:
  POST https://searchapi.api.cloud.yandex.net/v2/wordstat/topRequests
       {phrase, numPhrases 1..2000, regions:[id], devices:[DEVICE_ALL|DESKTOP|PHONE|TABLET]}
       → {results:[{phrase,count}], associations:[{phrase,count}], totalCount}
  POST .../regions   {phrase} → {results:[{region,count,share,affinityIndex}]}
  POST .../getRegionsTree {} → дерево регионов (справочник, 1103 узла)
  POST .../dynamics  {phrase, period, fromDate, toDate} — даты в формате RFC3339
Авторизация: заголовок Authorization: Api-Key <ключ> (секрет WORDSTAT_API_KEY).

Единица измерения — показы в поиске Яндекса за последние 30 дней, а не покупки
и не выручка. Пустой ответ {} означает «частотность ниже порога выдачи», а не ноль.

Запуск: python3 scripts/seo/collect_wordstat.py [YYYY-MM-DD]
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

SCHEMA_VERSION = "1.0.0"
BASE = "https://searchapi.api.cloud.yandex.net/v2/wordstat"
CONFIG = pathlib.Path("reports/seo/semantics/clusters.json")
OUT_DIR = pathlib.Path("reports/seo/semantics")
NUM_PHRASES = 100
PAUSE_SEC = 0.4          # держим запас по лимиту запросов в секунду
LOW_DEMAND_LIMIT = 30    # ниже — сигнал считается слабым, не выводом


def headers() -> dict:
    token = os.environ.get("WORDSTAT_API_KEY", "").strip()
    if not token:
        raise SystemExit("WORDSTAT_API_KEY не задан")
    return {"Authorization": f"Api-Key {token}", "Content-Type": "application/json"}


def call(path: str, body: dict, h: dict) -> tuple[dict | None, str]:
    """Возвращает (данные, статус). Пустой ответ — below_threshold, не ноль."""
    try:
        r = requests.post(BASE + path, json=body, headers=h, timeout=40)
    except requests.RequestException as e:
        return None, f"network_error: {type(e).__name__}"
    if r.status_code == 429:
        return None, "quota_exceeded"
    if r.status_code != 200:
        return None, f"http_{r.status_code}"
    try:
        data = r.json()
    except ValueError:
        return None, "not_json"
    if not data:
        return None, "below_threshold"
    return data, "ok"


def phrase_row(row: dict, seed: str) -> dict:
    text = row.get("phrase", "")
    count = row.get("count")
    return {
        "phrase": text,
        "impressions_wordstat": int(count) if count is not None else None,
        "intent": classify_intent(text),
        "contains_seed": seed.lower() in text.lower(),
    }


def collect_cluster(item: dict, region: str, h: dict, stats: dict) -> dict:
    seed = item["seed"]
    body = {"phrase": seed, "numPhrases": NUM_PHRASES, "regions": [region]}
    data, status = call("/topRequests", body, h)
    stats["requests"] += 1
    time.sleep(PAUSE_SEC)
    out = {
        "cluster": item["cluster"],
        "seed": seed,
        "page": item.get("page"),
        "priority": item.get("priority"),
        "status": status,
        "total_impressions": None,
        "phrases": [],
        "associations": [],
    }
    if status != "ok":
        if status != "below_threshold":
            stats["failures"] += 1
        return out
    total = data.get("totalCount")
    out["total_impressions"] = int(total) if total is not None else None
    out["phrases"] = [phrase_row(r, seed) for r in (data.get("results") or [])]
    out["associations"] = [phrase_row(r, seed) for r in (data.get("associations") or [])]
    commercial = [p for p in out["phrases"] if p["intent"] == "commercial"]
    out["commercial_phrases"] = len(commercial)
    out["commercial_impressions"] = sum(
        p["impressions_wordstat"] or 0 for p in commercial) or None
    out["confidence"] = ("sufficient" if (out["total_impressions"] or 0) >= LOW_DEMAND_LIMIT
                         else "low")
    return out


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    region = cfg.get("region_id", "225")
    h = headers()
    stats = {"requests": 0, "failures": 0}

    clusters = sorted(cfg["clusters"], key=lambda c: (c.get("priority", 9), c["cluster"]))
    results = [collect_cluster(c, region, h, stats) for c in clusters]

    snap = {
        "schema_version": SCHEMA_VERSION,
        "report_date": date,
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "source_name": "yandex_wordstat",
            "endpoint": f"{BASE}/topRequests",
            "region_id": region,
            "region_name": cfg.get("region_name", "Россия"),
            "devices": "DEVICE_ALL",
            "match_type": "broad",
            "window": "последние 30 дней",
            "unit": "показы в поиске Яндекса",
            "num_phrases_requested": NUM_PHRASES,
            "notes": "Показы Вордстата — объём поисковых запросов в Яндексе, не покупки "
                     "и не выручка. На Google не переносятся. Пустой ответ означает "
                     "частотность ниже порога выдачи, а не ноль.",
        },
        "quota": {"requests_made": stats["requests"], "failures": stats["failures"]},
        "clusters": results,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"core-{date}.json"
    out.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for c in results if c["status"] == "ok")
    print(f"wordstat: {out} — кластеров {ok}/{len(results)}, "
          f"запросов {stats['requests']}, ошибок {stats['failures']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
