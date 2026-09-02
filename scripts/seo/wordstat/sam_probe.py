#!/usr/bin/env python3
"""Замер спроса по когорте SAM/ITAM/SMP: частоты Вордстата и состав выдачи.

Зачем отдельный прогон. Штатный Discovery засевает вселенную брендами
существующего каталога, поэтому категориальные запросы корпоративного ПО
(«учёт лицензий», «инвентаризация ПО») и бренды вендоров, которых у нас нет,
в замер никогда не попадали. Решение «брать или не брать вендора» принималось
бы по ощущениям — этот скрипт заменяет ощущения фактом.

Что делает: по каждой фразе когорты один вызов getTop (частота самой фразы,
её смежные запросы с частотами), по отмеченным `serp: true` — ещё и веб-поиск
(кто занимает топ выдачи: вендор, реселлеры, магазины или наши конкуренты).
Ничего не пишет в семантическую вселенную: это разовый замер под решение, а не
пополнение базы. Расход учитывается штатным контроллером бюджета.

Запуск: python3 scripts/seo/wordstat/sam_probe.py [--set data/seo/sam-demand-probe.json]
        [--max-calls N] [--no-serp] [--dry-run]
Секреты: WORDSTAT_API_KEY (тот же ключ обслуживает Вордстат и веб-поиск).
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import pathlib
import sys
import xml.etree.ElementTree as ET

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import budget as budget_mod  # noqa: E402
import client as client_mod  # noqa: E402
import config  # noqa: E402
import normalize as N  # noqa: E402

SET_PATH = pathlib.Path("data/seo/sam-demand-probe.json")
OUT_DIR = pathlib.Path("reports/seo/wordstat")
SERP_URL = "https://searchapi.api.cloud.yandex.net/v2/web/search"
SERP_TOP = 10
REASON = "decision_validation"


# ── Вордстат ─────────────────────────────────────────────────────────────
def measure(cl, phrase: str, group: str, num_phrases: int) -> dict:
    """Частота фразы, сумма её топа и смежные запросы одним вызовом."""
    res = cl.top(phrase, reason=REASON, cluster=group, num_phrases=num_phrases)
    rows = (res.get("data") or {}).get("results") or []
    key = N.morph_key(phrase)
    exact = None
    related = []
    for r in rows:
        p = (r.get("phrase") or "").strip()
        c = r.get("count")
        c = int(c) if c is not None else None
        if not p or c is None:
            continue
        if N.morph_key(p) == key and exact is None:
            exact = c
            continue
        related.append({"phrase": p, "count": c})
    related.sort(key=lambda x: x["count"], reverse=True)
    return {
        "phrase": phrase,
        "group": group,
        "status": res["status"],
        "source": res["source"],
        "cost_rub": res["cost_rub"],
        "exact": exact,
        "top_sum": sum(r["count"] for r in related) + (exact or 0),
        "related_total": len(related),
        "related": related[:12],
    }


# ── Веб-поиск ────────────────────────────────────────────────────────────
def serp(key: str, query: str) -> dict:
    """Топ выдачи по фразе. Ошибка прав или тарифа возвращается как есть."""
    body = {"query": {"searchType": "SEARCH_TYPE_RU", "queryText": query}}
    folder = os.environ.get("SEARCH_API_FOLDER_ID", "").strip()
    if folder:
        body["folderId"] = folder
    try:
        r = requests.post(SERP_URL, json=body, timeout=60,
                          headers={"Authorization": f"Api-Key {key}",
                                   "Content-Type": "application/json"})
    except requests.RequestException as e:
        return {"error": f"сетевая ошибка: {type(e).__name__}"}
    if not r.ok:
        return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    raw = (r.json() or {}).get("rawData")
    if not raw:
        return {"error": "ответ без rawData"}
    try:
        root = ET.fromstring(base64.b64decode(raw).decode("utf-8", "replace"))
    except ET.ParseError as e:
        return {"error": f"ответ не является XML: {e}"}
    err = root.find(".//error")
    if err is not None:
        return {"error": f"сервис: {(err.text or '').strip()[:200]}"}
    docs = []
    for doc in root.findall(".//group/doc")[:SERP_TOP]:
        docs.append({"domain": (doc.findtext("domain") or "").strip(),
                     "title": ("".join(doc.find("title").itertext()).strip()
                               if doc.find("title") is not None else "")})
    found = root.findtext(".//found")
    return {"found": int(found) if found and found.isdigit() else None, "docs": docs}


# ── Отчёт ────────────────────────────────────────────────────────────────
def render(results: list[dict], serps: list[dict], groups: dict[str, str],
           spent: float) -> str:
    out = [f"# Спрос по когорте SAM/ITAM/SMP — {dt.date.today().isoformat()}",
           "",
           "Регион: Россия. Окно: последние 30 дней. Источник: Wordstat API "
           "(`getTop`) и веб-поиск Yandex Search API.",
           f"Потрачено за прогон: {spent:.2f} ₽.", ""]
    for key, title in groups.items():
        rows = [r for r in results if r["group"] == key]
        if not rows:
            continue
        rows.sort(key=lambda r: (r["exact"] or 0, r["top_sum"]), reverse=True)
        out += [f"## {title}", "",
                "| Фраза | Точная частота | Сумма кластера | Смежных фраз | Статус |",
                "|---|---:|---:|---:|---|"]
        for r in rows:
            out.append(f"| {r['phrase']} | {r['exact'] if r['exact'] is not None else '—'} "
                       f"| {r['top_sum'] or '—'} | {r['related_total']} | {r['status']} |")
        out.append("")
    out += ["## Смежные запросы (по 12 самых частотных на фразу)", ""]
    for r in sorted(results, key=lambda r: r["top_sum"], reverse=True):
        if not r["related"]:
            continue
        rel = ", ".join(f"{x['phrase']} — {x['count']}" for x in r["related"])
        out.append(f"- **{r['phrase']}**: {rel}")
    out.append("")
    if serps:
        out += ["## Состав выдачи", ""]
        for s in serps:
            out.append(f"### {s['query']}")
            if s.get("error"):
                out += [f"Выдача не снята: {s['error']}", ""]
                continue
            out.append(f"Найдено документов: {s.get('found') or '?'}")
            for i, d in enumerate(s.get("docs", []), 1):
                out.append(f"{i}. `{d['domain']}` — {d['title'][:90]}")
            out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default=str(SET_PATH))
    ap.add_argument("--max-calls", type=int, default=120)
    ap.add_argument("--no-serp", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    spec = json.loads(pathlib.Path(args.set).read_text(encoding="utf-8"))
    cfg = config.load()
    cfg["collection"]["region_id"] = spec.get("region", cfg["collection"]["region_id"])
    num_phrases = spec.get("num_phrases", cfg["collection"]["num_phrases"])
    groups = {g["key"]: g["title"] for g in spec["groups"]}

    tasks = [(g["key"], p) for g in spec["groups"] for p in g["phrases"]]
    if args.dry_run:
        serp_n = sum(1 for _, p in tasks if p.get("serp")) if not args.no_serp else 0
        price = config.price_of("getTop", dt.date.today().isoformat(), cfg)
        print(f"План: {len(tasks)} вызовов getTop ({len(tasks) * price:.2f} ₽) "
              f"и {serp_n} запросов веб-поиска. Ключ не тратится.")
        return 0

    budget = budget_mod.BudgetController(cfg)
    cl = client_mod.WordstatClient(budget, cfg)
    key = os.environ.get("WORDSTAT_API_KEY", "").strip()
    if not key:
        print("::error::WORDSTAT_API_KEY не задан")
        return 1

    results, serps, spent, calls = [], [], 0.0, 0
    for group, item in tasks:
        if calls >= args.max_calls:
            print(f"достигнут потолок вызовов ({args.max_calls}), остальные фразы пропущены")
            break
        r = measure(cl, item["p"], group, num_phrases)
        calls += 1
        if r["source"] == "api":
            spent += r["cost_rub"]
            budget.record(method="getTop", phrase=item["p"], cluster=group,
                          reason=REASON, cache_hit=False, status=r["status"],
                          result_count=r["related_total"])
        if r["status"] in ("quota_exceeded", "budget_blocked"):
            print(f"остановка на «{item['p']}»: {cl.stopped_by or r['status']}")
            results.append(r)
            break
        results.append(r)

    if not args.no_serp:
        for group, item in tasks:
            if not item.get("serp"):
                continue
            s = serp(key, item["p"])
            s["query"] = item["p"]
            serps.append(s)
            if s.get("error"):        # права или тариф — дальше пробовать нечего
                print(f"веб-поиск недоступен: {s['error']}")
                break

    report = render(results, serps, groups, spent)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.date.today().isoformat()
    (OUT_DIR / f"sam-demand-{stamp}.md").write_text(report, encoding="utf-8")
    (OUT_DIR / f"sam-demand-{stamp}.json").write_text(
        json.dumps({"generated_at": dt.datetime.now(dt.timezone.utc)
                    .isoformat(timespec="seconds"),
                    "region": cfg["collection"]["region_id"],
                    "spent_rub": round(spent, 4),
                    "results": results, "serp": serps},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
