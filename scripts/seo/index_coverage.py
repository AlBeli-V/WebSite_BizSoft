#!/usr/bin/env python3
"""Покрытие индекса по всему инвентарю sitemap — сенсор этапа 2 Growth Engine.

Зачем. До этого сенсора «Index Efficiency» складывалась из двух несопоставимых
чисел: у Google — страницы с показами (Search Analytics), у Яндекса — счётчик
searchable_pages_count из сводки хоста. Ни одно не отвечает на вопрос «почему
страница без показов»: Google не сообщал, знает ли он URL вообще, Яндекс —
какие именно страницы в поиске и почему исключены остальные. Разбор 03.09.2026
показал по выборке ops-index-validate, что все проверенные карточки товаров
для Google «неизвестны» (URL is unknown to Google) при поданном sitemap —
это вопрос обхода, а не текстов; без статуса по каждой странице такую причину
не отличить от «в индексе, но нет спроса».

Что снимает по каждому пути инвентаря (reports/seo/data/sitemap-<дата>.json):

  Google — URL Inspection API, тот же вызов, что в ops-index-validate, но по
    всему инвентарю. Квота ресурса — 2000 запросов в сутки и 600 в минуту.
    Прогон инспектирует не больше MAX_INSPECT URL: сначала те, у кого статуса
    ещё нет, затем давно не инспектированные; остальным достаётся прежний
    статус с пометкой stale_from. Так сенсор остаётся ежедневным и при росте
    sitemap за квоту, а резерв квоты остаётся ручному ops-index-validate.
  Яндекс — Webmaster API v4: страницы в поиске (search-urls/in-search/samples)
    и события появления/исключения с причиной (search-urls/events/samples).
    Страница считается исключённой, если её последнее событие в окне —
    REMOVED_FROM_SEARCH; причина — excluded_url_status.

Пишет index-google-<дата>.json и index-yandex-<дата>.json в reports/seo/data.
Потребители: inventory.py (загрузка и классификация), zero_impression.py
(раскладка страниц без показов по причинам), webreport.py.

Правило сборщиков: тело ошибки никогда не сохраняется как данные — сбой
источника кладётся в поле error, частичный сбой — в errors с сохранением
того, что успели снять.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import time
from zoneinfo import ZoneInfo

import requests

SITE = "biz-soft.pro"
BASE_URL = f"https://{SITE}"
OUT_DIR = pathlib.Path("reports/seo/data")
MSK = ZoneInfo("Europe/Moscow")

# Квота URL Inspection — 2000 в сутки на ресурс. 1800 оставляет запас ручному
# ops-index-validate и повторному прогону после сбоя.
MAX_INSPECT = 1800
INSPECT_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
# 600 запросов в минуту; пауза держит прогон ниже потолка без запаса «на глаз».
INSPECT_PAUSE = 0.12
LOOKBACK_DAYS = 7

YA_PAGE = 100          # предел страницы у samples-эндпоинтов
YA_MAX_IN_SEARCH = 6000
YA_MAX_EVENTS = 3000
YA_EVENTS_DAYS = 30


def today() -> str:
    return dt.datetime.now(MSK).date().isoformat()


def api_json(url, *, headers=None, params=None, body=None, timeout=30):
    """Как в collect.py: (данные, None) либо (None, «строка ошибки»)."""
    try:
        r = (requests.post(url, headers=headers, json=body, timeout=timeout)
             if body is not None else
             requests.get(url, headers=headers, params=params, timeout=timeout))
    except requests.RequestException as e:
        return None, f"{type(e).__name__}: {e}"
    if not r.ok:
        return None, f"HTTP {r.status_code}: {r.text[:300]}"
    try:
        return r.json(), None
    except ValueError as e:
        return None, f"ответ не является JSON ({e}): {r.text[:200]}"


def to_path(url: str) -> str:
    return (url or "").replace(BASE_URL, "") or "/"


# ── инвентарь и прежние срезы ────────────────────────────────────────────────

def load_inventory(date_s: str, out_dir: pathlib.Path = OUT_DIR) -> dict | None:
    date = dt.date.fromisoformat(date_s)
    for back in range(LOOKBACK_DAYS + 1):
        d = (date - dt.timedelta(days=back)).isoformat()
        p = out_dir / f"sitemap-{d}.json"
        if not p.exists():
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if raw.get("error") or not raw.get("urls"):
            continue
        return {"date": d, "paths": [u["path"] for u in raw["urls"]]}
    return None


def load_previous(prefix: str, date_s: str,
                  out_dir: pathlib.Path = OUT_DIR) -> dict:
    """Прежний срез (не сегодняшний): наследуемые статусы Google."""
    date = dt.date.fromisoformat(date_s)
    for back in range(1, LOOKBACK_DAYS + 1):
        d = (date - dt.timedelta(days=back)).isoformat()
        p = out_dir / f"{prefix}-{d}.json"
        if not p.exists():
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if raw.get("pages"):
            return raw["pages"]
    return {}


# ── Google: URL Inspection по инвентарю ──────────────────────────────────────

def inspection_order(paths: list[str], prev: dict) -> list[str]:
    """Сначала URL без статуса, затем по давности последней инспекции."""
    def key(p):
        rec = prev.get(p) or {}
        return (0 if not rec.get("inspected_at") else 1,
                rec.get("inspected_at") or "", p)
    return sorted(paths, key=key)


def inspect_google(paths: list[str], prev: dict, date_s: str,
                   max_inspect: int = MAX_INSPECT,
                   pause: float = INSPECT_PAUSE) -> dict:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    info = json.loads(os.environ["GSC_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    creds.refresh(Request())
    headers = {"Authorization": f"Bearer {creds.token}"}

    result = {"date": date_s, "source": "google_url_inspection",
              "quota_per_run": max_inspect, "pages": {}}
    sites, err = api_json("https://www.googleapis.com/webmasters/v3/sites",
                          headers=headers)
    if err:
        return {**result, "error": f"/sites: {err}"}
    entries = [s for s in sites.get("siteEntry", []) if SITE in s["siteUrl"]]
    if not entries:
        return {**result,
                "error": f"{SITE} не найден среди ресурсов сервисного аккаунта"}
    site_url = entries[0]["siteUrl"]
    result["site_url"] = site_url

    order = inspection_order(paths, prev)
    todo, rest = order[:max_inspect], order[max_inspect:]
    errors: list[str] = []
    inspected = 0
    stopped = False
    for i, path in enumerate(todo):
        if stopped:
            rest.append(path)
            continue
        data, err = api_json(INSPECT_URL, headers=headers,
                             body={"inspectionUrl": BASE_URL + path,
                                   "siteUrl": site_url})
        if err:
            errors.append(f"{path}: {err}")
            # Исчерпание квоты (429) или отказ доступа (403) повторяются на
            # каждом следующем URL — дальше не ходим, остальным — прежний
            # статус. Единичная ошибка одного URL прогон не останавливает.
            if "HTTP 429" in err or "HTTP 403" in err or len(errors) >= 20:
                stopped = True
            rest.append(path)
            continue
        idx = (data.get("inspectionResult") or {}).get("indexStatusResult") or {}
        result["pages"][path] = {
            "coverage_state": idx.get("coverageState"),
            "verdict": idx.get("verdict"),
            "indexing_state": idx.get("indexingState"),
            "robots_txt_state": idx.get("robotsTxtState"),
            "page_fetch_state": idx.get("pageFetchState"),
            "last_crawl": idx.get("lastCrawlTime"),
            "google_canonical": idx.get("googleCanonical"),
            "inspected_at": date_s,
        }
        inspected += 1
        if pause and i + 1 < len(todo):
            time.sleep(pause)

    for path in rest:
        old = prev.get(path)
        if old and old.get("inspected_at"):
            result["pages"][path] = {**old, "stale_from": old["inspected_at"]}
        else:
            result["pages"][path] = {"coverage_state": None, "inspected_at": None}

    result["inspected"] = inspected
    result["inherited"] = len([p for p in result["pages"].values()
                               if p.get("stale_from")])
    result["without_status"] = len([p for p in result["pages"].values()
                                    if not p.get("inspected_at")])
    if errors:
        result["errors"] = errors[:50]
    if inspected == 0 and errors:
        result["error"] = "ни один URL не проинспектирован: " + errors[0]
    return result


# ── Яндекс: страницы в поиске и причины исключения ───────────────────────────

def _paged(url: str, headers: dict, params: dict, key: str,
           limit_total: int) -> tuple[list, int | None, str | None]:
    items: list = []
    count = None
    for offset in range(0, limit_total, YA_PAGE):
        data, err = api_json(url, headers=headers,
                             params={**params, "offset": offset, "limit": YA_PAGE})
        if err:
            return items, count, err
        chunk = data.get(key) or []
        count = data.get("count", count)
        items.extend(chunk)
        if len(chunk) < YA_PAGE or (count is not None and len(items) >= count):
            break
    return items, count, None


def collect_yandex_index(date_s: str) -> dict:
    headers = {"Authorization": f"OAuth {os.environ['YANDEX_WEBMASTER_TOKEN']}"}
    base = "https://api.webmaster.yandex.net/v4/user"
    date_to = dt.date.fromisoformat(date_s)
    date_from = date_to - dt.timedelta(days=YA_EVENTS_DAYS)
    result = {"date": date_s, "source": "yandex_webmaster_pages",
              "window": {"from": date_from.isoformat(), "to": date_to.isoformat()}}

    user, err = api_json(base, headers=headers)
    if err or "user_id" not in (user or {}):
        result["error"] = ("/user: " + err) if err else "API /user не вернул user_id"
        return result
    uid = user["user_id"]
    hosts, err = api_json(f"{base}/{uid}/hosts", headers=headers)
    if err:
        result["error"] = f"/hosts: {err}"
        return result
    match = [h for h in hosts.get("hosts", []) if SITE in h.get("host_id", "")]
    if not match:
        result["error"] = f"{SITE} не найден в Вебмастере этого аккаунта"
        return result
    host = f"{base}/{uid}/hosts/{match[0]['host_id']}"
    result["host_id"] = match[0]["host_id"]

    samples, count, err = _paged(f"{host}/search-urls/in-search/samples",
                                 headers, {}, "samples", YA_MAX_IN_SEARCH)
    if err and not samples:
        result["error"] = f"in-search/samples: {err}"
        return result
    result["in_search"] = sorted({to_path(s.get("url")) for s in samples
                                  if s.get("url")})
    result["in_search_count"] = count
    result["in_search_fetched"] = len(samples)
    errors = [f"in-search/samples: {err}"] if err else []

    events, ev_count, err = _paged(
        f"{host}/search-urls/events/samples", headers,
        {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
        "samples", YA_MAX_EVENTS)
    if err:
        errors.append(f"events/samples: {err}")
    # Последнее событие по каждому пути решает: исключена ли страница сейчас.
    last: dict[str, dict] = {}
    for ev in events:
        path = to_path(ev.get("url"))
        when = ev.get("event_date") or ""
        if path not in last or when >= (last[path].get("event_date") or ""):
            last[path] = ev
    excluded = {}
    for path, ev in last.items():
        if ev.get("event") == "REMOVED_FROM_SEARCH":
            excluded[path] = {"status": ev.get("excluded_url_status"),
                              "date": (ev.get("event_date") or "")[:10],
                              "bad_http_status": ev.get("bad_http_status"),
                              "target_url": ev.get("target_url")}
    result["excluded"] = excluded
    result["events_count"] = ev_count
    result["events_fetched"] = len(events)
    if errors:
        result["errors"] = errors
    return result


# ── запуск ───────────────────────────────────────────────────────────────────

def main() -> int:
    date_s = today()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    inv = load_inventory(date_s)
    ok = True

    if not inv:
        g = {"date": date_s, "error": "инвентарь sitemap не собран — "
                                      "инспектировать нечего"}
        ok = False
    elif not os.environ.get("GSC_SERVICE_ACCOUNT_JSON"):
        g = {"date": date_s, "error": "секрет GSC_SERVICE_ACCOUNT_JSON не задан"}
        ok = False
    else:
        try:
            g = inspect_google(inv["paths"], load_previous("index-google", date_s),
                               date_s)
            g["inventory_date"] = inv["date"]
        except Exception as e:  # noqa: BLE001 — любая ошибка источника в JSON
            g = {"date": date_s, "error": f"{type(e).__name__}: {e}"}
        ok = ok and "error" not in g
    p = OUT_DIR / f"index-google-{date_s}.json"
    p.write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"google: {'ошибка: ' + g['error'] if 'error' in g else 'ок'} "
          f"(инспектировано {g.get('inspected', 0)}, унаследовано "
          f"{g.get('inherited', 0)}) -> {p}")

    if not os.environ.get("YANDEX_WEBMASTER_TOKEN"):
        y = {"date": date_s, "error": "секрет YANDEX_WEBMASTER_TOKEN не задан"}
        ok = False
    else:
        try:
            y = collect_yandex_index(date_s)
        except Exception as e:  # noqa: BLE001
            y = {"date": date_s, "error": f"{type(e).__name__}: {e}"}
        ok = ok and "error" not in y
    p = OUT_DIR / f"index-yandex-{date_s}.json"
    p.write_text(json.dumps(y, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"yandex: {'ошибка: ' + y['error'] if 'error' in y else 'ок'} "
          f"(в поиске {len(y.get('in_search') or [])}, исключено "
          f"{len(y.get('excluded') or {})}) -> {p}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
