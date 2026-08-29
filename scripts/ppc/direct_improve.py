#!/usr/bin/env python3
"""Оздоровление кампании bs-test-2026-09 по итогам первого дня открутки.

Поручение владельца 29.08.2026: убрать автотаргетинг, добавить минус-слова,
расшить фразовую семантику. Разбор дня 28.08 (issue #22, ops-direct-stats):
фразы дали 3 показа и 0 кликов, все 18 кликов и 591 ₽ принёс автотаргетинг,
из них ~половина — запросы без покупательского B2B-интента.

Режимы:
  dry-run — напечатать план изменений, в API только чтение;
  apply   — применить: suspend автотаргетингов, замена минус-списка
            кампании, добавление широких фраз.

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

# Минус-слова v3 (28 слов, поручение владельца 28.08) — сохраняются.
NEGATIVES_V3 = [
    "бесплатно", "бесплатный", "бесплатная", "скачать", "торрент", "взлом",
    "кряк", "промокод", "купон", "зеркало", "телеграм", "бот", "аккаунт",
    "аккаунты", "студент", "студенту", "школьник", "себя", "личный",
    "личная", "триал", "пробный", "пробная", "халява", "vpn", "картой",
    "реферал", "подарок",
]

# Добавка 29.08 — по фактическим поисковым запросам первого дня и типовым
# информационным хвостам, которые оживут при широком соответствии фраз.
# «как» НЕ минусуется: «как купить/оплатить X» — целевой интент.
NEGATIVES_NEW = [
    # факты дня 28.08
    "что", "это", "free", "дешево", "дешевый", "дешевле", "cloud",
    "сметчик", "сметчиков", "ходатайство", "логотип", "логотипа",
    "логотипы", "картинка", "картинки", "картинку", "изображение",
    "изображения", "яндекс", "системные", "требования", "попробовать",
    # информационные хвосты
    "чем", "какой", "какая", "зачем", "почему", "можно", "может",
    "обзор", "отзывы", "пример", "примеры", "инструкция", "гайд",
    "документация", "урок", "уроки", "курс", "курсы", "обучение",
    "альтернатива", "альтернативы", "аналог", "аналоги", "сравнение",
    "тест", "лимит", "лимиты",
    # технические запросы разработчиков без покупки
    "github", "плагин", "плагины", "plugin", "расширение", "extension",
    "review", "desktop", "установка", "установить", "настройка",
    "настроить", "windows", "linux", "macos",
]

# Широкие фразы взамен молчащих точных: кавычки с НЧ-формулировок сняты,
# охват вариаций защищают минус-слова выше.
NEW_PHRASES = {
    "Claude — подписки для компаний": [
        "claude купить",
        "купить подписку claude",
        "claude pro купить",
        "оплатить claude",
        "claude оплата подписки",
        "claude подписка +для компании",
    ],
    "Claude Code — для команд разработки": [
        "claude code купить",
        "claude code подписка",
        "claude code стоимость",
        "оплатить claude code",
    ],
    "Midjourney — контрольная корзина": [
        "midjourney купить",
        "оплатить midjourney",
    ],
    "ChatGPT Business — гипотеза с фильтром до клика": [
        "оплатить chatgpt",
        "chatgpt оплата подписки",
        "купить chatgpt +для компании",
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

    camps = call(
        "campaigns", "get",
        {"SelectionCriteria": {}, "FieldNames": ["Id", "Name", "NegativeKeywords"]},
        token,
    ).get("Campaigns", [])
    camp = next((c for c in camps if c["Name"] == CAMPAIGN_NAME), None)
    if camp is None:
        raise SystemExit(f"Кампания «{CAMPAIGN_NAME}» не найдена")
    cid = camp["Id"]
    current_neg = (camp.get("NegativeKeywords") or {}).get("Items") or []
    print(f"Кампания {cid}, минус-слов сейчас: {len(current_neg)}")

    groups = call(
        "adgroups", "get",
        {"SelectionCriteria": {"CampaignIds": [cid]}, "FieldNames": ["Id", "Name"]},
        token,
    ).get("AdGroups", [])
    gid_by_name = {g["Name"]: g["Id"] for g in groups}

    kws = call(
        "keywords", "get",
        {"SelectionCriteria": {"CampaignIds": [cid]},
         "FieldNames": ["Id", "Keyword", "AdGroupId", "State", "Status"]},
        token,
    ).get("Keywords", [])
    auto = [k for k in kws if k["Keyword"] == "---autotargeting" and k.get("State") != "SUSPENDED"]
    existing_phrases = {(k["AdGroupId"], k["Keyword"]) for k in kws}

    # 1. Автотаргетинг — приостановить.
    print(f"\n== 1. Автотаргетинг: к приостановке {len(auto)} ==")
    for k in auto:
        print(f"  - id {k['Id']} группа {k['AdGroupId']} ({k.get('State')}/{k.get('Status')})")
    if mode == "apply" and auto:
        res = call("keywords", "suspend",
                   {"SelectionCriteria": {"Ids": [k["Id"] for k in auto]}}, token)
        print_results("suspend", res, "SuspendResults")

    # 2. Минус-слова кампании — объединение v3 + добавка, без дублей.
    merged, seen = [], set()
    for w in current_neg + NEGATIVES_V3 + NEGATIVES_NEW:
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            merged.append(w)
    added = [w for w in merged if w.lower() not in {x.lower() for x in current_neg}]
    print(f"\n== 2. Минус-слова: было {len(current_neg)}, станет {len(merged)} (новых {len(added)}) ==")
    print("  добавка: " + ", ".join(added))
    total_len = sum(len(w) for w in merged)
    if total_len > 20000:
        raise SystemExit(f"суммарная длина минус-слов {total_len} > 20000")
    if mode == "apply":
        res = call("campaigns", "update",
                   {"Campaigns": [{"Id": cid, "NegativeKeywords": {"Items": merged}}]}, token)
        print_results("campaigns.update", res, "UpdateResults")

    # 3. Широкие фразы взамен молчащих точных.
    to_add = []
    print("\n== 3. Новые фразы ==")
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
        kws2 = call(
            "keywords", "get",
            {"SelectionCriteria": {"CampaignIds": [cid]},
             "FieldNames": ["Id", "Keyword", "AdGroupId", "State", "Status"]},
            token,
        ).get("Keywords", [])
        n_auto_on = sum(1 for k in kws2 if k["Keyword"] == "---autotargeting" and k.get("State") != "SUSPENDED")
        n_active = sum(1 for k in kws2 if k["Keyword"] != "---autotargeting" and k.get("State") != "SUSPENDED")
        camp2 = call("campaigns", "get",
                     {"SelectionCriteria": {"Ids": [cid]},
                      "FieldNames": ["Id", "NegativeKeywords"]}, token)["Campaigns"][0]
        n_neg = len((camp2.get("NegativeKeywords") or {}).get("Items") or [])
        print("\n== Итог сверки ==")
        print(f"  автотаргетингов активных: {n_auto_on} (ожидание 0)")
        print(f"  фраз активных: {n_active}")
        print(f"  минус-слов кампании: {n_neg}")


if __name__ == "__main__":
    main()
