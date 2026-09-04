#!/usr/bin/env python3
"""Расширение каталога: каких вендоров добавить на сайт.

Вордстат работает на две задачи. Первая — улучшать семантику существующих
карточек. Вторая — показывать, какие товары люди массово ищут, а у нас их нет.
Этот модуль отвечает за вторую.

Кандидаты — зарубежные разработчики ПО и сервисов. Российские исключены
осознанно: их лицензии продаются напрямую, и услуга оплаты из-за рубежа
к ним неприменима.

Приоритет — по покупательскому спросу от большего к меньшему, с поправкой на
трудоёмкость запуска: карточка одного продукта дешевле, чем целая линейка.
Для каждого кандидата готовится SEO-обвязка: адрес, заголовок, описание,
темы вопросов и целевые фразы — чтобы страницу можно было создать сразу.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import audience                    # noqa: E402

import discovery as D  # noqa: E402
import normalize as N  # noqa: E402

CANDIDATES_PATH = pathlib.Path("reports/seo/wordstat/vendor-candidates.json")
PAYMENT_PATH = pathlib.Path("reports/seo/wordstat/payment-check.json")
MIN_DEMAND = 100          # ниже — кандидат не выносится в рекомендации
MIN_COMMERCIAL = 30       # минимум покупательского спроса


# Что делать с вендором в зависимости от того, как у него устроена покупка.
PAYMENT_ACTION = {
    "card": ("рекомендуем добавить",
             "оплата картой на сайте вендора — сделка выполнима сразу"),
    "likely_card": ("рекомендуем добавить с проверкой",
                    "цены и покупка на сайте есть, платёжная система не опознана — "
                    "подтвердить при первой сделке"),
    "sales_only": ("требует решения",
                   "покупка только через отдел продаж: нужен договор с вендором, "
                   "это другая модель работы"),
    "unknown": ("проверить вручную",
                "признаков оплаты на странице тарифов не найдено"),
    "unreachable": ("проверить вручную",
                    "страница тарифов не открылась при автоматической проверке"),
    "not_checked": ("проверить вручную", "оплата не проверена"),
}


# Список брендов-омонимов один на систему и живёт в normalize: там же по нему
# отсеиваются чужие фразы при сборе. Здесь он нужен, чтобы пометить оставшийся
# спрос низкой достоверностью — фильтр строгий, но не безошибочный.
AMBIGUOUS_BRANDS = N.AMBIGUOUS_BRANDS


def demand_confidence(brand: str, phrases: list[dict]) -> tuple[str, str | None]:
    """Насколько цифре спроса можно верить."""
    if brand.lower() in AMBIGUOUS_BRANDS:
        return "низкая", ("имя бренда — обычное английское слово, в выборку "
                          "попадают запросы про другие товары; проверить выдачу "
                          "вручную перед решением")
    if len(phrases) < 3:
        return "средняя", "спрос подтверждён менее чем тремя фразами"
    return "высокая", None


def load_payments() -> dict:
    if not PAYMENT_PATH.exists():
        return {}
    return json.loads(PAYMENT_PATH.read_text(encoding="utf-8"))


def load_candidates() -> dict:
    if not CANDIDATES_PATH.exists():
        return {"candidates": [], "russian_vendors": [], "template": "{brand} купить"}
    return json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))


def is_russian(brand: str, russian: list[str]) -> bool:
    low = N.normalize(brand)
    return any(r in low or low in r for r in russian)


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9\u0430-\u044f]+", N.normalize(text)) if w]


def already_in_catalogue(brand: str, vendors: list[dict],
                         product_of: dict | None = None) -> bool:
    """Есть ли этот бренд на сайте — сам по себе или как продукт нашего вендора.

    Сравнение идёт по целым словам. Подстрока обманывает: «rive» сидит внутри
    «pipedrive», «sketch» внутри «sketchup», «audio» содержит «udio» — по такому
    совпадению система вычёркивала кандидатов, которых на сайте нет.

    Продукт вендора из каталога тоже считается закрытым вопросом: AutoCAD — это
    Autodesk, Cinema 4D — Maxon, канал закупки по ним уже отработан.
    """
    brand_words = _words(brand)
    if not brand_words:
        return False
    parent = (product_of or {}).get(brand.lower())
    for v in vendors:
        names = (v["anchor"], v["slug"].replace("-", " "), v["vendor"])
        for name in names:
            name_words = _words(name)
            if not name_words:
                continue
            if name_words == brand_words:
                return True
            # Многословное имя вендора внутри названия продукта: «adobe stock».
            if len(name_words) > 1 and _contains(brand_words, name_words):
                return True
            if len(name_words) == 1 and name_words[0] in brand_words:
                return True
        if parent and _words(parent) in ([_words(n) for n in names]):
            return True
    return False


def _contains(haystack: list[str], needle: list[str]) -> bool:
    n = len(needle)
    return any(haystack[i:i + n] == needle for i in range(len(haystack) - n + 1))


def pending(vendors: list[dict], universe) -> list[dict]:
    """Кандидаты, которых нет в каталоге и которые ещё не измерены."""
    cfg = load_candidates()
    russian = cfg.get("russian_vendors", [])
    product_of = cfg.get("product_of", {})
    template = cfg.get("template", "{brand} купить")
    out = []
    for item in cfg.get("candidates", []):
        brand = item["brand"] if isinstance(item, dict) else item
        if is_russian(brand, russian) or already_in_catalogue(brand, vendors, product_of):
            continue
        # Решение руководителя и аудитория сервиса. Возвращать в отчёт то, по
        # чему решение принято, значит заставлять принимать его заново каждый
        # день; предлагать юрлицам сервис для частных лиц — мерить спрос по
        # аудитории, которой мы не продаём.
        if audience.skip_reason(brand):
            continue
        phrase = template.format(brand=brand)
        out.append({"brand": brand, "phrase": phrase,
                    "kind": item.get("kind") if isinstance(item, dict) else None,
                    "measured": universe.get(phrase) is not None})
    return out


def slugify(brand: str) -> str:
    s = N.normalize(brand)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "vendor"


def seo_scaffold(brand: str, phrases: list[dict]) -> dict:
    """Заготовка SEO-обвязки: то, что понадобится при создании страницы."""
    name = brand.title() if brand.islower() else brand
    slug = slugify(brand)
    targets = [p["phrase"] for p in phrases[:8]]
    subclusters = sorted({N.subcluster_of(p["phrase"]) for p in phrases[:20]})
    return {
        "url": f"/vendors/{slug}",
        "title": f"Оплата {name} для юридических лиц из России — счёт, договор, ЭДО | BIZSoft",
        "description": (f"Оплатим подписку {name} на вашу компанию в рублях по счёту. "
                        "Договор, закрывающие документы через ЭДО, доступ за 1–3 дня."),
        "h1": f"{name} для юридических лиц",
        "faq_topics": [
            f"Как купить {name} на юрлицо — по счёту и договору?",
            "Какие закрывающие документы вы предоставляете?",
            f"Как быстро появится доступ к {name} после оплаты?",
            "В какой валюте оплата и как считается цена?",
        ],
        "target_phrases": targets,
        "needed_subclusters": subclusters,
        "internal_links": ["/catalog", "/blog/kak-kupit-zarubezhnoe-po-dlya-yurlica"],
    }


def effort_of(phrases: list[dict]) -> tuple[float, str]:
    """Трудоёмкость запуска: одна карточка или линейка продуктов."""
    products = {N.subcluster_of(p["phrase"]) for p in phrases[:30]}
    if len(products) >= 5:
        return 3.0, "линейка тарифов: нужна карточка и разбивка по планам"
    if len(products) >= 3:
        return 2.0, "карточка с несколькими вариантами покупки"
    return 1.0, "одна карточка вендора"


def build(universe, vendors: list[dict], limit: int = 10) -> dict:
    """Рекомендации по расширению каталога, отсортированные по спросу."""
    cfg = load_candidates()
    russian = cfg.get("russian_vendors", [])
    product_of = cfg.get("product_of", {})
    template = cfg.get("template", "{brand} купить")
    payments = load_payments()
    rows = []

    for item in cfg.get("candidates", []):
        brand = item["brand"] if isinstance(item, dict) else item
        kind = item.get("kind") if isinstance(item, dict) else None
        if is_russian(brand, russian) or already_in_catalogue(brand, vendors, product_of):
            continue
        # Решение руководителя и аудитория сервиса. Возвращать в отчёт то,
        # по чему решение принято, значит заставлять принимать его заново
        # каждый день; предлагать юрлицам сервис для частных лиц — мерить
        # спрос по аудитории, которой мы не продаём.
        if audience.skip_reason(brand):
            continue
        seed = template.format(brand=brand)
        related = [r for r in universe.rows.values()
                   if r.get("source_seed") == seed and r.get("in_scope") is not False]
        if not related:
            continue
        commercial = sorted(
            [{"phrase": r["phrase"], "frequency": r.get("wordstat_frequency") or 0}
             for r in related if r.get("intent") == "commercial"],
            key=lambda p: -p["frequency"])
        total = sum(r.get("wordstat_frequency") or 0 for r in related)
        commercial_demand = sum(p["frequency"] for p in commercial)
        if total < MIN_DEMAND or commercial_demand < MIN_COMMERCIAL:
            continue
        effort, effort_note = effort_of(commercial)
        confidence, confidence_note = demand_confidence(brand, commercial)
        trend = universe.trend(commercial[0]["phrase"]) if commercial else {"direction": "unknown"}
        pay = payments.get(brand) or {"verdict": "not_checked",
                                      "note": "оплата не проверена"}
        action, why = PAYMENT_ACTION.get(pay["verdict"], PAYMENT_ACTION["not_checked"])
        rows.append({
            "brand": brand,
            "kind": kind,
            "payment": {"verdict": pay["verdict"], "note": pay.get("note"),
                        "url": pay.get("url"), "checked_at": pay.get("checked_at")},
            "recommendation": action,
            "recommendation_why": why,
            "total_demand": total,
            "commercial_demand": commercial_demand,
            "commercial_phrases": len(commercial),
            "top_phrases": commercial[:5],
            "trend": trend["direction"],
            "effort": effort,
            "effort_note": effort_note,
            "demand_confidence": confidence,
            "demand_confidence_note": confidence_note,
            "priority_score": round(commercial_demand / effort, 1),
            "seo": seo_scaffold(brand, commercial or [{"phrase": seed}]),
            "measured_at": max((r.get("last_seen") or "") for r in related),
        })

    # Сначала те, где покупка выполнима сразу: спрос без возможности оплатить
    # не превращается в сделку. Внутри группы — по приоритету спроса.
    order = {"card": 0, "likely_card": 1, "not_checked": 2, "unknown": 2,
             "unreachable": 2, "sales_only": 3}
    rows.sort(key=lambda r: (order.get(r["payment"]["verdict"], 2),
                             r["demand_confidence"] == "низкая",
                             -r["priority_score"]))
    measured = sum(1 for c in pending(vendors, universe) if c["measured"])
    total_candidates = len(pending(vendors, universe))
    return {
        "available": bool(rows),
        "reason": None if rows else "рекомендовать некого: спрос кандидатов не измерен или ниже порогов",
        "candidates_total": total_candidates,
        "candidates_measured": measured,
        "recommended": rows[:limit],
        "recommended_total": len(rows),
        "combined_demand": sum(r["commercial_demand"] for r in rows),
        "by_payment": {v: sum(1 for r in rows if r["payment"]["verdict"] == v)
                       for v in sorted({r["payment"]["verdict"] for r in rows})},
        "by_kind": {k: sum(1 for r in rows if r["kind"] == k)
                    for k in sorted({r["kind"] for r in rows if r["kind"]})},
        "low_confidence": [r["brand"] for r in rows
                           if r["demand_confidence"] == "низкая"],
        "needs_manual_check": [r["brand"] for r in rows
                               if r["payment"]["verdict"] in
                               ("unknown", "unreachable", "not_checked")][:10],
        "note": "Российские вендоры исключены: их лицензии продаются напрямую, "
                "услуга оплаты из-за рубежа к ним неприменима.",
    }
