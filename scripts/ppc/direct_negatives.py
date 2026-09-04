#!/usr/bin/env python3
"""Пакет минус-слов кампании bs-test-2026-09 с защитой своей семантики.

Поручение владельца 03.09.2026 по фактам поведения визитов (секция
«Метрика: поведение по поисковым запросам» в ops-direct, action=stats): запросы
пиратского и активационного интента по Adobe дают 100 % отказов и 0-1
секунду на сайте — человек ищет взлом, видит цены и уходит.

Пакет v4 добавляется к действующим минусам кампании (v3 от 28.08 и
добавка 29.08), дубли отсеиваются. Перед добавлением каждое слово
проверяется на пересечение с действующими фразами кампании: если корень
встречается хотя бы в одной активной фразе, слово в пакет НЕ попадает —
минус, режущий собственную семантику, дороже мусора, который он ловит.

Режимы:
  dry-run — показать пакет и результат проверки, в API только чтение;
  apply   — применить объединённый список к кампании.

Минус-слова применяются мгновенно и перемодерации не требуют, поэтому
запуск в рабочее время показов безопасен. Деньги, ставки, стратегию,
объявления и чужие кампании скрипт не трогает.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"
CAMPAIGN_NAME = "bs-test-2026-09"

# Пакет v4 — маркеры пиратства и активации. Все слова взяты из фактических
# запросов 02-03.09 либо являются их прямыми синонимами того же интента.
NEGATIVES_V4 = [
    # факты: «активация полной версии адоб акробат» (2 визита, 100 % отказов),
    # «adobe photoshop 2024 ключ активации», «adobe acrobat reader ключ
    # активации» — словоформы «активации/активацию» ловятся этим же словом
    "активация",
    "активатор",
    "активированный",
    # синонимы того же интента, которых ещё не было в списке
    "кейген",
    "keygen",
    "crack",
    "cracked",
    "патч",
    "таблетка",
    "repack",
    "репак",
    "лекарство",
    "портабл",
    "portable",
    "nulled",
    "пиратка",
    "пиратский",
]

# Слова, сознательно НЕ вошедшие в пакет, — чтобы решение не пересматривали
# заново на каждом замере (причина указана для каждого).
REJECTED = {
    "ключ": "«claude api ключ купить» — покупка API-ключа наш оффер",
    "пополнить": "«пополнить баланс claude» — оплата баланса это наша услуга",
    "команды": "режет свои же фразы «claude code +для команды», «cursor +для команды»",
    "бессрочная": "«adobe acrobat pro купить лицензию бессрочную» — 0 % отказов, 17 с",
    "reader": "«adobe reader enterprise» — 0 % отказов, 16 с, корпоративный интент",
    "поставить": "риск пересечения с «поставка», «поставить на юрлицо»",
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


def stem(word: str) -> str:
    """Грубая основа слова: хватает, чтобы поймать пересечение словоформ."""
    w = word.lower()
    return w[:-2] if len(w) > 5 else w


def main() -> None:
    token = os.environ.get("DIRECT_TOKEN", "")
    if not token:
        raise SystemExit("DIRECT_TOKEN не задан")
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry-run"
    if mode not in ("dry-run", "apply"):
        raise SystemExit(f"неизвестный режим: {mode}")
    print(f"Режим: {mode}")

    camps = call("campaigns", "get",
                 {"SelectionCriteria": {},
                  "FieldNames": ["Id", "Name", "NegativeKeywords"]},
                 token).get("Campaigns", [])
    camp = next((c for c in camps if c["Name"] == CAMPAIGN_NAME), None)
    if camp is None:
        raise SystemExit(f"Кампания «{CAMPAIGN_NAME}» не найдена")
    cid = camp["Id"]
    current = (camp.get("NegativeKeywords") or {}).get("Items") or []
    print(f"Кампания {cid}, минус-слов сейчас: {len(current)}")

    kws = call("keywords", "get",
               {"SelectionCriteria": {"CampaignIds": [cid]},
                "FieldNames": ["Keyword", "State"]},
               token).get("Keywords", [])
    phrases = [k["Keyword"].lower() for k in kws
               if k["Keyword"] != "---autotargeting" and k.get("State") != "SUSPENDED"]
    print(f"Действующих фраз для проверки: {len(phrases)}")

    print(f"\n== Проверка пакета v4 на пересечение со своей семантикой ({len(NEGATIVES_V4)}) ==")
    safe, blocked = [], []
    for w in NEGATIVES_V4:
        hits = [p for p in phrases if stem(w) in p]
        if hits:
            blocked.append((w, hits[:3]))
            print(f"  ✗ «{w}» отклонено — режет фразы: {', '.join(hits[:3])}")
        else:
            safe.append(w)
            print(f"  ✓ «{w}»")

    if REJECTED:
        print("\n== Не вошли в пакет по решению разбора ==")
        for w, why in REJECTED.items():
            print(f"  — «{w}»: {why}")

    merged, seen = [], set()
    for w in current + safe:
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            merged.append(w)
    added = [w for w in merged if w.lower() not in {x.lower() for x in current}]

    print(f"\n== Итог: было {len(current)}, станет {len(merged)} (новых {len(added)}) ==")
    print("  добавка: " + (", ".join(added) or "(нечего добавлять)"))
    if blocked:
        print(f"  отклонено защитой: {len(blocked)}")

    total_len = sum(len(w) for w in merged)
    if total_len > 20000:
        raise SystemExit(f"суммарная длина минус-слов {total_len} > 20000")
    if len(merged) > 4096:
        raise SystemExit(f"минус-слов {len(merged)} > 4096")

    if mode != "apply":
        print("\ndry-run завершён — изменений нет.")
        return
    if not added:
        print("\nПрименять нечего.")
        return

    res = call("campaigns", "update",
               {"Campaigns": [{"Id": cid, "NegativeKeywords": {"Items": merged}}]},
               token)
    for i, r in enumerate(res.get("UpdateResults", [])):
        if r.get("Errors"):
            e = r["Errors"][0]
            print(f"  campaigns.update[{i}]: ОШИБКА {e.get('Code')} {e.get('Message')} — {e.get('Details')}")
        else:
            for w in r.get("Warnings") or []:
                print(f"  campaigns.update[{i}] предупреждение: {w.get('Code')} {w.get('Message')}")
            print(f"  campaigns.update[{i}]: OK id={r.get('Id')}")

    camp2 = call("campaigns", "get",
                 {"SelectionCriteria": {"Ids": [cid]},
                  "FieldNames": ["Id", "NegativeKeywords"]}, token)["Campaigns"][0]
    n = len((camp2.get("NegativeKeywords") or {}).get("Items") or [])
    print(f"\n== Итог сверки ==\n  минус-слов кампании: {n}")


if __name__ == "__main__":
    main()
