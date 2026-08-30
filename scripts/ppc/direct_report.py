#!/usr/bin/env python3
"""Ежедневная выгрузка статистики Яндекс.Директа (Reports API v5).

Этап A Direct Control Report (решение руководителя 29.08.2026). Забирает
два среза за всю жизнь кампании (объём мал, выгрузка идемпотентна):
  - по группам: дата, группа, показы, клики, расход;
  - по реальным поисковым запросам: дата, группа, запрос, показы, клики, расход.

Пишет reports/seo/ppc/direct-stats.json — единый файл-витрину, из которой
письмо строит блок «Реклама». Сбой выгрузки не стирает прежнюю витрину:
файл перезаписывается только при успешном ответе API.

Деньги запрашиваются в валюте (returnMoneyInMicros: false). Отчёт может
готовиться офлайн (HTTP 201/202) — ждём с повторами, как велит API.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

REPORTS_URL = "https://api.direct.yandex.com/json/v5/reports"
OUT = pathlib.Path("reports/seo/ppc/direct-stats.json")
CAMPAIGN_START = "2026-08-28"


def fetch_report(token: str, name: str, fields: list[str],
                 report_type: str, date_from: str, date_to: str) -> list[dict]:
    body = {
        "params": {
            "SelectionCriteria": {"DateFrom": date_from, "DateTo": date_to},
            "FieldNames": fields,
            "ReportName": f"{name}-{date_from}-{date_to}",
            "ReportType": report_type,
            "DateRangeType": "CUSTOM_DATE",
            "Format": "TSV",
            "IncludeVAT": "NO",
        }
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept-Language": "ru",
        "Content-Type": "application/json; charset=utf-8",
        "processingMode": "auto",
        "returnMoneyInMicros": "false",
        "skipReportHeader": "true",
        "skipReportSummary": "true",
    }
    for attempt in range(12):
        req = urllib.request.Request(REPORTS_URL, method="POST",
                                     data=json.dumps(body).encode("utf-8"),
                                     headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                if resp.status == 200:
                    return parse_tsv(resp.read().decode("utf-8"), fields)
                retry = int(resp.headers.get("retryIn", "10"))
        except urllib.error.HTTPError as e:
            if e.code in (201, 202):
                retry = int(e.headers.get("retryIn", "10"))
            else:
                raise SystemExit(f"Reports API HTTP {e.code}: {e.read().decode('utf-8')[:400]}")
        time.sleep(max(retry, 5))
    raise SystemExit("отчёт не подготовился за 12 попыток")


def parse_tsv(raw: str, fields: list[str]) -> list[dict]:
    """TSV без заголовка отчёта и итоговой строки: первая строка — имена полей."""
    lines = [l for l in raw.split("\n") if l.strip()]
    if not lines:
        return []
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        cells = line.split("\t")
        row = dict(zip(header, cells))
        parsed: dict = {}
        for f in fields:
            v = row.get(f, "")
            if f in ("Impressions", "Clicks"):
                parsed[f] = int(v or 0)
            elif f == "Cost":
                # «--» приходит там, где расхода нет.
                parsed[f] = float(v) if v not in ("", "--") else 0.0
            else:
                parsed[f] = v
        rows.append(parsed)
    return rows


def main() -> None:
    token = os.environ.get("DIRECT_TOKEN", "")
    if not token:
        print("DIRECT_TOKEN не задан — выгрузка Директа пропущена")
        return
    date_to = (dt.date.today() - dt.timedelta(days=0)).isoformat()

    groups = fetch_report(
        token, "bs-groups",
        ["Date", "CampaignId", "AdGroupId", "AdGroupName", "Impressions", "Clicks", "Cost"],
        "CUSTOM_REPORT", CAMPAIGN_START, date_to)
    queries = fetch_report(
        token, "bs-queries",
        ["Date", "AdGroupName", "Query", "Impressions", "Clicks", "Cost"],
        "SEARCH_QUERY_PERFORMANCE_REPORT", CAMPAIGN_START, date_to)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "schema_version": "1.0.0",
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "date_from": CAMPAIGN_START,
        "date_to": date_to,
        "groups": groups,
        "queries": queries,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    spend = sum(r["Cost"] for r in groups)
    clicks = sum(r["Clicks"] for r in groups)
    print(f"Директ: строк по группам {len(groups)}, запросов {len(queries)}, "
          f"расход всего {spend:.2f} ₽, кликов {clicks} -> {OUT}")


if __name__ == "__main__":
    main()
