#!/usr/bin/env python3
"""Возврат групп Claude и Claude Code в работу (решение владельца 09.09.2026).

Обе группы остановлены стоп-правилом раунда 2 по критерию «ноль заявок».
Разбор воронки 07.09 (reports/marketing/lead-funnel-experiment-2026-09-07.md)
показал, что заявку в тот момент было нечем ни отправить, ни измерить:
событие открытия формы не отправлялось вовсе, цель клика по главному
призыву не значилась в реестре и в кабинет не попадала, а сама заявка
требовала открыть модальное окно и назвать семь реквизитов сразу. Сверх
того счётчик Метрики не писал визиты с 05 по 07.09
(reports/marketing/metrika-outage-2026-09-08.md). То есть критерий, по
которому группы остановлены, измерялся сломанным инструментом.

Возвращаются две группы из трёх. ChatGPT остаётся на паузе: у него второй
ценник кампании при самом низком CTR, и его посадочная не входит в число
страниц с формой в первом экране, то есть к идущему замеру воронки он
ничего не добавит.

Скрипт возобновляет только объявления, остановленные в этих группах.
Группы, фразы, ставки, бюджет, стратегию и чужие кампании не трогает.
Объявления уже прошли модерацию (ACCEPTED), перемодерация возврату не
требуется — показы возобновляются в ближайшем окне.

Режимы:
  dry-run — показать, что будет возобновлено, в API только чтение;
  apply   — возобновить.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"
CAMPAIGN_NAME = "bs-test-2026-09"

# Группы к возврату. ChatGPT сюда сознательно не входит — см. docstring.
RESUME_GROUPS = [
    "Claude — подписки для компаний",
    "Claude Code — для команд разработки",
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


def print_results(label: str, result: dict, key: str) -> None:
    for i, r in enumerate(result.get(key, [])):
        if r.get("Errors"):
            e = r["Errors"][0]
            print(f"  {label}[{i}]: ОШИБКА {e.get('Code')} {e.get('Message')} — {e.get('Details')}")
            continue
        for w in r.get("Warnings") or []:
            print(f"  {label}[{i}] предупреждение: {w.get('Code')} {w.get('Message')} {w.get('Details') or ''}")
        print(f"  {label}[{i}]: OK id={r.get('Id')}")


def main() -> None:
    token = os.environ.get("DIRECT_TOKEN", "")
    if not token:
        raise SystemExit("DIRECT_TOKEN не задан")
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry-run"
    if mode not in ("dry-run", "apply"):
        raise SystemExit(f"неизвестный режим: {mode}")
    print(f"Режим: {mode}")

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
    target_ids = {g["Id"] for g in groups if g["Name"] in RESUME_GROUPS}
    missing = [n for n in RESUME_GROUPS if n not in {g["Name"] for g in groups}]
    for n in missing:
        print(f"  ! группа не найдена в кабинете: «{n}»")

    ads = call("ads", "get",
               {"SelectionCriteria": {"CampaignIds": [cid]},
                "FieldNames": ["Id", "AdGroupId", "State", "Status"],
                "TextAdFieldNames": ["Title"]},
               token).get("Ads", [])

    print(f"\n== Объявления групп к возврату ({len(RESUME_GROUPS)}) ==")
    to_resume = []
    for a in sorted(ads, key=lambda x: gname.get(x["AdGroupId"], "")):
        if a["AdGroupId"] not in target_ids:
            continue
        title = (a.get("TextAd") or {}).get("Title")
        mark = f"{a.get('State')}/{a.get('Status')}"
        if a.get("State") == "SUSPENDED":
            to_resume.append(a["Id"])
            print(f"  + id {a['Id']} [{gname.get(a['AdGroupId'])}] «{title}» — {mark} → возобновляем")
        else:
            print(f"  = id {a['Id']} [{gname.get(a['AdGroupId'])}] «{title}» — {mark}, уже работает")

    print(f"\n== Итог: возобновить {len(to_resume)} объявлений ==")
    if not to_resume:
        print("  возобновлять нечего — все объявления этих групп уже в работе")
        return
    if mode != "apply":
        print("\ndry-run завершён — изменений нет.")
        return

    res = call("ads", "resume", {"SelectionCriteria": {"Ids": to_resume}}, token)
    print_results("ads.resume", res, "ResumeResults")

    ads2 = call("ads", "get",
                {"SelectionCriteria": {"CampaignIds": [cid]},
                 "FieldNames": ["Id", "AdGroupId", "State", "Status"]},
                token).get("Ads", [])
    live = sum(1 for a in ads2
               if a["AdGroupId"] in target_ids and a.get("State") != "SUSPENDED")
    total = sum(1 for a in ads2 if a["AdGroupId"] in target_ids)
    print(f"\n== Итог сверки ==\n  объявлений в работе: {live} из {total}")


if __name__ == "__main__":
    main()
