#!/usr/bin/env python3
"""Выравнивание автотаргетинга кампании bs-test-2026-09 по режиму EXACT-only.

Поручение владельца 04.09.2026. Раунд 2 завёл четыре группы
(«Зарубежное ПО», Atlassian, «Box и Dropbox», Descript), не задав им
автотаргетинг: Директ включил его в полном режиме — том самом, что
дважды отключали 29.08 и 31.08 за увод трафика в мусор. Результат виден
в ленте кандидатов 03.09: «подключение к электронному документообороту
стоимость» 42,37 ₽ и «финансовые услуги по оплате за границу» 40,70 ₽ —
смежные услуги, которых нет в нашем оффере, по цене втрое выше обычного
клика.

Скрипт не привязан к списку групп: он читает фактические категории
каждого условия ---autotargeting и выравнивает те, что отличаются от
EXACT-only. Поэтому любая новая группа, заведённая позже без явного
указания режима, будет поймана следующим прогоном.

Режимы:
  dry-run — показать, у каких групп режим отличается, в API только чтение;
  apply   — выровнять расходящиеся группы.

Ставки, бюджет, стратегию, фразы, объявления и чужие кампании не трогает.
Категории автотаргетинга применяются мгновенно, перемодерации не требуют.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"
CAMPAIGN_NAME = "bs-test-2026-09"

EXACT_ONLY = [
    {"Category": "EXACT", "Value": "YES"},
    {"Category": "ALTERNATIVE", "Value": "NO"},
    {"Category": "COMPETITOR", "Value": "NO"},
    {"Category": "BROADER", "Value": "NO"},
    {"Category": "ACCESSORY", "Value": "NO"},
]
WANT = {c["Category"]: c["Value"] for c in EXACT_ONLY}


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


def categories_of(kw: dict) -> dict[str, str] | None:
    """Категории условия в виде {категория: YES|NO}; None — API их не отдал."""
    raw = kw.get("AutotargetingCategories")
    if not raw:
        return None
    out = {}
    for c in raw:
        if isinstance(c, dict) and "Category" in c:
            out[c["Category"]] = c.get("Value")
    return out or None


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

    kws = call("keywords", "get",
               {"SelectionCriteria": {"CampaignIds": [cid]},
                "FieldNames": ["Id", "Keyword", "AdGroupId",
                               "AutotargetingCategories"]},
               token).get("Keywords", [])
    autos = [k for k in kws if k["Keyword"] == "---autotargeting"]
    print(f"Кампания {cid}, условий автотаргетинга: {len(autos)}")

    print("\n== Режим по группам ==")
    diverged, unknown = [], []
    for k in sorted(autos, key=lambda x: gname.get(x["AdGroupId"], "")):
        name = gname.get(k["AdGroupId"], k["AdGroupId"])
        cats = categories_of(k)
        if cats is None:
            unknown.append(k)
            print(f"  ? «{name}» — категории API не отдал, выравниваем на всякий случай")
            continue
        if cats == WANT:
            print(f"  = «{name}» — уже EXACT-only")
        else:
            on = ", ".join(c for c, v in sorted(cats.items()) if v == "YES") or "ничего"
            diverged.append(k)
            print(f"  ~ «{name}» — включено: {on} → приводим к EXACT-only")

    to_fix = diverged + unknown
    print(f"\n== Итог: выровнять {len(to_fix)} из {len(autos)} ==")
    if not to_fix:
        print("  расхождений нет — кампания уже однородна")
        return
    if mode != "apply":
        print("\ndry-run завершён — изменений нет.")
        return

    res = call("keywords", "update",
               {"Keywords": [{"Id": k["Id"], "AutotargetingCategories": EXACT_ONLY}
                             for k in to_fix]}, token)
    for i, r in enumerate(res.get("UpdateResults", [])):
        if r.get("Errors"):
            e = r["Errors"][0]
            print(f"  keywords.update[{i}]: ОШИБКА {e.get('Code')} {e.get('Message')} — {e.get('Details')}")
        else:
            print(f"  keywords.update[{i}]: OK id={r.get('Id')}")

    kws2 = call("keywords", "get",
                {"SelectionCriteria": {"CampaignIds": [cid]},
                 "FieldNames": ["Id", "Keyword", "AdGroupId",
                                "AutotargetingCategories"]},
                token).get("Keywords", [])
    ok = sum(1 for k in kws2
             if k["Keyword"] == "---autotargeting" and categories_of(k) == WANT)
    total = sum(1 for k in kws2 if k["Keyword"] == "---autotargeting")
    print(f"\n== Итог сверки ==\n  EXACT-only: {ok} из {total} условий")
    if ok < total:
        print("  (часть категорий API не отдаёт при чтении — проверить следующим прогоном)")


if __name__ == "__main__":
    main()
