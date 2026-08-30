#!/usr/bin/env python3
"""Ядро запросов для SERP-watch — строится из данных, не руками.

Приоритет источников (дальше — дедупликация с сохранением порядка):
  A. коммерческие небрендовые запросы Вебмастера из снимка дня — реальные
     запросы, по которым сайт уже виден в Яндексе;
  B. money-радар (зона позиций 4–20, Яндекс + Google);
  C. верх коммерческого спроса Вордстата (top_commercial и фразы разрывов);
  D. кластеры «Аналоги X» — по страницам /alternatives/* из инвентаря.

Потолок — 500 запросов ядра («зелёный свет» руководителя 30.08.2026 на
полное коммерческое ядро; дневной бюджет serp_watch выше — ядро идёт ещё
и по второму региону).
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import inventory  # noqa: E402
import opportunity as opp_mod  # noqa: E402

SNAP_DIR = pathlib.Path("reports/seo/intelligence/snapshots")
LOOKBACK_DAYS = 7
CAP = 500
MIN_IMPRESSIONS = 3


def load_snapshot(date_s: str) -> dict | None:
    date = dt.date.fromisoformat(date_s)
    for back in range(LOOKBACK_DAYS + 1):
        p = SNAP_DIR / f"{(date - dt.timedelta(days=back)).isoformat()}.json"
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
    return None


def _phrases_from_demand(md: dict) -> list[str]:
    out = []
    for row in md.get("top_commercial") or []:
        if isinstance(row, str):
            out.append(row)
        elif isinstance(row, dict):
            ph = row.get("phrase") or row.get("query")
            if ph:
                out.append(ph)
    for rows in (md.get("gaps") or {}).values():
        for row in rows or []:
            if isinstance(row, dict) and row.get("phrase"):
                out.append(row["phrase"])
    return out


def build(date_s: str, cap: int = CAP) -> list[str]:
    snap = load_snapshot(date_s)
    ordered: list[str] = []

    if snap:
        # A. Вебмастер: коммерческое небрендовое, по показам.
        ents = [e for e in (snap.get("yandex") or {}).get("entities") or []
                if e.get("entity_type") == "query"
                and e.get("intent") == "commercial"
                and not e.get("branded")
                and (e.get("impressions") or 0) >= MIN_IMPRESSIONS]
        ordered += [e["entity_id"] for e in
                    sorted(ents, key=lambda e: -(e["impressions"] or 0))]
        # B. Money-радар обеих систем.
        mr = opp_mod.money_radar(snap, limit=50)
        ordered += [i["query"] for i in mr.get("items", [])]
        # C. Спрос Вордстата.
        md = snap.get("market_demand") or {}
        if md.get("available"):
            ordered += _phrases_from_demand(md)

    # D. «Аналоги X» по инвентарю.
    inv = inventory.load_latest(date_s)
    if inv:
        for u in inv["urls"]:
            path = u["path"]
            if path.startswith("/alternatives/"):
                slug = path.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
                if slug:
                    ordered.append(f"{slug} аналоги")

    seen, out = set(), []
    for q in ordered:
        key = " ".join((q or "").lower().split())
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(q.strip())
        if len(out) >= cap:
            break
    return out
