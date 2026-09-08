#!/usr/bin/env python3
"""Вывод по замеру первого экрана выдачи: почему первое место не даёт переходов.

Задача, которую этим не решить иначе. Позиции сайта известны только из Yandex
Search API (XML): он отдаёт органический список и по устройству ничего не знает
о рекламе и колдунщиках над ним. Поэтому «первое место и ноль переходов» этими
данными не объясняется в принципе — нужен вид страницы, а сессия в выдачу не
ходит. Замер ручной, протокол — data/seo/serp-fold-probe.json.

Правило вывода записано в самом протоколе и до замера: скрипт его применяет, а
не выбирает. Иначе любой результат истолковался бы в пользу уже сделанной работы.

Запуск: python3 scripts/seo/serp_fold.py [--probe data/seo/serp-fold-probe.json]
Возврат: 0 — вывод сделан; 2 — замер ещё не заполнен (это не ошибка).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

PROBE = pathlib.Path("data/seo/serp-fold-probe.json")

# Границы правила. Второй экран телефона — там, где показ уже почти наверняка
# не был увиденным; больше одного блока над органикой — выдача, где органика
# перестала быть первым, что видит человек.
MOBILE_FOLD_SCREEN = 2
BLOCKS_TOLERATED = 1


def filled(row: dict) -> bool:
    obs = row.get("observation") or {}
    return obs.get("our_result_screen_mobile") is not None \
        and obs.get("blocks_above_organic") is not None


def classify(row: dict) -> tuple[str, str]:
    """Версия, которую подтверждает одна строка замера."""
    obs = row["observation"]
    mobile = obs["our_result_screen_mobile"]
    blocks = obs["blocks_above_organic"]
    kinds = ", ".join(obs.get("block_kinds") or []) or "не указаны"
    if obs.get("answer_block_above"):
        return "intercepted", (f"над органикой стоит блок с ответом ({kinds}) — "
                               "клик забирают до нашего результата")
    if mobile >= MOBILE_FOLD_SCREEN:
        return "fold", (f"на телефоне наш результат на {mobile}-м экране, "
                        f"над органикой {blocks} блок(ов): {kinds}")
    if blocks <= BLOCKS_TOLERATED:
        return "non_human", (f"наш результат на первом экране телефона, над "
                             f"органикой {blocks} блок(ов) — вёрстка ноль "
                             "переходов не объясняет")
    return "crowded", (f"наш результат на первом экране, но над органикой "
                       f"{blocks} блок(ов): {kinds}")


VERDICT_TEXT = {
    "fold": "органика ниже первого экрана: потолок программы сниппетов мал, "
            "работать надо за топ-3 и за блоки над органикой",
    "non_human": "вёрстка ноль переходов не объясняет — остаётся версия про "
                 "нечеловеческие показы; кластеры уходят из планирования, "
                 "модели нужен гейт по доле показов без переходов в топ-3",
    "intercepted": "клик перехватывается блоком над органикой: работать надо "
                   "за попадание в этот блок, а не за позицию",
    "crowded": "органика на первом экране, но зажата блоками — промежуточный "
               "случай, нужен ещё один замер по другим запросам",
}


def build(probe: dict) -> dict:
    targets = [r for r in probe["queries"] if r["role"] == "target"]
    ready = [r for r in targets if filled(r)]
    if len(ready) < 3:
        return {"available": False,
                "reason": f"замер заполнен по {len(ready)} целевым запросам из "
                          f"{len(targets)}; вывод делается от трёх"}
    rows = []
    tally: dict[str, int] = {}
    for r in ready:
        verdict, why = classify(r)
        tally[verdict] = tally.get(verdict, 0) + 1
        rows.append({"query": r["query"], "impressions": r["impressions"],
                     "clicks": r["clicks"], "serp_position": r["serp_position"],
                     "verdict": verdict, "why": why})
    top = max(tally.items(), key=lambda kv: kv[1])
    decided = top[1] > len(ready) / 2

    controls = []
    for r in probe["queries"]:
        if r["role"].startswith("control") and filled(r):
            verdict, why = classify(r)
            controls.append({"query": r["query"], "role": r["role"],
                             "clicks": r["clicks"], "verdict": verdict, "why": why})
    # Контроль решает спор: если по брендовому запросу с CTR 16,7 % выдача
    # устроена так же, как у целевых, вёрстка разницы не объясняет.
    control_note = None
    brand = next((c for c in controls if c["role"] == "control_brand"), None)
    if brand:
        control_note = (
            "брендовый запрос с переходами устроен так же, как целевые "
            f"({brand['verdict']}) — вёрстка разницу не объясняет, дело в том, "
            "кто ищет"
            if brand["verdict"] == top[0] else
            f"брендовый запрос с переходами устроен иначе ({brand['verdict']}) "
            f"против {top[0]} у целевых — вёрстка разницу объясняет")

    return {"available": True, "queries": rows, "controls": controls,
            "tally": tally, "verdict": top[0] if decided else "не решено",
            "decided": decided,
            "meaning": VERDICT_TEXT[top[0]] if decided else
                       "версии разошлись поровну — нужен замер по большему числу запросов",
            "control_note": control_note,
            "measured_at": probe.get("measured_at")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", type=pathlib.Path, default=PROBE)
    args = ap.parse_args()
    probe = json.loads(args.probe.read_text(encoding="utf-8"))
    result = build(probe)
    if not result["available"]:
        print(result["reason"])
        return 2
    print(f"Замер {result['measured_at'] or 'без даты'} — вывод: {result['verdict']}")
    print(f"  {result['meaning']}\n")
    for r in result["queries"]:
        print(f"  [{r['verdict']:11}] {r['query']}")
        print(f"                {r['why']}")
    if result["controls"]:
        print("\n  Контроль:")
        for c in result["controls"]:
            # У контрольной строки важна не версия, а сам вид выдачи: она нужна
            # для сравнения с целевыми, а не для собственного вывода.
            print(f"  {c['query']} — переходов {c['clicks']}")
            print(f"                {c['why']}")
    if result["control_note"]:
        print(f"\n  {result['control_note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
