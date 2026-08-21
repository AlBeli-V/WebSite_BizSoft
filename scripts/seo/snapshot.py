#!/usr/bin/env python3
"""Канонический snapshot отчётности BIZSoft (schema v2).

Единственный источник цифр для отчёта: сырые выгрузки reports/seo/data/*.json
нормализуются в одну модель, из которой затем строятся executive brief,
приложение, графики и проверки качества. Правило: отсутствующее значение — None
(в отчёте «нет данных»), ноль означает измеренный ноль.

Запуск: python3 scripts/seo/snapshot.py [YYYY-MM-DD]
Результат: reports/seo/intelligence/snapshots/<дата>.json
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
import sys

SCHEMA_VERSION = "2.1.0"
TIMEZONE = "Asia/Bishkek (UTC+6)"
DATA_DIR = pathlib.Path("reports/seo/data")
OUT_DIR = pathlib.Path("reports/seo/intelligence/snapshots")

# Пороги низкой выборки — конфигурируемые (см. docs/seo/reporting-methodology.md)
THRESHOLDS = {
    "low_impressions": 50,     # ниже — выводы о видимости ненадёжны
    "low_visits": 20,          # ниже — выводы о конверсии ненадёжны
    "low_conversions": 5,      # ниже — только предварительный сигнал
    "top_position": 10.0,      # строгая граница «в топ-10»
    "reconciliation_ratio": 2.0,  # расхождение источников больше чем в 2 раза — critical
}

BRAND_MARKERS = ("bizsoft", "биз софт", "бизсофт", "biz-soft")
COMMERCIAL_MARKERS = (
    "купить", "оплат", "цен", "стоимост", "тариф", "подписк", "лицензи",
    "продл", "заказ", "счет", "счёт", "buy", "price", "license", "pricing",
)
INFO_MARKERS = ("как ", "что ", "почему ", "можно ли", "нужн", "how ", "what ")


def days_inclusive(a: str, b: str) -> int:
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days + 1


def classify_intent(q: str) -> str:
    low = q.lower()
    if any(m in low for m in BRAND_MARKERS):
        return "navigational"
    if any(m in low for m in COMMERCIAL_MARKERS):
        return "commercial"
    if any(low.startswith(m) for m in INFO_MARKERS):
        return "informational"
    return "unknown"


def is_branded(q: str) -> bool:
    return any(m in q.lower() for m in BRAND_MARKERS)


def confidence(sample: int | None, kind: str = "impressions") -> str:
    if sample is None:
        return "unknown"
    limit = THRESHOLDS["low_impressions"] if kind == "impressions" else THRESHOLDS["low_visits"]
    if sample < limit / 5:
        return "very_low"
    if sample < limit:
        return "low"
    return "sufficient"


def load(prefix: str, date: str) -> dict | None:
    p = DATA_DIR / f"{prefix}-{date}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def git_revisions(path: pathlib.Path, date: str) -> list[str]:
    """SHA коммитов, затронувших файл в указанный день (для учёта пересборов)."""
    try:
        out = subprocess.run(
            ["git", "log", "--format=%H %ad", "--date=short", "--", str(path)],
            capture_output=True, text=True, timeout=20, check=False).stdout
    except Exception:
        return []
    return [ln.split()[0] for ln in out.splitlines() if ln.strip().endswith(date)]


def git_show_json(sha: str, path: pathlib.Path) -> dict | None:
    try:
        out = subprocess.run(["git", "show", f"{sha}:{path}"],
                             capture_output=True, text=True, timeout=20, check=False)
        return json.loads(out.stdout) if out.returncode == 0 and out.stdout else None
    except Exception:
        return None


def revisions_for(prefix: str, date: str, extract, metric: str) -> dict | None:
    """Значения метрики во всех сборах указанного дня (источник мог пересобираться)."""
    path = DATA_DIR / f"{prefix}-{date}.json"
    if not path.exists():
        return None
    seen = []
    for sha in git_revisions(path, date):
        old = git_show_json(sha, path)
        if not old or old.get("error"):
            continue
        try:
            v = extract(old)
        except Exception:
            continue
        if v is not None and v not in seen:
            seen.append(v)
    current = extract(json.loads(path.read_text(encoding="utf-8")))
    values = sorted({float(v) for v in seen} | ({float(current)} if current is not None else set()))
    if len(values) < 2:
        return None
    return {"metric": metric, "date": date, "values_seen": values,
            "canonical": float(current) if current is not None else None,
            "reason": "источник пересобирался в течение дня; каноническим считается последний сбор"}


def source_meta(name, collected_at, latest_event, p_start, p_end, cmp_start, cmp_end,
                filters, status, notes=None) -> dict:
    return {
        "source_name": name,
        "collected_at": collected_at,
        "latest_event_date": latest_event,
        "current_period_start": p_start,
        "current_period_end": p_end,
        "current_period_days": days_inclusive(p_start, p_end) if p_start and p_end else None,
        "comparison_period_start": cmp_start,
        "comparison_period_end": cmp_end,
        "comparison_period_days": days_inclusive(cmp_start, cmp_end) if cmp_start and cmp_end else None,
        "filters": filters,
        "status": status,
        "notes": notes,
    }


def build_yandex(raw: dict | None, prev: dict | None, date: str) -> dict:
    if not raw or raw.get("error"):
        return {"available": False, "error": (raw or {}).get("error", "нет данных"),
                "source": source_meta("yandex_webmaster", None, None, None, None, None, None,
                                      {}, "unavailable")}
    pq = raw.get("popular_queries", {})
    p_from, p_to = pq.get("date_from"), pq.get("date_to")
    prev_pq = (prev or {}).get("popular_queries", {})
    entities = []
    for it in pq.get("queries", []):
        ind = it.get("indicators", {})
        shows = ind.get("TOTAL_SHOWS")
        clicks = ind.get("TOTAL_CLICKS")
        pos = ind.get("AVG_SHOW_POSITION")
        text = it.get("query_text", "")
        entities.append({
            "search_engine": "yandex",
            "entity_type": "query",
            "entity_id": text,
            "impressions": int(shows) if shows is not None else None,
            "clicks": int(clicks) if clicks is not None else None,
            "ctr": (clicks / shows) if shows else None,
            "average_position": round(pos, 2) if pos is not None else None,
            "branded": is_branded(text),
            "intent": classify_intent(text),
            "sample_size": int(shows) if shows is not None else None,
            "confidence": confidence(int(shows) if shows is not None else None),
        })
    impressions = sum(e["impressions"] or 0 for e in entities)
    clicks = sum(e["clicks"] or 0 for e in entities)
    in_top10 = [e for e in entities if e["average_position"] is not None
                and e["average_position"] <= THRESHOLDS["top_position"]]
    summary = raw.get("summary", {})
    sqi = summary.get("sqi")
    return {
        "available": True,
        "source": source_meta(
            "yandex_webmaster", raw.get("date"), p_to, p_from, p_to,
            prev_pq.get("date_from"), prev_pq.get("date_to"),
            {"scope": "top-100 запросов по показам (API popular queries)",
             "region": "не задан в запросе", "device": "все"},
            "ok",
            "Клики/показы относятся к выборке топ-100 запросов, а не ко всему сайту."),
        "entities": entities,
        "totals": {
            "impressions": impressions,
            "clicks": clicks,
            "ctr": (clicks / impressions) if impressions else None,
            "queries_tracked": len(entities),
            "queries_position_le_10": len(in_top10),
            "queries_position_le_3": len([e for e in entities if e["average_position"] is not None
                                          and e["average_position"] <= 3.0]),
            "scope_note": "выборка топ-100 запросов, не весь сайт",
        },
        "indexation": {
            "total_known_urls": (summary.get("searchable_pages_count") or 0)
                                + (summary.get("excluded_pages_count") or 0)
                                if summary.get("searchable_pages_count") is not None else None,
            "indexed_urls": summary.get("searchable_pages_count"),
            "excluded_urls": summary.get("excluded_pages_count"),
            "excluded_by_reason": None,
            "commercial_excluded_urls": None,
            "unclassified_excluded_urls": summary.get("excluded_pages_count"),
            "sqi": sqi,
            "site_problems": summary.get("site_problems"),
        },
    }


def build_google(raw: dict | None, prev: dict | None) -> dict:
    if not raw or raw.get("error"):
        return {"available": False, "error": (raw or {}).get("error", "нет данных"),
                "source": source_meta("google_search_console", None, None, None, None,
                                      None, None, {}, "unavailable")}
    a = raw.get("analytics", {})
    rows = a.get("date", {}).get("rows", [])
    daily = [{"date": r["keys"][0], "impressions": r["impressions"], "clicks": r["clicks"],
              "position": round(r.get("position", 0), 2)} for r in rows]
    latest = daily[-1]["date"] if daily else None
    last7, prev7 = daily[-7:], daily[-14:-7]
    entities = []
    for r in a.get("query", {}).get("rows", []):
        q = r["keys"][0]
        entities.append({
            "search_engine": "google", "entity_type": "query", "entity_id": q,
            "impressions": r["impressions"], "clicks": r["clicks"],
            "ctr": (r["clicks"] / r["impressions"]) if r["impressions"] else None,
            "average_position": round(r["position"], 2),
            "branded": is_branded(q), "intent": classify_intent(q),
            "sample_size": r["impressions"], "confidence": confidence(r["impressions"]),
        })
    pages = []
    for r in a.get("page", {}).get("rows", []):
        pages.append({
            "search_engine": "google", "entity_type": "page",
            "entity_id": r["keys"][0].replace("https://biz-soft.pro", "") or "/",
            "impressions": r["impressions"], "clicks": r["clicks"],
            "ctr": (r["clicks"] / r["impressions"]) if r["impressions"] else None,
            "average_position": round(r["position"], 2),
            "sample_size": r["impressions"], "confidence": confidence(r["impressions"]),
        })
    return {
        "available": True,
        "source": source_meta(
            "google_search_console", raw.get("date"), latest,
            daily[0]["date"] if daily else None, latest,
            prev7[0]["date"] if prev7 else None, prev7[-1]["date"] if prev7 else None,
            {"property": "sc-domain:biz-soft.pro", "search_type": "web"}, "ok",
            "Данные GSC отстают на 2–3 дня; последняя доступная дата события — "
            + str(latest)),
        "daily": daily,
        "entities": entities,
        "pages": pages,
        "totals": {
            "impressions_window": sum(d["impressions"] for d in daily),
            "clicks_window": sum(d["clicks"] for d in daily),
            "window_days": len(daily),
            "impressions_last7": sum(d["impressions"] for d in last7),
            "impressions_prev7": sum(d["impressions"] for d in prev7),
            "last7_start": last7[0]["date"] if last7 else None,
            "last7_end": last7[-1]["date"] if last7 else None,
            "prev7_start": prev7[0]["date"] if prev7 else None,
            "prev7_end": prev7[-1]["date"] if prev7 else None,
            "queries_tracked": len(entities),
            "queries_position_le_10": len([e for e in entities if e["average_position"] <= THRESHOLDS["top_position"]]),
            "pages_position_le_10": len([p for p in pages if p["average_position"] <= THRESHOLDS["top_position"]]),
        },
    }


def build_analytics(metrika: dict | None, ga4: dict | None, date: str) -> dict:
    out = {"metrika": {"available": False}, "ga4": {"available": False}, "intra_day_revisions": []}
    if metrika and not metrika.get("error"):
        ts = {r["dimensions"][0]["name"]: r["metrics"] for r in metrika["traffic_sources"]["data"]}
        tot = metrika["traffic_sources"].get("totals") or [None] * 5
        org = ts.get("Search engine traffic", [None] * 5)
        lp = [{"entity_id": r["dimensions"][0]["name"], "visits": r["metrics"][0],
               "bounce_rate": r["metrics"][1], "goal_events": r["metrics"][2]}
              for r in metrika["organic_landing_pages"]["data"]]
        w = metrika.get("window", {})
        out["metrika"] = {
            "available": True,
            "source": source_meta("yandex_metrika", metrika.get("date"), w.get("to"),
                                  w.get("from"), w.get("to"), None, None,
                                  {"counter": metrika.get("counter"), "accuracy": "full"}, "ok"),
            "metric_name": "visits (ym:s:visits)",
            "visits_total": tot[0], "users_total": tot[1],
            "goal_events_total": tot[4],
            "organic_visits": org[0], "organic_goal_events": org[4],
            "unique_goal_users": None,
            "qualified_leads": None, "deals": None, "revenue": None,
            "goals_configured": [{"id": g["id"], "name": g["name"], "type": g["type"]}
                                 for g in metrika.get("goals", [])],
            "organic_landing_pages": lp,
            "channels": {k: v[0] for k, v in ts.items()},
        }
        # Учёт пересборов внутри дня (несколько сборов => несколько значений)
        path = DATA_DIR / f"metrika-{date}.json"
        seen = []
        for sha in git_revisions(path, date):
            old = git_show_json(sha, path)
            if not old or old.get("error"):
                continue
            try:
                v = (old["traffic_sources"].get("totals") or [None])[0]
            except Exception:
                continue
            if v is not None and v not in seen:
                seen.append(v)
        if len(seen) > 1 or (seen and tot[0] is not None and float(tot[0]) not in [float(s) for s in seen]):
            values = sorted({float(v) for v in seen} | ({float(tot[0])} if tot[0] is not None else set()))
            out["intra_day_revisions"].append({
                "metric": "metrika.visits_total", "values_seen": values,
                "canonical": float(tot[0]) if tot[0] is not None else None,
                "reason": "источник пересобирался в течение дня; каноническим считается последний сбор",
            })
    if ga4 and not ga4.get("error"):
        ch = {r["dimensionValues"][0]["value"]: [x["value"] for x in r["metricValues"]]
              for r in ga4.get("channels", {}).get("rows", [])}
        org = ch.get("Organic Search", ["0", "0", "0"])
        w = ga4.get("window", {})
        lp = [{"entity_id": r["dimensionValues"][0]["value"],
               "sessions": int(r["metricValues"][0]["value"]),
               "key_events": int(r["metricValues"][1]["value"])}
              for r in ga4.get("organic_landing_pages", {}).get("rows", [])]
        out["ga4"] = {
            "available": True,
            "source": source_meta("ga4", ga4.get("date"), w.get("to"), w.get("from"),
                                  w.get("to"), None, None,
                                  {"property": ga4.get("property")}, "ok",
                                  "key events размечены 2026-08-18 — сравнение конверсий "
                                  "внутри периода некорректно"),
            "metric_name": "sessions (GA4)",
            "sessions_total": sum(int(v[0]) for v in ch.values()),
            "organic_sessions": int(org[0]),
            "organic_users": int(org[1]),
            "organic_key_events": int(org[2]),
            "key_events_marked_at": "2026-08-18",
            "channels": {k: int(v[0]) for k, v in ch.items()},
            "organic_sources": {r["dimensionValues"][0]["value"]: int(r["metricValues"][0]["value"])
                                for r in ga4.get("organic_sources", {}).get("rows", [])},
            "organic_landing_pages": lp,
        }
    return out


SEMANTICS_DIR = pathlib.Path("reports/seo/semantics")
DEMAND_STALE_DAYS = 45      # старше — замер считается устаревшим


def build_market_demand(date: str) -> dict:
    """Рыночный спрос из Вордстата — знаменатель для нашей видимости.

    Источник обновляется помесячно, поэтому в снимок дня попадает последний
    доступный замер с его собственной датой и возрастом. Суточной дельты у спроса
    нет и быть не может: сравнивать его день ко дню запрещено методикой.
    """
    briefs = sorted(SEMANTICS_DIR.glob("brief-*.json"))
    if not briefs:
        return {"available": False,
                "reason": "замер рыночного спроса ещё не собран",
                "comparable_to_visibility": False}
    brief = json.loads(briefs[-1].read_text(encoding="utf-8"))
    if "coverage" not in brief:
        # Замеры до 19.08.2026 собраны без фильтра релевантности: по транслитерациям
        # брендов в них попали омонимы («корал тревел», «пион корал шарм»).
        # Такой замер не используется — лучше отсутствие данных, чем чужие числа.
        return {"available": False,
                "reason": "замер собран до включения фильтра релевантности и не используется",
                "comparable_to_visibility": False}
    measured = brief.get("clusters_measured") or 0
    if not measured:
        return {"available": False,
                "reason": "замер начат, но ни один кластер ещё не собран",
                "measured_at": brief.get("report_date"),
                "coverage": brief.get("coverage"),
                "complete": brief.get("complete", False),
                "comparable_to_visibility": False}
    measured_at = brief.get("report_date")
    age = (dt.date.fromisoformat(date) - dt.date.fromisoformat(measured_at)).days
    gaps = brief.get("gaps") or {}
    return {
        "available": True,
        "source": {
            "source_name": "yandex_wordstat",
            "measured_at": measured_at,
            "age_days": age,
            "region": brief.get("region"),
            "unit": brief.get("unit"),
            "window": brief.get("window"),
            "match_type": brief.get("match_type"),
            "refresh": "помесячно",
        },
        "coverage": brief.get("coverage"),
        "complete": brief.get("complete", False),
        "stale": age > DEMAND_STALE_DAYS,
        "clusters_measured": measured,
        "clusters_planned": brief.get("clusters_planned"),
        "top_commercial": brief.get("top_commercial") or [],
        "gap_cards": len(gaps),
        "gap_phrases": sum(len(v) for v in gaps.values()),
        "gaps": gaps,
        "discovery": brief.get("discovery") or [],
        # Доля голоса не рассчитывается: наша видимость известна по выборке
        # топ-100 запросов Вебмастера, охват и периоды источников не сверены.
        "comparable_to_visibility": False,
    }


def build_experiments() -> list[dict]:
    p = pathlib.Path("reports/seo/intelligence/seo-experiments.json")
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8")).get("experiments", [])
    out = []
    for e in raw:
        out.append({
            "id": e.get("id"),
            "title": e.get("id"),
            "hypothesis": e.get("hypothesis"),
            "treatment_urls": e.get("pages", []),
            "control_urls": e.get("control_group"),
            "deployment_date": e.get("start"),
            "measurement_start_date": None,
            "status": e.get("status"),
            "primary_metric": e.get("success_metric"),
            "guardrail_metrics": ["impressions", "average_position", "organic_sessions"],
            "minimum_exposure": "не задан — требуется определить до объявления результата",
            "review_date": None,
            "owner": None,
            "result": None,
            "source": e.get("source"),
        })
    return out


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    prev_date = (dt.date.fromisoformat(date) - dt.timedelta(days=1)).isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    snap = {
        "schema_version": SCHEMA_VERSION,
        "report_date": date,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "reporting_timezone": TIMEZONE,
        "thresholds": THRESHOLDS,
        "yandex": build_yandex(load("yandex", date), load("yandex", prev_date), date),
        "google": build_google(load("gsc", date), load("gsc", prev_date)),
        "analytics": build_analytics(load("metrika", date), load("ga4", date), date),
        "experiments": build_experiments(),
        "market_demand": build_market_demand(date),
        "data_revisions": [r for r in [
            revisions_for("yandex", date, lambda d: d.get("summary", {}).get("searchable_pages_count"),
                          "yandex.indexed_urls"),
            revisions_for("yandex", prev_date, lambda d: d.get("summary", {}).get("searchable_pages_count"),
                          "yandex.indexed_urls (базовая линия предыдущего дня)"),
        ] if r],
        "crm": {"connected": False, "qualified_leads": None, "deals": None, "revenue": None,
                "note": "CRM не подключена — квалифицированные лиды, сделки и выручка недоступны"},
        "ctr_model": {"approved": False,
                      "note": "утверждённая CTR-кривая по позициям отсутствует; "
                              "расчёт «потерянных кликов» не выполняется"},
    }
    out = OUT_DIR / f"{date}.json"
    out.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"snapshot: {out} (schema {SCHEMA_VERSION})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
