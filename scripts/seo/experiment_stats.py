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

Фиксированные окна (перезапуск SEO-EXP-002, 03.09.2026). Скользящие
выгрузки дали два дефекта: baseline брался из усечённой выгрузки (до 23.08
сборщик забирал только топ-100 из ~450 запросов — «23 показа → 100» был
артефактом глубины выгрузки), а окно после внедрения ограничивалось
~12 днями и не росло. API Вебмастера принимает произвольные date_from/
date_to, поэтому реестр может задать окна явно (`windows`), а сборщик
experiment_windows.py выгружает их полным обходом в
yandex-window-<from>_<to>.json. Такие файлы имеют приоритет над выбором из
ежедневных выгрузок; окна равной длины (по умолчанию 28 дней) сравниваются
как есть.
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
    # Адаптация гейта под малые кластеры (вопрос руководителя 31.08.2026).
    # Окно Вебмастера скользящее: показы кластера за окно примерно постоянны,
    # и кластер с ёмкостью ниже гейта не наберёт его НИКОГДА — ждать
    # бессмысленно. Для таких кластеров гейт снижается до доли ёмкости окна
    # (не ниже пола), адаптация помечается, уверенность ограничивается, а
    # минимально различимый эффект (MDE) показывается явно.
    "EXPERIMENT_MIN_IMPRESSIONS_FLOOR": 100,
    "EXPERIMENT_ADAPTIVE_GATE_SHARE": 0.7,
    # Мощность для оценки MDE (какой рост CTR вообще различим при выборке).
    "EXPERIMENT_MDE_POWER_Z": 0.8416,   # z для мощности 80%
    "EXPERIMENT_MDE_ALPHA_Z": 1.9600,   # z для двустороннего alpha=0.05
    # Фиксированные окна: длина каждого окна и лаг источника (данные за день
    # устаиваются у Вебмастера примерно трое суток — окно baseline
    # заканчивается за лаг до старта, окно после внедрения выгружается,
    # когда прошёл лаг после его конца).
    "EXPERIMENT_WINDOW_DAYS": 28,
    "EXPERIMENT_SOURCE_LAG_DAYS": 3,
}


def effective_gate(window_capacity: int | None, need: int, cfg: dict | None = None) -> tuple[int, bool]:
    """Эффективный гейт экспозиции: (порог, адаптирован ли).

    Если ёмкость окна кластера ниже настроенного гейта, ждать набора
    бессмысленно (окно скользящее) — гейт снижается до доли ёмкости,
    но не ниже пола: меньше пола любой вывод — шум.
    """
    cfg = cfg or CONFIG
    if window_capacity is None or window_capacity >= need:
        return need, False
    adapted = max(cfg["EXPERIMENT_MIN_IMPRESSIONS_FLOOR"],
                  round(window_capacity * cfg["EXPERIMENT_ADAPTIVE_GATE_SHARE"]))
    return min(need, adapted), True


def min_detectable_uplift(p_base: float | None, n_base: int, n_exp: int,
                          cfg: dict | None = None) -> float | None:
    """Минимально различимый относительный рост CTR при данных выборках.

    Нормальное приближение (alpha 0.05 двусторонний, мощность 80%): честный
    ответ «какой эффект этот эксперимент способен увидеть в принципе».
    """
    cfg = cfg or CONFIG
    if not p_base or not n_base or not n_exp:
        return None
    z = cfg["EXPERIMENT_MDE_ALPHA_Z"] + cfg["EXPERIMENT_MDE_POWER_Z"]
    delta = z * math.sqrt(p_base * (1 - p_base) * (1 / n_base + 1 / n_exp))
    return delta / p_base


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


# ── Фиксированные окна ──────────────────────────────────────────────────────

def window_path(w_from: str, w_to: str) -> pathlib.Path:
    """Файл выгрузки Вебмастера за фиксированное окно."""
    return DATA_DIR / f"yandex-window-{w_from}_{w_to}.json"


def load_window(w_from: str, w_to: str) -> dict | None:
    """Выгрузка за фиксированное окно в том же виде, что у _load_day."""
    p = window_path(w_from, w_to)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    pq = d.get("popular_queries") or {}
    if pq.get("error") or not pq.get("queries"):
        return None
    return {"file_date": d.get("date") or w_to, "from": pq.get("date_from") or w_from,
            "to": pq.get("date_to") or w_to, "queries": pq["queries"], "fixed": True}


def plan_windows(start: dt.date, cfg: dict | None = None) -> dict:
    """Окна baseline/experiment от даты старта: равной длины, без лага источника.

    baseline заканчивается за лаг до старта (последние дни перед стартом у
    Вебмастера ещё не устоялись в момент активации), experiment начинается
    на следующий день после старта (выкат шёл в течение дня старта).
    """
    cfg = cfg or CONFIG
    days = cfg["EXPERIMENT_WINDOW_DAYS"]
    lag = cfg["EXPERIMENT_SOURCE_LAG_DAYS"]
    clean = cfg["CLEAN_WINDOW_STARTS_DAYS_AFTER"]
    b_to = start - dt.timedelta(days=lag + 1)
    b_from = b_to - dt.timedelta(days=days - 1)
    e_from = start + dt.timedelta(days=clean)
    e_to = e_from + dt.timedelta(days=days - 1)
    return {"days": days,
            "baseline": {"from": b_from.isoformat(), "to": b_to.isoformat()},
            "experiment": {"from": e_from.isoformat(), "to": e_to.isoformat()}}


def window_ready(window: dict, today: dt.date, cfg: dict | None = None) -> bool:
    """Окно можно выгружать: его последний день устоялся у источника."""
    cfg = cfg or CONFIG
    lag = cfg["EXPERIMENT_SOURCE_LAG_DAYS"]
    return dt.date.fromisoformat(window["to"]) + dt.timedelta(days=lag) <= today


def pick_windows(start: dt.date, today: dt.date, exp: dict | None = None) -> dict:
    """Выбрать выгрузки baseline и experiment для эксперимента с датой старта.

    baseline: последняя выгрузка, чьё окно закончилось ДО старта.
    experiment: свежайшая выгрузка, чьё окно началось ПОСЛЕ старта
    (окно, начинающееся в сам день старта, допускается с пометкой tainted:
    выкат шёл в течение дня, и часть окна могла увидеть старый вариант).

    Если реестр эксперимента (`exp`) задаёт фиксированные окна и их выгрузки
    уже лежат в каталоге данных, они имеют приоритет: полный обход без
    усечения и без пересечения с периодом до внедрения.
    """
    windows = _pick_rolling_windows(start, today)
    fixed = {"baseline": False, "experiment": False}
    planned = (exp or {}).get("windows") or {}
    if planned.get("baseline"):
        w = load_window(planned["baseline"]["from"], planned["baseline"]["to"])
        if w:
            windows["baseline"], fixed["baseline"] = w, True
    if planned.get("experiment"):
        w = load_window(planned["experiment"]["from"], planned["experiment"]["to"])
        if w:
            windows["experiment"], fixed["experiment"] = w, True
            windows["experiment_tainted"] = False
            windows["clean_experiment_eta"] = None
        elif windows["experiment"] is None or windows["experiment_tainted"]:
            # Чистое окно появится не раньше, чем устоится его последний день.
            eta = (dt.date.fromisoformat(planned["experiment"]["to"])
                   + dt.timedelta(days=CONFIG["EXPERIMENT_SOURCE_LAG_DAYS"]))
            windows["fixed_experiment_eta"] = eta.isoformat()
    windows["fixed"] = fixed
    windows["planned"] = planned or None
    return windows


def _pick_rolling_windows(start: dt.date, today: dt.date) -> dict:
    """Прежний выбор окон из ежедневных скользящих выгрузок."""
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


def interim_comparison(keys, start: dt.date, today: dt.date,
                       exp: dict | None = None) -> dict | None:
    """Предварительное сравнение «старый → новый» до появления чистого окна.

    Вопрос руководителя 31.08.2026: письмо обязано показывать, как идёт
    эксперимент, а не молчать до чистого окна. baseline — как в pick_windows;
    текущее окно — свежайшая доступная выгрузка, даже если она пересекает
    период до внедрения. Пересечение окон исключает статистический вывод,
    поэтому здесь нет p-value, а результат помечается предварительным:
    он отвечает «как идёт», а не «доказано ли».
    """
    windows = pick_windows(start, today, exp)
    base = windows["baseline"]
    current = None
    for date in reversed(_available_dates()):
        if date > today.isoformat():
            continue
        day = _load_day(date)
        if day and day["from"] and day["to"]:
            current = day
            break
    if not base or not current:
        return None
    base_rows = _rows_for_cluster(base["queries"], keys)
    cur_rows = _rows_for_cluster(current["queries"], keys)
    bm, cm = metrics(base_rows), metrics(cur_rows)
    w_from = dt.date.fromisoformat(current["from"])
    w_to = dt.date.fromisoformat(current["to"])
    window_days = (w_to - w_from).days + 1
    post_days = max(0, min((w_to - start).days, window_days))
    caveats = []
    if len(base["queries"]) < 200 and not base.get("fixed"):
        caveats.append(f"базовое окно из усечённой выгрузки "
                       f"({len(base['queries'])} запросов) — клики занижены")
    if base.get("fixed"):
        caveats.append("базовое окно фиксированное (полная выгрузка "
                       f"{base['from']}–{base['to']}); текущее — скользящее, "
                       "окна разной длины сравниваются по CTR, не по показам")
    if post_days < window_days:
        caveats.append(f"текущее окно пересекает период до внедрения: "
                       f"{post_days} из {window_days} дней — после")
    rel = None
    if bm["ctr"] and cm["ctr"] is not None:
        rel = (cm["ctr"] - bm["ctr"]) / bm["ctr"]
    return {
        "preliminary": True,
        "baseline": {"from": base["from"], "to": base["to"], **bm},
        "current": {"from": current["from"], "to": current["to"], **cm,
                    "post_days": post_days, "window_days": window_days},
        "relative_uplift": rel,
        "caveats": caveats,
    }


# ── Метрики по набору запросов ──────────────────────────────────────────────

def _rows_for_cluster(queries: list[dict], keys) -> list[dict]:
    """Запросы кластера эксперимента по ключам атрибуции.

    Привязки запрос→страница у Вебмастера нет; ключи строит
    experiments.cluster_keys (маркеры/исключения/интент из реестра), поэтому
    охваты письма и вердикта совпадают. Это оценка, и она так и подписывается.
    Список строк (наследие: голые slug) принимается для совместимости.
    """
    if isinstance(keys, (list, tuple, set)):
        keys = {"any": sorted({s.replace("-", " ") for s in keys} | set(keys)),
                "exclude": [], "intent_any": []}
    import experiments
    return [q for q in queries
            if experiments.query_matches(q.get("query_text") or "", keys)]


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
