#!/usr/bin/env python3
"""Статистический слой оценки SEO-экспериментов (данные → числа, без выводов).

Задание руководителя 30.08.2026: вердикт эксперимента должен быть доказуемым.
Этот модуль отвечает только за данные и математику: окна baseline/experiment,
matched query set, метрики, two-proportion z-test. Никаких вердиктов и
рекомендаций здесь нет — они в experiment_verdict.py; рендер — в письме.

Ключевое ограничение источника (проверено по фактическим данным 30.08):
у Яндекс.Вебмастера НЕТ дневных рядов по запросам — каждая ежедневная
выгрузка yandex-<дата>.json это скользящий агрегат ~13 дней с лагом ~3 дня.
Поэтому окна строятся выбором выгрузок: baseline — последняя выгрузка, чьё
окно целиком до старта; experiment — свежайшая, чьё окно после старта.
Окна не пересекаются, поэтому сравнение двух binomial-пропорций корректно
без дневной разбивки. Пока чистого experiment-окна нет, слой честно
возвращает его отсутствие и дату, когда окно очистится.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import pathlib

DATA_DIR = pathlib.Path("reports/seo/data")

# ── Конфигурация (задание §4/§7: не хардкодить пороги в бизнес-логике) ──────
CONFIG = {
    # Минимальная экспозиция каждой стороны — гейт для попытки вывода (§5).
    "EXPERIMENT_MIN_BASELINE_IMPRESSIONS": 500,
    "EXPERIMENT_MIN_POST_IMPRESSIONS": 500,
    # Порог значимости двустороннего z-теста (§4).
    "EXPERIMENT_ALPHA": 0.05,
    # Минимум совпавших запросов, чтобы matched-CTR считался репрезентативным (§2).
    "EXPERIMENT_MIN_MATCHED_QUERIES": 5,
    # Насколько позиция может сместиться, чтобы рост CTR считался «чистым» (§3).
    "MAX_POSITION_DELTA_FOR_CLEAN_RESULT": 1.0,
    # Минимальный бизнес-эффект: относительный рост CTR ниже — не масштабируем (§7).
    "EXPERIMENT_MIN_RELATIVE_UPLIFT": 0.10,
    # Сколько дней после старта окно выгрузки считается «загрязнённым», если
    # захватывает сам день внедрения (выкат шёл в течение дня).
    "CLEAN_WINDOW_STARTS_DAYS_AFTER": 1,
}


# ── Окна из выгрузок Вебмастера ─────────────────────────────────────────────

def _load_day(date: str) -> dict | None:
    p = DATA_DIR / f"yandex-{date}.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    pq = d.get("popular_queries") or {}
    if not pq.get("queries"):
        return None
    return {"file_date": date, "from": pq.get("date_from"), "to": pq.get("date_to"),
            "queries": pq["queries"]}


def _available_dates() -> list[str]:
    return sorted(p.name[len("yandex-"):-len(".json")]
                  for p in DATA_DIR.glob("yandex-????-??-??.json"))


def pick_windows(start: dt.date, today: dt.date) -> dict:
    """Выбрать выгрузки baseline и experiment для эксперимента с датой старта.

    baseline: последняя выгрузка, чьё окно закончилось ДО старта.
    experiment: свежайшая выгрузка, чьё окно началось ПОСЛЕ старта
    (окно, начинающееся в сам день старта, допускается с пометкой tainted:
    выкат шёл в течение дня, и часть окна могла увидеть старый вариант).
    """
    base = exp = None
    exp_tainted = False
    for date in _available_dates():
        if date > today.isoformat():
            continue
        day = _load_day(date)
        if not day or not day["from"] or not day["to"]:
            continue
        w_from = dt.date.fromisoformat(day["from"])
        w_to = dt.date.fromisoformat(day["to"])
        if w_to < start:
            if base is None or day["file_date"] > base["file_date"]:
                base = day
        clean_from = start + dt.timedelta(
            days=CONFIG["CLEAN_WINDOW_STARTS_DAYS_AFTER"])
        if w_from >= clean_from:
            exp, exp_tainted = day, False
        elif w_from >= start and (exp is None or exp_tainted):
            exp, exp_tainted = day, True
    # Когда чистое окно появится: лаг источника ~3 дня, окно должно начаться
    # после старта — оцениваем по фактическому сдвигу последней выгрузки.
    clean_eta = None
    if exp is None or exp_tainted:
        last = _load_day(_available_dates()[-1]) if _available_dates() else None
        if last and last["from"]:
            lag = (dt.date.fromisoformat(last["file_date"])
                   - dt.date.fromisoformat(last["from"])).days
            clean_eta = (start + dt.timedelta(
                days=CONFIG["CLEAN_WINDOW_STARTS_DAYS_AFTER"] + lag)).isoformat()
    return {"baseline": base, "experiment": exp,
            "experiment_tainted": exp_tainted, "clean_experiment_eta": clean_eta}


# ── Метрики по набору запросов ──────────────────────────────────────────────

def _rows_for_cluster(queries: list[dict], slugs: list[str]) -> list[dict]:
    """Запросы кластера эксперимента: содержат имя вендора страницы.

    Привязки запрос→страница у Вебмастера нет; используется та же эвристика,
    что и в экспозиции письма (experiments.impressions_for_pages), поэтому
    охваты письма и вердикта совпадают. Это оценка, и она так и подписывается.
    """
    keys = {s.replace("-", " ") for s in slugs} | set(slugs)
    out = []
    for q in queries:
        text = (q.get("query_text") or "").lower()
        if any(k in text for k in keys):
            out.append(q)
    return out


def metrics(rows: list[dict]) -> dict:
    imp = sum(int(q["indicators"].get("TOTAL_SHOWS") or 0) for q in rows)
    clicks = sum(int(q["indicators"].get("TOTAL_CLICKS") or 0) for q in rows)
    wpos_num = sum((q["indicators"].get("AVG_SHOW_POSITION") or 0.0)
                   * (q["indicators"].get("TOTAL_SHOWS") or 0) for q in rows)
    return {
        "impressions": imp,
        "clicks": clicks,
        "ctr": (clicks / imp) if imp else None,
        "avg_position": (wpos_num / imp) if imp else None,
        "queries": len(rows),
    }


def matched_sets(base_rows: list[dict], exp_rows: list[dict]) -> tuple[list, list]:
    """Пары строк по запросам, присутствующим в обоих окнах (§2)."""
    base_by = {q["query_text"]: q for q in base_rows if q.get("query_text")}
    exp_by = {q["query_text"]: q for q in exp_rows if q.get("query_text")}
    common = sorted(set(base_by) & set(exp_by))
    return [base_by[t] for t in common], [exp_by[t] for t in common]


# ── Two-proportion z-test (§4) ──────────────────────────────────────────────

def two_proportion_test(clicks_a: int, imp_a: int,
                        clicks_b: int, imp_b: int) -> dict:
    """Двусторонний z-тест равенства двух binomial-пропорций (CTR).

    Нормальное приближение с pooled-оценкой; p-value через erfc — без
    внешних зависимостей (в CI конвейера нет scipy). При нулевых или
    вырожденных выборках тест честно возвращает p_value=None.
    """
    out = {
        "baseline_ctr": (clicks_a / imp_a) if imp_a else None,
        "experiment_ctr": (clicks_b / imp_b) if imp_b else None,
        "absolute_uplift": None, "relative_uplift": None,
        "z": None, "p_value": None,
        "sample_sizes": {"baseline": imp_a, "experiment": imp_b},
    }
    if not imp_a or not imp_b:
        return out
    p1, p2 = clicks_a / imp_a, clicks_b / imp_b
    out["absolute_uplift"] = p2 - p1
    out["relative_uplift"] = ((p2 - p1) / p1) if p1 > 0 else None
    pooled = (clicks_a + clicks_b) / (imp_a + imp_b)
    se = math.sqrt(pooled * (1 - pooled) * (1 / imp_a + 1 / imp_b))
    if se == 0:
        # Обе стороны без кликов (или все показы кликнуты): различий нет.
        out["z"], out["p_value"] = 0.0, 1.0
        return out
    z = (p2 - p1) / se
    out["z"] = z
    out["p_value"] = math.erfc(abs(z) / math.sqrt(2))
    return out
