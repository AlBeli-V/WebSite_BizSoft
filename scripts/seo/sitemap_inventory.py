#!/usr/bin/env python3
"""Инвентарь URL сайта из живого sitemap.xml — сенсор этапа 2 Growth Engine.

Запускается шагом workflow seo-data-collect (раннер GitHub, egress открыт;
у сессии прямого доступа к проду нет — правило проекта). Секретов не требует:
sitemap публичный. Пишет:

  reports/seo/data/sitemap-<дата>.json   — список путей с lastmod;
  reports/seo/data/url-first-seen.json   — реестр «когда путь впервые появился
                                           в инвентаре» (только пополняется).

Реестр first-seen — основа Indexation SLA и zero-impression отчёта: возраст
страницы в инвентаре считается от первой фиксации, поэтому у страниц, живших
до запуска сенсора, возраст — нижняя оценка (помечается потребителями).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

OUT_DIR = pathlib.Path("reports/seo/data")
SITE_URL = os.environ.get("SITE_URL", "https://biz-soft.pro").rstrip("/")
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

MSK = ZoneInfo("Europe/Moscow")


def today() -> str:
    return dt.datetime.now(MSK).date().isoformat()


def parse_sitemap(xml_text: str, site: str = SITE_URL) -> list[dict]:
    """<urlset> → [{path, lastmod}]. Индексные sitemap здесь не поддержаны
    сознательно: у сайта один плоский sitemap; появление <sitemapindex>
    должно упасть заметно, а не молча дать пустой инвентарь."""
    root = ET.fromstring(xml_text)
    if root.tag.endswith("sitemapindex"):
        raise ValueError("sitemap стал индексным (sitemapindex) — "
                         "нужно доработать разбор")
    urls = []
    for u in root.findall("sm:url", NS):
        loc = (u.findtext("sm:loc", "", NS) or "").strip()
        if not loc:
            continue
        path = loc.replace(site, "") or "/"
        urls.append({"path": path,
                     "lastmod": (u.findtext("sm:lastmod", "", NS) or "").strip()
                                or None})
    if not urls:
        raise ValueError("sitemap разобран, но не содержит ни одного <url>")
    return urls


def update_first_seen(paths: list[str], date: str,
                      registry_path: pathlib.Path) -> dict:
    """Реестр first-seen только пополняется: дата первой фиксации не
    пересматривается, исчезновение пути из sitemap записи не удаляет
    (страница могла быть снята — это тоже история)."""
    reg = {"paths": {}, "started": date}
    if registry_path.exists():
        try:
            reg = json.loads(registry_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    known = reg.setdefault("paths", {})
    added = 0
    for p in paths:
        if p not in known:
            known[p] = date
            added += 1
    reg["updated_at"] = date
    reg["added_last_run"] = added
    registry_path.write_text(json.dumps(reg, ensure_ascii=False, indent=1,
                                        sort_keys=True), encoding="utf-8")
    return reg


def main() -> int:
    import requests

    date = today()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"sitemap-{date}.json"
    url = f"{SITE_URL}/sitemap.xml"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        urls = parse_sitemap(r.text)
    except Exception as e:  # noqa: BLE001 — сбой сенсора фиксируется в JSON
        out_path.write_text(json.dumps(
            {"date": date, "source": url,
             "error": f"{type(e).__name__}: {e}"},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"sitemap-инвентарь: ошибка — {type(e).__name__}: {e}")
        return 1
    out_path.write_text(json.dumps(
        {"date": date, "source": url, "count": len(urls), "urls": urls},
        ensure_ascii=False, indent=1), encoding="utf-8")
    reg = update_first_seen([u["path"] for u in urls], date,
                            OUT_DIR / "url-first-seen.json")
    print(f"sitemap-инвентарь: {len(urls)} URL -> {out_path}; "
          f"новых в реестре first-seen: {reg.get('added_last_run', 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
