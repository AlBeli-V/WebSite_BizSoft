#!/usr/bin/env python3
"""Zero-impression: страницы инвентаря без показов Google — с причиной.

1 000+ карточек не одинаково полезны: страница, месяцами не получающая ни
одного показа, — вопрос к индексации, спросу, названию или перелинковке.
Детектор не генерирует туда тексты вслепую (правило предложения №4): он
классифицирует и отдаёт список на разбор.

Причина берётся из сенсора покрытия индекса (index_coverage.py), когда его
срез есть: статус URL Inspection Google раскладывает страницы без показов на
«URL неизвестен» (вопрос обхода и ссылок), «обнаружен, не сканирован»
(краулинговый бюджет), «сканирован, не в индексе» (качество/дубль — вот
где уместен разбор содержимого), «в индексе без показов» (спрос, название,
сниппет) и технические исключения. Срез Вебмастера по страницам даёт второе
измерение: страница в поиске Яндекса или исключена, и с какой причиной.
Без срезов детектор работает как раньше — общий вердикт «разобрать».

Возраст страницы считается от первой фиксации в инвентаре (url-first-seen):
у страниц старше самого сенсора возраст — нижняя оценка, это помечается.
Показы — только Google (Яндекс разбивку показов по страницам не отдаёт).
"""

from __future__ import annotations

import datetime as dt

import inventory
from mismatch import page_type

YOUNG_DAYS = 14     # моложе — «рано судить», это не находка
OLD_DAYS = 30       # старше без показов — кандидат на разбор
LIMIT = 40

# Вердикт по классу статуса Google: что именно разбирать. Формулировки
# нарочно называют направление работы, а не «улучшить страницу».
VERDICT_BY_CLASS = {
    "unknown": ("Google не знает URL — обход и ссылки (внутренние, внешние), "
                "не тексты"),
    "discovered": ("Google обнаружил, но не сканировал — краулинговый бюджет и "
                   "приоритет обхода"),
    "crawled": ("Google сканировал, но не проиндексировал — качество/дубль, "
                "разбор содержимого"),
    "indexed": "в индексе Google без показов — спрос, название, сниппет",
    "technical": ("техническое исключение Google ({state}) — canonical, "
                  "редирект, noindex"),
}
GENERIC_VERDICT = ("без показов Google — разобрать: индексация / спрос / "
                   "название / перелинковка")
WAIT_VERDICT = "наблюдение: показов нет, срок ещё не вышел"


def _google_status(path: str, gpages: dict) -> dict:
    rec = gpages.get(path) or {}
    state = rec.get("coverage_state")
    return {"class": inventory.google_class(state) if gpages else "no_data",
            "state": state,
            "label": inventory.GOOGLE_CLASS_LABEL[
                inventory.google_class(state) if gpages else "no_data"],
            "last_crawl": (rec.get("last_crawl") or "")[:10] or None,
            "stale_from": rec.get("stale_from")}


def _yandex_status(path: str, yidx: dict | None,
                   in_search: set, excluded: dict) -> dict:
    if yidx is None:
        return {"status": "no_data", "reason": None, "label": "нет данных"}
    if path in in_search:
        return {"status": "in_search", "reason": None, "label": "в поиске"}
    ex = excluded.get(path)
    if ex:
        return {"status": "excluded", "reason": ex.get("status"),
                "label": "исключена: "
                         + inventory.yandex_reason_label(ex.get("status"))}
    return {"status": "absent", "reason": None,
            "label": "не в поиске, причина не зафиксирована"}


def build(date_s: str) -> dict:
    inv = inventory.load_latest(date_s)
    if not inv:
        return {"available": False,
                "reason": "инвентарь sitemap ещё не собран "
                          "(шаг workflow seo-data-collect)",
                "items": []}
    seen = inventory.pages_with_impressions(date_s)
    reg = inventory.first_seen()
    started = reg.get("started")
    date = dt.date.fromisoformat(date_s)

    gidx = inventory.google_index(date_s)
    gpages = (gidx or {}).get("pages") or {}
    yidx = inventory.yandex_index(date_s)
    y_in = set((yidx or {}).get("in_search") or [])
    y_ex = (yidx or {}).get("excluded") or {}

    items, young = [], 0
    g_by_class: dict[str, int] = {}
    y_by_status: dict[str, int] = {}
    y_excluded_by_reason: dict[str, int] = {}
    zero_by_cause: dict[str, int] = {}
    for u in inv["urls"]:
        path = u["path"]
        g = _google_status(path, gpages)
        y = _yandex_status(path, yidx, y_in, y_ex)
        g_by_class[g["class"]] = g_by_class.get(g["class"], 0) + 1
        y_by_status[y["status"]] = y_by_status.get(y["status"], 0) + 1
        if y["status"] == "excluded":
            lbl = inventory.yandex_reason_label(y["reason"])
            y_excluded_by_reason[lbl] = y_excluded_by_reason.get(lbl, 0) + 1
        if path in seen:
            continue
        first = reg["paths"].get(path)
        days = (date - dt.date.fromisoformat(first)).days if first else None
        floor = bool(first and started and first == started)
        if days is not None and days < YOUNG_DAYS and not floor:
            young += 1
            continue        # молодая страница без показов — норма, не находка
        if g["class"] in VERDICT_BY_CLASS:
            verdict = VERDICT_BY_CLASS[g["class"]].format(state=g["state"])
        elif days is not None and days < OLD_DAYS and not floor:
            verdict = WAIT_VERDICT
        else:
            verdict = GENERIC_VERDICT
        zero_by_cause[g["class"]] = zero_by_cause.get(g["class"], 0) + 1
        items.append({
            "path": path,
            "page_type": page_type(path),
            "known_days": days,
            "known_days_is_floor": floor,
            "lastmod": u.get("lastmod"),
            "google_index": g,
            "yandex_index": y,
            "verdict": verdict,
        })
    # Сначала то, что требует разбора содержимого и что уже в индексе, — там
    # действие ближе всего; «неизвестные» URL — одна общая причина, их в хвост.
    cause_rank = {"crawled": 0, "indexed": 1, "technical": 2, "discovered": 3,
                  "no_data": 4, "unknown": 5}
    items.sort(key=lambda i: (cause_rank.get(i["google_index"]["class"], 9),
                              i["page_type"], i["path"]))
    total = len(inv["urls"])
    covered = len([u for u in inv["urls"] if u["path"] in seen])
    by_type: dict[str, int] = {}
    for i in items:
        by_type[i["page_type"]] = by_type.get(i["page_type"], 0) + 1
    g_indexed = g_by_class.get("indexed", 0)
    y_in_inventory = y_by_status.get("in_search", 0)
    return {
        "available": True,
        "as_of": inv["date"],
        "inventory_total": total,
        "with_impressions": covered,
        "coverage_google": round(covered / total, 3) if total else None,
        "young_skipped": young,
        "zero_total": len(items),
        "by_type": by_type,
        "by_cause": zero_by_cause,
        "index_google": {
            "available": bool(gpages),
            "as_of": (gidx or {}).get("as_of"),
            "indexed": g_indexed,
            "coverage_indexed": round(g_indexed / total, 3) if total and gpages else None,
            "by_class": g_by_class,
            "inspected": (gidx or {}).get("inspected"),
            "inherited": (gidx or {}).get("inherited"),
        },
        "index_yandex": {
            "available": yidx is not None,
            "as_of": (yidx or {}).get("as_of"),
            "in_search": y_in_inventory,
            "coverage": round(y_in_inventory / total, 3) if total and yidx else None,
            "in_search_host_total": (yidx or {}).get("in_search_count"),
            "by_status": y_by_status,
            "excluded_by_reason": y_excluded_by_reason,
        },
        "items": items[:LIMIT],
        "note": ("показы — Google Search Console (окно 28 дней); статус "
                 "индекса — URL Inspection Google и выборки Вебмастера по "
                 "страницам; возраст — от первой фиксации в инвентаре, у "
                 "страниц старше сенсора это нижняя оценка"),
    }
