#!/usr/bin/env python3
"""Сравнение каналов: что принесла реклама и что принесли остальные.

Вопрос руководителя 21.09.2026: сколько потрачено на рекламу с первого
дня, сколько она дала визитов и обращений, и как это выглядит рядом с
поиском без рекламы. Рекламный отчёт на него не отвечает: он считает
кампании, а не каналы, и про органику не знает ничего.

Считаются две стороны одной таблицы:

  деньги и клики  — Директ, все кампании кабинета за период;
  визиты по каналам — Метрика, ym:s:lastTrafficSource.

Заявки сюда не подмешиваются намеренно. Обращение живёт в воронке, а не
в счётчике: цель «отправлена заявка» покрывает только форму /api/lead,
тогда как запрос КП идёт своим путём, и по целям Метрики число
обращений вышло бы заниженным. Источник заявок — витрина
reports/seo/data/leads-<дата>.json ветки seo-data, где у каждой заявки
восстановлен путь посетителя.

Важная оговорка про сравнение периодов: с 16.09.2026 счётчик не
запускается до согласия на cookie, и визиты тех, кто ничего не нажал, в
статистику не попадают вовсе. Доля видимых визитов упала примерно
впятеро, одинаково для всех каналов — поэтому отношения каналов друг к
другу сравнивать можно, а абсолютные числа с периодом до 16.09 нельзя.

Запуск: channel_report.py [дата-с] [дата-по]; по умолчанию — с первого
дня рекламы по вчерашний день.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DIRECT_API = "https://api.direct.yandex.com/json/v5/"
METRIKA_API = "https://api-metrika.yandex.net/"
FIRST_AD_DAY = "2026-08-28"

# Как Метрика называет канал → как называем его мы. Порядок задаёт вывод.
CHANNELS = [
    ("ad", "реклама"),
    ("organic", "поиск без рекламы"),
    ("direct", "прямые заходы"),
    ("referral", "переходы с сайтов"),
    ("internal", "внутренние переходы"),
    ("social", "соцсети"),
    ("email", "письма"),
    ("recommend", "рекомендательные системы"),
    ("saved", "сохранённые страницы"),
    ("undefined", "источник не определён"),
]


def direct_call(service: str, method: str, params: dict, token: str) -> dict:
    body = json.dumps({"method": method, "params": params}).encode("utf-8")
    req = urllib.request.Request(
        DIRECT_API + service, data=body,
        headers={"Authorization": f"Bearer {token}", "Accept-Language": "ru",
                 "Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} на {service}.{method}: {e.read().decode('utf-8')[:400]}")
    if "error" in data:
        err = data["error"]
        raise SystemExit(f"API-ошибка {err.get('error_code')}: {err.get('error_string')}")
    return data.get("result", {})


def direct_spend(token: str, date_from: str, date_to: str) -> list[dict]:
    """Клики и расход по кампаниям за период (отчёт CAMPAIGN_PERFORMANCE)."""
    body = json.dumps({"params": {
        "SelectionCriteria": {"DateFrom": date_from, "DateTo": date_to},
        "FieldNames": ["CampaignName", "Impressions", "Clicks", "Cost"],
        "ReportName": f"channels-{date_from}-{date_to}",
        "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
        "DateRangeType": "CUSTOM_DATE", "Format": "TSV",
        "IncludeVAT": "YES", "IncludeDiscount": "NO",
    }}).encode("utf-8")
    req = urllib.request.Request(
        DIRECT_API + "reports", data=body,
        headers={"Authorization": f"Bearer {token}", "Accept-Language": "ru",
                 "Content-Type": "application/json; charset=utf-8",
                 "processingMode": "auto", "returnMoneyInMicros": "false"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} на reports: {e.read().decode('utf-8')[:400]}")
    rows = []
    for line in text.splitlines():
        f = line.split("\t")
        if len(f) == 4 and f[1].isdigit():
            rows.append({"name": f[0], "impressions": int(f[1]),
                         "clicks": int(f[2]), "cost": float(f[3])})
    return rows


def metrika_get(path: str, params: dict, token: str) -> dict:
    url = METRIKA_API + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"OAuth {token}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} на Метрике: {e.read().decode('utf-8')[:400]}")


def channel_visits(counter: str, token: str, date_from: str, date_to: str) -> dict[str, dict]:
    """Визиты, отказы и глубина по каналам за период."""
    data = metrika_get("stat/v1/data", {
        "ids": counter, "date1": date_from, "date2": date_to, "accuracy": "full",
        "dimensions": "ym:s:lastTrafficSource",
        "metrics": "ym:s:visits,ym:s:bounceRate,ym:s:pageDepth,ym:s:avgVisitDurationSeconds",
        "sort": "-ym:s:visits", "limit": 100,
    }, token)
    out = {}
    for row in data.get("data") or []:
        key = (row["dimensions"][0].get("id") or "undefined")
        m = row["metrics"]
        out[key] = {"visits": int(m[0]), "bounce": m[1], "depth": m[2], "seconds": m[3]}
    return out


def main() -> None:
    direct_token = os.environ.get("DIRECT_TOKEN", "")
    m_token = os.environ.get("YANDEX_METRIKA_TOKEN", "")
    counter = os.environ.get("YANDEX_METRIKA_COUNTER_ID", "")
    if not direct_token:
        raise SystemExit("DIRECT_TOKEN не задан")
    if not m_token or not counter:
        raise SystemExit("YANDEX_METRIKA_TOKEN или YANDEX_METRIKA_COUNTER_ID не заданы")

    date_from = sys.argv[1] if len(sys.argv) > 1 else FIRST_AD_DAY
    date_to = sys.argv[2] if len(sys.argv) > 2 else (dt.date.today() - dt.timedelta(days=1)).isoformat()
    print(f"Период: {date_from} — {date_to}")

    print("\n== Директ: расход по кампаниям (с НДС) ==")
    rows = direct_spend(direct_token, date_from, date_to)
    clicks = cost = shows = 0
    for r in sorted(rows, key=lambda x: -x["cost"]):
        cpc = r["cost"] / r["clicks"] if r["clicks"] else 0
        print(f"  {r['name']:30} показы {r['impressions']:7}  клики {r['clicks']:5}  "
              f"{r['cost']:10.2f} ₽  цена клика {cpc:6.2f} ₽")
        clicks += r["clicks"]; cost += r["cost"]; shows += r["impressions"]
    cpc_all = cost / clicks if clicks else 0
    print(f"  {'ИТОГО':30} показы {shows:7}  клики {clicks:5}  {cost:10.2f} ₽  "
          f"цена клика {cpc_all:6.2f} ₽")

    print("\n== Метрика: визиты по каналам ==")
    visits = channel_visits(counter, m_token, date_from, date_to)
    total = sum(v["visits"] for v in visits.values()) or 1
    known = set()
    for key, label in CHANNELS:
        v = visits.get(key)
        if not v:
            continue
        known.add(key)
        print(f"  {label:26} {v['visits']:5} виз. ({v['visits'] * 100 / total:4.1f}%) | "
              f"отказы {v['bounce']:4.0f}% | глубина {v['depth']:.2f} | {v['seconds']:.0f} с")
    for key, v in visits.items():
        if key not in known:
            print(f"  {key:26} {v['visits']:5} виз. ({v['visits'] * 100 / total:4.1f}%)")
    print(f"  {'ВСЕГО':26} {total:5} виз.")

    ad = visits.get("ad", {}).get("visits", 0)
    if clicks:
        print(f"\n  доехало до счётчика: {ad} из {clicks} кликов "
              f"({ad * 100 / clicks:.0f}%)")
    if ad:
        print(f"  цена визита с рекламы: {cost / ad:.2f} ₽ с НДС")
    org = visits.get("organic", {}).get("visits", 0)
    if org:
        print(f"  визитов из поиска без рекламы на один рекламный: "
              f"{org / ad:.1f}" if ad else f"  визитов из поиска без рекламы: {org}")


if __name__ == "__main__":
    main()
