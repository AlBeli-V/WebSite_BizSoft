#!/usr/bin/env python3
"""Вердикт-движок SEO-экспериментов: оценка → вердикт → рекомендация.

Задание руководителя 30.08.2026. Слой получает данные из experiment_stats
и возвращает структурированный результат (§17); письмо только отображает.

Вердикты (§6):
  CONFIRMED         — значимый положительный эффект, не объяснимый позицией,
                      выше бизнес-порога;
  REJECTED          — доказанное значимое ухудшение (не «нет роста»);
  INCONCLUSIVE      — данных достаточно, надёжного вывода нет (с причиной);
  INSUFFICIENT_DATA — экспозиция ниже гейта (с расчётом, сколько не хватает).

Никаких автодействий: рекомендация всегда со статусом «требуется решение
владельца», решение фиксируется в append-only журнале (§10). История каждой
оценки на контрольной точке сохраняется отдельным снимком (§13).
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import experiment_stats as st  # noqa: E402

HISTORY_DIR = pathlib.Path("reports/seo/intelligence/experiments-history")
DECISIONS = pathlib.Path("reports/seo/intelligence/experiment-decisions.jsonl")
VENDOR_DEMAND = pathlib.Path("src/data/vendor-demand.json")
VENDORS_TS = pathlib.Path("src/data/vendors.ts")

VERDICTS = ("CONFIRMED", "REJECTED", "INCONCLUSIVE", "INSUFFICIENT_DATA")
RECOMMENDATIONS = ("EXPAND", "REVERT", "KEEP", "EXTEND", "NEW_TEST")


# ── Оценка одного эксперимента ──────────────────────────────────────────────

def evaluate(exp: dict, date: str) -> dict:
    """Полная оценка эксперимента на дату `date` (данные Яндекса).

    Возвращает структуру §17; никогда не бросает исключение из-за отсутствия
    данных — деградирует в INSUFFICIENT_DATA с конкретной причиной.
    """
    cfg = st.CONFIG
    start = dt.date.fromisoformat(exp["start"])
    today = dt.date.fromisoformat(date)
    slugs = [p.rstrip("/").rsplit("/", 1)[-1] for p in exp.get("pages") or []]

    res = {
        "experiment_id": exp["id"],
        "ticket": exp.get("ticket", ""),
        "date": date,
        "source": "yandex",
        "windows": None,
        "metrics": None, "matched_metrics": None,
        "position_delta": None,
        "sample_quality": [],
        "statistical_result": None,
        "confidence": "LOW",
        "verdict": "INSUFFICIENT_DATA",
        "verdict_reason": "",
        "recommendation": "EXTEND",
        "recommendation_detail": "",
        "recommended_targets": [],
        "requires_owner_decision": False,
    }

    win = st.pick_windows(start, today)
    if not win["baseline"]:
        res["verdict_reason"] = ("нет выгрузки Вебмастера с окном целиком до "
                                 "старта — baseline построить не из чего")
        res["recommendation_detail"] = "оценка невозможна для этого эксперимента"
        return res
    if not win["experiment"]:
        res["verdict_reason"] = (
            "окно источника ещё не очистилось от периода до внедрения; "
            f"чистое окно ожидается к {win['clean_experiment_eta'] or '—'}")
        res["recommendation_detail"] = (
            f"продлить наблюдение до {win['clean_experiment_eta'] or 'следующей вехи'}")
        return res

    res["windows"] = {
        "baseline": {"from": win["baseline"]["from"], "to": win["baseline"]["to"],
                     "file": win["baseline"]["file_date"]},
        "experiment": {"from": win["experiment"]["from"], "to": win["experiment"]["to"],
                       "file": win["experiment"]["file_date"],
                       "tainted": win["experiment_tainted"]},
    }
    if win["experiment_tainted"]:
        res["sample_quality"].append(
            "окно эксперимента захватывает день внедрения — часть показов могла "
            "увидеть старый вариант")
    # До 24.08 сборщик забирал только топ-100 запросов (постраничный обход
    # появился позже): усечённый baseline занижает matched-набор — это
    # ограничение данных, а не результат эксперимента.
    if len(win["baseline"]["queries"]) < 200:
        res["sample_quality"].append(
            f"baseline из усечённой выгрузки ({len(win['baseline']['queries'])} "
            "запросов) — совпадающий набор занижен")

    base_rows = st._rows_for_cluster(win["baseline"]["queries"], slugs)
    exp_rows = st._rows_for_cluster(win["experiment"]["queries"], slugs)
    overall_b, overall_e = st.metrics(base_rows), st.metrics(exp_rows)
    res["metrics"] = {"baseline": overall_b, "experiment": overall_e,
                      "days": {
                          "baseline": _days(win["baseline"]),
                          "experiment": _days(win["experiment"])}}

    mb, me = st.matched_sets(base_rows, exp_rows)
    matched_b, matched_e = st.metrics(mb), st.metrics(me)
    res["matched_metrics"] = {"baseline": matched_b, "experiment": matched_e,
                              "queries": len(mb)}

    # Гейт экспозиции (§5) — по matched-набору: именно он несёт вывод.
    need_b = cfg["EXPERIMENT_MIN_BASELINE_IMPRESSIONS"]
    need_e = cfg["EXPERIMENT_MIN_POST_IMPRESSIONS"]
    if matched_b["impressions"] < need_b or matched_e["impressions"] < need_e:
        lack = []
        if matched_b["impressions"] < need_b:
            lack.append(f"baseline: {matched_b['impressions']} из {need_b} показов")
        if matched_e["impressions"] < need_e:
            lack.append(f"после внедрения: {matched_e['impressions']} из {need_e}")
        res["verdict_reason"] = ("экспозиция ниже минимальной по совпадающим "
                                 "запросам (" + "; ".join(lack) + ")")
        res["recommendation_detail"] = (
            f"копить данные до следующей вехи; не хватает "
            f"{max(0, need_b - matched_b['impressions']) + max(0, need_e - matched_e['impressions'])} "
            "показов суммарно")
        return res

    if len(mb) < cfg["EXPERIMENT_MIN_MATCHED_QUERIES"]:
        res["sample_quality"].append(
            f"совпадающих запросов всего {len(mb)} — набор нерепрезентативен")

    stat = st.two_proportion_test(
        matched_b["clicks"], matched_b["impressions"],
        matched_e["clicks"], matched_e["impressions"])
    res["statistical_result"] = stat

    pos_delta = None
    if matched_b["avg_position"] is not None and matched_e["avg_position"] is not None:
        # Положительная дельта = позиция улучшилась (число уменьшилось).
        pos_delta = matched_b["avg_position"] - matched_e["avg_position"]
    res["position_delta"] = pos_delta

    _decide(res, stat, pos_delta, cfg)
    _recommend(res, exp, stat)
    return res


def _days(window: dict) -> int:
    return (dt.date.fromisoformat(window["to"])
            - dt.date.fromisoformat(window["from"])).days + 1


def _decide(res: dict, stat: dict, pos_delta: float | None, cfg: dict) -> None:
    """Правила вердикта (§6) и confidence (§8)."""
    alpha = cfg["EXPERIMENT_ALPHA"]
    min_uplift = cfg["EXPERIMENT_MIN_RELATIVE_UPLIFT"]
    max_pos = cfg["MAX_POSITION_DELTA_FOR_CLEAN_RESULT"]
    p = stat["p_value"]
    rel = stat["relative_uplift"]
    up = stat["absolute_uplift"] or 0.0

    significant = p is not None and p < alpha
    position_clean = pos_delta is None or abs(pos_delta) <= max_pos
    small_matched = any("нерепрезентативен" in s for s in res["sample_quality"])

    if significant and up < 0:
        res["verdict"] = "REJECTED"
        res["verdict_reason"] = (
            f"CTR по совпадающим запросам статистически значимо снизился "
            f"({_pct(stat['baseline_ctr'])} → {_pct(stat['experiment_ctr'])}, "
            f"p={p:.3f})")
    elif (significant and up > 0 and position_clean and not small_matched
          and rel is not None and rel >= min_uplift):
        res["verdict"] = "CONFIRMED"
        res["verdict_reason"] = (
            f"статистически значимый рост CTR "
            f"({_pct(stat['baseline_ctr'])} → {_pct(stat['experiment_ctr'])}, "
            f"p={p:.3f}) при стабильной позиции "
            f"({_signed(pos_delta)} поз.)")
    else:
        res["verdict"] = "INCONCLUSIVE"
        if significant and up > 0 and not position_clean:
            res["verdict_reason"] = (
                f"CTR вырос, но средняя позиция изменилась на {_signed(pos_delta)} "
                f"(порог {max_pos}) — рост может объясняться позицией, а не сниппетом")
        elif significant and up > 0 and small_matched:
            res["verdict_reason"] = ("рост значим, но совпадающих запросов слишком "
                                     "мало для надёжного вывода")
        elif significant and rel is not None and rel < min_uplift:
            res["verdict_reason"] = (
                f"эффект статистически значим, но {_pct(rel, raw=True)} — ниже "
                f"бизнес-порога {_pct(min_uplift, raw=True)}: масштабировать нечего")
        else:
            res["verdict_reason"] = (
                f"различие CTR статистически неразличимо "
                f"(p={p:.3f} при пороге {alpha})" if p is not None else
                "тест не дал оценки: вырожденная выборка")

    # Confidence (§8): сочетание значимости, объёма, позиции и качества выборки.
    score = 0
    if significant:
        score += 1
    if p is not None and p < alpha / 5:
        score += 1
    if stat["sample_sizes"]["baseline"] >= 2000 and stat["sample_sizes"]["experiment"] >= 2000:
        score += 1
    if position_clean:
        score += 1
    if not res["sample_quality"]:
        score += 1
    res["confidence"] = "HIGH" if score >= 4 else "MEDIUM" if score >= 2 else "LOW"


def _recommend(res: dict, exp: dict, stat: dict) -> None:
    """Рекомендация по вердикту (§9). Только предложение — решение за владельцем."""
    v = res["verdict"]
    if v == "CONFIRMED":
        targets = expand_candidates(exclude_pages=exp.get("pages") or [])
        res["recommendation"] = "EXPAND"
        res["recommended_targets"] = targets
        res["recommendation_detail"] = (
            "применить подтверждённую формулу сниппета к следующим "
            f"{len(targets)} карточкам (по убыванию замеренного спроса)")
        res["requires_owner_decision"] = True
    elif v == "REJECTED":
        res["recommendation"] = "REVERT"
        drop = stat["absolute_uplift"] or 0.0
        res["recommendation_detail"] = (
            f"откатить формулу на страницах эксперимента: при сохранении теряем "
            f"≈{_pct(abs(drop), raw=True)} CTR по совпадающим запросам; "
            "откат возвращает прежние сниппеты (вариант KEEP — оставить и "
            "наблюдать — допустим, если снижение объяснимо сезоном)")
        res["requires_owner_decision"] = True
    elif v == "INCONCLUSIVE":
        res["recommendation"] = "EXTEND"
        res["recommendation_detail"] = (
            "оставить как есть и продлить наблюдение до следующей вехи; "
            "если и она не даст вывода — NEW_TEST с более контрастной формулой")
        res["requires_owner_decision"] = False
    else:  # INSUFFICIENT_DATA
        res["recommendation"] = "EXTEND"
        res["requires_owner_decision"] = False


def _pct(v: float | None, raw: bool = False) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.1f}%" if not raw else f"{v * 100:+.0f}%".lstrip("+") + ""


def _signed(v: float | None) -> str:
    return "—" if v is None else f"{v:+.1f}"


# ── EXPAND-кандидаты (§9): следующие карточки по замеренному спросу ─────────

def expand_candidates(exclude_pages: list[str], limit: int = 10) -> list[str]:
    """Карточки вендоров с наибольшим спросом Вордстата вне экспериментов."""
    try:
        demand = json.loads(VENDOR_DEMAND.read_text(encoding="utf-8"))["vendors"]
        text = VENDORS_TS.read_text(encoding="utf-8")
    except (OSError, KeyError, json.JSONDecodeError):
        return []
    slug_by_name = {name: slug for slug, name in
                    re.findall(r"\{\s*slug:\s*'([^']+)',\s*vendor:\s*'([^']+)'", text)}
    excluded = {p.rstrip("/").rsplit("/", 1)[-1] for p in exclude_pages}
    # Все страницы действующих экспериментов тоже вне кандидатов.
    try:
        reg = json.loads(pathlib.Path(
            "reports/seo/intelligence/seo-experiments.json").read_text(encoding="utf-8"))
        for e in reg.get("experiments", []):
            excluded |= {p.rstrip("/").rsplit("/", 1)[-1] for p in e.get("pages") or []}
    except (OSError, json.JSONDecodeError):
        pass
    out = []
    for name, vol in sorted(demand.items(), key=lambda kv: -kv[1]):
        slug = slug_by_name.get(name)
        if not slug or slug in excluded:
            continue
        out.append(f"/vendors/{slug}")
        if len(out) >= limit:
            break
    return out


# ── История и журнал решений (§10, §13) ─────────────────────────────────────

def save_history(result: dict) -> pathlib.Path:
    """Снимок оценки на контрольной точке; прежние снимки не перезаписываются."""
    d = HISTORY_DIR / result["experiment_id"]
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{result['date']}.json"
    if not path.exists():
        path.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    return path


def append_decision(experiment_id: str, date: str, verdict: str,
                    recommendation: str, owner_decision: str, note: str = "") -> None:
    """Запись решения владельца в append-only журнал.

    Вызывается сессией по явной команде владельца (KEEP/REVERT/EXPAND/EXTEND/
    NEW_TEST), никогда автоматически.
    """
    DECISIONS.parent.mkdir(parents=True, exist_ok=True)
    rec = {"experiment_id": experiment_id, "date": date, "verdict": verdict,
           "recommendation": recommendation, "owner_decision": owner_decision,
           "decided_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "note": note}
    with DECISIONS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
