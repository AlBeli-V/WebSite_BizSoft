#!/usr/bin/env python3
"""Сбор статистики Яндекс.Директа по кампании bs-test-2026-09: только чтение.

Запускается воркфлоу ops-direct-stats. Ничего в кабинете не меняет.
Собирает и печатает:
  1. Состояние кампании, групп, объявлений и фраз (get-методы v5).
  2. Отчёты Reports API: по дням, по условиям показа (фразы/автотаргетинг),
     по поисковым запросам, по площадкам/устройствам.

Поля, зависящие от привязки Метрики (конверсии, отказы), запрашиваются
второй попыткой: если API их не отдаёт, отчёт печатается без них,
а не падает целиком.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"
CAMPAIGN_NAME = "bs-test-2026-09"


def call(service: str, method: str, params: dict, token: str) -> dict:
    body = json.dumps({"method": method, "params": params}).encode("utf-8")
    req = urllib.request.Request(
        API + service,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept-Language": "ru",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "error" in data:
        err = data["error"]
        raise SystemExit(
            f"API-ошибка на {service}.{method}: код {err.get('error_code')} "
            f"{err.get('error_string')} — {err.get('error_detail')}"
        )
    return data.get("result", {})


def report(token: str, name: str, definition: dict) -> str | None:
    """Reports API: онлайн-режим с ожиданием офлайн-очереди. None — ошибка полей."""
    body = json.dumps({"params": definition}).encode("utf-8")
    for attempt in range(20):
        req = urllib.request.Request(
            API + "reports",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept-Language": "ru",
                "Content-Type": "application/json; charset=utf-8",
                "processingMode": "auto",
                "returnMoneyInMicros": "false",
                "skipReportHeader": "true",
                "skipReportSummary": "false",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                if resp.status == 200:
                    return resp.read().decode("utf-8")
                retry = int(resp.headers.get("retryIn", "10") or "10")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8")[:400]
            print(f"  [{name}] HTTP {e.code}: {detail}")
            return None
        time.sleep(min(retry, 30))
    print(f"  [{name}] отчёт не дождался готовности")
    return None


def print_tsv(title: str, tsv: str | None) -> None:
    print(f"\n== {title} ==")
    if not tsv or not tsv.strip():
        print("(нет данных)")
        return
    lines = tsv.rstrip("\n").split("\n")
    for ln in lines[:120]:
        print(ln)
    if len(lines) > 120:
        print(f"... ещё {len(lines) - 120} строк")


def main() -> None:
    token = os.environ.get("DIRECT_TOKEN", "")
    if not token:
        raise SystemExit("DIRECT_TOKEN не задан")

    camps = call(
        "campaigns", "get",
        {"SelectionCriteria": {}, "FieldNames": [
            "Id", "Name", "State", "Status", "StatusPayment", "StartDate",
            "Currency", "Funds", "Statistics"]},
        token,
    ).get("Campaigns", [])
    print("== Кампании кабинета ==")
    target_id = None
    for c in camps:
        funds = c.get("Funds", {})
        fmode = funds.get("Mode")
        finfo = funds.get("CampaignFunds") or funds.get("SharedAccountFunds") or {}
        bal = finfo.get("Balance") or finfo.get("Spend")
        stats = c.get("Statistics", {})
        print(f"- {c['Id']} «{c['Name']}» [{c.get('State')}/{c.get('Status')}] "
              f"оплата: {c.get('StatusPayment')} старт: {c.get('StartDate')} "
              f"валюта: {c.get('Currency')} финансы({fmode}): {bal} "
              f"клики(всего/сегодня): {stats.get('Clicks')} показы: {stats.get('Impressions')}")
        if c["Name"] == CAMPAIGN_NAME:
            target_id = c["Id"]
    if target_id is None:
        raise SystemExit(f"Кампания «{CAMPAIGN_NAME}» не найдена")

    groups = call(
        "adgroups", "get",
        {"SelectionCriteria": {"CampaignIds": [target_id]},
         "FieldNames": ["Id", "Name", "Status", "ServingStatus"]},
        token,
    ).get("AdGroups", [])
    print("\n== Группы ==")
    gname = {}
    for g in groups:
        gname[g["Id"]] = g["Name"]
        print(f"- {g['Id']} «{g['Name']}» {g.get('Status')}/{g.get('ServingStatus')}")

    ads = call(
        "ads", "get",
        {"SelectionCriteria": {"CampaignIds": [target_id]},
         "FieldNames": ["Id", "AdGroupId", "State", "Status", "StatusClarification"]},
        token,
    ).get("Ads", [])
    print("\n== Объявления ==")
    for a in ads:
        note = (a.get("StatusClarification") or "").replace("\n", " ")[:120]
        print(f"- {a['Id']} группа «{gname.get(a['AdGroupId'], a['AdGroupId'])}» "
              f"{a.get('State')}/{a.get('Status')} {note}")

    kws = call(
        "keywords", "get",
        {"SelectionCriteria": {"CampaignIds": [target_id]},
         "FieldNames": ["Id", "Keyword", "AdGroupId", "State", "Status",
                        "Productivity", "StatisticsSearch"]},
        token,
    ).get("Keywords", [])
    print(f"\n== Фразы ({len(kws)}) ==")
    for k in kws:
        st = k.get("StatisticsSearch", {})
        print(f"- [{gname.get(k['AdGroupId'], '?')}] «{k['Keyword']}» "
              f"{k.get('State')}/{k.get('Status')} "
              f"показы: {st.get('Impressions')} клики: {st.get('Clicks')}")

    sel = {"Filter": [{"Field": "CampaignId", "Operator": "EQUALS",
                       "Values": [str(target_id)]}]}
    base_days = ["Date", "Impressions", "Clicks", "Ctr", "AvgCpc", "Cost"]
    ext_days = base_days + ["AvgPageviews", "BounceRate", "Conversions"]

    tsv = report(token, "days-ext", {
        "SelectionCriteria": sel, "FieldNames": ext_days,
        "ReportName": f"bs-days-ext-{int(time.time())}",
        "ReportType": "CUSTOM_REPORT", "DateRangeType": "ALL_TIME",
        "Format": "TSV", "IncludeVAT": "YES",
    })
    if tsv is None:
        tsv = report(token, "days-base", {
            "SelectionCriteria": sel, "FieldNames": base_days,
            "ReportName": f"bs-days-base-{int(time.time())}",
            "ReportType": "CUSTOM_REPORT", "DateRangeType": "ALL_TIME",
            "Format": "TSV", "IncludeVAT": "YES",
        })
    print_tsv("Отчёт по дням (Cost с НДС, ₽)", tsv)

    tsv = report(token, "criteria", {
        "SelectionCriteria": sel,
        "FieldNames": ["AdGroupName", "CriterionType", "Criterion",
                       "Impressions", "Clicks", "Ctr", "AvgCpc", "Cost"],
        "ReportName": f"bs-criteria-{int(time.time())}",
        "ReportType": "CRITERIA_PERFORMANCE_REPORT", "DateRangeType": "ALL_TIME",
        "Format": "TSV", "IncludeVAT": "YES",
    })
    print_tsv("Отчёт по условиям показа (фразы и автотаргетинг)", tsv)

    tsv = report(token, "queries", {
        "SelectionCriteria": sel,
        "FieldNames": ["AdGroupName", "Query", "CriterionType",
                       "Impressions", "Clicks", "Cost"],
        "ReportName": f"bs-queries-{int(time.time())}",
        "ReportType": "SEARCH_QUERY_PERFORMANCE_REPORT", "DateRangeType": "ALL_TIME",
        "Format": "TSV", "IncludeVAT": "YES",
    })
    print_tsv("Отчёт по поисковым запросам", tsv)

    tsv = report(token, "device", {
        "SelectionCriteria": sel,
        "FieldNames": ["Device", "Impressions", "Clicks", "Ctr", "AvgCpc", "Cost"],
        "ReportName": f"bs-device-{int(time.time())}",
        "ReportType": "CUSTOM_REPORT", "DateRangeType": "ALL_TIME",
        "Format": "TSV", "IncludeVAT": "YES",
    })
    print_tsv("Отчёт по устройствам", tsv)

    tsv = report(token, "position", {
        "SelectionCriteria": sel,
        "FieldNames": ["Placement", "Impressions", "Clicks", "Ctr", "AvgCpc", "Cost"],
        "ReportName": f"bs-placement-{int(time.time())}",
        "ReportType": "CUSTOM_REPORT", "DateRangeType": "ALL_TIME",
        "Format": "TSV", "IncludeVAT": "YES",
    })
    print_tsv("Отчёт по площадкам", tsv)


if __name__ == "__main__":
    main()
