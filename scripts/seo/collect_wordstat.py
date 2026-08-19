#!/usr/bin/env python3
"""Сбор рыночного спроса из Вордстата (Yandex Cloud Search API v2).

Контракт проверен на живом ключе 19.08.2026:
  POST https://searchapi.api.cloud.yandex.net/v2/wordstat/topRequests
       {phrase, numPhrases 1..2000, regions:[id], devices:[DEVICE_ALL|...]}
       → {results:[{phrase,count}], associations:[{phrase,count}], totalCount}
  POST .../regions   {phrase} → {results:[{region,count,share,affinityIndex}]}
  POST .../dynamics  {phrase, period, fromDate, toDate} — даты в RFC3339
Авторизация: Authorization: Api-Key <ключ> (секрет WORDSTAT_API_KEY).

ЛИМИТ СЕРВИСА: 100 запросов в час на облако
(`search-api.wordstatRequestsPerHour.rate`, замер 19.08.2026 — HTTP 429).
Поэтому сбор возобновляемый: каждый прогон берёт до RUN_CAP новых фраз,
кладёт ответы в помесячный кэш и продолжает с того места на следующем часу.
Полный проход по каталогу — около семи часовых прогонов.

Единица — показы в поиске Яндекса за 30 дней: спрос, не покупки и не выручка.
Пустой ответ {} означает «частотность ниже порога выдачи», а не ноль.
Бюджет обращений согласован руководителем 19.08.2026: до 10 000 запросов в месяц.

Запуск: python3 scripts/seo/collect_wordstat.py [YYYY-MM-DD] [--run-cap N]
Результат: reports/seo/semantics/cache-<ГГГГ-ММ>.json и core-<дата>.json
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

HOURLY_LIMIT = 100        # жёсткий лимит сервиса
RUN_CAP = 90              # запас, чтобы не упереться в 429 на последних фразах
MONTHLY_BUDGET = 10_000   # согласованный потолок
NUM_PHRASES = 300         # глубина выдачи квоту не тратит
PAUSE_SEC = 0.2
LOW_DEMAND_LIMIT = 30
DYNAMICS_CLUSTERS = 25
REGION_CLUSTERS = 15


def headers() -> dict:
    token = os.environ.get("WORDSTAT_API_KEY", "").strip()
    if not token:
        raise SystemExit("WORDSTAT_API_KEY не задан")
    return {"Authorization": f"Api-Key {token}", "Content-Type": "application/json"}


class Session:
    """Один часовой прогон: считает запросы и останавливается на лимите."""

    def __init__(self, cap: int, h: dict):
        self.cap = cap
        self.h = h
        self.used = 0
        self.failures = 0
        self.stopped = None

    def can_continue(self) -> bool:
        return self.stopped is None and self.used < self.cap

    def post(self, path: str, body: dict) -> tuple[dict | None, str]:
        if not self.can_continue():
            return None, "run_cap_reached"
        self.used += 1
        try:
            r = requests.post(BASE + path, json=body, headers=self.h, timeout=40)
        except requests.RequestException as e:
            self.failures += 1
            return None, f"network_error: {type(e).__name__}"
        time.sleep(PAUSE_SEC)
        if r.status_code == 429:
            self.stopped = "hourly_quota_exceeded"
            return None, "quota_exceeded"
        if r.status_code != 200:
            self.failures += 1
            return None, f"http_{r.status_code}"
        try:
            data = r.json()
        except ValueError:
            self.failures += 1
            return None, "not_json"
        if not data:
            return None, "below_threshold"
        return data, "ok"


def row(item: dict) -> dict:
    text = item.get("phrase", "")
    count = item.get("count")
    return {"phrase": text,
            "impressions_wordstat": int(count) if count is not None else None,
            "intent": classify_intent(text)}


def fetch(kind: str, phrase: str, region: str, s: Session) -> dict:
    """Один запрос к API; результат сразу приводится к компактному виду."""
    if kind == "top":
        data, status = s.post("/topRequests",
                              {"phrase": phrase, "numPhrases": NUM_PHRASES,
                               "regions": [region]})
        if status != "ok":
            return {"status": status}
        total = data.get("totalCount")
        return {"status": "ok",
                "total_impressions": int(total) if total is not None else None,
                "results": [row(r) for r in (data.get("results") or [])],
                "associations": [row(r) for r in (data.get("associations") or [])]}
    if kind == "regions":
        data, status = s.post("/regions", {"phrase": phrase})
        if status != "ok":
            return {"status": status}
        rows = sorted(data.get("results") or [],
                      key=lambda r: -int(r.get("count") or 0))[:25]
        return {"status": "ok", "regions": rows}
    if kind == "dynamics":
        today = dt.date.today()
        start = (today - dt.timedelta(days=365)).isoformat()
        data, status = s.post("/dynamics",
                              {"phrase": phrase, "period": "PERIOD_MONTHLY",
                               "regions": [region],
                               "fromDate": f"{start}T00:00:00Z",
                               "toDate": f"{today.isoformat()}T00:00:00Z"})
        return {"status": status, "series": data if status == "ok" else None}
    raise ValueError(kind)


def request_plan(plan: dict, discovery: dict | None) -> list[dict]:
    """Полный список запросов месяца в порядке приоритета."""
    specs: list[dict] = []
    for c in plan["clusters"]:
        for phrase in c["phrases"]:
            specs.append({"kind": "top", "phrase": phrase, "cluster": c["cluster"]})
    if discovery:
        tpl = discovery.get("template", "{brand} купить для юридических лиц")
        for brand in discovery.get("brands", []):
            specs.append({"kind": "top", "phrase": tpl.format(brand=brand),
                          "cluster": None, "brand": brand})
    seeds = [c["phrases"][0] for c in plan["clusters"]]
    for phrase in seeds[:DYNAMICS_CLUSTERS]:
        specs.append({"kind": "dynamics", "phrase": phrase})
    for phrase in seeds[:REGION_CLUSTERS]:
        specs.append({"kind": "regions", "phrase": phrase})
    return specs


def relevant(item: dict, token: str) -> bool:
    """Фраза относится к кластеру, только если содержит якорь бренда.

    Без проверки транслитерации притягивают омонимы: по «корел купить»
    Вордстат отдаёт «корал тревел», «пионы корал шарм», «корела водка».
    Замер 19.08.2026: 24 922 «коммерческих» показа CorelDRAW оказались чужими.
    """
    return token.lower() in item.get("phrase", "").lower()


def dedupe(rows: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for r in rows:
        prev = best.get(r["phrase"])
        if prev is None or (r["impressions_wordstat"] or 0) > (prev["impressions_wordstat"] or 0):
            best[r["phrase"]] = r
    return sorted(best.values(), key=lambda r: -(r["impressions_wordstat"] or 0))


def assemble(plan: dict, discovery: dict | None, cache: dict, date: str,
             region: str, session: Session, specs: list[dict]) -> dict:
    clusters = []
    for c in plan["clusters"]:
        token = c.get("relevance_token") or c["phrases"][0].split()[0]
        probes = [{"phrase": p, **cache.get(f"top|{p}", {"status": "not_collected"})}
                  for p in c["phrases"]]
        measured = [p for p in probes if p.get("status") == "ok"]
        raw = dedupe([r for p in measured for r in p.get("results", [])])
        rows = [r for r in raw if relevant(r, token)]
        commercial = [r for r in rows if r["intent"] == "commercial"]
        seed = cache.get(f"top|{c['phrases'][0]}", {})
        clusters.append({
            "cluster": c["cluster"],
            "vendor": c.get("vendor"),
            "page": c.get("page"),
            "priority": c.get("priority"),
            "relevance_token": token,
            "status": "ok" if measured else "not_collected",
            "coverage": f"{len(measured)}/{len(probes)}",
            "seed_impressions": seed.get("total_impressions"),
            "probes": [{"phrase": p["phrase"], "status": p.get("status"),
                        "total_impressions": p.get("total_impressions")} for p in probes],
            "phrases_dropped_as_irrelevant": len(raw) - len(rows),
            "phrases": rows[:400],
            "associations": [r for r in dedupe(
                [r for p in measured for r in p.get("associations", [])])
                if relevant(r, token)][:40],
            "commercial_phrases": len(commercial),
            "commercial_impressions": sum(
                r["impressions_wordstat"] or 0 for r in commercial) or None,
            "confidence": "sufficient" if (seed.get("total_impressions") or 0)
                          >= LOW_DEMAND_LIMIT else "low",
        })

    disc_rows = []
    if discovery:
        tpl = discovery.get("template", "{brand} купить для юридических лиц")
        for brand in discovery.get("brands", []):
            entry = cache.get(f"top|{tpl.format(brand=brand)}")
            if not entry:
                continue
            token = brand.split()[0]
            commercial = [r for r in entry.get("results", [])
                          if r["intent"] == "commercial" and relevant(r, token)]
            disc_rows.append({"brand": brand, "status": entry.get("status"),
                              "demand": entry.get("total_impressions"),
                              "top_commercial": commercial[:5]})

    seeds = [c["phrases"][0] for c in plan["clusters"]]
    seasonality = [{"phrase": p, **cache[f"dynamics|{p}"]}
                   for p in seeds[:DYNAMICS_CLUSTERS] if f"dynamics|{p}" in cache]
    geography = [{"phrase": p, **cache[f"regions|{p}"]}
                 for p in seeds[:REGION_CLUSTERS] if f"regions|{p}" in cache]

    done = sum(1 for s in specs if f"{s['kind']}|{s['phrase']}" in cache)
    return {
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
            "hourly_limit": HOURLY_LIMIT,
            "monthly_budget": MONTHLY_BUDGET,
            "run_cap": session.cap,
            "requests_this_run": session.used,
            "failures": session.failures,
            "stopped_by": session.stopped,
            "collected_total": done,
            "planned_total": len(specs),
            "complete": done >= len(specs),
        },
        "clusters": clusters,
        "seasonality": seasonality,
        "geography": geography,
        "discovery": disc_rows,
    }


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    date = args[0] if args else dt.date.today().isoformat()
    cap = RUN_CAP
    if "--run-cap" in sys.argv:
        cap = int(sys.argv[sys.argv.index("--run-cap") + 1])

    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    discovery = json.loads(DISCOVERY.read_text(encoding="utf-8")) if DISCOVERY.exists() else None
    region = plan.get("region_id", "225")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = OUT_DIR / f"cache-{date[:7]}.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    specs = request_plan(plan, discovery)
    session = Session(cap, headers())
    for spec in specs:
        key = f"{spec['kind']}|{spec['phrase']}"
        if key in cache:
            continue
        if not session.can_continue():
            break
        result = fetch(spec["kind"], spec["phrase"], region, session)
        if result.get("status") in ("run_cap_reached", "quota_exceeded"):
            break
        cache[key] = result

    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    snap = assemble(plan, discovery, cache, date, region, session, specs)
    (OUT_DIR / f"core-{date}.json").write_text(
        json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")

    q = snap["quota"]
    print(f"wordstat: запросов за прогон {q['requests_this_run']}, ошибок {q['failures']}, "
          f"остановка: {q['stopped_by'] or 'нет'}; "
          f"собрано {q['collected_total']}/{q['planned_total']} "
          f"({'полный проход' if q['complete'] else 'продолжится в следующем часу'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
