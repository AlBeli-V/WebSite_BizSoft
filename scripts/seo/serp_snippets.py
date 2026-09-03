#!/usr/bin/env python3
"""Статус страниц эксперимента в живой выдаче Яндекса по SERP-замерам.

Вопрос руководителя 31.08.2026: «страницы с новым сниппетом появились в
выдаче или нет?» — ответ есть в собственных данных (serp-watch пишет топ-10
с заголовками в reports/seo/data/serp/*.jsonl), но к блоку эксперимента он
не был подключён. Этот модуль сопоставляет: страница эксперимента → её
появления в замеренной выдаче → совпадает ли заголовок в выдаче с живым
заголовком страницы (его даёт проверка сайта site-check). Совпадение
означает, что Яндекс уже переобошёл страницу и показывает новый вариант.

Один замер — один день: берётся свежайший файл с успешными строками не
старше MAX_AGE_DAYS, чтобы у вывода была одна честная дата, а не смесь дней.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re

# Каталог-владение workflow seo-serp-watch (миграция из data/serp — этап 3.1).
SERP_DIR = pathlib.Path("reports/seo/serp")
OUR_DOMAIN = "biz-soft.pro"
MAX_AGE_DAYS = 7
# Минимальная длина сравниваемого префикса: короче — совпадение случайно.
MIN_PREFIX = 15


def _norm(title: str) -> str:
    t = title.lower().replace("ё", "е")
    # Яндекс усекает заголовок многоточием и может опустить хвост с брендом.
    t = re.sub(r"(\.\.\.|…).*$", "", t)
    t = re.sub(r"[\s ]+", " ", t)
    return t.strip(" -—|·")


def titles_match(serp_title: str, live_title: str) -> bool:
    """Заголовок в выдаче — это живой заголовок страницы (возможно, усечённый)."""
    s, l = _norm(serp_title), _norm(live_title)
    if len(s) < MIN_PREFIX:
        return False
    return l.startswith(s) or s.startswith(l)


def _latest_measure(today: dt.date) -> tuple[str, list[dict]] | None:
    """Свежайший SERP-файл с успешными строками не старше MAX_AGE_DAYS."""
    for p in sorted(SERP_DIR.glob("????-??-??-serp.jsonl"), reverse=True):
        date = p.name[:10]
        try:
            age = (today - dt.date.fromisoformat(date)).days
        except ValueError:
            continue
        if age > MAX_AGE_DAYS or age < 0:
            continue
        rows = []
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not r.get("error") and isinstance(r.get("top"), list):
                rows.append(r)
        if rows:
            return date, rows
    return None


def serp_status(pages: list[str], live_titles: dict[str, str],
                today: dt.date) -> dict | None:
    """Статус страниц эксперимента в выдаче по свежайшему SERP-замеру.

    live_titles: {"/vendors/canva": "<живой title>"} из site-check; пустой
    словарь допустим — тогда фиксируются только появления и позиции, без
    вывода о новизне сниппета.
    """
    measure = _latest_measure(today)
    if not measure:
        return None
    date, rows = measure
    seen: dict[str, dict] = {}
    for r in rows:
        for i, t in enumerate(r.get("top") or [], 1):
            url = t.get("url") or ""
            if OUR_DOMAIN not in (t.get("domain") or ""):
                continue
            path = re.sub(r"^https?://[^/]+", "", url).rstrip("/")
            for page in pages:
                if path != page.rstrip("/"):
                    continue
                cur = seen.get(page)
                if cur is None or i < cur["best_position"]:
                    live = live_titles.get(page)
                    seen[page] = {
                        "best_position": i,
                        "serp_title": t.get("title") or "",
                        "query": r.get("query") or "",
                        "new_snippet": (titles_match(t.get("title") or "", live)
                                        if live else None),
                    }
    matched = sum(1 for v in seen.values() if v["new_snippet"])
    return {
        "measured_at": date,
        "pages_total": len(pages),
        "pages_seen": len(seen),
        "pages_with_new_snippet": (matched if live_titles else None),
        "pages": seen,
    }
