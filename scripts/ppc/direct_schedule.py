#!/usr/bin/env python3
"""Перевод кампаний подарочных карт Apple на будни (решение владельца 13.09.2026).

Кампании раунда 3 заведены 07.09 с показами все семь дней (9:00–21:00 МСК):
спрос на подарочные карты выходным календарём не ограничен. Замер первой
недели показал, что выходная открутка идёт мимо оффера: 12.09, в субботу,
кампании Apple потратили 428 ₽ при 82 кликах и ни одном шаге воронки, а
доля информационного класса в их расходе — 69–72 %. Кампания bs-test в тот
же день не работала вовсе: у неё показы только по будням.

Решение владельца: привести Apple к тому же режиму — показы пн–пт.
Часы не трогаются: поручение касалось дней недели, а окно 9:00–21:00
кампаниям раунда 3 задавалось отдельным решением 05.09 и своей проверки
пока не прошло.

Вместе с днями снимается и особый режим праздников: показы в праздничные
дни задавались ради непрерывной открутки семь дней в неделю, а для
кампании выходного дня без выходных смысла в нём нет — праздники
приравниваются к нерабочим дням, как у bs-test.

Скрипт читает фактическое расписание каждой кампании и меняет только те,
у которых включены субботние или воскресные часы. Ставки, бюджет,
стратегию, группы, фразы и объявления не трогает; кампания bs-test и любые
чужие кампании кабинета не затрагиваются — список имён задан явно.

Режимы:
  dry-run — показать текущее расписание и план, в API только чтение;
  apply   — применить.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"

# Кампании к переводу. Список явный: расписание — настройка уровня
# кампании, и «починить все разом» здесь означало бы задеть bs-test,
# у которой режим и так правильный.
CAMPAIGNS = ["bs-apple-gift-2026-09", "bs-apple-regions-2026-09"]
WORKDAYS = (1, 2, 3, 4, 5)


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


def parse_items(items: list[str]) -> dict[int, list[int]]:
    """Строки «день,ч0,…,ч23» → {день: [коэффициенты по часам]}."""
    out: dict[int, list[int]] = {}
    for row in items or []:
        parts = [int(x) for x in row.split(",")]
        out[parts[0]] = parts[1:]
    return out


def hours_of(day_row: list[int]) -> tuple[int, int] | None:
    """Границы окна показов дня; None — день выключен."""
    on = [h for h, v in enumerate(day_row) if v]
    return (on[0], on[-1] + 1) if on else None


def describe(by_day: dict[int, list[int]]) -> str:
    names = {1: "пн", 2: "вт", 3: "ср", 4: "чт", 5: "пт", 6: "сб", 7: "вс"}
    parts = []
    for d in range(1, 8):
        win = hours_of(by_day.get(d, []))
        parts.append(f"{names[d]} {win[0]}–{win[1]}" if win else f"{names[d]} —")
    return ", ".join(parts)


def main() -> None:
    token = os.environ.get("DIRECT_TOKEN", "")
    if not token:
        raise SystemExit("DIRECT_TOKEN не задан")
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry-run"
    if mode not in ("dry-run", "apply"):
        raise SystemExit(f"неизвестный режим: {mode}")
    print(f"Режим: {mode}")

    camps = call("campaigns", "get",
                 {"SelectionCriteria": {}, "FieldNames": ["Id", "Name", "TimeTargeting"]},
                 token).get("Campaigns", [])
    by_name = {c["Name"]: c for c in camps}

    updates = []
    for name in CAMPAIGNS:
        camp = by_name.get(name)
        if camp is None:
            print(f"  ! кампания не найдена: «{name}»")
            continue
        tt = camp.get("TimeTargeting") or {}
        by_day = parse_items((tt.get("Schedule") or {}).get("Items"))
        print(f"\n== «{name}» (id {camp['Id']}) ==")
        print(f"  сейчас: {describe(by_day)}")
        weekend_on = [d for d in (6, 7) if hours_of(by_day.get(d, []))]
        if not weekend_on:
            print("  = выходные уже выключены — менять нечего")
            continue

        # Окно будней сохраняется как есть: меняем дни, а не часы. Если
        # будни почему-то выключены, опереться не на что — такой случай
        # разбирается руками, молча выдумывать часы нельзя.
        windows = [hours_of(by_day.get(d, [])) for d in WORKDAYS]
        windows = [w for w in windows if w]
        if not windows:
            print("  ! будни выключены целиком — расписание задать нечем, пропуск")
            continue
        hour_from = min(w[0] for w in windows)
        hour_to = max(w[1] for w in windows)
        items = [",".join(str(v) for v in [d] + [
            100 if (d in WORKDAYS and hour_from <= h < hour_to) else 0 for h in range(24)])
            for d in range(1, 8)]
        print(f"  станет: пн–пт {hour_from}–{hour_to}, сб и вс выключены; "
              f"праздники — как нерабочие дни")
        updates.append({"Id": camp["Id"],
                        "TimeTargeting": {"Schedule": {"Items": items},
                                          "ConsiderWorkingWeekends": "NO",
                                          "HolidaysSchedule": {"SuspendOnHolidays": "YES"}}})

    print(f"\n== Итог: перевести {len(updates)} кампаний ==")
    if not updates:
        print("  расхождений нет")
        return
    if mode != "apply":
        print("\ndry-run завершён — изменений нет.")
        return

    res = call("campaigns", "update", {"Campaigns": updates}, token)
    for i, r in enumerate(res.get("UpdateResults", [])):
        if r.get("Errors"):
            e = r["Errors"][0]
            print(f"  campaigns.update[{i}]: ОШИБКА {e.get('Code')} {e.get('Message')} — {e.get('Details')}")
        else:
            for w in r.get("Warnings") or []:
                print(f"  campaigns.update[{i}] предупреждение: {w.get('Code')} {w.get('Message')}")
            print(f"  campaigns.update[{i}]: OK id={r.get('Id')}")

    camps2 = call("campaigns", "get",
                  {"SelectionCriteria": {"Ids": [u["Id"] for u in updates]},
                   "FieldNames": ["Id", "Name", "TimeTargeting"]},
                  token).get("Campaigns", [])
    print("\n== Итог сверки ==")
    for c in camps2:
        by_day = parse_items(((c.get("TimeTargeting") or {}).get("Schedule") or {}).get("Items"))
        print(f"  «{c['Name']}»: {describe(by_day)}")


if __name__ == "__main__":
    main()
