#!/usr/bin/env python3
"""Query-page mismatch: коммерческий запрос ведёт на некоммерческую страницу.

Если поиск стабильно показывает по запросу «купить/цена/оплата…» статью
блога, служебную страницу или главную — это сигнал архитектуры: либо
коммерческой посадочной нет, либо она недостаточно релевантна. Детектор
наблюдает и предлагает; сами правки идут обычным циклом PR.

Источник — пары «запрос × страница × день» GSC (pairs.py); классификация
интента запроса — та же, что в снимке (snapshot.classify_intent).
"""

from __future__ import annotations

import pairs
from snapshot import classify_intent, is_branded

MIN_IMPRESSIONS = 8      # порог радара возможностей — то же значение
DOMINANT_SHARE = 0.6     # страница «ведёт» запрос с этой доли показов
LIMIT = 15

# Тип страницы по началу пути. Порядок важен: первый совпавший префикс.
PAGE_TYPES = [
    ("/blog", "informational"),
    ("/faq", "service"), ("/about", "service"), ("/contacts", "service"),
    ("/how-we-work", "service"), ("/documents", "service"),
    ("/cases", "service"),
    ("/product/", "product"),
    ("/vendors", "vendor"),
    ("/catalog", "catalog"),
    ("/alternatives", "comparison"), ("/compare", "comparison"),
    ("/solutions", "landing"), ("/pricing", "landing"),
]
# Типы, на которых коммерческий запрос уместен.
COMMERCIAL_TYPES = {"product", "vendor", "catalog", "comparison", "landing"}


def page_type(page: str) -> str:
    if page == "/":
        return "home"
    for prefix, kind in PAGE_TYPES:
        if page.startswith(prefix):
            return kind
    return "other"


def build(date_s: str) -> dict:
    data = pairs.load_latest(date_s)
    if not data:
        return {"available": False,
                "reason": "данных сенсора пар «запрос × страница» за окно нет",
                "items": []}
    agg = pairs.by_query(data["rows"])
    items = []
    for query, q in agg.items():
        if q["impressions"] < MIN_IMPRESSIONS or is_branded(query):
            continue
        if classify_intent(query) != "commercial":
            continue
        page, p = max(q["pages"].items(), key=lambda kv: kv[1]["impressions"])
        kind = page_type(page)
        if kind in COMMERCIAL_TYPES or p["share"] < DOMINANT_SHARE:
            continue
        # Есть ли у запроса коммерческая страница на вторых ролях —
        # тогда задача «передать ей запрос», а не «создать посадочную».
        commercial_alt = next(
            (cp for cp, cv in sorted(q["pages"].items(),
                                     key=lambda kv: -kv[1]["impressions"])
             if page_type(cp) in COMMERCIAL_TYPES and cv["impressions"] > 0),
            None)
        items.append({
            "query": query,
            "impressions": q["impressions"],
            "clicks": q["clicks"],
            "page": page,
            "page_type": kind,
            "share": round(p["share"], 2),
            "avg_position": p["avg_position"],
            "commercial_alt": commercial_alt,
            "recommended_action": (
                f"передать запрос странице {commercial_alt}: ответ на запрос, "
                "заголовок, внутренняя ссылка с {page}".replace("{page}", page)
                if commercial_alt else
                "коммерческой посадочной под запрос нет — кандидат на новую "
                "страницу через квалификацию спроса (гейт анти-doorway)"),
        })
    if not items:
        return {"available": True, "items": [],
                "reason": "коммерческих запросов, ведущих на некоммерческие "
                          "страницы, не найдено",
                "as_of": data["date"], "window": data["window"]}
    items.sort(key=lambda i: -i["impressions"])
    return {"available": True, "items": items[:LIMIT],
            "considered": len(items),
            "as_of": data["date"], "window": data["window"],
            "note": ("данные Google Search Console; интент запроса — та же "
                     "классификация, что в снимке дня")}
