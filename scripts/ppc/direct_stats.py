#!/usr/bin/env python3
"""Сбор статистики Яндекс.Директа по кампании bs-test-2026-09: только чтение.

Запускается воркфлоу ops-direct-stats. Ничего в кабинете не меняет.
Собирает и печатает:
  1. Состояние кампании, групп, объявлений и фраз (get-методы v5).
  2. Отчёты Reports API: по дням, по условиям показа (фразы/автотаргетинг),
     по поисковым запросам с классификацией интента и кандидатами в фразы,
     по площадкам/устройствам.
  3. Разделы Метрики по визитам кампании (поручение владельца 31.08, пункт
     P1 аудита): конверсии в разбивке по целям счётчика, поведение визитов
     (отказы/глубина/время) по поисковым запросам и по посадочным.

Поля, зависящие от привязки Метрики (конверсии, отказы), запрашиваются
второй попыткой: если API их не отдаёт, отчёт печатается без них,
а не падает целиком. Разделы Метрики требуют YANDEX_METRIKA_TOKEN и
YANDEX_METRIKA_COUNTER_ID; без них (или при ошибке API) печатается причина,
основной сбор Директа не прерывается.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"
METRIKA_API = "https://api-metrika.yandex.net/"
CAMPAIGN_NAME = "bs-test-2026-09"
CAMPAIGN_START = "2026-08-28"  # StartDate кампании — окно выборок Метрики


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


# Классификация поисковых запросов по коммерческому интенту (аудит
# direct-audit-2026-08-29.md): A — целевой B2B, B — коммерческий без
# B2B-маркера, C — информационный/навигационный, D — нерелевантный.
B2B_MARKERS = ("юрлиц", "юридическ", "компани", "организаци", "бизнес",
               "корпоратив", "team", "business", "enterprise", "счет",
               "счёт", "ндс", "договор", "команд")
COMMERCE_MARKERS = ("купить", "оплат", "подписк", "цена", "стоимость",
                    "тариф", "лицензи", "продлен", "приобрес")
IRRELEVANT_MARKERS = ("логотип", "картин", "изображен", "самокат",
                      "присадк", "ходатайств", "сметчик", "ваканси",
                      "зарплат", "резюме")


def classify_query(q: str) -> str:
    ql = q.lower()
    if any(m in ql for m in IRRELEVANT_MARKERS):
        return "D"
    commerce = any(m in ql for m in COMMERCE_MARKERS)
    b2b = any(m in ql for m in B2B_MARKERS)
    if commerce and b2b:
        return "A"
    if commerce:
        return "B"
    return "C"


def print_query_classes(tsv: str | None) -> None:
    """Сводка расхода по классам интента из отчёта по поисковым запросам."""
    if not tsv or not tsv.strip():
        return
    lines = tsv.rstrip("\n").split("\n")
    header = lines[0].split("\t")
    try:
        i_q = header.index("Query")
        i_imp = header.index("Impressions")
        i_cl = header.index("Clicks")
        i_cost = header.index("Cost")
    except ValueError:
        return
    try:
        i_type = header.index("CriterionType")
    except ValueError:
        i_type = None
    agg = {c: [0, 0, 0.0] for c in "ABCD"}
    worst: list[tuple[float, str, str]] = []
    candidates: list[tuple[float, int, str]] = []
    for ln in lines[1:]:
        parts = ln.split("\t")
        if len(parts) <= max(i_q, i_imp, i_cl, i_cost) or parts[i_q] == "Total rows:":
            continue
        try:
            imp, cl, cost = int(parts[i_imp]), int(parts[i_cl]), float(parts[i_cost])
        except ValueError:
            continue
        cls = classify_query(parts[i_q])
        agg[cls][0] += imp
        agg[cls][1] += cl
        agg[cls][2] += cost
        if cls in "CD" and cost > 0:
            worst.append((cost, cls, parts[i_q]))
        # Механизм P3 «запрос → ключ»: коммерческие запросы, пришедшие через
        # автотаргетинг и получившие клики, — кандидаты на перенос в фразы.
        if (cls in "AB" and cl > 0 and i_type is not None
                and len(parts) > i_type and parts[i_type] == "AUTOTARGETING"):
            candidates.append((cost, cl, parts[i_q]))
    total_cost = sum(v[2] for v in agg.values())
    print("\n== Классы интента (A целевой B2B / B коммерческий / C информационный / D нерелевантный) ==")
    for c in "ABCD":
        imp, cl, cost = agg[c]
        share = (cost / total_cost * 100) if total_cost else 0.0
        print(f"  {c}: показы {imp}, клики {cl}, расход {cost:.2f} ₽ ({share:.0f}%)")
    leak = agg["C"][2] + agg["D"][2]
    print(f"  Утечка C+D: {leak:.2f} ₽" +
          (f" ({leak / total_cost * 100:.0f}% расхода)" if total_cost else ""))
    for cost, cls, q in sorted(worst, reverse=True)[:10]:
        print(f"    {cls} {cost:.2f} ₽ — «{q}»")
    if candidates:
        print("  Кандидаты в фразы (A/B-запросы автотаргетинга с кликами):")
        for cost, cl, q in sorted(candidates, reverse=True)[:10]:
            print(f"    {cost:.2f} ₽, кликов {cl} — «{q}»")


def metrika_get(path: str, params: dict, token: str) -> dict:
    url = METRIKA_API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"OAuth {token}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"Метрика HTTP {e.code} на {path}: {e.read().decode('utf-8')[:300]}")


def metrika_stat(counter: str, token: str, **params) -> dict:
    base = {"ids": counter, "date1": CAMPAIGN_START, "date2": "today",
            "accuracy": "full"}
    base.update(params)
    return metrika_get("stat/v1/data", base, token)


def metrika_sections() -> None:
    """Конверсии по целям и поведение визитов кампании (данные Метрики).

    Визиты кампании отбираются фильтром по utm_campaign, при нуле — по
    атрибуции Директа (счётчик привязан к кампании). Разделы вспомогательные:
    любая ошибка печатается и не прерывает основной сбор Директа.
    """
    token = os.environ.get("YANDEX_METRIKA_TOKEN", "")
    counter = os.environ.get("YANDEX_METRIKA_COUNTER_ID", "")
    print("\n== Метрика: визиты кампании (с 28.08) ==")
    if not token or not counter:
        print("(YANDEX_METRIKA_TOKEN/YANDEX_METRIKA_COUNTER_ID не заданы — разделы пропущены)")
        return

    flt = None
    for cand in (f"ym:s:UTMCampaign=='{CAMPAIGN_NAME}'",
                 f"ym:s:lastDirectClickOrder=='{CAMPAIGN_NAME}'"):
        try:
            data = metrika_stat(counter, token, metrics="ym:s:visits", filters=cand)
        except RuntimeError as e:
            print(f"  (фильтр не принят: {e})")
            continue
        visits = int((data.get("totals") or [0])[0])
        if visits:
            flt = cand
            print(f"  визитов: {visits} (фильтр {cand.split('==')[0]})")
            break
    if flt is None:
        print("  визиты кампании не найдены ни по UTM, ни по атрибуции — разделы Метрики пропущены")
        return

    try:
        goals = metrika_get(f"management/v1/counter/{counter}/goals",
                            {}, token).get("goals", [])
    except RuntimeError as e:
        print(f"  (список целей не прочитан: {e})")
        goals = []

    if goals:
        print("\n== Метрика: конверсии кампании по целям ==")
        reached: list[tuple[int, str]] = []
        for i in range(0, len(goals), 18):
            chunk = goals[i:i + 18]
            metrics = ",".join(f"ym:s:goal{g['id']}reaches" for g in chunk)
            try:
                data = metrika_stat(counter, token, metrics=metrics, filters=flt)
            except RuntimeError as e:
                print(f"  (пакет целей не прочитан: {e})")
                continue
            for g, total in zip(chunk, data.get("totals") or []):
                if total:
                    reached.append((int(total), g.get("name", g["id"])))
        if reached:
            for total, name in sorted(reached, reverse=True):
                print(f"  {name}: {total}")
        else:
            print("  достижений целей с кампании нет (0 по всем целям)")

    behaviour = ("ym:s:visits,ym:s:bounceRate,ym:s:pageDepth,"
                 "ym:s:avgVisitDurationSeconds")

    print("\n== Метрика: поведение по поисковым запросам ==")
    shown = False
    for dim in ("ym:s:lastDirectSearchPhrase", "ym:s:lastDirectPhraseOrCond"):
        try:
            data = metrika_stat(counter, token, dimensions=dim,
                                metrics=behaviour, filters=flt,
                                sort="-ym:s:visits", limit=40)
        except RuntimeError as e:
            print(f"  ({dim} не принят: {e})")
            continue
        for row in data.get("data") or []:
            name = (row["dimensions"][0].get("name") or "(не определено)")
            v, br, pd, dur = row["metrics"]
            print(f"  {int(v):>3} виз. | отказы {br:.0f}% | глубина {pd:.2f} | "
                  f"{dur:.0f} с — «{name}»")
        shown = True
        break
    if not shown:
        print("  (запросы недоступны)")

    # Страницы входа сводятся по пути своими силами: измерения Метрики
    # держат в имени и query (startURLPathFull), поэтому одна посадочная
    # растекалась на десяток строк с utm-метками. Отказы, глубина и время
    # усредняются по визитам.
    print("\n== Метрика: поведение по посадочным ==")
    shown = False
    for dim in ("ym:s:startURL", "ym:s:startURLPathFull"):
        try:
            data = metrika_stat(counter, token, dimensions=dim,
                                metrics=behaviour, filters=flt,
                                sort="-ym:s:visits", limit=200)
        except RuntimeError as e:
            print(f"  ({dim} не принят: {e})")
            continue
        agg: dict[str, list[float]] = {}
        for row in data.get("data") or []:
            url = (row["dimensions"][0].get("name") or "?").split("?")[0]
            for prefix in ("https://biz-soft.pro", "http://biz-soft.pro"):
                if url.startswith(prefix):
                    url = url[len(prefix):] or "/"
            if len(url) > 1:
                url = url.rstrip("/")
            v, br, pd, dur = (float(x or 0) for x in row["metrics"])
            cur = agg.setdefault(url, [0.0, 0.0, 0.0, 0.0])
            cur[0] += v
            cur[1] += br * v
            cur[2] += pd * v
            cur[3] += dur * v
        for url, (v, br, pd, dur) in sorted(agg.items(), key=lambda kv: -kv[1][0])[:20]:
            n = v or 1
            print(f"  {int(v):>3} виз. | отказы {br / n:.0f}% | глубина {pd / n:.2f} | "
                  f"{dur / n:.0f} с — {url}")
        shown = True
        break
    if not shown:
        print("  (посадочные недоступны)")

    # Эксперимент «быстрые ссылки»: их входы помечены utm_content=sl-*.
    print("\n== Метрика: визиты по utm_content (sl-* — быстрые ссылки) ==")
    try:
        data = metrika_stat(counter, token, dimensions="ym:s:UTMContent",
                            metrics=behaviour, filters=flt,
                            sort="-ym:s:visits", limit=20)
        for row in data.get("data") or []:
            name = row["dimensions"][0].get("name") or "(без метки)"
            v, br, pd, dur = row["metrics"]
            print(f"  {int(v):>3} виз. | отказы {br:.0f}% | глубина {pd:.2f} | "
                  f"{dur:.0f} с — {name}")
    except RuntimeError as e:
        print(f"  (utm_content не прочитан: {e})")


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
    print_query_classes(tsv)

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

    # Измерение эксперимента «быстрые ссылки»: клики по элементам
    # объявления (sitelink1..8 против title и остальных). Показы, CTR и
    # позиции с ClickType несовместимы (ошибка 4000) — их здесь нет:
    # у элемента объявления нет собственного показа, только клик.
    tsv = report(token, "click-type", {
        "SelectionCriteria": sel,
        "FieldNames": ["ClickType", "Clicks", "AvgCpc", "Cost"],
        "ReportName": f"bs-clicktype-{int(time.time())}",
        "ReportType": "CUSTOM_REPORT", "DateRangeType": "ALL_TIME",
        "Format": "TSV", "IncludeVAT": "YES",
    })
    print_tsv("Отчёт по элементам объявления (ClickType)", tsv)

    try:
        metrika_sections()
    except Exception as e:  # раздел вспомогательный, сбор Директа важнее
        print(f"\n(разделы Метрики упали: {e})")


if __name__ == "__main__":
    main()
