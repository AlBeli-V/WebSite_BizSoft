#!/usr/bin/env python3
"""Остановка кампании bs-test-2026-09 (решение руководителя 21.09.2026).

Две полные недели наблюдения с исправленными посадочными пройдены. Итог:
348 визитов кампании, 68 показов формы заявки, ноль начатых заполнений и
ноль заявок; с 07.09 потрачено 7911 ₽ с НДС при ориентире около 10 000 ₽,
за всё время кампании с 28.08 — 13 461 ₽.

Финансовое правило эксперимента от 07.09.2026: при нуле заявок бюджет не
наращивают, а кампанию останавливают и пересобирают предложение. Это
прямое исполнение правила, а не оптимизация: ставки, фразы, минус-слова,
автотаргетинг и структура не трогаются — кампания переводится в паузу
целиком и в таком виде ждёт нового оффера.

Останавливается ровно одна кампания по имени. Кампании Apple в том же
кабинете работают и к этому эксперименту отношения не имеют, поэтому имя
проверяется точным совпадением, а несовпадение роняет прогон.

Режимы:
  dry-run — напечатать план, в API только чтение;
  apply   — остановить.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"
# Имя по умолчанию — кампания первого эксперимента. Любая другая задаётся
# вторым аргументом: 21.09.2026 понадобилось остановить bs-ai-business-2026-09,
# и жёсткое имя в коде означало бы правку скрипта ради одной остановки.
DEFAULT_CAMPAIGN = "bs-test-2026-09"
# Состояния, из которых остановка имеет смысл. Кампания на модерации или
# уже в архиве в паузу не переводится — это другой разговор, и молча
# «починить» его нельзя.
PAUSABLE_STATES = ("ON",)


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


def pick(campaigns: list[dict], name: str) -> dict:
    """Выбрать кампанию по точному имени и проверить, что её можно остановить.

    Отдельная функция без сети: на ней держатся обе защиты — от остановки
    чужой кампании и от остановки той, что уже не работает.
    """
    named = [c for c in campaigns if c.get("Name") == name]
    if not named:
        raise SystemExit(
            f"кампания «{name}» не найдена — останавливать нечего; "
            f"в кабинете: {', '.join(sorted(c.get('Name', '?') for c in campaigns)) or 'пусто'}")
    if len(named) > 1:
        raise SystemExit(
            f"кампаний с именем «{name}» несколько ({len(named)}) — "
            "какую останавливать, скрипт не решает")
    camp = named[0]
    state = camp.get("State")
    if state not in PAUSABLE_STATES:
        raise SystemExit(
            f"кампания «{name}» в состоянии {state}, а остановка предусмотрена "
            f"из {', '.join(PAUSABLE_STATES)} — прогон остановлен без изменений")
    return camp


def main() -> None:
    token = os.environ.get("DIRECT_TOKEN", "")
    if not token:
        raise SystemExit("DIRECT_TOKEN не задан")
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry-run"
    campaign_name = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CAMPAIGN
    if mode not in ("dry-run", "apply"):
        raise SystemExit(f"неизвестный режим: {mode}")
    # ops-direct передаёт имя кампании входом spec, у которого своё
    # умолчание — имя файла спецификации. Сказать об этом прямо дешевле,
    # чем разбирать потом «кампания round1-spec.json не найдена».
    if campaign_name.endswith(".json"):
        raise SystemExit(
            f"во входе spec осталось имя файла спецификации ({campaign_name}) — "
            f"для остановки укажите там имя кампании")
    print(f"Режим: {mode}; кампания: {campaign_name}")

    camps = call("campaigns", "get",
                 {"SelectionCriteria": {},
                  "FieldNames": ["Id", "Name", "State", "Status", "StatusPayment"]},
                 token).get("Campaigns", [])
    print("\n== Кампании кабинета ==")
    for c in camps:
        mark = "→ " if c.get("Name") == campaign_name else "  "
        print(f"{mark}{c.get('Id')} «{c.get('Name')}» {c.get('State')}/{c.get('Status')}")

    camp = pick(camps, campaign_name)
    cid = camp["Id"]
    print(f"\n== План ==\n  «{campaign_name}» ({cid}): {camp.get('State')} → SUSPENDED")
    print("  ставки, фразы, минус-слова, автотаргетинг и структура не меняются")

    if mode != "apply":
        print("\ndry-run завершён — запустите с apply")
        return

    res = call("campaigns", "suspend", {"SelectionCriteria": {"Ids": [cid]}}, token)
    ok = False
    for i, r in enumerate(res.get("SuspendResults", [])):
        if r.get("Errors"):
            e = r["Errors"][0]
            print(f"  campaigns.suspend[{i}]: ОШИБКА {e.get('Code')} "
                  f"{e.get('Message')} — {e.get('Details')}")
        else:
            ok = True
            print(f"  campaigns.suspend[{i}]: остановлена, Id {r.get('Id')}")
    if not ok:
        raise SystemExit("остановить кампанию не удалось — см. ошибки выше")

    after = call("campaigns", "get",
                 {"SelectionCriteria": {"Ids": [cid]},
                  "FieldNames": ["Id", "Name", "State", "Status"]},
                 token).get("Campaigns", [])
    for c in after:
        print(f"\n== После ==\n  «{c.get('Name')}» {c.get('State')}/{c.get('Status')}")


if __name__ == "__main__":
    main()
