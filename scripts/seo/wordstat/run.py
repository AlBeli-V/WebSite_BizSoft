#!/usr/bin/env python3
"""Wordstat Intelligence: единая точка запуска.

Режимы:
  --dry-run   ничего не вызывает, показывает план и оценку стоимости;
  --pilot     ограниченный прогон с отдельным потолком 500 ₽;
  --daily     суточный распределитель в пределах квоты и бюджета.

Массовый обход без явного режима не запускается.

Запуск: python3 scripts/seo/wordstat/run.py --dry-run [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import budget as budget_mod      # noqa: E402
import client as client_mod      # noqa: E402
import config                    # noqa: E402
import coverage as cov_mod       # noqa: E402
import discovery as D            # noqa: E402
import limiter as limiter_mod    # noqa: E402
import opportunity as opp_mod    # noqa: E402
import planner as planner_mod    # noqa: E402
import tiers as tiers_mod        # noqa: E402
import universe as universe_mod  # noqa: E402
import vendor_expansion as vx    # noqa: E402

OUT = pathlib.Path("reports/seo/wordstat")
STATE = OUT / "last-runs.json"
SNAP_DIR = pathlib.Path("reports/seo/intelligence/snapshots")


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def latest_snapshot(date: str) -> dict:
    path = SNAP_DIR / f"{date}.json"
    if not path.exists():
        candidates = sorted(SNAP_DIR.glob("*.json"))
        if not candidates:
            return {}
        path = candidates[-1]
    return json.loads(path.read_text(encoding="utf-8"))


def prepare(date: str, cfg: dict):
    """Собрать текущую картину: база, кластеры, уровни, разрывы, план задач."""
    vendors = D.site_vendors()
    uni = universe_mod.Universe(vendors=D.vendor_index(vendors))
    snap = latest_snapshot(date)
    if snap:
        cov_mod.enrich_universe(uni, snap, {v["slug"]: v["url"] for v in vendors})
    clusters = cov_mod.clusters_of(uni)
    tiers = tiers_mod.assign(clusters, cfg)
    gaps = cov_mod.gap_analysis(uni, clusters, conversion_clusters=set())
    covered = {c["cluster"] for c in clusters.values() if c["page_exists"]}
    stats = D.PatternStats()
    seed_plan = D.build_seed_plan(vendors, uni, stats, covered, cfg["thresholds"])
    # Кандидаты на расширение каталога: спрос на вендоров, которых у нас нет.
    # Измеряются один раз, дальше отвечает кэш — это дешёвая, но важная часть
    # исследования: она отвечает на вопрос «что добавить», а не только
    # «как улучшить существующее».
    for cand in vx.pending(vendors, uni):
        if cand["measured"]:
            continue
        seed_plan.append({
            "phrase": cand["phrase"], "cluster": None, "vendor": cand["brand"],
            "category": "кандидат на добавление", "url": None,
            "pattern": None, "rationale": "спрос на вендора, которого нет в каталоге",
            "expected_information_gain": 0.6, "depth": 0,
            "reason_override": "vendor_expansion",
        })

    state = load_state()
    dyn = tiers_mod.dynamics_due(clusters, tiers, state, cfg, date)
    reg = tiers_mod.regions_due(clusters, tiers, state, cfg, date,
                                ppc_candidates={g["cluster"] for g in gaps
                                                if g["gap"] == "GAP-F"})
    return uni, vendors, clusters, tiers, gaps, seed_plan, dyn, reg, stats


def run_tasks(tasks, client, uni, vendors, stats, budget, cfg, date, *, cap=None,
              wait_for_quota=False, deadline=None, sleep=None):
    """Выполнить задачи до исчерпания лимитов. Возвращает сводку прогона.

    В режиме ожидания квоты прогон не завершается при исчерпании часового окна,
    а дожидается следующего: полный цикл исследования — около 240 вызовов, это
    один часовой слот при квоте 500 в час, и растягивать его на недели незачем.
    """
    import time as _time
    sleep = sleep or _time.sleep
    index = D.vendor_index(vendors)
    vendor_by_slug = {v["slug"]: v for v in vendors}
    done = {"calls": 0, "ok": 0, "empty": 0, "raw": 0, "new_phrases": 0,
            "new_clusters": 0, "new_commercial": 0, "stopped": None}
    known_clusters = {r.get("cluster") for r in uni.rows.values()}
    empty_streak: dict[str, int] = {}

    queue = list(tasks)
    while queue:
        task = queue[0]
        if cap is not None and done["calls"] >= cap:
            done["stopped"] = "достигнут потолок прогона"
            break
        pattern = task.get("pattern")
        if pattern and empty_streak.get(pattern, 0) >= cfg["thresholds"]["empty_seed_streak_stop"]:
            queue.pop(0)
            continue

        if task["method"] == "getTop":
            res = client.top(task["phrase"], reason=task["reason"],
                             cluster=task.get("cluster"))
        elif task["method"] == "getDynamics":
            res = client.dynamics(task["phrase"], reason=task["reason"],
                                  cluster=task.get("cluster"), today=date)
        else:
            res = client.regions(task["phrase"], reason=task["reason"],
                                 cluster=task.get("cluster"))

        if res["status"] == "quota_exceeded" and wait_for_quota:
            if deadline is not None and _time.time() >= deadline:
                done["stopped"] = "исчерпан отведённый срок полного цикла"
                break
            waited = client.limiter.wait_for_slot(sleep=sleep)
            done["waited_sec"] = round(done.get("waited_sec", 0) + waited, 1)
            done["quota_waits"] = done.get("quota_waits", 0) + 1
            continue                      # та же задача пробуется снова
        queue.pop(0)
        if res["status"] in ("quota_exceeded", "budget_blocked"):
            done["stopped"] = client.stopped_by or res["status"]
            break
        done["calls"] += 1
        if res["status"] != "ok":
            done["empty"] += 1
            if pattern:
                empty_streak[pattern] = empty_streak.get(pattern, 0) + 1
                stats.record(pattern, ok=False, unique_new=0)
            if res["source"] == "api":
                budget.record(method=task["method"], phrase=task["phrase"],
                              cluster=task.get("cluster"), reason=task["reason"],
                              cache_hit=False, status=res["status"])
            continue

        done["ok"] += 1
        if pattern:
            empty_streak[pattern] = 0
        if task["method"] != "getTop":
            # Ответ на запрос динамики раньше выбрасывался сразу после оплаты:
            # тренд у всех кластеров оставался «неизвестен», хотя ряд был куплен.
            rows_out = (res["data"] or {}).get("results") or []
            if task["method"] == "getDynamics":
                uni.observe_dynamics(task["phrase"], rows_out)
            if res["source"] == "api":
                budget.record(method=task["method"], phrase=task["phrase"],
                              cluster=task.get("cluster"), reason=task["reason"],
                              cache_hit=False, status="ok",
                              result_count=len(rows_out) or 1)
            continue

        rows = (res["data"] or {}).get("results") or []
        before_phrases, before_clusters = len(uni), set(known_clusters)
        new_commercial = 0
        vendor = vendor_by_slug.get(task.get("cluster"), {})
        for r in rows:
            phrase = r.get("phrase", "")
            freq = int(r["count"]) if r.get("count") is not None else None
            row, is_new = uni.observe(
                phrase=phrase, frequency=freq, date=date,
                source_seed=task["phrase"], region=cfg["collection"]["region_id"],
                period="последние 30 дней", method="getTop",
                cost_rub=res["cost_rub"] / max(1, len(rows)), vendors=index,
                vendor=vendor.get("vendor"), category=vendor.get("category"),
                source=res["source"])
            known_clusters.add(row.get("cluster"))
            if is_new and row["intent"] == "commercial" and row.get("in_scope"):
                new_commercial += 1
        unique_new = len(uni) - before_phrases
        new_clusters = len(known_clusters - before_clusters)
        done["raw"] += len(rows)
        done["new_phrases"] += unique_new
        done["new_clusters"] += new_clusters
        done["new_commercial"] += new_commercial
        if pattern:
            stats.record(pattern, ok=True, unique_new=unique_new)
        if res["source"] == "api":
            budget.record(method="getTop", phrase=task["phrase"],
                          cluster=task.get("cluster"), reason=task["reason"],
                          cache_hit=False, status="ok", result_count=len(rows),
                          unique_result_count=unique_new,
                          new_commercial_phrases=new_commercial,
                          new_clusters=new_clusters)
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=config.today_msk())
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--daily", action="store_true")
    ap.add_argument("--full", action="store_true",
                    help="полный цикл исследования: при исчерпании квоты "
                         "приостанавливается и продолжает, пока задачи не кончатся")
    ap.add_argument("--max-hours", type=float, default=5.0,
                    help="потолок длительности полного цикла в часах")
    ap.add_argument("--max-calls", type=int, default=None)
    ap.add_argument("--hours", type=int, default=1)
    args = ap.parse_args()

    cfg = config.load()
    date = args.date
    uni, vendors, clusters, tiers, gaps, seed_plan, dyn, reg, stats = prepare(date, cfg)
    plan = planner_mod.monthly_plan(uni, clusters, tiers, seed_plan, dyn, reg,
                                    cfg, date[:7])
    OUT.mkdir(parents=True, exist_ok=True)
    planner_mod.write_plan_md(plan, OUT / f"{date[:7]}-research-plan.md")

    budget = budget_mod.BudgetController(cfg, today=date, pilot=args.pilot)
    if args.full:
        # Полный цикл: очередь не режется часовым окном. Ограничителями остаются
        # бюджет и отведённый срок — цикл идёт до конца задач, а не по слотам.
        alloc = {"slots_available": len(plan["tasks"]),
                 "selected": plan["tasks"],
                 "estimated_cost_rub": plan["estimated_cost_rub"],
                 "limited_by": "полный цикл: ограничивают бюджет и срок"}
    else:
        # Плановый прогон берёт квоту за вычетом резерва: часть слотов остаётся
        # свободной под срочные проверки, иначе исследование по расписанию
        # блокирует любую валидацию до следующего часа.
        usable_quota = (cfg["quota"]["requests_per_hour"]
                        - cfg["quota"].get("reserved_slots_per_hour", 0))
        alloc = planner_mod.allocate_day(
            plan["tasks"], hourly_quota=usable_quota,
            hours_available=args.hours, budget_remaining_rub=budget.remaining(),
            daily_cap_rub=(cfg["budget"]["pilot_cap_rub"] if args.pilot
                           else cfg["budget"]["daily_cap_rub"]))

    if args.dry_run:
        report = {
            "mode": "dry-run", "date": date,
            "vendors": len(vendors),
            "seed_phrases": len(seed_plan),
            "planned_gettop": plan["planned_calls_by_method"].get("getTop", 0),
            "planned_dynamics": plan["planned_calls_by_method"].get("getDynamics", 0),
            "planned_regions": plan["planned_calls_by_method"]
                .get("getRegionsDistribution", 0),
            "planned_calls_total": plan["planned_calls"],
            "estimated_cost_rub": plan["estimated_cost_rub"],
            "budget_utilisation": plan["budget_utilisation"],
            "runtime_hours_at_current_quota": plan["runtime_hours_at_current_quota"],
            "runtime_hours_at_500": plan["runtime_hours_at_target_quota"],
            "max_possible_spend_rub": plan["max_possible_spend_current_quota_rub"],
            "budget_is_binding": plan["budget_is_binding"],
            "today_slots": alloc["slots_available"],
            "today_selected": len(alloc["selected"]),
            "today_cost_rub": alloc["estimated_cost_rub"],
            "today_limited_by": alloc["limited_by"],
            "universe": uni.stats(),
        }
        (OUT / f"{date}-dry-run.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        for k, v in report.items():
            if k != "universe":
                print(f"  {k:28} {v}")
        print(f"  {'universe':28} {report['universe']}")
        return 0

    if not (args.pilot or args.daily or args.full):
        print("Массовый прогон без режима запрещён: укажите --dry-run, --pilot, "
              "--daily или --full.", file=sys.stderr)
        return 2

    import time as _time
    client = client_mod.WordstatClient(budget, cfg)
    deadline = _time.time() + args.max_hours * 3600 if args.full else None
    done = run_tasks(alloc["selected"], client, uni, vendors, stats, budget, cfg,
                     date, cap=args.max_calls, wait_for_quota=args.full,
                     deadline=deadline)
    uni.save()
    stats.save()

    state = load_state()
    for t in alloc["selected"][:done["calls"]]:
        if t["method"] == "getDynamics":
            state[f"dynamics|{t['cluster']}"] = date
        if t["method"] == "getRegionsDistribution":
            state[f"regions|{t['cluster']}"] = date
    save_state(state)

    eff = budget.efficiency()
    mode = "full" if args.full else ("pilot" if args.pilot else "daily")
    result = {"mode": mode, "date": date,
              "run": done, "efficiency": eff, "universe": uni.stats()}
    (OUT / f"{date}-{mode}-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
