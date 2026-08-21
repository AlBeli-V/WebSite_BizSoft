#!/usr/bin/env python3
"""Планировщик исследований: месячный план и суточное распределение вызовов.

Ранжирование задач: business_value × information_gain × confidence / api_cost.

План не рассчитан на освоение всего бюджета. При квоте 100 запросов в час
израсходовать 5 500 ₽ невозможно (аудит 20.08.2026), поэтому дефицитный ресурс —
слоты квоты и время, а не рубли. Планировщик распределяет именно слоты.

Приоритет суточного распределения:
  1) данные для активного делового решения;
  2) проверка уже найденных возможностей;
  3) обнаружение непокрытого коммерческого спроса;
  4) наблюдение за трендом;
  5) свободный поиск.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import config  # noqa: E402
import discovery as D  # noqa: E402

PRIORITY = {
    "decision_validation": 1,
    "opportunity_validation": 2,
    "vendor_expansion": 3,
    "discovery": 3,
    "trend_monitoring": 4,
    "exploration": 5,
    "regional_research": 4,
}
# Ценность задачи для бизнеса: сколько решений она разблокирует.
BUSINESS_VALUE = {
    "decision_validation": 1.0, "opportunity_validation": 0.8,
    # Расширение каталога ценно наравне с обнаружением: оно отвечает на вопрос,
    # какие товары добавить, а не только как улучшить имеющиеся.
    "vendor_expansion": 0.7,
    "discovery": 0.6, "regional_research": 0.5,
    "trend_monitoring": 0.4, "exploration": 0.2,
}


def task_rank(task: dict, cfg: dict) -> float:
    cost = config.price_of(task["method"], cfg=cfg) or 0.0001
    value = BUSINESS_VALUE.get(task["reason"], 0.3)
    gain = task.get("expected_information_gain", 0.5)
    conf = task.get("confidence", 0.8)
    return round(value * gain * conf / cost, 3)


def build_tasks(seed_plan: list[dict], dynamics: list[dict], regions: list[dict],
                cfg: dict) -> list[dict]:
    tasks = []
    for s in seed_plan:
        tasks.append({
            "method": "getTop", "phrase": s["phrase"], "cluster": s["cluster"],
            "reason": s.get("reason_override", "discovery"),
            "expected_information_gain": s["expected_information_gain"],
            "confidence": 0.8, "why": s["rationale"],
            "pattern": s.get("pattern"), "vendor": s.get("vendor"),
        })
    for d in dynamics:
        tasks.append({
            "method": "getDynamics", "phrase": d["phrase"], "cluster": d["cluster"],
            "reason": d["reason"], "expected_information_gain": 0.5,
            "confidence": 0.85, "why": d["why"], "tier": d["tier"],
        })
    for r in regions:
        tasks.append({
            "method": "getRegionsDistribution", "phrase": r["phrase"],
            "cluster": r["cluster"], "reason": r["reason"],
            "expected_information_gain": 0.4, "confidence": 0.8, "why": r["why"],
        })
    for t in tasks:
        t["priority"] = PRIORITY.get(t["reason"], 5)
        t["rank"] = task_rank(t, cfg)
        t["estimated_cost_rub"] = round(config.price_of(t["method"], cfg=cfg), 4)
    tasks.sort(key=lambda t: (t["priority"], -t["rank"]))
    return tasks


def allocate_day(tasks: list[dict], *, hourly_quota: int, hours_available: int,
                 budget_remaining_rub: float, daily_cap_rub: float) -> dict:
    """Сколько задач помещается в сутки: ограничение — слоты, затем деньги."""
    slots = hourly_quota * hours_available
    chosen, spend = [], 0.0
    for t in tasks:
        if len(chosen) >= slots:
            break
        cost = t["estimated_cost_rub"]
        if spend + cost > min(daily_cap_rub, budget_remaining_rub):
            break
        chosen.append(t)
        spend += cost
    return {
        "slots_available": slots,
        "selected": chosen,
        "estimated_cost_rub": round(spend, 4),
        "limited_by": ("слоты квоты" if len(chosen) >= slots else
                       "бюджет" if spend >= min(daily_cap_rub, budget_remaining_rub)
                       else "исчерпан список задач"),
    }


def monthly_plan(universe, clusters: dict, tiers: dict, seed_plan: list[dict],
                 dynamics: list[dict], regions: list[dict], cfg: dict,
                 month: str) -> dict:
    tasks = build_tasks(seed_plan, dynamics, regions, cfg)
    by_method: dict[str, int] = {}
    cost = 0.0
    for t in tasks:
        by_method[t["method"]] = by_method.get(t["method"], 0) + 1
        cost += t["estimated_cost_rub"]
    rph = cfg["quota"]["requests_per_hour"]
    uncovered = [c for c in clusters.values()
                 if not c["page_exists"] and c["commercial_demand"] >= 100]
    return {
        "month": month,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "universe": universe.stats(),
        "clusters_total": len(clusters),
        "clusters_uncovered": len(uncovered),
        "uncovered_demand": sum(c["commercial_demand"] for c in uncovered),
        "tiers": {t: sum(1 for v in tiers.values() if v == t) for t in ("A", "B", "C")},
        "planned_calls": len(tasks),
        "planned_calls_by_method": by_method,
        "estimated_cost_rub": round(cost, 2),
        "budget_hard_cap_rub": cfg["budget"]["monthly_hard_cap_rub"],
        "budget_utilisation": round(cost / cfg["budget"]["monthly_hard_cap_rub"], 4),
        "runtime_hours_at_current_quota": round(len(tasks) / rph, 1),
        "runtime_hours_at_target_quota": round(
            len(tasks) / cfg["quota"]["requests_per_hour_target"], 1),
        "max_possible_spend_current_quota_rub": round(config.max_monthly_spend(cfg), 0),
        "budget_is_binding": config.budget_is_binding(cfg),
        "tasks": tasks,
    }


def write_plan_md(plan: dict, path: pathlib.Path) -> None:
    L = [f"# План исследований Вордстата — {plan['month']}", "",
         f"Сформирован {plan['generated_at'][:10]}. Числа — оценка до вызовов.", "",
         "## Что уже известно", "",
         f"- фраз в базе семантики: {plan['universe']['phrases']:,}".replace(",", " "),
         f"- из них коммерческих: {plan['universe']['commercial_phrases']:,}".replace(",", " "),
         f"- кластеров: {plan['clusters_total']}, "
         f"без страницы на сайте: {plan['clusters_uncovered']}",
         f"- спрос непокрытых кластеров: {plan['uncovered_demand']:,} показов в месяц"
         .replace(",", " "),
         f"- уровни мониторинга: A — {plan['tiers']['A']}, B — {plan['tiers']['B']}, "
         f"C — {plan['tiers']['C']}", "",
         "## Что планируется", "",
         "| Метод | Вызовов | Стоимость |", "|---|---|---|"]
    import config as cfgmod
    for method, n in plan["planned_calls_by_method"].items():
        L.append(f"| {method} | {n} | {n * cfgmod.price_of(method):.2f} ₽ |")
    L += [f"| **Итого** | **{plan['planned_calls']}** | "
          f"**{plan['estimated_cost_rub']:.2f} ₽** |", "",
          "## Бюджет и квота", "",
          f"- месячный потолок: {plan['budget_hard_cap_rub']} ₽",
          f"- план расходует: {plan['budget_utilisation']:.1%} потолка",
          f"- максимум, который вообще можно потратить при действующей квоте: "
          f"{plan['max_possible_spend_current_quota_rub']:.0f} ₽",
          f"- бюджет является ограничением: "
          f"{'да' if plan['budget_is_binding'] else 'нет — ограничивает квота'}",
          f"- время прохода при 100 запросах в час: "
          f"{plan['runtime_hours_at_current_quota']} ч",
          f"- при 500 запросах в час: {plan['runtime_hours_at_target_quota']} ч", "",
          "План не предполагает освоения всего бюджета: цель — полезная информация "
          "на вызов, а не расход рублей.", "",
          "## Очередь задач (первые 30)", "",
          "| № | Метод | Фраза | Причина | Ожидаемый прирост | Ранг |",
          "|---|---|---|---|---|---|"]
    for i, t in enumerate(plan["tasks"][:30], 1):
        L.append(f"| {i} | {t['method']} | {t['phrase']} | {t['reason']} | "
                 f"{t['expected_information_gain']} | {t['rank']} |")
    L.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L), encoding="utf-8")
