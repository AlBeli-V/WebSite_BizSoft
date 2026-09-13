#!/usr/bin/env python3
"""Что API Директа знает о категориях автотаргетинга — разведка.

Внешний аудит 13.09.2026 поставил задачу: построить матрицу «категория
автотаргетинга против класса интента против расхода» и на ней пересобрать
кампании Apple. Задача упирается в вопрос, ответа на который у нас нет:
отдаёт ли API статистику в разрезе категорий вообще.

Известно только, что чтение настроек их не возвращает: прогон 04.09 по
кампании bs-test показал пустое поле AutotargetingCategories у всех
десяти условий, хотя запись категорий API принимает. Отчётный разрез
никто не проверял.

Скрипт ничего не меняет. Он делает три вещи:
  1. читает настройки условий ---autotargeting в кампаниях Apple;
  2. перебирает поля отчётов, которые могли бы нести категорию, и
     печатает, какие из них API принял, а какие отклонил и с какой
     формулировкой;
  3. по принятому полю (если найдётся) собирает срез расхода и строит
     матрицу «категория против класса интента»: сколько денег каждая
     категория тратит на запросы с покупательским словом и сколько — без.

Перебор идёт по одному полю за запрос: Reports API отвергает весь запрос
целиком, поэтому узнать, какое именно поле лишнее, можно только так.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"
CAMPAIGNS = ["bs-apple-gift-2026-09", "bs-apple-regions-2026-09"]
REPORT_FROM = "2026-09-07"

# Кандидаты в имена поля категории. Взяты из соседних по смыслу полей
# отчётов Директа: точного имени в нашей практике не встречалось, поэтому
# проверяем перебором, а не догадкой.
# Покупательские маркеры — те же, что в пакете минус-слов кампаний Apple.
BUY_MARKERS = (
    "пополн", "оплат", "купить", "куплю", "подарочн", "gift", "сертификат",
    "корпоратив", "юрлиц", "юр лиц", "заказать", "заказ",
    "стоимост", "цена", "цены", "прайс", "счет", "счёт", "тенге", "лир",
)
BUY_PAIRS = (
    ("сотрудник", ("купить", "заказ", "карт", "сертификат", "корпоратив",
                   "счет", "счёт", "оптом", "стоимост", "цена", "gift")),
    ("клиентам", ("купить", "заказ", "карт", "сертификат", "счет", "счёт")),
)

FIELD_CANDIDATES = [
    "TargetingCategory",
    "AutotargetingCategory",
    "AutoTargetingCategory",
    "AutotargetingCategoryName",
    "CriterionType",
    "MatchType",
    "MatchedKeyword",
    "Criterion",
]


def is_buy(query: str) -> bool:
    """Покупательский ли запрос: прямой маркер либо связка слова с деньгами."""
    q = query.lower()
    if any(m in q for m in BUY_MARKERS):
        return True
    return any(weak in q and any(strong in q for strong in strongs)
               for weak, strongs in BUY_PAIRS)


def call(service: str, method: str, params: dict, token: str) -> dict:
    body = json.dumps({"method": method, "params": params}).encode("utf-8")
    req = urllib.request.Request(
        API + service, data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept-Language": "ru",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} на {service}.{method}: {e.read().decode('utf-8')[:400]}")
    if "error" in data:
        err = data["error"]
        raise SystemExit(f"API-ошибка на {service}.{method}: код {err.get('error_code')} "
                         f"{err.get('error_string')} — {err.get('error_detail')}")
    return data.get("result", {})


def try_report(token: str, fields: list[str], report_type: str,
               campaign_ids: list[int]) -> tuple[bool, str, list[list[str]]]:
    """Попытка отчёта. Возврат: принят ли, пояснение, строки."""
    definition = {
        "SelectionCriteria": {
            "DateFrom": REPORT_FROM,
            "DateTo": time.strftime("%Y-%m-%d"),
            "Filter": [{"Field": "CampaignId", "Operator": "IN",
                        "Values": [str(i) for i in campaign_ids]}],
        },
        "FieldNames": fields,
        "ReportName": f"aa-{report_type[:6]}-{int(time.time()*1000)}",
        "ReportType": report_type,
        "DateRangeType": "CUSTOM_DATE",
        "Format": "TSV",
        "IncludeVAT": "NO",
    }
    body = json.dumps({"params": definition}).encode("utf-8")
    for _ in range(12):
        req = urllib.request.Request(
            API + "reports", data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept-Language": "ru",
                "Content-Type": "application/json; charset=utf-8",
                "processingMode": "auto",
                "returnMoneyInMicros": "false",
                "skipReportHeader": "true",
                "skipReportSummary": "true",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                if resp.status == 200:
                    lines = resp.read().decode("utf-8").strip().split("\n")
                    return True, "принято", [l.split("\t") for l in lines]
                retry = int(resp.headers.get("retryIn", "5") or "5")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8")
            try:
                err = json.loads(detail)["error"]
                msg = f"{err.get('error_string')} — {err.get('error_detail')}"
            except Exception:
                msg = detail[:200].replace("\n", " ")
            return False, msg, []
        time.sleep(min(retry, 20))
    return False, "отчёт не дождался готовности", []


def main() -> None:
    token = os.environ.get("DIRECT_TOKEN", "")
    if not token:
        raise SystemExit("DIRECT_TOKEN не задан")

    camps = call("campaigns", "get",
                 {"SelectionCriteria": {}, "FieldNames": ["Id", "Name"]},
                 token).get("Campaigns", [])
    targets = [c for c in camps if c["Name"] in CAMPAIGNS]
    if not targets:
        raise SystemExit("кампании Apple не найдены")
    ids = [c["Id"] for c in targets]
    print(f"Кампании: {', '.join(c['Name'] for c in targets)}")

    print("\n== 1. Настройки условий автотаргетинга ==")
    kws = call("keywords", "get",
               {"SelectionCriteria": {"CampaignIds": ids},
                "FieldNames": ["Id", "Keyword", "AdGroupId", "AutotargetingCategories"]},
               token).get("Keywords", [])
    autos = [k for k in kws if k["Keyword"] == "---autotargeting"]
    groups = call("adgroups", "get",
                  {"SelectionCriteria": {"CampaignIds": ids},
                   "FieldNames": ["Id", "Name"]}, token).get("AdGroups", [])
    gname = {g["Id"]: g["Name"] for g in groups}
    print(f"  условий автотаргетинга: {len(autos)} при {len(groups)} группах")
    for k in autos:
        raw = k.get("AutotargetingCategories")
        if raw:
            cats = ", ".join(f"{c['Category']}={c['Value']}" for c in raw
                             if isinstance(c, dict))
            print(f"  «{gname.get(k['AdGroupId'], k['AdGroupId'])}»: {cats}")
        else:
            print(f"  «{gname.get(k['AdGroupId'], k['AdGroupId'])}»: категории не отданы")

    print("\n== 2. Перебор полей отчёта ==")
    base = ["Impressions", "Clicks", "Cost"]
    found = []
    for report_type in ("CUSTOM_REPORT", "SEARCH_QUERY_PERFORMANCE_REPORT"):
        print(f"\n  -- {report_type} --")
        for field in FIELD_CANDIDATES:
            ok, msg, rows = try_report(token, [field] + base, report_type, ids)
            if ok:
                print(f"    ✓ {field}: принято, строк {max(len(rows) - 1, 0)}")
                found.append((report_type, field, rows))
            else:
                print(f"    ✗ {field}: {msg[:150]}")

    print("\n== 3. Что дала принятая разбивка ==")
    if not found:
        print("  ни одно поле не принято — разреза по категориям в отчётах нет")
        return
    for report_type, field, rows in found:
        if len(rows) < 2:
            print(f"  {report_type}.{field}: строк нет")
            continue
        head = rows[0]
        agg: dict[str, list[float]] = {}
        for r in rows[1:]:
            if len(r) != len(head):
                continue
            row = dict(zip(head, r))
            a = agg.setdefault(row[field], [0.0, 0.0, 0.0])
            a[0] += float(row["Impressions"])
            a[1] += float(row["Clicks"])
            a[2] += float(row["Cost"])
        print(f"\n  {report_type} по полю {field}: значений {len(agg)}")
        for value, (imp, clicks, cost) in sorted(agg.items(), key=lambda x: -x[1][2])[:15]:
            print(f"    {cost:8.2f} ₽ | показы {imp:7.0f} | клики {clicks:4.0f} | {value}")

    print("\n== 4. Матрица: категория против интента ==")
    matrix = next(((f, r) for t, f, r in found
                   if t == "SEARCH_QUERY_PERFORMANCE_REPORT" and f == "TargetingCategory"), None)
    if matrix is None:
        print("  разреза по категориям с запросами нет — матрицу не построить")
        return
    field, rows = matrix
    head = rows[0]
    if "Query" not in head:
        print("  в отчёте нет колонки запроса — повторяю запрос с ней")
        ok, msg, rows = try_report(token, [field, "Query", "Impressions", "Clicks", "Cost"],
                                   "SEARCH_QUERY_PERFORMANCE_REPORT", ids)
        if not ok:
            print(f"  не вышло: {msg[:200]}")
            return
        head = rows[0]

    cells: dict[str, list[float]] = {}
    examples: dict[str, list[tuple[float, str]]] = {}
    for r in rows[1:]:
        if len(r) != len(head):
            continue
        row = dict(zip(head, r))
        cat = row[field]
        cost = float(row["Cost"])
        clicks = float(row["Clicks"])
        imp = float(row["Impressions"])
        buy = is_buy(row["Query"])
        c = cells.setdefault(cat, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        idx = 0 if buy else 3
        c[idx] += cost
        c[idx + 1] += clicks
        c[idx + 2] += imp
        if not buy and clicks > 0:
            examples.setdefault(cat, []).append((cost, row["Query"]))

    print(f"  {'категория':14} {'деньги всего':>13} {'покупательских':>15} {'доля':>6} "
          f"{'кликов A/B':>11} {'кликов C/D':>11}")
    for cat, (bc, bcl, bi, jc, jcl, ji) in sorted(cells.items(), key=lambda x: -(x[1][0] + x[1][3])):
        total = bc + jc
        share = 100 * bc / total if total else 0
        print(f"  {cat:14} {total:11.2f} ₽ {bc:13.2f} ₽ {share:5.0f}% "
              f"{bcl:11.0f} {jcl:11.0f}")
    print("\n  Куда уходят деньги вне покупательского интента (топ-5 по категориям):")
    for cat in sorted(examples, key=lambda c: -cells[c][3])[:5]:
        top = sorted(examples[cat], reverse=True)[:5]
        print(f"    {cat}:")
        for cost, q in top:
            print(f"      {cost:7.2f} ₽ | {q}")


if __name__ == "__main__":
    main()
