#!/usr/bin/env python3
"""Чтение инвентаря URL (sitemap) и страниц с показами — слой этапа 2.

Инвентарь пишет sitemap_inventory.py (workflow seo-data-collect); здесь —
загрузка последней выгрузки, реестра first-seen и множества страниц, у
которых есть показы в Google (пары + разрез page). Поверх этого работают
zero_impression.py и lifecycle.py.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib

import pairs

DATA_DIR = pathlib.Path("reports/seo/data")
LOOKBACK_DAYS = 7


def load_latest(date_s: str) -> dict | None:
    """Последний инвентарь sitemap не старше LOOKBACK_DAYS."""
    date = dt.date.fromisoformat(date_s)
    for back in range(LOOKBACK_DAYS + 1):
        d = (date - dt.timedelta(days=back)).isoformat()
        p = DATA_DIR / f"sitemap-{d}.json"
        if not p.exists():
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if raw.get("error") or not raw.get("urls"):
            continue
        return {"date": d, "urls": raw["urls"], "count": raw.get("count")}
    return None


def first_seen() -> dict:
    """Реестр «путь → дата первой фиксации в инвентаре»."""
    p = DATA_DIR / "url-first-seen.json"
    if not p.exists():
        return {"paths": {}, "started": None}
    try:
        reg = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"paths": {}, "started": None}
    reg.setdefault("paths", {})
    return reg


def pages_with_impressions(date_s: str) -> set[str]:
    """Страницы с показами Google за окно 28 дней: пары + разрез page.

    Оба источника — выборки одного GSC; объединение даёт самое полное из
    доступного. Яндекс разбивку по страницам не отдаёт — покрытие считается
    только по Google, и потребители обязаны называть это явно.
    """
    seen: set[str] = set()
    data = pairs.load_latest(date_s)
    if data:
        seen |= {r["page"] for r in data["rows"] if r["impressions"] > 0}
    date = dt.date.fromisoformat(date_s)
    for back in range(LOOKBACK_DAYS + 1):
        d = (date - dt.timedelta(days=back)).isoformat()
        p = DATA_DIR / f"gsc-{d}.json"
        if not p.exists():
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for r in ((raw.get("analytics") or {}).get("page") or {}).get("rows", []):
            if (r.get("impressions") or 0) > 0 and r.get("keys"):
                seen.add((r["keys"][0] or "").replace(pairs.SITE, "") or "/")
        break
    return seen


# ── Покрытие индекса по страницам (сенсор index_coverage.py) ─────────────────
#
# До сенсора «Index Efficiency» складывалась из двух несопоставимых чисел:
# у Google — страницы с показами, у Яндекса — счётчик searchable_pages_count
# из сводки хоста. Файлы index-google-<дата>.json и index-yandex-<дата>.json
# дают статус каждой страницы инвентаря; здесь — их загрузка и единая
# классификация, чтобы потребители не разбирали строки API сами.

def _load_latest(prefix: str, date_s: str) -> dict | None:
    date = dt.date.fromisoformat(date_s)
    for back in range(LOOKBACK_DAYS + 1):
        d = (date - dt.timedelta(days=back)).isoformat()
        p = DATA_DIR / f"{prefix}-{d}.json"
        if not p.exists():
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if raw.get("error"):
            continue
        return {**raw, "as_of": d}
    return None


def google_index(date_s: str) -> dict | None:
    """Последний срез URL Inspection: {'pages': {путь: {coverage_state, ...}}}."""
    raw = _load_latest("index-google", date_s)
    if not raw or not raw.get("pages"):
        return None
    return raw


def yandex_index(date_s: str) -> dict | None:
    """Последний срез Вебмастера по страницам: in_search (список путей) и
    excluded ({путь: {status, date}})."""
    raw = _load_latest("index-yandex", date_s)
    if not raw or raw.get("in_search") is None:
        return None
    return raw


# Классы статуса Google по строке coverageState из URL Inspection. Порядок
# важен: «Indexed, not submitted in sitemap» содержит «not», а «Submitted
# and indexed» — «indexed»; сначала проверяются точные признаки.
GOOGLE_CLASS_LABEL = {
    "indexed": "в индексе",
    "unknown": "URL неизвестен Google",
    "discovered": "обнаружен, не сканирован",
    "crawled": "сканирован, не в индексе",
    "technical": "техническое исключение",
    "no_data": "нет данных инспекции",
}


def google_class(state: str | None) -> str:
    if not state:
        return "no_data"
    s = state.lower()
    if "unknown to google" in s:
        return "unknown"
    if s.startswith("discovered"):
        return "discovered"
    if s.startswith("crawled"):
        return "crawled"
    if "indexed" in s and "not indexed" not in s:
        return "indexed"
    return "technical"


# Причины исключения Вебмастера (ExcludedUrlStatus API v4) — по-русски, как
# в кабинете. Неизвестный код показывается как есть, а не прячется в «прочее».
YANDEX_REASON_LABEL = {
    "LOW_QUALITY": "малоценная или маловостребованная",
    "DUPLICATE": "дубль",
    "NOT_CANONICAL": "неканоническая",
    "NOTHING_FOUND": "страница неизвестна роботу",
    "HTTP_ERROR": "ошибка HTTP",
    "HOST_ERROR": "ошибка подключения к серверу",
    "REDIRECT_NOTSEARCHABLE": "редирект",
    "PARSER_ERROR": "ошибка разбора страницы",
    "ROBOTS_HOST_ERROR": "сайт запрещён в robots.txt",
    "ROBOTS_URL_ERROR": "запрещена в robots.txt",
    "CLEAN_PARAMS": "Clean-param",
    "NO_INDEX": "noindex",
    "NOT_MAIN_MIRROR": "неглавное зеркало",
    "INDEXING_NOT_ALLOWED": "индексирование запрещено",
    "OTHER": "прочее",
}


def yandex_reason_label(code: str | None) -> str:
    if not code:
        return "причина не зафиксирована"
    return YANDEX_REASON_LABEL.get(code, code)
