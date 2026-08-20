#!/usr/bin/env python3
"""Уровни мониторинга: кому и как часто нужна динамика и география.

GetDynamics для всей семантики — 6 500 вызовов в месяц, то есть 65 часов
непрерывной работы при квоте 100/час ради данных, которые для длинного хвоста
никто не использует. Поэтому три уровня.

  A — стратегические кластеры: высокий спрос, коммерческий интент, есть или
      планируется коммерческая страница. Динамика раз в неделю.
  B — перспективные: динамика раз в месяц.
  C — длинный хвост: динамика только по событию — повторное обнаружение,
      рост кластера, подготовка решения.

География (GetRegionsDistribution) стоит в 2,5 раза дороже и меняется медленно,
поэтому запрашивается только для уровня A и кандидатов в платный канал.
"""

from __future__ import annotations

import datetime as dt


def tier_of(cluster: dict, rank: int, cfg: dict) -> str:
    t = cfg["tiers"]
    demand = cluster["commercial_demand"]
    commercial = cluster["commercial_phrases"] > 0
    business_page = cluster["page_exists"] or demand >= 5000
    if commercial and business_page and rank < t["A"]["max_items"] and demand >= 500:
        return "A"
    if commercial and rank < t["B"]["max_items"] and demand >= 100:
        return "B"
    return "C"


def assign(clusters: dict[str, dict], cfg: dict) -> dict[str, str]:
    ranked = sorted(clusters.values(), key=lambda c: -c["commercial_demand"])
    return {c["cluster"]: tier_of(c, i, cfg) for i, c in enumerate(ranked)}


def due(last_run: str | None, every_days: int | None, today: str) -> bool:
    """Пора ли обновлять. Уровень C по расписанию не обновляется никогда."""
    if every_days is None:
        return False
    if last_run is None:
        return True
    age = (dt.date.fromisoformat(today) - dt.date.fromisoformat(last_run)).days
    return age >= every_days


def dynamics_due(clusters: dict[str, dict], tiers: dict[str, str], last_runs: dict,
                 cfg: dict, today: str, events: set[str] | None = None) -> list[dict]:
    """Кластеры, которым сегодня нужна динамика: по расписанию или по событию."""
    events = events or set()
    out = []
    for name, cluster in clusters.items():
        tier = tiers.get(name, "C")
        every = cfg["tiers"][tier]["dynamics_every_days"]
        by_schedule = due(last_runs.get(f"dynamics|{name}"), every, today)
        by_event = name in events
        if not (by_schedule or by_event):
            continue
        out.append({
            "cluster": name, "tier": tier,
            "reason": "trend_monitoring" if by_schedule else "decision_validation",
            "why": ("плановое обновление динамики уровня " + tier if by_schedule
                    else "событие: требуется для решения"),
            "demand": cluster["commercial_demand"],
            "phrase": (cluster["top_phrases"][0]["phrase"]
                       if cluster["top_phrases"] else name),
        })
    out.sort(key=lambda r: (-{"A": 2, "B": 1, "C": 0}[r["tier"]], -r["demand"]))
    return out


def regions_due(clusters: dict[str, dict], tiers: dict[str, str], last_runs: dict,
                cfg: dict, today: str, ppc_candidates: set[str] | None = None) -> list[dict]:
    """География — только для уровня A и кандидатов в платный канал."""
    ppc_candidates = ppc_candidates or set()
    out = []
    for name, cluster in clusters.items():
        tier = tiers.get(name, "C")
        if tier != "A" and name not in ppc_candidates:
            continue
        every = cfg["tiers"]["A"]["regions_every_days"]
        if not due(last_runs.get(f"regions|{name}"), every, today):
            continue
        out.append({
            "cluster": name, "tier": tier,
            "reason": "regional_research",
            "why": ("география влияет на решение по платному каналу"
                    if name in ppc_candidates else "стратегический кластер"),
            "demand": cluster["commercial_demand"],
            "phrase": (cluster["top_phrases"][0]["phrase"]
                       if cluster["top_phrases"] else name),
        })
    out.sort(key=lambda r: -r["demand"])
    return out
