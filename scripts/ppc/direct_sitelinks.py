#!/usr/bin/env python3
"""Быстрые ссылки для bs-test-2026-09 — отдельный эксперимент.

Поручение владельца 31.08.2026. Гипотеза: быстрые ссылки поднимут CTR и
усилят B2B-фильтр до клика — «Оплата по счёту» и «Договор и ЭДО» видны в
объявлении, физлица реже кликают, юрлица получают ответ на главный вопрос
до перехода. План эксперимента и критерии решения —
reports/marketing/direct-sitelinks-experiment-2026-08-31.md.

Один набор из четырёх ссылок на служебные страницы сайта (не дублируют
посадочные объявлений — требование модерации), у каждой своя метка
utm_content=sl-*: входы через быстрые ссылки отличимы в Метрике, а клики
по элементам объявления считает отчёт ClickType в ops-direct (action=stats).

ВНИМАНИЕ: привязка набора отправляет объявления на перемодерацию.
Применять вне окна показов (после 19:00 МСК или в выходные), чтобы не
терять открутку.

Режимы:
  dry-run  — напечатать набор и план привязки, в API только чтение;
  apply    — создать набор и привязать ко всем объявлениям кампании
             (объявления, у которых набор уже есть, пропускаются);
  rollback — отвязать наборы от всех объявлений кампании (откат
             эксперимента; сам набор в кабинете остаётся, он безвреден).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"
CAMPAIGN_NAME = "bs-test-2026-09"
SITE = "https://biz-soft.pro"
UTM = ("utm_source=yandex&utm_medium=cpc&utm_campaign=bs-test-2026-09"
       "&utm_content=sl-{slug}")

# Лимиты Директа на быстрые ссылки.
LIMITS = {"Title": 30, "Description": 60, "TitleSum": 66}

# Набор: заголовок, описание, страница, метка. Страницы служебные и
# существуют на сайте (how-we-work, documents, pricing, contacts).
SITELINKS = [
    ("Оплата по счёту", "Счёт юрлицу, оплата в рублях, доступ за 1–3 дня",
     "/how-we-work", "schet"),
    ("Договор и ЭДО", "Договор, НДС, закрывающие документы через ЭДО",
     "/documents", "edo"),
    ("Расчёт стоимости", "Посчитаем под состав команды и срок подписки",
     "/pricing", "raschet"),
    ("Контакты", "Телефон, почта и мессенджеры, отвечаем в рабочие часы",
     "/contacts", "kontakty"),
]


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
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} на {service}.{method}: {e.read().decode('utf-8')[:500]}")
    if "error" in data:
        err = data["error"]
        raise SystemExit(
            f"API-ошибка на {service}.{method}: код {err.get('error_code')} "
            f"{err.get('error_string')} — {err.get('error_detail')}"
        )
    return data.get("result", {})


def print_results(label: str, result: dict, key: str) -> list[int]:
    ids: list[int] = []
    for i, r in enumerate(result.get(key, [])):
        if r.get("Errors"):
            e = r["Errors"][0]
            print(f"  {label}[{i}]: ОШИБКА {e.get('Code')} {e.get('Message')} — {e.get('Details')}")
            continue
        for w in r.get("Warnings") or []:
            print(f"  {label}[{i}] предупреждение: {w.get('Code')} {w.get('Message')} {w.get('Details') or ''}")
        print(f"  {label}[{i}]: OK id={r.get('Id')}")
        ids.append(r.get("Id"))
    return ids


def validate() -> None:
    total = 0
    for title, desc, path, slug in SITELINKS:
        assert len(title) <= LIMITS["Title"], f"Title длиннее {LIMITS['Title']}: {title!r}"
        assert len(desc) <= LIMITS["Description"], f"Description длиннее {LIMITS['Description']}: {desc!r}"
        total += len(title)
    assert total <= LIMITS["TitleSum"], f"сумма заголовков {total} > {LIMITS['TitleSum']}"


def main() -> None:
    token = os.environ.get("DIRECT_TOKEN", "")
    if not token:
        raise SystemExit("DIRECT_TOKEN не задан")
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry-run"
    if mode not in ("dry-run", "apply", "rollback"):
        raise SystemExit(f"неизвестный режим: {mode}")
    print(f"Режим: {mode}")
    validate()

    camps = call("campaigns", "get",
                 {"SelectionCriteria": {}, "FieldNames": ["Id", "Name"]},
                 token).get("Campaigns", [])
    camp = next((c for c in camps if c["Name"] == CAMPAIGN_NAME), None)
    if camp is None:
        raise SystemExit(f"Кампания «{CAMPAIGN_NAME}» не найдена")
    cid = camp["Id"]

    groups = call("adgroups", "get",
                  {"SelectionCriteria": {"CampaignIds": [cid]},
                   "FieldNames": ["Id", "Name"]}, token).get("AdGroups", [])
    gname = {g["Id"]: g["Name"] for g in groups}

    ads = call("ads", "get",
               {"SelectionCriteria": {"CampaignIds": [cid]},
                "FieldNames": ["Id", "AdGroupId", "State", "Status"],
                "TextAdFieldNames": ["Title", "SitelinkSetId"]},
               token).get("Ads", [])

    print(f"\n== Набор быстрых ссылок ({len(SITELINKS)}) ==")
    items = []
    for title, desc, path, slug in SITELINKS:
        href = f"{SITE}{path}?{UTM.replace('{slug}', slug)}"
        print(f"  «{title}» — {desc}")
        print(f"    → {href}")
        items.append({"Title": title, "Description": desc, "Href": href})

    with_set = [a for a in ads if (a.get("TextAd") or {}).get("SitelinkSetId")]
    without_set = [a for a in ads if not (a.get("TextAd") or {}).get("SitelinkSetId")]

    print(f"\n== Объявления кампании ({len(ads)}) ==")
    for a in ads:
        ta = a.get("TextAd") or {}
        mark = f"набор {ta.get('SitelinkSetId')}" if ta.get("SitelinkSetId") else "набора нет"
        print(f"  - id {a['Id']} [{gname.get(a['AdGroupId'], '?')}] «{ta.get('Title')}» — {mark}")

    if mode == "rollback":
        if not with_set:
            print("\nОткатывать нечего: наборы не привязаны.")
            return
        print(f"\n== Откат: отвязка набора у {len(with_set)} объявлений ==")
        res = call("ads", "update",
                   {"Ads": [{"Id": a["Id"], "TextAd": {"SitelinkSetId": None}}
                            for a in with_set]}, token)
        print_results("ads.update", res, "UpdateResults")
        print("Объявления уйдут на перемодерацию без быстрых ссылок.")
        return

    if not without_set:
        print("\nВсе объявления уже с наборами — привязывать нечего.")
        return
    print(f"\n== Привязка: {len(without_set)} объявлений без набора"
          + (f", {len(with_set)} пропущено (набор уже есть)" if with_set else "") + " ==")

    if mode != "apply":
        print("\ndry-run завершён — изменений нет. Применять вне окна показов:")
        print("объявления уйдут на перемодерацию.")
        return

    res = call("sitelinks", "add", {"SitelinksSets": [{"Sitelinks": items}]}, token)
    set_ids = print_results("sitelinks.add", res, "AddResults")
    if not set_ids or set_ids[0] is None:
        raise SystemExit("набор быстрых ссылок не создан")
    set_id = set_ids[0]

    res = call("ads", "update",
               {"Ads": [{"Id": a["Id"], "TextAd": {"SitelinkSetId": set_id}}
                        for a in without_set]}, token)
    print_results("ads.update", res, "UpdateResults")

    # Контрольное чтение.
    ads2 = call("ads", "get",
                {"SelectionCriteria": {"CampaignIds": [cid]},
                 "FieldNames": ["Id", "State", "Status"],
                 "TextAdFieldNames": ["Title", "SitelinkSetId"]},
                token).get("Ads", [])
    n_ok = sum(1 for a in ads2 if (a.get("TextAd") or {}).get("SitelinkSetId"))
    print(f"\n== Итог сверки ==\n  объявлений с набором: {n_ok} из {len(ads2)}")
    print("  объявления отправлены на перемодерацию — статусы выровняются после её прохождения")


if __name__ == "__main__":
    main()
