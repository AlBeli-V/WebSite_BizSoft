#!/usr/bin/env python3
"""Создание тестовой кампании Яндекс.Директа из спецификации round1-spec.json.

Запускается только воркфлоу ops-direct (action=apply) по прямому поручению владельца
(решение о запуске рекламы — уровень Execute модели доступа, зафиксированной
в спецификации). Режимы:
  dry-run — собрать и напечатать все payload'ы, в API не ходить (кроме
            Clients.get для проверки доступа);
  apply   — создать кампанию, группы, фразы, объявления, корректировки,
            отправить объявления на модерацию.

Вид плана задаётся полем plan_kind спецификации:
  create_campaign (по умолчанию) — создание кампании с нуля; защита от
            дублей: если кампания с этим именем уже есть, скрипт
            останавливается и ничего не создаёт;
  extend_campaign — правка существующей кампании: паузы отработавших групп
            и добавление новых. Бюджет, стратегия, расписание и
            корректировки не трогаются вовсе.

Деньги, платёжные настройки, чужие кампании — не трогает ни в каком режиме.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"

AD_LIMITS = {"Title": 56, "Title2": 30, "Text": 81, "TitleSum": 52}


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


def schedule_business_hours(days: tuple[int, ...] = (1, 2, 3, 4, 5),
                            hour_from: int = 9, hour_to: int = 19) -> list[str]:
    """Расписание показов: по умолчанию пн–пт 9:00–19:00 (слоты 9..18), сб–вс — нет.

    Дни и часы задаёт спецификация (ключ campaign.time_targeting, см.
    schedule_from_spec): кампания подарочных карт Apple (раунд 3) показывается
    и вечером, и в выходные — спрос на пополнение баланса не рабочий. Слот
    hour_to не включается: 9..19 означает часы 9, 10, …, 18.
    API ждёт каждый день строкой «день,ч0,...,ч23» (ошибка 8000 при массиве).
    """
    items = []
    for day in range(1, 8):
        on = [100 if (day in days and hour_from <= h < hour_to) else 0 for h in range(24)]
        items.append(",".join(str(v) for v in [day] + on))
    return items


def schedule_from_spec(camp: dict) -> tuple[list[str], dict]:
    """Расписание и блок праздников из campaign.time_targeting.

    Без ключа — прежнее поведение (пн–пт 9–19, праздники выключены), так что
    спецификации раундов 1–2 воспроизводятся без изменений. Кампания с
    показами в выходные не останавливается и в праздники: её спрос не
    привязан к рабочему календарю. У API при SuspendOnHolidays = NO
    обязательны часы показов в праздники StartHour (0–23) и EndHour (1–24) —
    без них Campaigns.add отвечает кодом 5000 (прогон 05.09.2026, раунд 3);
    берём те же часы, что и в будни.
    """
    tt = camp.get("time_targeting") or {}
    days = tuple(int(d) for d in tt.get("days", (1, 2, 3, 4, 5)))
    hour_from = int(tt.get("hour_from", 9))
    hour_to = int(tt.get("hour_to", 19))
    if not days or any(d < 1 or d > 7 for d in days) or not (0 <= hour_from < hour_to <= 24):
        raise SystemExit(f"time_targeting некорректен: days={days} hours={hour_from}-{hour_to}")
    weekends = any(d >= 6 for d in days)
    if weekends:
        holidays = {"SuspendOnHolidays": "NO", "StartHour": hour_from, "EndHour": hour_to,
                    "BidPercent": 100}
    else:
        holidays = {"SuspendOnHolidays": "YES"}
    return schedule_business_hours(days, hour_from, hour_to), holidays


def build_campaign(spec: dict) -> dict:
    camp = spec["campaign"]
    weekly_net_rub = camp["strategy"]["weekly_limit_rub_net"]
    bid_ceiling_rub = max(g["max_bid_rub"] for g in spec["groups"])
    schedule, holidays = schedule_from_spec(camp)
    return {
        "Campaigns": [
            {
                "Name": camp["name"],
                "StartDate": camp["start_date"],
                "TimeZone": "Europe/Moscow",
                "TimeTargeting": {
                    "Schedule": {"Items": schedule},
                    "ConsiderWorkingWeekends": "NO",
                    "HolidaysSchedule": holidays,
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
    """Группы объявлений. Пустой список минусов в запрос не попадает.

    Директ отвергает AdGroups.NegativeKeywords.Items с нулём элементов
    (код 8000), и спецификация без групповых минусов роняла прогон уже
    после создания кампании — 21.09.2026 так появилась кампания 714629311
    без единой группы. Минусы кампании при этом действуют на все её
    группы, поэтому групповой список честно необязателен.
    """
    groups = []
    for g in spec["groups"]:
        item = {
            "Name": g["title"],
            "CampaignId": campaign_id,
            "RegionIds": [225],
        }
        if g.get("minus_words"):
            item["NegativeKeywords"] = {"Items": g["minus_words"]}
        groups.append(item)
    return {"AdGroups": groups}


def build_keywords(spec: dict, group_ids: list[int]) -> dict:
    kws = []
    for g, gid in zip(spec["groups"], group_ids):
        for k in g["keywords"]:
            kws.append({"AdGroupId": gid, "Keyword": k["keyword"]})
    return {"Keywords": kws}


def check_ad_texts(ad: dict, where: str, strict_sum: bool) -> None:
    """Лимиты Директа: длина полей и сумма заголовков.

    Сумма Title+Title2 сверх 52 символов не ошибка API, а предупреждение
    10254: Директ молча отбрасывает Title2 — так раунд 1 остался без вторых
    заголовков. В новых планах это ошибка, в старых (спецификация раунда 1
    хранится как история) — предупреждение.
    """
    for field, key in (("Title", "title1"), ("Title2", "title2"), ("Text", "text")):
        if len(ad[key]) > AD_LIMITS[field]:
            raise SystemExit(
                f"{where}: {field} длиннее {AD_LIMITS[field]}: {len(ad[key])} — «{ad[key]}»")
    total = len(ad["title1"]) + len(ad["title2"])
    if total > AD_LIMITS["TitleSum"]:
        msg = (f"{where}: Title+Title2 = {total} > {AD_LIMITS['TitleSum']} — "
               f"Директ отбросит второй заголовок")
        if strict_sum:
            raise SystemExit(msg)
        print(f"  предупреждение: {msg}")


def check_keyword(phrase: str, where: str) -> None:
    """Фраза Директа — не более семи слов, служебные слова считаются."""
    words = [w for w in phrase.replace('"', " ").replace("+", " ").split() if w]
    if len(words) > 7:
        raise SystemExit(f"{where}: во фразе {len(words)} слов при лимите 7 — «{phrase}»")


def build_ads(spec: dict, group_ids: list[int]) -> dict:
    ads = []
    utm = spec["campaign"]["utm_template"]
    for g, gid in zip(spec["groups"], group_ids):
        href = g["landing"] + "?" + utm.replace("{group}", g["id"])
        for ad in g["ads"]:
            check_ad_texts(ad, g["id"], strict_sum=spec.get("plan_kind") == "extend_campaign")
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


def find_campaign(token: str, name: str) -> int | None:
    existing = call("campaigns", "get",
                    {"SelectionCriteria": {}, "FieldNames": ["Id", "Name", "State"]}, token)
    for c in existing.get("Campaigns") or []:
        if c["Name"] == name:
            return c["Id"]
    return None


def mode_tune(spec: dict, token: str) -> None:
    """Привязка счётчика Метрики, разметка yclid, мониторинг сайта, StartDate."""
    name = spec["campaign"]["name"]
    camp_id = find_campaign(token, name)
    if camp_id is None:
        raise SystemExit(f"кампания «{name}» не найдена — сначала apply")
    counter = spec["campaign"]["metrika_counter_id"]
    payload = {"Campaigns": [{
        "Id": camp_id,
        "StartDate": spec["campaign"]["start_date"],
        "TextCampaign": {
            "CounterIds": {"Items": [counter]},
            "Settings": [
                {"Option": "ADD_METRICA_TAG", "Value": "YES"},
                {"Option": "ENABLE_SITE_MONITORING", "Value": "YES"},
            ],
        },
    }]}
    check_add_results("Campaigns.update", call("campaigns", "update", payload, token),
                      key="UpdateResults")
    print(f"кампания {camp_id} обновлена: счётчик Метрики {counter}, разметка yclid "
          f"включена, мониторинг сайта включён, StartDate {spec['campaign']['start_date']}")


def mode_audit(spec: dict, token: str) -> None:
    """Сверка фактического состояния кампании со спецификацией (только чтение)."""
    name = spec["campaign"]["name"]
    camp_id = find_campaign(token, name)
    if camp_id is None:
        raise SystemExit(f"кампания «{name}» не найдена")
    camp = call("campaigns", "get", {
        "SelectionCriteria": {"Ids": [camp_id]},
        "FieldNames": ["Id", "Name", "State", "Status", "StatusPayment", "StartDate"],
        "TextCampaignFieldNames": ["CounterIds", "Settings"],
    }, token)["Campaigns"][0]
    print(f"кампания {camp['Id']} «{camp['Name']}»")
    print(f"  State={camp['State']} Status={camp['Status']} "
          f"StatusPayment={camp.get('StatusPayment')} StartDate={camp['StartDate']}")
    tc = camp.get("TextCampaign") or {}
    print(f"  счётчики Метрики: {(tc.get('CounterIds') or {}).get('Items')}")
    on = [s["Option"] for s in tc.get("Settings", []) if s.get("Value") == "YES"]
    print(f"  включённые настройки: {', '.join(sorted(on)) or 'нет'}")

    groups = call("adgroups", "get", {
        "SelectionCriteria": {"CampaignIds": [camp_id]},
        "FieldNames": ["Id", "Name", "Status"],
    }, token).get("AdGroups", [])
    for g in groups:
        print(f"  группа {g['Id']} «{g['Name']}»: {g['Status']}")

    ads = call("ads", "get", {
        "SelectionCriteria": {"CampaignIds": [camp_id]},
        "FieldNames": ["Id", "AdGroupId", "State", "Status", "StatusClarification"],
    }, token).get("Ads", [])
    from collections import Counter
    print(f"  объявлений: {len(ads)}; статусы: "
          + ", ".join(f"{k}={v}" for k, v in Counter(a["Status"] for a in ads).items())
          + "; состояния: "
          + ", ".join(f"{k}={v}" for k, v in Counter(a["State"] for a in ads).items()))
    for a in ads:
        note = (a.get("StatusClarification") or "").strip()
        if a["Status"] == "REJECTED" and note:
            print(f"    ОТКЛОНЕНО {a['Id']}: {note[:200]}")

    kws = call("keywords", "get", {
        "SelectionCriteria": {"CampaignIds": [camp_id]},
        "FieldNames": ["Id", "Status"],
    }, token).get("Keywords", [])
    print(f"  фраз: {len(kws)}; статусы: "
          + ", ".join(f"{k}={v}" for k, v in Counter(k_['Status'] for k_ in kws).items()))


# Полное отключение: условие ---autotargeting останавливается целиком.
# Решение руководителя 21.09.2026 — платим только за строгие совпадения
# заданных фраз. Даже EXACT-режим оставляет Директу право подбирать
# «похожие» запросы, а разбор трёх недель показал, чем это кончается:
# 24% расхода ушло на классы C и D, то есть на розницу и смежные услуги.
AUTOTARGETING_OFF = "suspend"

EXACT_ONLY = [
    {"Category": "EXACT", "Value": "YES"},
    {"Category": "ALTERNATIVE", "Value": "NO"},
    {"Category": "COMPETITOR", "Value": "NO"},
    {"Category": "BROADER", "Value": "NO"},
    {"Category": "ACCESSORY", "Value": "NO"},
]


def mode_extend(spec: dict, token: str, apply: bool) -> None:
    """Правка существующей кампании: паузы отработавших групп и новые группы.

    Раунд 2 не создаёт кампанию заново: недельный лимит, стратегия,
    расписание, корректировки ставок и общекампанийные минусы остаются
    как есть. Пауза группы делается остановкой её объявлений — отдельного
    метода остановки групп в API Директа нет; действие обратимо
    (ads.resume). Ничего не удаляется.
    """
    name = spec["campaign"]["name"]
    camp_id = find_campaign(token, name)
    if camp_id is None:
        raise SystemExit(f"кампания «{name}» не найдена — режим extend правит существующую")
    head = "план" if not apply else "применение"
    print(f"== {head}: кампания {camp_id} «{name}» ==")
    print("  бюджет, стратегия, расписание и корректировки не меняются")

    camp = call("campaigns", "get", {
        "SelectionCriteria": {"Ids": [camp_id]},
        "FieldNames": ["Id", "Name", "State", "Status"],
        "TextCampaignFieldNames": ["BiddingStrategy"],
    }, token)["Campaigns"][0]
    strategy = (((camp.get("TextCampaign") or {}).get("BiddingStrategy") or {})
                .get("Search") or {})
    wb = strategy.get("WbMaximumClicks") or {}
    ceiling = wb.get("BidCeiling")
    weekly = wb.get("WeeklySpendLimit")
    if weekly:
        print(f"  недельный лимит в кабинете: {weekly / 1_000_000:.0f} ₽")
    need_ceiling = max(g["max_bid_rub"] for g in spec["groups"])
    if ceiling is not None and ceiling / 1_000_000 < need_ceiling:
        print(f"  ! потолок ставки в кабинете {ceiling / 1_000_000:.0f} ₽ ниже "
              f"{need_ceiling} ₽ из спецификации — новые группы будут ограничены потолком")
    print("  доли бюджета (share) в кабинет не переносятся: стратегия «максимум "
          "кликов» распределяет показы сама, доли — ориентир для разбора итогов")

    live_groups = call("adgroups", "get", {
        "SelectionCriteria": {"CampaignIds": [camp_id]},
        "FieldNames": ["Id", "Name", "Status"],
    }, token).get("AdGroups", [])
    by_name = {g["Name"]: g for g in live_groups}
    live_ads = call("ads", "get", {
        "SelectionCriteria": {"CampaignIds": [camp_id]},
        "FieldNames": ["Id", "AdGroupId", "State", "Status"],
    }, token).get("Ads", [])
    ads_by_group: dict[int, list[dict]] = {}
    for a in live_ads:
        ads_by_group.setdefault(a["AdGroupId"], []).append(a)

    problems: list[str] = []

    print(f"\n== 1. На паузу: групп {len(spec.get('pause', []))} ==")
    to_suspend: list[int] = []
    for item in spec.get("pause", []):
        g = by_name.get(item["group"])
        if g is None:
            problems.append(f"группа «{item['group']}» (раздел pause) в кабинете не найдена")
            print(f"  ! «{item['group']}»: в кабинете нет такой группы")
            continue
        group_ads = ads_by_group.get(g["Id"], [])
        stop = [a for a in group_ads if a["State"] != "SUSPENDED"]
        to_suspend += [a["Id"] for a in stop]
        print(f"  «{g['Name']}» (Id {g['Id']}, {g['Status']})")
        print(f"    факты: {item['facts']}")
        print(f"    причина: {item['reason']}")
        print(f"    остановить объявлений: {len(stop)} из {len(group_ads)}")

    print(f"\n== 2. Остаются работать: групп {len(spec.get('keep', []))} ==")
    for item in spec.get("keep", []):
        g = by_name.get(item["group"])
        if g is None:
            problems.append(f"группа «{item['group']}» (раздел keep) в кабинете не найдена")
            print(f"  ! «{item['group']}»: в кабинете нет такой группы")
            continue
        print(f"  «{g['Name']}» (Id {g['Id']}, {g['Status']}): {item['facts']}")
        print(f"    причина: {item['reason']}")

    untouched = [g["Name"] for g in live_groups
                 if g["Name"] not in {i["group"] for i in spec.get("pause", [])}
                 and g["Name"] not in {i["group"] for i in spec.get("keep", [])}
                 and g["Name"] not in {x["title"] for x in spec["groups"]}]
    if untouched:
        print(f"\n  не упомянуты в спецификации и остаются как есть: "
              + ", ".join(f"«{n}»" for n in untouched))

    utm = spec["campaign"]["utm_template"]
    fresh = [g for g in spec["groups"] if g["title"] not in by_name]
    already = [g["title"] for g in spec["groups"] if g["title"] in by_name]
    print(f"\n== 3. Новые группы: {len(fresh)} из {len(spec['groups'])} ==")
    for title in already:
        print(f"  пропуск «{title}»: группа с таким именем уже есть — не дублирую")
    for g in fresh:
        href = g["landing"] + "?" + utm.replace("{group}", g["id"])
        print(f"  + «{g['title']}» ({g['id']}) → {href}")
        print(f"    зачем: {g['why']}")
        print(f"    потолок ставки по плану: {g['max_bid_rub']} ₽, "
              f"доля бюджета {int(g['share'] * 100)} %, "
              f"порог CPA {g['cpa_limit_rub']} ₽")
        print(f"    правило остановки: {g['stop_rule']}")
        for k in g["keywords"]:
            check_keyword(k["keyword"], g["id"])
            imp = k.get("our_impressions")
            tail = f" (наши показы {imp}, позиция {k.get('our_position')})" if imp else ""
            print(f"    фраза: {k['keyword']}{tail}")
        print(f"    групповые минус-слова ({len(g['minus_words'])}): "
              + (", ".join(g["minus_words"]) or "нет"))
        for ad in g["ads"]:
            check_ad_texts(ad, g["id"], strict_sum=True)
            print(f"    объявление: «{ad['title1']}» / «{ad['title2']}» / {ad['text']}")
            print(f"      длины: {len(ad['title1'])}+{len(ad['title2'])}"
                  f"={len(ad['title1']) + len(ad['title2'])} (лимит {AD_LIMITS['TitleSum']}), "
                  f"текст {len(ad['text'])} (лимит {AD_LIMITS['Text']})")

    if problems:
        raise SystemExit("план не сходится с кабинетом:\n  - " + "\n  - ".join(problems))

    if not apply:
        print(f"\ndry-run завершён: к остановке объявлений — {len(to_suspend)}, "
              f"новых групп — {len(fresh)}; в API запись не выполнялась")
        return

    if to_suspend:
        res = call("ads", "suspend", {"SelectionCriteria": {"Ids": to_suspend}}, token)
        check_add_results("ads.suspend", res, key="SuspendResults")
        print(f"объявлений остановлено: {len(to_suspend)}")

    for g in fresh:
        item = {"Name": g["title"], "CampaignId": camp_id, "RegionIds": [225]}
        if g["minus_words"]:
            item["NegativeKeywords"] = {"Items": g["minus_words"]}
        gid = check_add_results("adgroups.add", call("adgroups", "add", {"AdGroups": [item]}, token))
        if not gid:
            raise SystemExit(f"группа «{g['title']}» не создана")
        gid = gid[0]
        check_add_results("keywords.add", call("keywords", "add", {
            "Keywords": [{"Keyword": k["keyword"], "AdGroupId": gid} for k in g["keywords"]]},
            token))
        href = g["landing"] + "?" + utm.replace("{group}", g["id"])
        ad_items = [{"AdGroupId": gid, "TextAd": {
            "Title": ad["title1"], "Title2": ad["title2"], "Text": ad["text"],
            "Href": href, "Mobile": "NO"}} for ad in g["ads"]]
        ad_ids = [i for i in check_add_results("ads.add", call("ads", "add", {"Ads": ad_items}, token)) if i]
        if ad_ids:
            check_add_results("ads.moderate",
                              call("ads", "moderate", {"SelectionCriteria": {"Ids": ad_ids}}, token),
                              key="ModerateResults")
        kws = call("keywords", "get", {
            "SelectionCriteria": {"AdGroupIds": [gid]},
            "FieldNames": ["Id", "Keyword"]}, token).get("Keywords", [])
        auto = [k["Id"] for k in kws if k["Keyword"] == "---autotargeting"]
        if auto:
            apply_autotargeting(auto, spec, token)
        else:
            print("  ! автотаргетинг новой группы не найден — проверить вручную")
        print(f"группа «{g['title']}» создана: Id {gid}")

    print(f"ГОТОВО: остановлено объявлений {len(to_suspend)}, создано групп {len(fresh)}; "
          f"новые объявления отправлены на модерацию, показы начнутся после её "
          f"прохождения по расписанию пн–пт 9:00–19:00 МСК")


def apply_autotargeting(ids: list[int], spec: dict, token: str) -> None:
    """Режим автотаргетинга новых групп: «off» останавливает его совсем.

    Спецификация без явного указания получает прежнее поведение —
    EXACT-only. Полное отключение задаётся полем campaign.autotargeting.
    """
    mode = (spec.get("campaign") or {}).get("autotargeting", "exact")
    if mode == "off":
        check_add_results("keywords.suspend(автотаргетинг)", call("keywords", "suspend", {
            "SelectionCriteria": {"Ids": ids}}, token), key="SuspendResults")
        print(f"  автотаргетинг отключён полностью: условий {len(ids)}")
        return
    check_add_results("keywords.update(автотаргетинг)", call("keywords", "update", {
        "Keywords": [{"Id": i, "AutotargetingCategories": EXACT_ONLY} for i in ids]},
        token), key="UpdateResults")
    print(f"  автотаргетинг ограничен точными совпадениями: условий {len(ids)}")


def main() -> None:
    modes = ("dry-run", "apply", "tune", "audit")
    if len(sys.argv) != 3 or sys.argv[2] not in modes:
        raise SystemExit(f"использование: direct_apply.py <spec.json> <{'|'.join(modes)}>")
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    mode = sys.argv[2]
    token = os.environ.get("DIRECT_TOKEN", "")
    if not token:
        raise SystemExit("нет токена в DIRECT_TOKEN")

    who = call("clients", "get", {"FieldNames": ["Login", "Currency"]}, token)
    info = (who.get("Clients") or [{}])[0]
    print(f"кабинет: {info.get('Login')} ({info.get('Currency')})")

    if mode == "tune":
        mode_tune(spec, token)
        return
    if mode == "audit":
        mode_audit(spec, token)
        return

    if spec.get("plan_kind", "create_campaign") == "extend_campaign":
        mode_extend(spec, token, apply=(mode == "apply"))
        return

    if spec.get("plan_kind", "create_campaign") == "extend_campaign":
        mode_extend(spec, token, apply=(mode == "apply"))
        return

    existing = call("campaigns", "get",
                    {"SelectionCriteria": {}, "FieldNames": ["Id", "Name", "State"]}, token)
    name = spec["campaign"]["name"]
    existing_id = None
    for c in existing.get("Campaigns") or []:
        print(f"  существующая кампания: {c['Id']} «{c['Name']}» {c['State']}")
        if c["Name"] == name:
            existing_id = c["Id"]

    # Кампания с таким именем уже есть. Дубль не создаём никогда, но пустую
    # кампанию дозаполняем: прогон может упасть между созданием кампании и
    # добавлением групп (21.09.2026 так и вышло — кампания 714629311
    # осталась без единой группы), и без этой ветки её нельзя ни достроить,
    # ни пересоздать под тем же именем.
    if existing_id is not None:
        groups = call("adgroups", "get", {
            "SelectionCriteria": {"CampaignIds": [existing_id]},
            "FieldNames": ["Id"],
        }, token)
        if groups.get("AdGroups"):
            raise SystemExit(
                f"кампания «{name}» уже существует (Id {existing_id}) и наполнена "
                f"({len(groups['AdGroups'])} групп) — дубль не создаю")
        print(f"кампания «{name}» уже создана (Id {existing_id}), но пуста — дозаполняю")

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

    if existing_id is None:
        camp_id = check_add_results("Campaigns", call("campaigns", "add", camp_payload, token))[0]
        print(f"кампания создана: Id {camp_id}")
    else:
        camp_id = existing_id
        print(f"кампания уже была создана: Id {camp_id}")

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

    # Автотаргетинг Директ заводит в новой группе сам. Пока его режим не
    # задан, группа показывается по «похожим» запросам — на этом прошлая
    # кампания потеряла 24% расхода.
    auto = [k["Id"] for k in call("keywords", "get", {
        "SelectionCriteria": {"AdGroupIds": group_ids},
        "FieldNames": ["Id", "Keyword"]}, token).get("Keywords", [])
        if k["Keyword"] == "---autotargeting"]
    if auto:
        apply_autotargeting(auto, spec, token)
    else:
        print("  ! автотаргетинг новых групп не найден — проверить вручную")

    call("ads", "moderate", {"SelectionCriteria": {"Ids": ad_ids}}, token)
    print("объявления отправлены на модерацию")
    # Текст расписания берётся из спецификации: до раунда 3 строка «пн–пт
    # 9:00–19:00» была зашита и в журнале issue #22 расходилась с фактическим
    # ежедневным расписанием кампаний подарочных карт Apple (05.09.2026).
    schedule_note = spec["campaign"].get("schedule") or "пн–пт 9:00–19:00 МСК"
    print(f"ГОТОВО: кампания «{name}» (Id {camp_id}) создана; показы начнутся "
          f"{spec['campaign']['start_date']} по расписанию {schedule_note} "
          f"после модерации и при положительном балансе кабинета")


if __name__ == "__main__":
    main()
