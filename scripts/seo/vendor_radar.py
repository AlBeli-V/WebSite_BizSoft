#!/usr/bin/env python3
"""Радар вендоров поверх канонического снимка.

Перенос полезной аналитики упразднённого intelligence.py (Vendor Demand Radar
и кандидаты PPC-research) на snapshot — единственный источник чисел отчёта.
Прежний слой читал сырые выгрузки напрямую и давал второй ответ на вопросы,
на которые канонический ответ даёт снимок.

Правила методики соблюдаются здесь, а не в тексте письма:
  - показы наших страниц по «вендорным» запросам — интерес аудитории к вендору
    в нашей выдаче, НЕ рыночный спрос (спрос измеряет Вордстат);
  - числа Яндекса и Google не складываются: движки считаются и показываются
    раздельно (ранжирование — по Яндексу как основному объёму);
  - недоступный источник не участвует: радар строится по доступным движкам,
    без обоих движков блок честно отсутствует.

Список вендоров — каталог сайта (src/data/vendors.ts), а не зашитый список:
новый вендор попадает в радар вместе с карточкой на сайте.
"""

from __future__ import annotations

import pathlib
import re

VENDORS_TS = pathlib.Path("src/data/vendors.ts")
MIN_SHOWS = 8          # ниже — шум, а не интерес (порог как в радаре возможностей)
PPC_MIN_SHOWS = 15     # кандидат в платный трафик обязан иметь заметную базу
PPC_POSITION = (3.5, 20.0)   # топ-3 уже работает; глубже 20 показы малоинформативны
EMPTY = {"impressions": 0, "clicks": 0, "queries": 0, "best_position": None}


def catalogue() -> dict[str, list[re.Pattern]]:
    """Вендор каталога → паттерны его упоминания в запросе (slug и имя)."""
    if not VENDORS_TS.exists():
        return {}
    text = VENDORS_TS.read_text(encoding="utf-8")
    out: dict[str, list[re.Pattern]] = {}
    for slug, name in re.findall(r"\{\s*slug:\s*'([^']+)',\s*vendor:\s*'([^']+)'", text):
        tokens = {slug.replace("-", " ").lower(), name.lower()}
        # Границы слова, а не подстрока: «box» не должен присваивать себе
        # запросы про dropbox (тот же принцип, что в отборе вендоров письма).
        out.setdefault(name, []).extend(
            re.compile(r"(?<![a-zа-яё0-9])" + re.escape(t) + r"(?![a-zа-яё0-9])")
            for t in tokens)
    return out


def vendor_of(query: str, cat: dict[str, list[re.Pattern]]) -> str | None:
    low = query.lower()
    for name, pats in cat.items():
        if any(p.search(low) for p in pats):
            return name
    return None


def _query_entities(block: dict) -> list[dict]:
    if not block.get("available"):
        return []
    return [e for e in block.get("entities") or []
            if e.get("entity_type") == "query"]


def build(snap: dict) -> dict:
    """Интерес к вендорам в поиске + кандидаты на проверку платным трафиком."""
    cat = catalogue()
    yx, g = snap.get("yandex") or {}, snap.get("google") or {}
    if not cat:
        return {"available": False, "reason": "каталог вендоров недоступен"}
    if not (yx.get("available") or g.get("available")):
        return {"available": False,
                "reason": "источники поиска не отдали данных"}

    items: dict[str, dict] = {}
    for engine, block in (("yandex", yx), ("google", g)):
        for e in _query_entities(block):
            v = vendor_of(e.get("entity_id", ""), cat)
            if not v:
                continue
            it = items.setdefault(v, {"vendor": v,
                                      "yandex": dict(EMPTY), "google": dict(EMPTY)})
            s = it[engine]
            s["impressions"] += e.get("impressions") or 0
            s["clicks"] += e.get("clicks") or 0
            s["queries"] += 1
            p = e.get("average_position")
            if p is not None and (s["best_position"] is None or p < s["best_position"]):
                s["best_position"] = round(p, 1)

    ranked = [it for it in items.values()
              if it["yandex"]["impressions"] >= MIN_SHOWS
              or it["google"]["impressions"] >= MIN_SHOWS]
    ranked.sort(key=lambda it: (-it["yandex"]["impressions"],
                                -it["google"]["impressions"], it["vendor"]))
    return {
        "available": bool(ranked),
        "reason": None if ranked else "вендорные запросы ниже порога значимости",
        "items": ranked,
        "ppc": ppc_candidates(snap, cat),
        # Коротко: полная методологическая оговорка живёт в карте измерений
        # веб-отчёта, письмо не тратит на неё бюджет слов (issue #168).
        "note": ("Интерес в нашей выдаче, не рыночный спрос "
                 "(его измеряет Вордстат)."),
    }


def ppc_candidates(snap: dict, cat: dict | None = None) -> list[dict]:
    """Коммерческие запросы с базой показов вне топ-3 — кандидаты на проверку
    платным трафиком. Прогнозов ставок и конверсии нет — не выдумываются:
    кандидат несёт только измеренный поисковый сигнал и открытый вопрос."""
    cat = cat if cat is not None else catalogue()
    lo, hi = PPC_POSITION
    seen, out = set(), []
    for e in _query_entities(snap.get("yandex") or {}):
        if e.get("intent") != "commercial" or e.get("branded"):
            continue
        shows, pos = e.get("impressions") or 0, e.get("average_position")
        if shows < PPC_MIN_SHOWS or pos is None or not lo < pos <= hi:
            continue
        v = vendor_of(e.get("entity_id", ""), cat)
        key = v or e["entity_id"]
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "query": e["entity_id"], "vendor": v,
            "shows": shows, "position": round(pos, 1),
            "business_question": (f"приводит ли интент «{e['entity_id']}» "
                                  "платёжеспособных B2B-клиентов"),
        })
    out.sort(key=lambda c: -c["shows"])
    return out[:4]
