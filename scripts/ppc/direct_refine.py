#!/usr/bin/env python3
"""Доводка кампании bs-test-2026-09, раунд 2 — по фактам дня 01.09.

Затяжка 31.08 (`direct_tighten.py`) сбила долю мусора вдвое: класс C+D
в чистом периоде 25 % против 49 % накопительно. Оставшийся класс C
прирос двумя семьями запросов — «активация/ключ» (розничный интент к
коробке) и «команды для claude code» (справочник команд, не покупка).
Этот пакет закрывает их, доносит подтверждённые запросы в фразы и НЕ
трогает то, где интент спорный.

Три изменения одним прогоном:
  1. Минус-слова кампании: «активация», «активировать», «ключ».
     Лемматизация Директа покрывает «ключи/ключа», «активации».
  2. Групповая минус-ФРАЗА «команды для» в группе Claude Code.
     Одиночное «команды» брать нельзя: лемма та же, что у собственной
     фразы «claude code +для команды» — первой B2B-фразы, давшей клик.
     Фраза срезает «команды для claude code», но не «claude code для
     команды разработки»: в минус-фразах Директа порядок слов значим.
  3. Перенос подтверждённых запросов в фразы (механизм P3 «запрос →
     ключ»): класс A «оформить чат gpt оплата юр лицом», «тарифы
     claude» (2 клика), транскрипция «клод код».

Чего пакет сознательно НЕ делает:
  - не минусует «пополнить»: «пополнить chatgpt», «как пополнить счет
    в claude» — это интент оплаты, а пополнение баланса у нас в
    ассортименте (OpenAI API на лендинге /vendors/openai, товар
    «Пополнение баланса OpenRouter»). Вынесено на решение владельца;
  - не берёт фразу «клод код нейросеть купить» дословно: «нейросеть»
    стоит групповым минусом с 31.08, фраза и минус конфликтовали бы.
    Транскрипция покрывается фразой «клод код купить»;
  - не трогает бюджет, ставки, стратегию, расписание и чужие кампании.

Guard непересечения: перед применением скрипт читает все ключевые
фразы кампании и падает, если новый минус задевает собственную
семантику. Проверка идёт по корню слова, а не по точному написанию —
иначе «команды» прошло бы мимо «для команды».

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
CLAUDE_CODE_GROUP = "Claude Code — для команд разработки"

# Минус-слова кампании: (слово, корень для guard-проверки, обоснование).
# Корень пишется руками: автоматическое отсечение окончаний либо режет
# лишнее, либо пропускает пересечение — цена ошибки здесь выше экономии.
CAMPAIGN_NEGATIVES_ADD = [
    ("активация", "актив",
     "«активация полной версии адоб акробат» — 17,34 ₽, интент к коробке"),
    ("активировать", "актив",
     "та же семья запросов, другая словоформа обращения"),
    ("ключ", "ключ",
     "«adobe acrobat ключ» — розничный/пиратский интент, мы продаём лицензии"),
]

# Групповые минус-ФРАЗЫ Claude Code: одиночным словом эти запросы не
# режутся без ущерба собственной семантике.
GROUP_NEGATIVE_PHRASES = {
    CLAUDE_CODE_GROUP: [
        ("команды для", "команды для",
         "«команды для claude code» — 17,03 ₽, справочник команд, не покупка"),
    ],
}

# Перенос запросов дня в фразы.
NEW_PHRASES = {
    "Claude — подписки для компаний": [
        "тарифы claude",                 # 2 клика 01.09
    ],
    CLAUDE_CODE_GROUP: [
        "клод код купить",               # транскрипция, без слова «нейросеть»
    ],
    "ChatGPT Business — гипотеза с фильтром до клика": [
        "чат gpt оплата +юр лицом",      # класс A, 47 ₽
        "оформить chatgpt +на юр лицо",
    ],
}

# Вынесено на решение владельца — печатается в плане, не применяется.
DEFERRED = [
    ("пополнить",
     "«пополнить chatgpt» 27,67 ₽, «как пополнить счет в claude» 16,61 ₽ — "
     "интент оплаты; пополнение баланса есть в ассортименте (OpenAI API, "
     "OpenRouter), поэтому минус может срезать своё же"),
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
        else:
            for w in r.get("Warnings") or []:
                print(f"  {label}[{i}] предупреждение: {w.get('Code')} {w.get('Message')} {w.get('Details') or ''}")
            print(f"  {label}[{i}]: OK id={r.get('Id')}")


def guard_no_overlap(phrases_by_group: dict[int, list[str]],
                     gname_by_id: dict[int, str]) -> None:
    """Упасть, если минус задевает собственную ключевую фразу.

    Кампанийный минус проверяется по всем фразам кампании, групповой —
    только по фразам своей группы. Слово фразы считается задетым, если
    начинается с корня минуса: «команды» ↔ «команды» в «+для команды».
    """
    problems: list[str] = []

    all_phrases = [(gid, p) for gid, ps in phrases_by_group.items() for p in ps]
    for word, stem, _ in CAMPAIGN_NEGATIVES_ADD:
        for gid, phrase in all_phrases:
            hit = [w for w in phrase.replace("+", "").split() if w.startswith(stem)]
            if hit:
                problems.append(
                    f"минус «{word}» (корень «{stem}») задевает фразу "
                    f"[{gname_by_id.get(gid, gid)}] «{phrase}» — слово «{hit[0]}»")

    for gname, items in GROUP_NEGATIVE_PHRASES.items():
        gid = next((i for i, n in gname_by_id.items() if n == gname), None)
        if gid is None:
            continue
        for text, _, _ in items:
            for phrase in phrases_by_group.get(gid, []):
                if text in phrase.replace("+", ""):
                    problems.append(
                        f"минус-фраза «{text}» входит в собственную фразу "
                        f"[{gname}] «{phrase}»")

    print("\n== Guard: непересечение минусов с собственной семантикой ==")
    if problems:
        for p in problems:
            print(f"  ✗ {p}")
        raise SystemExit("пакет не применяется: минус режет свою же фразу")
    print(f"  ✓ проверено фраз: {len(all_phrases)}, пересечений нет")


def main() -> None:
    token = os.environ.get("DIRECT_TOKEN", "")
    if not token:
        raise SystemExit("DIRECT_TOKEN не задан")
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry-run"
    if mode not in ("dry-run", "apply"):
        raise SystemExit(f"неизвестный режим: {mode}")
    print(f"Режим: {mode}")

    camps = call("campaigns", "get",
                 {"SelectionCriteria": {}, "FieldNames": ["Id", "Name", "NegativeKeywords"]},
                 token).get("Campaigns", [])
    camp = next((c for c in camps if c["Name"] == CAMPAIGN_NAME), None)
    if camp is None:
        raise SystemExit(f"Кампания «{CAMPAIGN_NAME}» не найдена")
    cid = camp["Id"]
    current_neg = (camp.get("NegativeKeywords") or {}).get("Items") or []

    groups = call("adgroups", "get",
                  {"SelectionCriteria": {"CampaignIds": [cid]},
                   "FieldNames": ["Id", "Name", "NegativeKeywords"]},
                  token).get("AdGroups", [])
    gid_by_name = {g["Name"]: g["Id"] for g in groups}
    gname_by_id = {g["Id"]: g["Name"] for g in groups}

    kws = call("keywords", "get",
               {"SelectionCriteria": {"CampaignIds": [cid]},
                "FieldNames": ["Id", "Keyword", "AdGroupId"]},
               token).get("Keywords", [])
    existing_phrases = {(k["AdGroupId"], k["Keyword"]) for k in kws}
    phrases_by_group: dict[int, list[str]] = {}
    for k in kws:
        if k["Keyword"] == "---autotargeting":
            continue
        phrases_by_group.setdefault(k["AdGroupId"], []).append(k["Keyword"])

    guard_no_overlap(phrases_by_group, gname_by_id)

    # 1. Минус-слова кампании.
    add_words = [w for w, _, _ in CAMPAIGN_NEGATIVES_ADD]
    merged, seen = [], set()
    for w in current_neg + add_words:
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            merged.append(w)
    added = [w for w in merged if w.lower() not in {x.lower() for x in current_neg}]
    print(f"\n== 1. Минус-слова кампании: было {len(current_neg)}, "
          f"станет {len(merged)} (новых {len(added)}) ==")
    for word, _, why in CAMPAIGN_NEGATIVES_ADD:
        mark = "+" if word in added else "="
        print(f"  {mark} «{word}» — {why}")
    total_len = sum(len(w) for w in merged)
    if total_len > 20000:
        raise SystemExit(f"суммарная длина минус-слов {total_len} > 20000")
    if mode == "apply" and added:
        res = call("campaigns", "update",
                   {"Campaigns": [{"Id": cid, "NegativeKeywords": {"Items": merged}}]}, token)
        print_results("campaigns.update", res, "UpdateResults")

    # 2. Групповые минус-фразы.
    print("\n== 2. Минус-фразы группы ==")
    for gname, items in GROUP_NEGATIVE_PHRASES.items():
        gid = gid_by_name.get(gname)
        if gid is None:
            print(f"  ! группа не найдена: {gname}")
            continue
        group = next(g for g in groups if g["Id"] == gid)
        cur = (group.get("NegativeKeywords") or {}).get("Items") or []
        g_merged, g_seen = [], set()
        for w in cur + [t for t, _, _ in items]:
            lw = w.lower()
            if lw not in g_seen:
                g_seen.add(lw)
                g_merged.append(w)
        g_added = [w for w in g_merged if w.lower() not in {x.lower() for x in cur}]
        print(f"  [{gname}] было {len(cur)}, станет {len(g_merged)} (новых {len(g_added)})")
        for text, _, why in items:
            mark = "+" if text in g_added else "="
            print(f"    {mark} «{text}» — {why}")
        if sum(len(w) for w in g_merged) > 4000:
            raise SystemExit("суммарная длина групповых минусов > 4000")
        if mode == "apply" and g_added:
            res = call("adgroups", "update",
                       {"AdGroups": [{"Id": gid,
                                      "NegativeKeywords": {"Items": g_merged}}]}, token)
            print_results("adgroups.update", res, "UpdateResults")

    # 3. Перенос запросов в фразы.
    to_add = []
    print("\n== 3. Новые фразы из поисковых запросов 01.09 ==")
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

    # 4. Отложенные кандидаты — печатаются, не применяются.
    print("\n== 4. Вынесено на решение владельца (в этом прогоне не применяется) ==")
    for word, why in DEFERRED:
        print(f"  ? «{word}» — {why}")

    # 5. Контрольное чтение после применения.
    if mode == "apply":
        camps2 = call("campaigns", "get",
                      {"SelectionCriteria": {"Ids": [cid]},
                       "FieldNames": ["Id", "NegativeKeywords"]},
                      token).get("Campaigns", [])
        kws2 = call("keywords", "get",
                    {"SelectionCriteria": {"CampaignIds": [cid]},
                     "FieldNames": ["Id", "Keyword", "AdGroupId"]},
                    token).get("Keywords", [])
        groups2 = call("adgroups", "get",
                       {"SelectionCriteria": {"CampaignIds": [cid]},
                        "FieldNames": ["Id", "Name", "NegativeKeywords"]},
                       token).get("AdGroups", [])
        n_camp_neg = len(((camps2[0] if camps2 else {}).get("NegativeKeywords") or {}).get("Items") or [])
        n_phrases = sum(1 for k in kws2 if k["Keyword"] != "---autotargeting")
        print("\n== Итог сверки ==")
        print(f"  минус-слов кампании: {n_camp_neg}")
        print(f"  фраз в кампании: {n_phrases}")
        for g in groups2:
            if g["Name"] in GROUP_NEGATIVE_PHRASES:
                n = len((g.get("NegativeKeywords") or {}).get("Items") or [])
                print(f"  минусов группы «{g['Name']}»: {n}")


if __name__ == "__main__":
    main()
