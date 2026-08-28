#!/usr/bin/env python3
"""Создание тестовой кампании Яндекс.Директа из спецификации round1-spec.json.

Запускается только воркфлоу ops-direct-apply по прямому поручению владельца
(решение о запуске рекламы — уровень Execute модели доступа, зафиксированной
в спецификации). Режимы:
  dry-run — собрать и напечатать все payload'ы, в API не ходить (кроме
            Clients.get для проверки доступа);
  apply   — создать кампанию, группы, фразы, объявления, корректировки,
            отправить объявления на модерацию.

Защита от дублей: если кампания с именем из спецификации уже существует
в кабинете — скрипт останавливается и ничего не создаёт.

Деньги, платёжные настройки, чужие кампании — не трогает ни в каком режиме.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"

AD_LIMITS = {"Title": 56, "Title2": 30, "Text": 81}


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
            units = resp.headers.get("Units", "")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} на {service}.{method}: {e.read().decode('utf-8')[:500]}")
    if "error" in data:
        err = data["error"]
        raise SystemExit(
            f"API-ошибка на {service}.{method}: код {err.get('error_code')} "
            f"{err.get('error_string')} — {err.get('error_detail')}"
        )
    if units:
        print(f"  [units {units}]")
    return data.get("result", {})


def check_add_results(label: str, result: dict, key: str = "AddResults") -> list[int]:
    ids: list[int] = []
    for i, r in enumerate(result.get(key, [])):
        if "Errors" in r and r["Errors"]:
            e = r["Errors"][0]
            raise SystemExit(f"{label}[{i}]: код {e.get('Code')} {e.get('Message')} — {e.get('Details')}")
        if "Warnings" in r and r["Warnings"]:
            for w in r["Warnings"]:
                print(f"  {label}[{i}] предупреждение: {w.get('Code')} {w.get('Message')} {w.get('Details') or ''}")
        ids.append(r.get("Id"))
    return ids


def schedule_business_hours() -> list[list[int]]:
    """Пн–пт 9:00–19:00 (слоты 9..18), сб–вс — показов нет."""
    items = []
    for day in range(1, 8):
        on = [100 if (day <= 5 and 9 <= h <= 18) else 0 for h in range(24)]
        items.append([day] + on)
    return items


def build_campaign(spec: dict) -> dict:
    camp = spec["campaign"]
    weekly_net_rub = camp["strategy"]["weekly_limit_rub_net"]
    bid_ceiling_rub = max(g["max_bid_rub"] for g in spec["groups"])
    return {
        "Campaigns": [
            {
                "Name": camp["name"],
                "StartDate": camp["start_date"],
                "TimeZone": "Europe/Moscow",
                "TimeTargeting": {
                    "Schedule": {"Items": schedule_business_hours()},
                    "ConsiderWorkingWeekends": "NO",
                    "HolidaysSchedule": {"SuspendOnHolidays": "YES"},
                },
                "NegativeKeywords": {"Items": camp["negative_keywords"]},
                "TextCampaign": {
                    "BiddingStrategy": {
                        "Search": {
                            "BiddingStrategyType": "WB_MAXIMUM_CLICKS",
                            "WbMaximumClicks": {
                                "WeeklySpendLimit": weekly_net_rub * 1_000_000,
                                "BidCeiling": bid_ceiling_rub * 1_000_000,
                            },
                        },
                        "Network": {"BiddingStrategyType": "SERVING_OFF"},
                    },
                },
            }
        ]
    }


def build_bid_modifiers(spec: dict, campaign_id: int) -> dict:
    mods = []
    bm = spec["campaign"].get("bid_modifiers", {})
    if "mobile_pct" in bm:
        mods.append({"CampaignId": campaign_id,
                     "MobileAdjustment": {"BidModifier": bm["mobile_pct"]}})
    if bm.get("age_under_18_off"):
        mods.append({"CampaignId": campaign_id,
                     "DemographicsAdjustments": [{"Age": "AGE_0_17", "BidModifier": 0}]})
    return {"BidModifiers": mods}


def build_groups(spec: dict, campaign_id: int) -> dict:
    return {
        "AdGroups": [
            {
                "Name": g["title"],
                "CampaignId": campaign_id,
                "RegionIds": [225],
                "NegativeKeywords": {"Items": g["minus_words"]},
            }
            for g in spec["groups"]
        ]
    }


def build_keywords(spec: dict, group_ids: list[int]) -> dict:
    kws = []
    for g, gid in zip(spec["groups"], group_ids):
        for k in g["keywords"]:
            kws.append({"AdGroupId": gid, "Keyword": k["keyword"]})
    return {"Keywords": kws}


def build_ads(spec: dict, group_ids: list[int]) -> dict:
    ads = []
    utm = spec["campaign"]["utm_template"]
    for g, gid in zip(spec["groups"], group_ids):
        href = g["landing"] + "?" + utm.replace("{group}", g["id"])
        for ad in g["ads"]:
            for field, limit in AD_LIMITS.items():
                key = {"Title": "title1", "Title2": "title2", "Text": "text"}[field]
                if len(ad[key]) > limit:
                    raise SystemExit(
                        f"{g['id']}: {field} длиннее {limit}: {len(ad[key])} — «{ad[key]}»")
            ads.append({
                "AdGroupId": gid,
                "TextAd": {
                    "Title": ad["title1"],
                    "Title2": ad["title2"],
                    "Text": ad["text"],
                    "Href": href,
                    "Mobile": "NO",
                },
            })
    return {"Ads": ads}


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[2] not in ("dry-run", "apply"):
        raise SystemExit("использование: direct_apply.py <spec.json> <dry-run|apply>")
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    mode = sys.argv[2]
    token = os.environ.get("DIRECT_TOKEN", "")
    if not token:
        raise SystemExit("нет токена в DIRECT_TOKEN")

    who = call("clients", "get", {"FieldNames": ["Login", "Currency"]}, token)
    info = (who.get("Clients") or [{}])[0]
    print(f"кабинет: {info.get('Login')} ({info.get('Currency')})")

    existing = call("campaigns", "get",
                    {"SelectionCriteria": {}, "FieldNames": ["Id", "Name", "State"]}, token)
    name = spec["campaign"]["name"]
    for c in existing.get("Campaigns") or []:
        print(f"  существующая кампания: {c['Id']} «{c['Name']}» {c['State']}")
        if c["Name"] == name:
            raise SystemExit(f"кампания «{name}» уже существует (Id {c['Id']}) — дубль не создаю")

    camp_payload = build_campaign(spec)
    if mode == "dry-run":
        print("== dry-run: payload кампании ==")
        print(json.dumps(camp_payload, ensure_ascii=False, indent=1))
        fake_ids = list(range(1, len(spec["groups"]) + 1))
        for label, payload in [
            ("корректировки", build_bid_modifiers(spec, 0)),
            ("группы", build_groups(spec, 0)),
            ("фразы", build_keywords(spec, fake_ids)),
            ("объявления", build_ads(spec, fake_ids)),
        ]:
            print(f"== dry-run: {label} ==")
            print(json.dumps(payload, ensure_ascii=False, indent=1))
        print("dry-run завершён: лимиты текстов проверены, в API запись не выполнялась")
        return

    camp_id = check_add_results("Campaigns", call("campaigns", "add", camp_payload, token))[0]
    print(f"кампания создана: Id {camp_id}")

    mods = build_bid_modifiers(spec, camp_id)
    if mods["BidModifiers"]:
        call("bidmodifiers", "add", mods, token)
        print(f"корректировки заданы: {len(mods['BidModifiers'])}")

    group_ids = check_add_results("AdGroups", call("adgroups", "add", build_groups(spec, camp_id), token))
    print(f"группы созданы: {group_ids}")

    kw_ids = check_add_results("Keywords", call("keywords", "add", build_keywords(spec, group_ids), token))
    print(f"фраз добавлено: {len(kw_ids)}")

    ad_ids = check_add_results("Ads", call("ads", "add", build_ads(spec, group_ids), token))
    print(f"объявлений добавлено: {len(ad_ids)}")

    call("ads", "moderate", {"SelectionCriteria": {"Ids": ad_ids}}, token)
    print("объявления отправлены на модерацию")
    print(f"ГОТОВО: кампания «{name}» (Id {camp_id}) создана; показы начнутся "
          f"{spec['campaign']['start_date']} по расписанию пн–пт 9:00–19:00 МСК "
          f"после модерации и при положительном балансе кабинета")


if __name__ == "__main__":
    main()
