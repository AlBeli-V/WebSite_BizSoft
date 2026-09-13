#!/usr/bin/env python3
"""Выравнивание автотаргетинга кампаний по их целевому режиму.

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

Кампании Apple (13.09.2026) получают другой набор — всё, кроме
сопутствующих запросов. Его выбрала матрица категорий, собранная
ops-direct (action=autotargeting-audit): из пяти категорий проблемная
ровно одна. ACCESSORY взяла 2918,87 ₽ расхода и дала 382 клика мимо
покупательского интента против 181 в него — доля целевых денег 39 %.
Остальные категории чисты: EXACT 96 %, NARROW 87 %, BROADER 85 %,
ALTERNATIVE 100 %. Поэтому сопутствующие выключаются, а широкие и
альтернативные, которые по первому впечатлению выглядели кандидатами на
отключение, остаются работать.

Меняется ровно одна категория: так следующий замер ответит, что именно
дало эффект.

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

EXACT_ONLY = [
    {"Category": "EXACT", "Value": "YES"},
    {"Category": "ALTERNATIVE", "Value": "NO"},
    {"Category": "COMPETITOR", "Value": "NO"},
    {"Category": "BROADER", "Value": "NO"},
    {"Category": "ACCESSORY", "Value": "NO"},
]
# Кампании Apple: выключены только сопутствующие запросы. Конкурентная
# категория за период наблюдения не дала ни рубля, поэтому её значение не
# трогается — менять её заодно значило бы смешать два изменения в одном.
NO_ACCESSORY = [
    {"Category": "EXACT", "Value": "YES"},
    {"Category": "ALTERNATIVE", "Value": "YES"},
    {"Category": "COMPETITOR", "Value": "YES"},
    {"Category": "BROADER", "Value": "YES"},
    {"Category": "ACCESSORY", "Value": "NO"},
]

# Целевой режим по кампаниям. Кампания вне списка не трогается.
TARGETS = {
    "bs-test-2026-09": EXACT_ONLY,
    "bs-apple-gift-2026-09": NO_ACCESSORY,
    "bs-apple-regions-2026-09": NO_ACCESSORY,
}


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
    targets = [c for c in camps if c["Name"] in TARGETS]
    for name in TARGETS:
        if name not in {c["Name"] for c in targets}:
            print(f"  ! кампания не найдена: «{name}»")
    if not targets:
        raise SystemExit("ни одной кампании из списка не найдено")

    updates: list[dict] = []
    for camp in sorted(targets, key=lambda c: c["Name"]):
        want_list = TARGETS[camp["Name"]]
        want = {c["Category"]: c["Value"] for c in want_list}
        on_want = ", ".join(c for c, v in sorted(want.items()) if v == "YES")
        print(f"\n== «{camp['Name']}» (id {camp['Id']}) → {on_want} ==")

        groups = call("adgroups", "get",
                      {"SelectionCriteria": {"CampaignIds": [camp["Id"]]},
                       "FieldNames": ["Id", "Name"]}, token).get("AdGroups", [])
        gname = {g["Id"]: g["Name"] for g in groups}
        kws = call("keywords", "get",
                   {"SelectionCriteria": {"CampaignIds": [camp["Id"]]},
                    "FieldNames": ["Id", "Keyword", "AdGroupId",
                                   "AutotargetingCategories"]},
                   token).get("Keywords", [])
        autos = [k for k in kws if k["Keyword"] == "---autotargeting"]
        print(f"  условий автотаргетинга: {len(autos)}")

        for k in sorted(autos, key=lambda x: gname.get(x["AdGroupId"], "")):
            name = gname.get(k["AdGroupId"], k["AdGroupId"])
            cats = categories_of(k)
            if cats is None:
                updates.append((camp["Name"], k["Id"], want_list))
                print(f"  ? «{name}» — категории API не отдал, выравниваем на всякий случай")
            elif cats == want:
                print(f"  = «{name}» — уже целевой режим")
            else:
                on = ", ".join(c for c, v in sorted(cats.items()) if v == "YES") or "ничего"
                updates.append((camp["Name"], k["Id"], want_list))
                print(f"  ~ «{name}» — включено: {on} → приводим к целевому")

    print(f"\n== Итог: выровнять {len(updates)} условий ==")
    if not updates:
        print("  расхождений нет — кабинет однороден")
        return
    if mode != "apply":
        print("\ndry-run завершён — изменений нет.")
        return

    res = call("keywords", "update",
               {"Keywords": [{"Id": kid, "AutotargetingCategories": want_list}
                             for _, kid, want_list in updates]}, token)
    for i, r in enumerate(res.get("UpdateResults", [])):
        if r.get("Errors"):
            e = r["Errors"][0]
            print(f"  keywords.update[{i}]: ОШИБКА {e.get('Code')} {e.get('Message')} — {e.get('Details')}")
        else:
            print(f"  keywords.update[{i}]: OK id={r.get('Id')}")

    print("\n== Итог сверки ==")
    for camp in sorted(targets, key=lambda c: c["Name"]):
        want = {c["Category"]: c["Value"] for c in TARGETS[camp["Name"]]}
        kws2 = call("keywords", "get",
                    {"SelectionCriteria": {"CampaignIds": [camp["Id"]]},
                     "FieldNames": ["Id", "Keyword", "AdGroupId",
                                    "AutotargetingCategories"]},
                    token).get("Keywords", [])
        autos = [k for k in kws2 if k["Keyword"] == "---autotargeting"]
        ok = sum(1 for k in autos if categories_of(k) == want)
        print(f"  «{camp['Name']}»: целевой режим у {ok} из {len(autos)} условий")
    print("  (категории API при чтении не отдаёт — ноль здесь означает "
          "«прочитать нечем», а не «не применилось»; проверка — по разрезу "
          "TargetingCategory в следующем замере)")


if __name__ == "__main__":
    main()
