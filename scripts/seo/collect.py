#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сбор SEO-данных biz-soft.pro из API Яндекс.Вебмастера v4.

Запуск (токен в переменной окружения YANDEX_OAUTH):

    YANDEX_OAUTH=... python3 scripts/seo/collect.py --yandex
        → data/yandex-<YYYY-MM-DD>.json

Флаг --stdout-b64 вместо записи файла печатает gzip+base64 JSON между
маркерами ---YJSON-BEGIN--- / ---YJSON-END--- — транспорт результата через
stdout SSH-шага воркфлоу seo-data-collect (из облачной сессии ассистента
нет egress к api.webmaster.yandex.net, а токен хранится только на сервере).

Ключ excluded_samples в результате — выборки страниц, исключённых из поиска:
прямого эндпоинта «excluded» в v4 нет, поэтому причины исключения берём из
событий поиска (search-urls/events/samples, event=REMOVED_FROM_SEARCH), а
эндпоинт search-urls/samples пробуем дополнительно и ошибку лишь фиксируем.
"""

import argparse
import base64
import datetime as dt
import gzip
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.webmaster.yandex.net/v4"
HOST_MATCH = "biz-soft.pro"
PAGE_LIMIT = 100     # максимум samples на один запрос API
MAX_SAMPLES = 3000   # потолок постраничной выгрузки на эндпоинт


def api_get(token, path, params=None):
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "OAuth " + token)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read() or b"{}")
        except Exception:
            body = {}
        return e.code, body
    except urllib.error.URLError as e:
        return 0, {"error_message": str(e)}


def fetch_paged(token, path, params=None, max_items=MAX_SAMPLES):
    """Постраничная выгрузка samples-эндпоинтов (offset/limit, count в ответе)."""
    out = {"endpoint": path, "count": None, "samples": []}
    offset = 0
    while True:
        q = dict(params or {})
        q.update({"offset": offset, "limit": PAGE_LIMIT})
        status, data = api_get(token, path, q)
        if status != 200:
            out["error"] = {"http_status": status, "body": data}
            break
        batch = data.get("samples") or []
        if out["count"] is None:
            out["count"] = data.get("count")
        out["samples"].extend(batch)
        offset += len(batch)
        if (not batch or offset >= max_items
                or (out["count"] is not None and offset >= out["count"])):
            break
    out["fetched"] = len(out["samples"])
    return out


def collect_yandex(token):
    """Сводка индексации и выборки исключённых из поиска страниц."""
    result = {
        "source": "yandex.webmaster.v4",
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }

    status, user = api_get(token, "/user")
    if status != 200:
        result["error"] = {"step": "user", "http_status": status, "body": user}
        return result
    uid = user["user_id"]

    status, hosts = api_get(token, f"/user/{uid}/hosts")
    host_id = next(
        (h["host_id"] for h in hosts.get("hosts", [])
         if HOST_MATCH in h["host_id"] and h["host_id"].startswith("https")),
        None,
    )
    result["host_id"] = host_id
    if not host_id:
        result["error"] = {
            "step": "hosts", "http_status": status,
            "available": [h.get("host_id") for h in hosts.get("hosts", [])],
        }
        return result
    base = f"/user/{uid}/hosts/{host_id}"

    status, summary = api_get(token, base + "/summary")
    result["summary"] = summary if status == 200 else {"error": {"http_status": status, "body": summary}}

    events = fetch_paged(token, base + "/search-urls/events/samples")
    legacy = fetch_paged(token, base + "/search-urls/samples", max_items=PAGE_LIMIT)
    removed = [s for s in events["samples"] if s.get("event") == "REMOVED_FROM_SEARCH"]
    result["excluded_samples"] = {
        "removed_from_search": removed,
        "removed_fetched": len(removed),
        "events_raw": events,
        "search_urls_samples_raw": legacy,
    }

    # Контекст для классификации: что сейчас в поиске и что видел робот.
    result["in_search_samples"] = fetch_paged(token, base + "/search-urls/in-search/samples", max_items=1000)
    result["indexing_samples"] = fetch_paged(token, base + "/indexing/samples")
    return result


def _reason(sample):
    return sample.get("excluded_url_status") or sample.get("reason") or "UNKNOWN"


def print_summary(data):
    print("== Яндекс.Вебмастер: сводка сбора ==")
    if data.get("error"):
        print("ошибка:", json.dumps(data["error"], ensure_ascii=False))
        return
    print("host:", data.get("host_id"))
    summary = data.get("summary") or {}
    for key in ("searchable_pages_count", "excluded_pages_count", "sqi", "site_problems"):
        if key in summary:
            print(f"{key}: {json.dumps(summary[key], ensure_ascii=False)}")
    ex = data.get("excluded_samples") or {}
    removed = ex.get("removed_from_search") or []
    total = (ex.get("events_raw") or {}).get("count")
    print(f"событий поиска выгружено: {(ex.get('events_raw') or {}).get('fetched')} из {total}")
    print(f"из них исключений (REMOVED_FROM_SEARCH): {len(removed)}")
    reasons = {}
    for s in removed:
        reasons[_reason(s)] = reasons.get(_reason(s), 0) + 1
    for name, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {name}: {n}")
    idx = data.get("indexing_samples") or {}
    print(f"indexing/samples: {idx.get('fetched')} из {idx.get('count')}")
    ins = data.get("in_search_samples") or {}
    print(f"in-search/samples: {ins.get('fetched')} из {ins.get('count')}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Сбор SEO-данных biz-soft.pro")
    ap.add_argument("--yandex", action="store_true", help="собрать данные Яндекс.Вебмастера")
    ap.add_argument("--stdout-b64", action="store_true",
                    help="печать gzip+base64 JSON в stdout вместо записи файла")
    ap.add_argument("--out-dir", default="data", help="каталог для data/yandex-<дата>.json")
    args = ap.parse_args(argv)
    if not args.yandex:
        ap.error("укажите --yandex (других коллекторов пока нет)")

    token = os.environ.get("YANDEX_OAUTH", "").strip()
    if not token:
        print("ошибка: переменная окружения YANDEX_OAUTH не задана", file=sys.stderr)
        return 2

    data = collect_yandex(token)
    print_summary(data)

    if args.stdout_b64:
        payload = base64.b64encode(
            gzip.compress(json.dumps(data, ensure_ascii=False).encode())
        ).decode()
        print("---YJSON-BEGIN---")
        for i in range(0, len(payload), 200):
            print(payload[i:i + 200])
        print("---YJSON-END---")
    else:
        os.makedirs(args.out_dir, exist_ok=True)
        path = os.path.join(args.out_dir, f"yandex-{dt.date.today().isoformat()}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("записано:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
