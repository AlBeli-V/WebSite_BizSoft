#!/usr/bin/env python3
"""Затяжка кампании bs-test-2026-09 по поручению владельца 31.08.2026.

Основание — статистика двух дней открутки (28.08 и 31.08, ops-direct
(action=stats) в issue #22). EXACT-only автотаргетинг в группах вне Claude Code доказал
эффективность (мусор Midjourney: 185 ₽ в пятницу → 0 в понедельник), а
discovery-автотаргетинг Claude Code дал ~65 % кликов дня и почти весь
класс C: информационные хвосты и чужой бренд Google Cloud Code.

Три изменения одним прогоном:
  1. Автотаргетинг группы Claude Code → только «целевые запросы» (EXACT).
     Discovery-режим своё отработал: запросы двух дней собраны, целевые
     формулировки переносятся в фразы этим же прогоном.
  2. Групповые минусы Claude Code по фактам двух дней, включая «cloud»:
     вопрос «опечатка ли cloud code» закрыт данными — 51 показ, 9 кликов,
     ~106 ₽, все запросы про Google Cloud Code, признаков нашего интента нет.
  3. Перенос целевых формулировок из поисковых запросов в фразы
     (механизм P3 аудита: запрос → ключ): оплата Claude из России,
     ChatGPT для юрлиц, цена/тарифы Claude Code.

Чего пакет сознательно НЕ делает:
  - не минусует голый «claude code»: минус-фраза срезала бы и собственные
    фразы группы; оценка бренд-трафика — по секции поведения по запросам
    в ops-direct (action=stats) (отказы/глубина), решение после недели данных;
  - не трогает бюджет, стратегию, расписание, чужие кампании и деньги.

Режимы:
  dry-run — напечатать план, в API только чтение;
  apply   — применить изменения в кабинете.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"
CAMPAIGN_NAME = "bs-test-2026-09"
TARGET_GROUP = "Claude Code — для команд разработки"

EXACT_ONLY = [
    {"Category": "EXACT", "Value": "YES"},
    {"Category": "ALTERNATIVE", "Value": "NO"},
    {"Category": "COMPETITOR", "Value": "NO"},
    {"Category": "BROADER", "Value": "NO"},
    {"Category": "ACCESSORY", "Value": "NO"},
]

# Групповые минусы Claude Code — по фактическим запросам 28.08 и 31.08.
# Кампанийные минусы (что/это/обзор/установка/github и т.д.) стоят с 29.08
# (direct_improve) и здесь не дублируются. «россия/рф» не минусуются —
# «оплата из России» и есть оффер.
GROUP_NEGATIVES_ADD = [
    "cloud",          # Google Cloud Code: 9 кликов, ~106 ₽, конверсий нет
    "пользоваться",   # «как пользоваться claude code»
    "использовать",   # «claude code как использовать в россии»
    "использование",
    "русский",        # «claude code на русском»
    "онлайн",         # «claude code онлайн» — использование, не покупка
    "агент",          # «агенты claude code»
    "нейросеть",      # «клауд код нейросеть»
    "кастомный",      # «claude code с кастомными моделями»
    "setup",          # англоязычные use-хвосты без интента покупки
    "skills",
    "practice",
]

# Перенос запросов двух дней в фразы. Дубли с уже существующими фразами
# отсеиваются на месте (сверка по точному тексту в той же группе).
NEW_PHRASES = {
    "Claude — подписки для компаний": [
        "как оплатить claude",         # 6 формулировок дня, 2 клика
        "оплатить claude +из россии",  # ядро оффера
    ],
    TARGET_GROUP: [
        "claude code цена",            # клик 31.08
        "claude code тарифы",
        "клауд код тарифы",            # транскрипция, клик 31.08
    ],
    "ChatGPT Business — гипотеза с фильтром до клика": [
        "chatgpt +для юрлица",
        "chat gpt +для юр лица",         # запрос «чат gpt 5 для юр лица»
        "подключение chat gpt business", # запрос «подключение chat gpt business рф»
    ],
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


def print_results(label: str, result: dict, key: str) -> None:
    for i, r in enumerate(result.get(key, [])):
        if r.get("Errors"):
            e = r["Errors"][0]
            print(f"  {label}[{i}]: ОШИБКА {e.get('Code')} {e.get('Message')} — {e.get('Details')}")
        else:
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
                   "FieldNames": ["Id", "Name", "NegativeKeywords"]},
                  token).get("AdGroups", [])
    gid_by_name = {g["Name"]: g["Id"] for g in groups}
    gname_by_id = {g["Id"]: g["Name"] for g in groups}
    target = next((g for g in groups if g["Name"] == TARGET_GROUP), None)
    if target is None:
        raise SystemExit(f"группа не найдена: {TARGET_GROUP}")

    kws = call("keywords", "get",
               {"SelectionCriteria": {"CampaignIds": [cid]},
                "FieldNames": ["Id", "Keyword", "AdGroupId"]},
               token).get("Keywords", [])
    existing_phrases = {(k["AdGroupId"], k["Keyword"]) for k in kws}

    # 1. Автотаргетинг Claude Code → EXACT-only (последняя discovery-группа).
    autos = [k for k in kws
             if k["Keyword"] == "---autotargeting" and k["AdGroupId"] == target["Id"]]
    print(f"\n== 1. Автотаргетинг «{TARGET_GROUP}» → только «целевые запросы» ==")
    if not autos:
        print("  ! условие ---autotargeting в группе не найдено — проверить вручную")
    for k in autos:
        print(f"  - id {k['Id']} → EXACT=YES, остальные категории NO")
    if mode == "apply" and autos:
        res = call("keywords", "update",
                   {"Keywords": [{"Id": k["Id"], "AutotargetingCategories": EXACT_ONLY}
                                 for k in autos]}, token)
        print_results("keywords.update", res, "UpdateResults")

    # 2. Групповые минусы Claude Code: объединение с текущими, без дублей.
    current_neg = (target.get("NegativeKeywords") or {}).get("Items") or []
    merged, seen = [], set()
    for w in current_neg + GROUP_NEGATIVES_ADD:
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            merged.append(w)
    added = [w for w in merged if w.lower() not in {x.lower() for x in current_neg}]
    print(f"\n== 2. Минусы группы «{TARGET_GROUP}»: было {len(current_neg)}, "
          f"станет {len(merged)} (новых {len(added)}) ==")
    print("  добавка: " + (", ".join(added) or "(нечего добавлять)"))
    total_len = sum(len(w) for w in merged)
    if total_len > 4000:
        raise SystemExit(f"суммарная длина групповых минусов {total_len} > 4000")
    if mode == "apply" and added:
        res = call("adgroups", "update",
                   {"AdGroups": [{"Id": target["Id"],
                                  "NegativeKeywords": {"Items": merged}}]}, token)
        print_results("adgroups.update", res, "UpdateResults")

    # 3. Перенос запросов в фразы.
    to_add = []
    print("\n== 3. Новые фразы из поисковых запросов двух дней ==")
    for gname, phrases in NEW_PHRASES.items():
        gid = gid_by_name.get(gname)
        if gid is None:
            print(f"  ! группа не найдена: {gname}")
            continue
        for p in phrases:
            if (gid, p) in existing_phrases:
                print(f"  = уже есть: [{gname}] «{p}»")
                continue
            to_add.append({"Keyword": p, "AdGroupId": gid})
            print(f"  + [{gname}] «{p}»")
    if mode == "apply" and to_add:
        res = call("keywords", "add", {"Keywords": to_add}, token)
        print_results("keywords.add", res, "AddResults")

    # 4. Контрольное чтение после применения.
    if mode == "apply":
        try:
            kws2 = call("keywords", "get",
                        {"SelectionCriteria": {"CampaignIds": [cid]},
                         "FieldNames": ["Id", "Keyword", "AdGroupId",
                                        "AutotargetingCategories"]},
                        token).get("Keywords", [])
            with_cats = True
        except SystemExit as e:
            print(f"  (категории в keywords.get не читаются: {e})")
            kws2 = call("keywords", "get",
                        {"SelectionCriteria": {"CampaignIds": [cid]},
                         "FieldNames": ["Id", "Keyword", "AdGroupId"]},
                        token).get("Keywords", [])
            with_cats = False
        groups2 = call("adgroups", "get",
                       {"SelectionCriteria": {"Ids": [target["Id"]]},
                        "FieldNames": ["Id", "NegativeKeywords"]},
                       token).get("AdGroups", [])
        print("\n== Итог сверки ==")
        if with_cats:
            for k in kws2:
                if k["Keyword"] == "---autotargeting":
                    raw = k.get("AutotargetingCategories") or []
                    cats = ", ".join(
                        f"{c['Category']}={c['Value']}" if isinstance(c, dict) else str(c)
                        for c in raw)
                    print(f"  автотаргетинг «{gname_by_id.get(k['AdGroupId'], k['AdGroupId'])}»: "
                          f"{cats or 'категории не отдаются'}")
        n_phrases = sum(1 for k in kws2 if k["Keyword"] != "---autotargeting")
        n_neg = len((groups2[0].get("NegativeKeywords") or {}).get("Items") or []) if groups2 else 0
        print(f"  фраз в кампании: {n_phrases}")
        print(f"  минусов группы «{TARGET_GROUP}»: {n_neg}")


if __name__ == "__main__":
    main()
