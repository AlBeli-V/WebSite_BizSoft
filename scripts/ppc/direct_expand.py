#!/usr/bin/env python3
"""Расширение кампании bs-test-2026-09 по поручению владельца 29.08.2026.

Три изменения одним прогоном:
  1. Title/Title2 семи существующих объявлений: при создании Title2 не
     применился ни у одного (предупреждение 10254 — суммарная длина
     заголовков сверх лимита комбинаторного формата). Заголовки укорочены,
     B2B-фильтр возвращён в Title2. Обновление отправляет объявления на
     перемодерацию — прогон рассчитан на выходные, когда показов нет.
  2. Две новые группы под товарные запросы с наибольшим чистым
     коммерческим спросом Вордстата (замер 27.08), чтобы компенсировать
     ожидаемое падение объёма после EXACT-only автотаргетинга:
     Cursor (8 374 показов/мес, растёт, чистый B2B-dev интент) и
     Adobe (23 322 показов/мес, класс GAP-F «исследование платного
     канала»). Бюджет кампании НЕ увеличивается.
  3. Автотаргетинг новых групп сразу ограничивается категорией EXACT
     (полный discovery остаётся только в Claude Code — решение PPC-D-005).

Режимы:
  dry-run — напечатать текущие тексты и весь план, в API только чтение;
  apply   — применить и отправить новые объявления на модерацию.

Деньги, платёжные настройки, чужие кампании — не трогает.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"
CAMPAIGN_NAME = "bs-test-2026-09"
UTM = ("utm_source=yandex&utm_medium=cpc&utm_campaign=bs-test-2026-09"
       "&utm_content={group}&utm_term={keyword}")

# Лимиты Директа; 10254 показал, что для комбинаторного формата суммарная
# длина Title+Title2 тоже ограничена — держим её не выше 52.
AD_LIMITS = {"Title": 56, "Title2": 30, "Text": 81, "TitleSum": 52}

# Новые заголовки существующих объявлений: ключ — текущий Title.
RETITLE = {
    "Claude для компании — счёт, НДС, договор":
        ("Claude для компании", "Счёт, НДС, договор"),
    "Подписка Claude на юрлицо — оформим официально":
        ("Подписка Claude на юрлицо", "Счёт и закрывающие"),
    "Claude Code для команды — только юрлицам":
        ("Claude Code для команды", "Только юрлицам"),
    "Claude Code для отдела разработки — по счёту":
        ("Claude Code — по счёту", "Для отделов разработки"),
    "Midjourney для компании — оплата по счёту":
        ("Midjourney для компании", "Счёт, НДС, только юрлицам"),
    "Midjourney на юрлицо — легально из России":
        ("Midjourney на юрлицо", "Оплата по счёту из России"),
    "ChatGPT для компании — от 2 рабочих мест":
        ("ChatGPT для компании", "Счёт, договор, НДС"),
}

# Новые группы: спрос — Вордстат 27.08 (см. direct-audit-2026-08-29.md).
NEW_GROUPS = [
    {
        "name": "Cursor — редактор для команд разработки",
        "landing": "https://biz-soft.pro/vendors/cursor",
        "utm_content": "cursor",
        # cursor — омоним (курсор мыши, CSS): групповые минусы.
        "negative": ["мышь", "мыши", "мышка", "css", "html", "sql",
                     "excel", "word", "юникод", "символ"],
        "phrases": [
            "cursor купить",
            "купить cursor",
            "cursor подписка",
            "оплатить cursor",
            "cursor pro купить",
            "cursor business купить",
            "cursor +для команды",
            "cursor подписка +для компании",
            "cursor цена",
            "cursor стоимость",
        ],
        "ads": [
            ("Cursor для команд разработки", "Счёт, договор, ЭДО",
             "Оплатим подписку Cursor в рублях по счёту. Закрывающие через ЭДО. Юрлицам."),
            ("Cursor Business на юрлицо", "Оплата по счёту из России",
             "Подписки Cursor для компаний. Договор, НДС, закрывающие. Физлицам не оформляем."),
        ],
    },
    {
        "name": "Adobe — подписки для юрлиц",
        "landing": "https://biz-soft.pro/vendors/adobe",
        "utm_content": "adobe",
        "negative": [],
        "phrases": [
            "adobe купить",
            "adobe подписка",
            "лицензия adobe",
            "купить лицензию adobe",
            "adobe +для юридических лиц",
            "оплатить adobe",
            "adobe creative cloud купить",
            "adobe подписка +для компании",
        ],
        "ads": [
            ("Adobe для юридических лиц", "Счёт, договор, ЭДО",
             "Оплата подписок Adobe по счёту в рублях. Закрывающие документы. Юрлицам."),
            ("Подписка Adobe на юрлицо", "Оплата по счёту из России",
             "Creative Cloud для компаний. Договор, НДС, закрывающие. Физлицам не оформляем."),
        ],
    },
]

EXACT_ONLY = [
    {"Category": "EXACT", "Value": "YES"},
    {"Category": "ALTERNATIVE", "Value": "NO"},
    {"Category": "COMPETITOR", "Value": "NO"},
    {"Category": "BROADER", "Value": "NO"},
    {"Category": "ACCESSORY", "Value": "NO"},
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


def check_results(label: str, result: dict, key: str) -> list[int]:
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


def validate_ad(t1: str, t2: str, text: str) -> None:
    assert len(t1) <= AD_LIMITS["Title"], f"Title длиннее {AD_LIMITS['Title']}: {t1!r}"
    assert len(t2) <= AD_LIMITS["Title2"], f"Title2 длиннее {AD_LIMITS['Title2']}: {t2!r}"
    assert len(text) <= AD_LIMITS["Text"], f"Text длиннее {AD_LIMITS['Text']}: {text!r}"
    assert len(t1) + len(t2) <= AD_LIMITS["TitleSum"], \
        f"Title+Title2 длиннее {AD_LIMITS['TitleSum']}: {t1!r} + {t2!r}"


def main() -> None:
    token = os.environ.get("DIRECT_TOKEN", "")
    if not token:
        raise SystemExit("DIRECT_TOKEN не задан")
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry-run"
    if mode not in ("dry-run", "apply"):
        raise SystemExit(f"неизвестный режим: {mode}")
    print(f"Режим: {mode}")

    for t1, t2 in RETITLE.values():
        assert len(t1) + len(t2) <= AD_LIMITS["TitleSum"]
    for g in NEW_GROUPS:
        for t1, t2, text in g["ads"]:
            validate_ad(t1, t2, text)

    camps = call("campaigns", "get",
                 {"SelectionCriteria": {}, "FieldNames": ["Id", "Name"]}, token).get("Campaigns", [])
    camp = next((c for c in camps if c["Name"] == CAMPAIGN_NAME), None)
    if camp is None:
        raise SystemExit(f"Кампания «{CAMPAIGN_NAME}» не найдена")
    cid = camp["Id"]

    groups = call("adgroups", "get",
                  {"SelectionCriteria": {"CampaignIds": [cid]},
                   "FieldNames": ["Id", "Name"]}, token).get("AdGroups", [])
    existing_group_names = {g["Name"] for g in groups}

    # 1. Title/Title2 существующих объявлений.
    ads = call("ads", "get",
               {"SelectionCriteria": {"CampaignIds": [cid]},
                "FieldNames": ["Id", "AdGroupId", "State", "Status"],
                "TextAdFieldNames": ["Title", "Title2", "Text"]},
               token).get("Ads", [])
    print(f"\n== 1. Заголовки существующих объявлений ({len(ads)}) ==")
    retitle_items = []
    for a in ads:
        ta = a.get("TextAd") or {}
        cur = ta.get("Title") or ""
        if cur in RETITLE:
            t1, t2 = RETITLE[cur]
            print(f"  ~ id {a['Id']}: «{cur}» / «{ta.get('Title2')}» → «{t1}» / «{t2}»")
            retitle_items.append({"Id": a["Id"], "TextAd": {"Title": t1, "Title2": t2}})
        else:
            print(f"  = id {a['Id']}: «{cur}» — без изменений (нет в карте)")
    if mode == "apply" and retitle_items:
        res = call("ads", "update", {"Ads": retitle_items}, token)
        check_results("ads.update", res, "UpdateResults")

    # 2. Новые группы.
    print("\n== 2. Новые группы ==")
    for spec in NEW_GROUPS:
        if spec["name"] in existing_group_names:
            print(f"  = уже существует: «{spec['name']}» — пропуск")
            continue
        print(f"  + «{spec['name']}» → {spec['landing']}")
        print(f"    фраз: {len(spec['phrases'])}, групповых минусов: {len(spec['negative'])}")
        for t1, t2, text in spec["ads"]:
            print(f"    объявление: «{t1}» / «{t2}» / {text}")
        if mode != "apply":
            continue
        add_item = {"Name": spec["name"], "CampaignId": cid, "RegionIds": [225]}
        if spec["negative"]:
            add_item["NegativeKeywords"] = {"Items": spec["negative"]}
        res = call("adgroups", "add", {"AdGroups": [add_item]}, token)
        gids = check_results("adgroups.add", res, "AddResults")
        if not gids or gids[0] is None:
            raise SystemExit(f"группа «{spec['name']}» не создана")
        gid = gids[0]

        res = call("keywords", "add",
                   {"Keywords": [{"Keyword": p, "AdGroupId": gid} for p in spec["phrases"]]},
                   token)
        check_results("keywords.add", res, "AddResults")

        href = spec["landing"] + "?" + UTM.replace("{group}", spec["utm_content"])
        ad_items = [{"AdGroupId": gid,
                     "TextAd": {"Title": t1, "Title2": t2, "Text": text,
                                "Href": href, "Mobile": "NO"}}
                    for t1, t2, text in spec["ads"]]
        res = call("ads", "add", {"Ads": ad_items}, token)
        ad_ids = [i for i in check_results("ads.add", res, "AddResults") if i]
        if ad_ids:
            res = call("ads", "moderate", {"SelectionCriteria": {"Ids": ad_ids}}, token)
            check_results("ads.moderate", res, "ModerateResults")

        # Автотаргетинг новой группы сразу в EXACT-only.
        kws = call("keywords", "get",
                   {"SelectionCriteria": {"AdGroupIds": [gid]},
                    "FieldNames": ["Id", "Keyword"]}, token).get("Keywords", [])
        auto_ids = [k["Id"] for k in kws if k["Keyword"] == "---autotargeting"]
        if auto_ids:
            res = call("keywords", "update",
                       {"Keywords": [{"Id": i, "AutotargetingCategories": EXACT_ONLY}
                                     for i in auto_ids]}, token)
            check_results("keywords.update(autotargeting)", res, "UpdateResults")
        else:
            print("  ! автотаргетинг в новой группе не найден — проверить вручную")

    # 3. Сверка.
    if mode == "apply":
        groups2 = call("adgroups", "get",
                       {"SelectionCriteria": {"CampaignIds": [cid]},
                        "FieldNames": ["Id", "Name", "Status", "ServingStatus"]},
                       token).get("AdGroups", [])
        ads2 = call("ads", "get",
                    {"SelectionCriteria": {"CampaignIds": [cid]},
                     "FieldNames": ["Id", "AdGroupId", "State", "Status"],
                     "TextAdFieldNames": ["Title", "Title2"]},
                    token).get("Ads", [])
        gname = {g["Id"]: g["Name"] for g in groups2}
        print("\n== Итог сверки ==")
        print(f"  групп: {len(groups2)}")
        for g in groups2:
            print(f"  - «{g['Name']}» {g.get('Status')}/{g.get('ServingStatus')}")
        print(f"  объявлений: {len(ads2)}")
        for a in ads2:
            ta = a.get("TextAd") or {}
            print(f"  - [{gname.get(a['AdGroupId'], '?')}] «{ta.get('Title')}» / "
                  f"«{ta.get('Title2')}» {a.get('State')}/{a.get('Status')}")


if __name__ == "__main__":
    main()
