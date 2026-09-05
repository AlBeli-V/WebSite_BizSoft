#!/usr/bin/env python3
"""Потолок цены клика в bs-test-2026-09 (решение руководителя 04.09.2026).

Замер недели 31.08–04.09: средняя цена клика выросла с 11 до 39 ₽ с НДС,
недельный лимит выбран на 99 % при 261 клике и одном контакте. Хвост
дорогих строк съедает бюджет единичными кликами:

  «claude code купить»       69,76 ₽ за 1 клик
  «cursor купить»            55,74 ₽ за клик (222,95 ₽ за 4)
  «claude купить подписку»   50,97 ₽ за клик
  автотаргетинг ChatGPT      36,87 ₽ за клик

Кампания идёт на автостратегии «максимум кликов» (WB_MAXIMUM_CLICKS):
ставки по фразам вручную не задаются, единственный штатный рычаг —
BidCeiling, ограничение цены клика на уровне стратегии. Решение
руководителя: недельный лимит оставить прежним, срезать дорогие клики.

Порог 30 ₽ без НДС (≈36,6 ₽ с НДС в отчётах) выбран так, чтобы отсечь
хвост, но не тронуть основную массу: средняя цена клика накопительно —
21,27 ₽ с НДС, то есть 17,4 ₽ без НДС, порог выше неё в 1,7 раза.

Недельный лимит скрипт не меняет: читает текущий и записывает обратно
как есть. Если стратегия окажется другой — прогон останавливается,
чужую стратегию контур не переписывает.

Режимы:
  dry-run — напечатать план, в API только чтение;
  apply   — применить.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"
CAMPAIGN_NAME = "bs-test-2026-09"
CEILING_RUB = 30
EXPECTED_STRATEGY = "WB_MAXIMUM_CLICKS"


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


def plan(strategy: dict, ceiling_rub: int) -> tuple[str, int | None, int]:
    """Разобрать стратегию: тип, текущий потолок и недельный лимит (в ₽).

    Отдельная функция без сети — на ней держатся проверки: подмена типа
    стратегии или потеря недельного лимита должны ронять прогон, а не
    уезжать в кабинет.
    """
    kind = strategy.get("BiddingStrategyType")
    if kind != EXPECTED_STRATEGY:
        raise SystemExit(
            f"стратегия поиска — {kind}, ожидалась {EXPECTED_STRATEGY}: "
            "потолок ставки задаётся только для «максимума кликов», "
            "чужую стратегию контур не переписывает")
    wb = strategy.get("WbMaximumClicks") or {}
    weekly = wb.get("WeeklySpendLimit")
    if not weekly:
        raise SystemExit(
            "в стратегии нет недельного лимита — записывать её обратно нельзя: "
            "прогон снял бы ограничение расхода")
    current = wb.get("BidCeiling")
    return kind, (None if current is None else int(current) // 1_000_000), int(weekly) // 1_000_000


def main() -> None:
    token = os.environ.get("DIRECT_TOKEN", "")
    if not token:
        raise SystemExit("DIRECT_TOKEN не задан")
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry-run"
    if mode not in ("dry-run", "apply"):
        raise SystemExit(f"неизвестный режим: {mode}")
    print(f"Режим: {mode}")

    camps = call("campaigns", "get",
                 {"SelectionCriteria": {}, "FieldNames": ["Id", "Name"],
                  "TextCampaignFieldNames": ["BiddingStrategy"]},
                 token).get("Campaigns", [])
    camp = next((c for c in camps if c["Name"] == CAMPAIGN_NAME), None)
    if camp is None:
        raise SystemExit(f"Кампания «{CAMPAIGN_NAME}» не найдена")
    cid = camp["Id"]
    search = (((camp.get("TextCampaign") or {}).get("BiddingStrategy") or {})
              .get("Search") or {})

    kind, current, weekly = plan(search, CEILING_RUB)
    print(f"\n== Стратегия поиска: {kind} ==")
    print(f"  недельный лимит: {weekly} ₽ без НДС — не меняется")
    print(f"  потолок цены клика: "
          f"{'не задан' if current is None else str(current) + ' ₽'} → {CEILING_RUB} ₽ без НДС "
          f"(≈{CEILING_RUB * 1.22:.0f} ₽ с НДС в отчётах)")
    if current == CEILING_RUB:
        print("  потолок уже стоит на этом значении — менять нечего")
        return

    if mode == "apply":
        res = call("campaigns", "update", {"Campaigns": [{
            "Id": cid,
            "TextCampaign": {"BiddingStrategy": {
                "Search": {
                    "BiddingStrategyType": EXPECTED_STRATEGY,
                    "WbMaximumClicks": {
                        "WeeklySpendLimit": weekly * 1_000_000,
                        "BidCeiling": CEILING_RUB * 1_000_000,
                    },
                },
                "Network": {"BiddingStrategyType": "SERVING_OFF"},
            }},
        }]}, token)
        for i, r in enumerate(res.get("UpdateResults", [])):
            if r.get("Errors"):
                e = r["Errors"][0]
                print(f"  campaigns.update[{i}]: ОШИБКА {e.get('Code')} "
                      f"{e.get('Message')} — {e.get('Details')}")
            else:
                for w in r.get("Warnings") or []:
                    print(f"  предупреждение: {w.get('Code')} {w.get('Message')}")
                print(f"  campaigns.update[{i}]: OK id={r.get('Id')}")

        after = call("campaigns", "get",
                     {"SelectionCriteria": {"Ids": [cid]}, "FieldNames": ["Id"],
                      "TextCampaignFieldNames": ["BiddingStrategy"]},
                     token).get("Campaigns", [])
        wb2 = ((((after[0] if after else {}).get("TextCampaign") or {})
                .get("BiddingStrategy") or {}).get("Search") or {}).get("WbMaximumClicks") or {}
        print("\n== Итог сверки ==")
        print(f"  потолок цены клика: {int(wb2.get('BidCeiling', 0)) // 1_000_000} ₽")
        print(f"  недельный лимит: {int(wb2.get('WeeklySpendLimit', 0)) // 1_000_000} ₽")


if __name__ == "__main__":
    main()
