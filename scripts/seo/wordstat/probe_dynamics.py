#!/usr/bin/env python3
"""Пробник getDynamics: почему сервис отвечает отказом 400.

Все 27 запросов динамики в прогоне 20.08.2026 вернули 400 — деньги списаны,
данных нет. Текст отказа в журнал тогда не писался, поэтому причина неизвестна.
Пробник перебирает несколько вариантов тела запроса и печатает ответ сервиса
на каждый: дешевле один раз спросить, чем угадывать за деньги.

Стоит около 0,12 ₽ (6 вызовов). Запускается на раннере — Яндекс из среды
мониторинга недоступен.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import config as C  # noqa: E402

URL = "https://searchapi.api.cloud.yandex.net/v2/wordstat/getDynamics"
PHRASE = "adobe купить"


def variants(region: str) -> list[tuple[str, dict]]:
    today = dt.date.today()
    month_start = today.replace(day=1)
    year_ago = (month_start - dt.timedelta(days=365)).replace(day=1)
    return [
        ("как в прогоне: 365 дней назад, произвольные даты", {
            "phrase": PHRASE, "period": "PERIOD_MONTHLY", "regions": [region],
            "fromDate": f"{today - dt.timedelta(days=365)}T00:00:00Z",
            "toDate": f"{today}T00:00:00Z"}),
        ("границы месяцев", {
            "phrase": PHRASE, "period": "PERIOD_MONTHLY", "regions": [region],
            "fromDate": f"{year_ago}T00:00:00Z",
            "toDate": f"{month_start}T00:00:00Z"}),
        ("даты без времени", {
            "phrase": PHRASE, "period": "PERIOD_MONTHLY", "regions": [region],
            "fromDate": str(year_ago), "toDate": str(month_start)}),
        ("период MONTHLY без префикса", {
            "phrase": PHRASE, "period": "MONTHLY", "regions": [region],
            "fromDate": f"{year_ago}T00:00:00Z",
            "toDate": f"{month_start}T00:00:00Z"}),
        ("недельный период", {
            "phrase": PHRASE, "period": "PERIOD_WEEKLY", "regions": [region],
            "fromDate": f"{today - dt.timedelta(days=90)}T00:00:00Z",
            "toDate": f"{today}T00:00:00Z"}),
        ("без регионов", {
            "phrase": PHRASE, "period": "PERIOD_MONTHLY",
            "fromDate": f"{year_ago}T00:00:00Z",
            "toDate": f"{month_start}T00:00:00Z"}),
    ]


def main() -> int:
    key = os.environ.get("WORDSTAT_API_KEY")
    if not key:
        print("нет ключа WORDSTAT_API_KEY")
        return 1
    cfg = C.load()
    region = cfg["collection"]["region_id"]
    headers = {"Authorization": f"Api-Key {key}", "Content-Type": "application/json"}
    results = []
    for title, body in variants(region):
        try:
            r = requests.post(URL, json=body, headers=headers, timeout=40)
            text = (r.text or "")[:400]
            code = r.status_code
        except requests.RequestException as e:
            code, text = None, f"{type(e).__name__}"
        ok = code == 200
        print(f"\n=== {title} ===")
        print("тело:", json.dumps(body, ensure_ascii=False))
        print("ответ:", code, text[:300])
        results.append({"variant": title, "body": body, "status": code,
                        "response": text[:300], "ok": ok})
        if ok:
            print("→ рабочий вариант найден, перебор остановлен")
            break
    out = pathlib.Path("reports/seo/wordstat/dynamics-probe.json")
    out.write_text(json.dumps({
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nсохранено: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
