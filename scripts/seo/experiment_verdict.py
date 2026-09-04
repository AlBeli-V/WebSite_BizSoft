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
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import experiment_stats as st  # noqa: E402

HISTORY_DIR = pathlib.Path("reports/seo/intelligence/experiments-history")
DECISIONS = pathlib.Path("reports/seo/intelligence/experiment-decisions.jsonl")

VERDICTS = ("CONFIRMED", "REJECTED", "INCONCLUSIVE", "INSUFFICIENT_DATA")
RECOMMENDATIONS = ("EXPAND", "REVERT", "KEEP", "EXTEND", "NEW_TEST")


# ── Оценка одного эксперимента ──────────────────────────────────────────────

def evaluate(exp: dict, date: str) -> dict:
    """Полная оценка эксперимента на дату `date` (данные Яндекса).

    Возвращает структуру §17; никогда не бросает исключение из-за отсутствия
    данных — деградирует в INSUFFICIENT_DATA с конкретной причиной.

    Тип оценки задаётся реестром (evaluation_kind, проверка руководителя
    31.08.2026 — «выводы что делаем» нужны каждому эксперименту, а не только
    CTR-обеим): "ctr" (по умолчанию) — z-тест кликабельности; "impressions_
    growth" — рост показов кластера к зафиксированному в реестре baseline
    (CONTENT-001: у контент-эксперимента цель — показы и вход статьи в
    топ-10, а не CTR); "launch" — запуск новых страниц (PAGES-EXP-001:
    baseline-окна не существует по построению — страниц не было, CTR-гейт
    давал бы INSUFFICIENT_DATA вечно; критерии — из launch_criteria реестра).
    """
    kind = exp.get("evaluation_kind", "ctr")
    if kind == "impressions_growth":
        return _evaluate_impressions_growth(exp, date)
    if kind == "launch":
        return _evaluate_launch(exp, date)
    res = _evaluate_ctr(exp, date)
    # Объединённая оценка формулы (вопрос руководителя 31.08.2026): малый
    # кластер участника не наберёт собственный гейт, но эксперименты одной
    # формулы складываются — статистической мощности группы хватает раньше.
    # Пул — вспомогательное свидетельство о ФОРМУЛЕ, вердикт участника он
    # не подменяет.
    if exp.get("formula_group"):
        try:
            res["formula_group_result"] = _formula_group_result(
                exp["formula_group"], date)
        except Exception:  # noqa: BLE001 — пул вспомогателен, письмо не ломаем
            res["formula_group_result"] = None
        _apply_group_hint(res)
    return res


def _evaluate_ctr(exp: dict, date: str) -> dict:
    cfg = st.CONFIG
    start = dt.date.fromisoformat(exp["start"])
    today = dt.date.fromisoformat(date)
    keys = _keys(exp)

    res = _skeleton(exp, date)

    win = st.pick_windows(start, today, exp)
    if not win["baseline"]:
        res["verdict_reason"] = ("нет выгрузки Вебмастера с окном целиком до "
                                 "старта — baseline построить не из чего")
        res["recommendation_detail"] = "оценка невозможна для этого эксперимента"
        return res
    if not win["experiment"]:
        eta = win.get("fixed_experiment_eta") or win["clean_experiment_eta"]
        res["clean_window_eta"] = eta
        res["verdict_reason"] = (
            "окно источника захватывает период до внедрения; "
            f"чистое окно — с {eta or '—'}")
        res["recommendation_detail"] = (
            f"продлить наблюдение до {eta or 'следующей вехи'}")
        return res

    fixed = win.get("fixed") or {}
    res["windows"] = {
        "baseline": {"from": win["baseline"]["from"], "to": win["baseline"]["to"],
                     "file": win["baseline"]["file_date"],
                     "fixed": bool(fixed.get("baseline"))},
        "experiment": {"from": win["experiment"]["from"], "to": win["experiment"]["to"],
                       "file": win["experiment"]["file_date"],
                       "tainted": win["experiment_tainted"],
                       "fixed": bool(fixed.get("experiment"))},
    }
    if win["experiment_tainted"]:
        res["sample_quality"].append(
            "окно эксперимента захватывает день внедрения — часть показов могла "
            "увидеть старый вариант")
    # До 24.08 сборщик забирал только топ-100 запросов (постраничный обход
    # появился позже): усечённый baseline занижает matched-набор — это
    # ограничение данных, а не результат эксперимента. Фиксированное окно
    # выгружается полным обходом — там усечения нет по построению.
    if len(win["baseline"]["queries"]) < 200 and not fixed.get("baseline"):
        res["sample_quality"].append(
            f"baseline из усечённой выгрузки ({len(win['baseline']['queries'])} "
            "запросов) — совпадающий набор занижен")
    if fixed.get("baseline") and not fixed.get("experiment"):
        res["sample_quality"].append(
            "окно после внедрения пока скользящее (короче фиксированного "
            "baseline): сравнение предварительное до выгрузки полного окна "
            f"к {win.get('fixed_experiment_eta') or '—'}")

    base_rows = st._rows_for_cluster(win["baseline"]["queries"], keys)
    exp_rows = st._rows_for_cluster(win["experiment"]["queries"], keys)
    overall_b, overall_e = st.metrics(base_rows), st.metrics(exp_rows)
    res["metrics"] = {"baseline": overall_b, "experiment": overall_e,
                      "days": {
                          "baseline": _days(win["baseline"]),
                          "experiment": _days(win["experiment"])}}
    res["per_page"] = _per_page_metrics(exp, win)

    mb, me = st.matched_sets(base_rows, exp_rows)
    matched_b, matched_e = st.metrics(mb), st.metrics(me)
    res["matched_metrics"] = {"baseline": matched_b, "experiment": matched_e,
                              "queries": len(mb)}

    # Гейт экспозиции (§5) — по matched-набору: именно он несёт вывод.
    # Адаптация (31.08.2026): окно источника скользящее, малый кластер
    # настроенный порог не наберёт никогда — порог снижается до доли ёмкости
    # с пометкой и ограничением уверенности.
    # Гейт адаптируется по ёмкости ТОГО набора, на котором делается вывод, —
    # matched (issue #297). Прежде он считался от overall: 02.09 SEO-EXP-001
    # имел overall 532/610 (≥500 → адаптации нет) при matched 485/250, и
    # эксперимент получил «копить данные». Копить нечего: matched ограничен
    # пересечением с baseline-окном, которое в прошлом и не растёт.
    need_b, adapted_b = st.effective_gate(
        matched_b["impressions"], cfg["EXPERIMENT_MIN_BASELINE_IMPRESSIONS"], cfg)
    need_e, adapted_e = st.effective_gate(
        matched_e["impressions"], cfg["EXPERIMENT_MIN_POST_IMPRESSIONS"], cfg)
    adapted = adapted_b or adapted_e
    res["effective_gate"] = {"baseline": need_b, "experiment": need_e,
                             "adapted": adapted}
    if adapted:
        mde = st.min_detectable_uplift(
            matched_b["ctr"] or overall_b["ctr"],
            max(matched_b["impressions"], 1), max(matched_e["impressions"], 1), cfg)
        res["sample_quality"].append(
            "порог экспозиции адаптирован под ёмкость кластера "
            f"({need_b}/{need_e} вместо "
            f"{cfg['EXPERIMENT_MIN_BASELINE_IMPRESSIONS']}/"
            f"{cfg['EXPERIMENT_MIN_POST_IMPRESSIONS']}): окно источника "
            "скользящее, и больший объём кластер не наберёт"
            + (f"; надёжно различим только рост CTR от ×{1 + mde:.1f}"
               if mde is not None else ""))
    if matched_b["impressions"] < need_b or matched_e["impressions"] < need_e:
        lack = []
        if matched_b["impressions"] < need_b:
            lack.append(f"baseline: {matched_b['impressions']} из {need_b} показов")
        if matched_e["impressions"] < need_e:
            lack.append(f"после внедрения: {matched_e['impressions']} из {need_e}")
        res["verdict_reason"] = ("экспозиция ниже минимальной по совпадающим "
                                 "запросам (" + "; ".join(lack) + ")")
        lack_total = (max(0, need_b - matched_b["impressions"])
                      + max(0, need_e - matched_e["impressions"]))
        if matched_b["impressions"] < need_b:
            # baseline-окно в прошлом: ожидание его не увеличит (issue #297).
            res["recommendation_detail"] = (
                "ожидание не поможет: не хватает показов в базовом окне, а оно "
                "в прошлом и не растёт. Варианты — NEW_TEST с чистым baseline "
                "или решение по предварительному сравнению из письма")
            res["recommendation"] = "NEW_TEST"
        else:
            res["recommendation_detail"] = (
                f"копить данные до следующей вехи; не хватает {lack_total} "
                "показов суммарно")
        return res

    if len(mb) < cfg["EXPERIMENT_MIN_MATCHED_QUERIES"]:
        res["sample_quality"].append(
            f"совпадающих запросов всего {len(mb)} — набор нерепрезентативен")

    stat = st.two_proportion_test(
        matched_b["clicks"], matched_b["impressions"],
        matched_e["clicks"], matched_e["impressions"])
    stat["min_detectable_relative_uplift"] = st.min_detectable_uplift(
        stat["baseline_ctr"], matched_b["impressions"],
        matched_e["impressions"], cfg)
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


def _per_page_metrics(exp: dict, win: dict) -> list[dict]:
    """Метрики каждой страницы эксперимента в обоих окнах (page_markers).

    Вердикт по-прежнему один на эксперимент — это не разделение совместного
    внедрения, а контроль экспозиции: страница без показов в обоих окнах
    видна сразу, а не растворяется в сумме по кластеру.
    """
    import experiments
    out = []
    for page, pk in experiments.page_keys(exp).items():
        b_rows = st._rows_for_cluster(win["baseline"]["queries"], pk)
        e_rows = st._rows_for_cluster(win["experiment"]["queries"], pk)
        mb, me = st.matched_sets(b_rows, e_rows)
        out.append({"page": page,
                    "baseline": st.metrics(b_rows),
                    "experiment": st.metrics(e_rows),
                    "matched_queries": len(mb),
                    "matched": {"baseline": st.metrics(mb),
                                "experiment": st.metrics(me)}})
    return out


def _keys(exp: dict) -> dict:
    import experiments
    return experiments.cluster_keys(exp)


def _skeleton(exp: dict, date: str) -> dict:
    """Общий каркас результата §17 для всех типов оценки."""
    return {
        "experiment_id": exp["id"],
        "ticket": exp.get("ticket", ""),
        "date": date,
        "source": "yandex",
        "evaluation_kind": exp.get("evaluation_kind", "ctr"),
        "windows": None,
        "metrics": None, "matched_metrics": None,
        "position_delta": None,
        "sample_quality": [],
        "statistical_result": None,
        "summary_line": None,
        "confidence": "LOW",
        "verdict": "INSUFFICIENT_DATA",
        "verdict_reason": "",
        "recommendation": "EXTEND",
        "recommendation_detail": "",
        "recommended_targets": [],
        "requires_owner_decision": False,
    }


def _serp_pages(exp: dict, today: dt.date) -> dict | None:
    """Статус страниц эксперимента в выдаче (без утверждений о новизне)."""
    import serp_snippets
    try:
        return serp_snippets.serp_status(exp.get("pages") or [], {}, today)
    except Exception:  # noqa: BLE001 — SERP вспомогателен для этих оценок
        return None


def _target_pages(exp: dict) -> list[str]:
    """Целевые страницы приёма: партия (`target_pages`) или одна (`target_page`).

    Тиражирование по построению выкатывает несколько страниц сразу, и вывод
    «статья в топ-10» об одной из шести скрывал бы остальные пять.
    """
    pages = exp.get("target_pages") or (
        [exp["target_page"]] if exp.get("target_page") else [])
    return pages or (exp.get("pages") or [])[:1]


def _target_pages_note(exp: dict, today: dt.date) -> tuple[str, int | None, dict]:
    """Строка о положении целевых страниц в выдаче и счёт вошедших в топ-10."""
    targets = _target_pages(exp)
    serp = _serp_pages(exp, today)
    measured = {p: serp["pages"][p]["best_position"] for p in targets
                if serp and p in (serp.get("pages") or {})}
    stat = {"targets": len(targets), "measured": len(measured),
            "in_top": sum(1 for pos in measured.values() if pos <= 10)}
    if not measured:
        return ("страницы в замер выдачи не попали" if len(targets) != 1
                else "статья в замер выдачи не попала"), None, stat
    first_pos = measured[targets[0]] if targets[0] in measured else None
    if len(targets) == 1:
        pos = next(iter(measured.values()))
        note = (f"статья в топ-10: позиция {pos} (замер {serp['measured_at']})"
                if pos <= 10 else f"статья вне топ-10: позиция {pos}")
        return note, pos, stat
    positions = ", ".join(f"{p.rsplit('/', 1)[-1]} — {measured[p]}"
                          for p in targets if p in measured)
    note = (f"в топ-10 {stat['in_top']} из {stat['measured']} замеренных "
            f"страниц партии (позиции: {positions}; замер {serp['measured_at']})")
    return note, first_pos, stat


def _top10_reason(top10: dict, target_pos: int | None, prefix: str = ", ") -> str:
    """Хвост причины вердикта о положении целевых страниц."""
    if top10["targets"] == 1:
        if target_pos is not None and target_pos <= 10:
            return f"{prefix}статья вошла в топ-10 (позиция {target_pos})"
        return ""
    if not top10["in_top"]:
        return ""
    return (f"{prefix}в топ-10 вошли {top10['in_top']} из "
            f"{top10['measured']} замеренных страниц партии")


def _evaluate_impressions_growth(exp: dict, date: str) -> dict:
    """Оценка контент-эксперимента: рост показов кластера + вход статьи в топ.

    Метрика CONTENT-001 — не CTR, а рост показов кластера к baseline,
    зафиксированному в реестре при запуске, и вход статьи в топ-10. У показов
    нет модели испытаний для z-теста, поэтому критерия значимости здесь нет —
    это прямо указывается, а падение показов не объявляется REJECTED
    (сезонность неотличима от эффекта без теста).
    """
    cfg = st.CONFIG
    res = _skeleton(exp, date)
    start = dt.date.fromisoformat(exp["start"])
    today = dt.date.fromisoformat(date)
    base = exp.get("baseline") or {}
    base_imp = base.get("impressions_cluster")
    base_days = base.get("days") or 14
    if not base_imp:
        res["verdict_reason"] = ("в реестре нет baseline показов кластера — "
                                 "рост считать не от чего")
        return res

    win = st.pick_windows(start, today, exp)
    if not win["experiment"]:
        eta = win.get("fixed_experiment_eta") or win["clean_experiment_eta"]
        # Дату чистого окна показывает и блок эксперимента в письме — рядом с
        # «порог пройден», иначе набранная экспозиция читается как готовность
        # вывода (проверка 04.09.2026).
        res["clean_window_eta"] = eta
        res["verdict_reason"] = (
            "окно источника захватывает период до внедрения; "
            f"чистое окно — с {eta or '—'}")
        res["recommendation_detail"] = (
            f"продлить наблюдение до {eta or 'следующей вехи'}")
        return res

    w = win["experiment"]
    rows = st._rows_for_cluster(w["queries"], _keys(exp))
    m = st.metrics(rows)
    cur_days = _days(w)
    per_day_cur = m["impressions"] / cur_days if cur_days else 0.0
    per_day_base = base_imp / base_days
    growth = (per_day_cur - per_day_base) / per_day_base if per_day_base else None
    res["windows"] = {"experiment": {"from": w["from"], "to": w["to"],
                                     "file": w["file_date"],
                                     "tainted": win["experiment_tainted"]}}
    res["metrics"] = {"experiment": m,
                      "baseline_registry": {"impressions": base_imp,
                                            "days": base_days}}
    if win["experiment_tainted"]:
        res["sample_quality"].append(
            "окно захватывает день внедрения — рост слегка занижен")

    top_note, target_pos, top10 = _target_pages_note(exp, today)
    res["summary_line"] = (
        f"показы кластера {per_day_cur:.0f}/день (окно {w['from']}–{w['to']}) "
        f"против {per_day_base:.0f}/день baseline ({base_imp} за {base_days} дн.)"
        + (f" — {growth * 100:+.0f}%" if growth is not None else "")
        + f" · {top_note} · без критерия значимости (у показов нет модели испытаний)")

    min_uplift = cfg["EXPERIMENT_MIN_RELATIVE_UPLIFT"]
    if growth is not None and growth >= min_uplift:
        res["verdict"] = "CONFIRMED"
        res["verdict_reason"] = (
            f"показы кластера выросли на {growth * 100:+.0f}% к baseline "
            f"({per_day_base:.0f} → {per_day_cur:.0f} показов/день)"
            + _top10_reason(top10, target_pos))
        res["confidence"] = ("HIGH" if growth >= 0.5 and m["impressions"] >= 500
                             and top10["in_top"] * 2 >= max(top10["measured"], 1)
                             and top10["in_top"] else "MEDIUM")
        targets = expand_candidates(exclude_pages=exp.get("pages") or [],
                                    profile="content")
        res["recommendation"] = "EXPAND"
        res["recommended_targets"] = targets
        res["recommendation_detail"] = (
            "перенести приём (статья под транзакционный интент + взаимная "
            f"перелинковка с карточками) на следующие {len(targets)} кластеров, "
            "где условия оригинала выполнены целиком: сайт уже показывается "
            "по кластеру со средней позицией в топ-10 и есть карточки товара "
            "для перелинковки" if targets else
            "приём подтверждён, но кластеров с условиями оригинала не найдено: "
            "нет выгрузки Вебмастера или ни один кластер не проходит гейты — "
            "цели нужно отобрать вручную")
        res["requires_owner_decision"] = True
    elif growth is not None and growth <= -min_uplift:
        res["verdict"] = "INCONCLUSIVE"
        res["verdict_reason"] = (
            f"показы кластера снизились на {growth * 100:.0f}% к baseline — "
            "без критерия значимости падение неотличимо от сезонного")
        res["recommendation"] = "EXTEND"
        res["recommendation_detail"] = ("продлить наблюдение и разобрать причины "
                                        "(сезонность, смена выдачи, каннибализация "
                                        "статьёй карточек)")
    else:
        res["verdict"] = "INCONCLUSIVE"
        res["verdict_reason"] = (
            f"изменение показов ({(growth or 0) * 100:+.0f}%) в пределах "
            f"бизнес-порога ±{min_uplift * 100:.0f}%"
            + (_top10_reason(top10, target_pos, prefix="; ")))
        res["recommendation"] = "EXTEND"
        res["recommendation_detail"] = "продлить наблюдение до следующей вехи"
    return res


def _evaluate_launch(exp: dict, date: str) -> dict:
    """Оценка запуска новых страниц: индексация, показы, первые клики.

    У новых страниц baseline-окна не существует по построению, поэтому
    критерии берутся из launch_criteria реестра (страниц в выдаче, показов
    в неделю к контрольному дню). Пересечение окна выгрузки с датой старта
    не загрязняет оценку: до старта показов у этих страниц быть не могло.
    """
    res = _skeleton(exp, date)
    start = dt.date.fromisoformat(exp["start"])
    today = dt.date.fromisoformat(date)
    crit = exp.get("launch_criteria") or {}
    need_pages = crit.get("min_pages_in_search", 5)
    need_weekly = crit.get("min_weekly_impressions", 300)
    by_day = crit.get("by_day", 14)
    clicks_by_day = crit.get("first_clicks_by_day", 28)
    days = (today - start).days
    pages_total = len(exp.get("pages") or [])

    serp = _serp_pages(exp, today)
    in_search = serp["pages_seen"] if serp else 0
    serp_note = (f"(замер {serp['measured_at']})" if serp
                 else "(нет успешного SERP-замера за 7 дней)")

    win = st.pick_windows(start, today, exp)
    w = win["experiment"] or win["baseline"]
    weekly = clicks = 0
    if w:
        # Для запуска годится и пересекающее окно: показы кластера с
        # интент-фильтром до старта невозможны — страниц не существовало.
        last = None
        for d in reversed(st._available_dates()):
            if d <= date:
                last = st._load_day(d)
                if last:
                    break
        if last:
            m = st.metrics(st._rows_for_cluster(last["queries"], _keys(exp)))
            wd = (dt.date.fromisoformat(last["to"])
                  - dt.date.fromisoformat(last["from"])).days + 1
            weekly = round(m["impressions"] / wd * 7) if wd else 0
            clicks = m["clicks"]
    res["metrics"] = {"launch": {
        "pages_total": pages_total, "pages_in_search": in_search,
        "weekly_impressions": weekly, "clicks": clicks,
        "need_pages": need_pages, "need_weekly": need_weekly}}
    res["summary_line"] = (
        f"в выдаче {in_search} из {pages_total} страниц {serp_note} · "
        f"~{weekly} показов/нед из {need_weekly} · "
        f"{clicks} кликов · день {days} из {by_day} до первой вехи")

    if days < by_day:
        res["verdict_reason"] = (
            f"идёт набор: {in_search} из {need_pages} страниц в выдаче, "
            f"~{weekly} из {need_weekly} показов/нед; веха — "
            f"{(start + dt.timedelta(days=by_day)).isoformat()}")
        res["recommendation_detail"] = "копить данные до вехи"
        return res

    met_pages, met_weekly = in_search >= need_pages, weekly >= need_weekly
    if met_pages and met_weekly:
        res["verdict"] = "CONFIRMED"
        res["verdict_reason"] = (
            f"запуск состоялся: {in_search} из {pages_total} страниц в выдаче, "
            f"~{weekly} показов/нед (порог {need_weekly})")
        res["confidence"] = "MEDIUM" if clicks == 0 else "HIGH"
        res["recommendation"] = "KEEP"
        res["recommendation_detail"] = (
            "держать курс до вехи первых кликов "
            f"({(start + dt.timedelta(days=clicks_by_day)).isoformat()}); после "
            "первых кликов — решение о расширении набора сравнений")
    else:
        missing = []
        if not met_pages:
            missing.append(f"в выдаче {in_search} из {need_pages} страниц")
        if not met_weekly:
            missing.append(f"~{weekly} из {need_weekly} показов/нед")
        res["verdict"] = "INCONCLUSIVE"
        res["verdict_reason"] = "веха не выполнена: " + "; ".join(missing)
        res["recommendation"] = "EXTEND"
        res["recommendation_detail"] = (
            "разобрать отсутствующие страницы (индексация, сниппеты); "
            "запросить переобход через ops-yandex-recrawl; "
            "если и следующая веха провалена — решение о судьбе раздела")
        res["requires_owner_decision"] = days >= clicks_by_day
    return res


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
            mde = stat.get("min_detectable_relative_uplift")
            if (p is not None and rel is not None and mde is not None
                    and 0 < rel < mde):
                res["verdict_reason"] += (
                    f"; наблюдаемый рост {rel * 100:+.0f}% меньше минимально "
                    f"различимого при этой выборке (от ×{1 + mde:.1f})")

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
    # Адаптированный гейт означает малую выборку по построению: уверенность
    # выше средней такой вывод носить не может.
    if any("адаптирован" in s for s in res["sample_quality"]) \
            and res["confidence"] == "HIGH":
        res["confidence"] = "MEDIUM"


def _recommend(res: dict, exp: dict, stat: dict) -> None:
    """Рекомендация по вердикту (§9). Только предложение — решение за владельцем."""
    v = res["verdict"]
    if v == "CONFIRMED":
        targets = expand_candidates(exclude_pages=exp.get("pages") or [],
                                    profile="snippet")
        res["recommendation"] = "EXPAND"
        res["recommended_targets"] = targets
        res["recommendation_detail"] = (
            "применить подтверждённую формулу сниппета к следующим "
            f"{len(targets)} карточкам (по убыванию коммерческого спроса "
            "Вордстата)" if targets else
            "формула подтверждена, но список карточек не собран: нет выгрузки "
            "спроса — кандидатов нужно отобрать вручную")
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


def _formula_group_result(group: str, date: str) -> dict | None:
    """Объединённый z-тест формулы по всем её экспериментам.

    Каждый участник вносит свои matched-наборы в СВОИХ окнах (стар — разные);
    суммируются клики и показы обеих сторон. Возвращается None, пока чистые
    окна есть меньше чем у двух участников.
    """
    import experiments
    today_s = date
    members, sb = [], {"clicks": 0, "impressions": 0}
    se = {"clicks": 0, "impressions": 0}
    for e in experiments.load_registry():
        if (e.get("formula_group") != group
                or e.get("status") not in ("running", "observing")
                or e.get("evaluation_kind", "ctr") != "ctr"):
            continue
        win = st.pick_windows(dt.date.fromisoformat(e["start"]),
                              dt.date.fromisoformat(today_s), e)
        if not win["baseline"] or not win["experiment"]:
            continue
        keys = experiments.cluster_keys(e)
        mb, me = st.matched_sets(
            st._rows_for_cluster(win["baseline"]["queries"], keys),
            st._rows_for_cluster(win["experiment"]["queries"], keys))
        bm, em = st.metrics(mb), st.metrics(me)
        members.append(e.get("ticket", e["id"]))
        sb["clicks"] += bm["clicks"]; sb["impressions"] += bm["impressions"]
        se["clicks"] += em["clicks"]; se["impressions"] += em["impressions"]
    if len(members) < 2:
        return None
    stat = st.two_proportion_test(sb["clicks"], sb["impressions"],
                                  se["clicks"], se["impressions"])
    return {"group": group, "members": members,
            "baseline": sb, "experiment": se, "stat": stat,
            "note": ("объединённая оценка формулы по кластерам участников; "
                     "окна у каждого свои, вердикты участников не подменяет")}


def _apply_group_hint(res: dict) -> None:
    """Подсказка в рекомендацию, когда группа отвечает раньше участника."""
    g = res.get("formula_group_result")
    if not g or res["verdict"] in ("CONFIRMED", "REJECTED"):
        return
    stat = g["stat"]
    p = stat.get("p_value")
    rel = stat.get("relative_uplift")
    if p is not None and p < st.CONFIG["EXPERIMENT_ALPHA"] and (rel or 0) > 0:
        res["recommendation_detail"] = (res["recommendation_detail"] +
            f"; объединённая оценка формулы по группе ({', '.join(g['members'])}): "
            f"рост CTR {_pct(stat['baseline_ctr'])} → {_pct(stat['experiment_ctr'])}"
            f" при p={p:.3f} — решение о тираже формулы можно принимать на группе"
        ).lstrip("; ")


def _pct(v: float | None, raw: bool = False) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.1f}%" if not raw else f"{v * 100:+.0f}%".lstrip("+") + ""


def _signed(v: float | None) -> str:
    return "—" if v is None else f"{v:+.1f}"


# ── EXPAND-кандидаты (§9): следующие страницы для тиражирования ─────────────

def expand_candidates(exclude_pages: list[str], limit: int = 10,
                      profile: str = "snippet") -> list[str]:
    """Страницы для тиражирования приёма — слой `expansion.py`.

    Раньше кандидаты брались сортировкой `src/data/vendor-demand.json`, то есть
    по ОБЩЕЙ частотности бренда; правило 10 отчётности это запрещает, и на
    вердикте CONTENT-001 от 02.09.2026 ошибка стала видна: в цели попали
    Google, Microsoft и Docker — кластеры, где либо спрос не покупательский,
    либо сайта нет в выдаче. Отбор перенесён в `expansion.candidates` и
    разведён по профилям приёма.
    """
    import expansion
    try:
        return expansion.candidate_urls(exclude_pages, limit, profile)
    except Exception:  # noqa: BLE001 — рекомендация не должна ронять письмо
        return []


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
