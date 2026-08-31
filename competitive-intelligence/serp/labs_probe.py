#!/usr/bin/env python3
"""Проба DataForSEO Labs API: покрывает ли база конкурентную аналитику по РФ.

Решение руководителя 31.08: перед тем как строить discovery конкурентов на
Labs, проверить пробой, есть ли в базе русскоязычный Google. Labs работает
только по базе DataForSEO (не live-выдача) и только по Google.

Первый прогон вернул пустой total_count по всем доменам без ошибок API —
это можно прочитать двояко (база не покрывает РФ / мы неверно читаем ответ),
поэтому добавлены две вещи: печать сырого ответа и КОНТРОЛЬНЫЙ вызов по
заведомо крупному домену в локации США. Контроль различает случаи:
  - контроль пуст  → дело в нашем вызове или доступе к Labs;
  - контроль полон → метод рабочий, а по РФ базы действительно нет.

Env:
  DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD — учётные данные API
  LOCATION_CODE — принудительная локация (пусто = автовыбор из справочника)
  RIVAL — домен конкурента для проверки следа (по умолчанию raketapay.ru)
"""
import json
import os
import sys

import requests

API = "https://api.dataforseo.com/v3"
OUR_DOMAIN = "biz-soft.pro"
# Порядок предпочтения гео для русскоязычной выдачи (у Google нет таргетинга РФ)
COUNTRY_PREFERENCE = ["Russia", "Belarus", "Kazakhstan", "Kyrgyzstan"]
CONTROL_DOMAIN = "figma.com"
CONTROL_LOCATION = 2840  # United States
SPENT = []


def call(auth, path, body=None):
    """Один вызов Labs. Возвращает (task, ошибка_строкой)."""
    try:
        if body is None:
            r = requests.get(f"{API}{path}", auth=auth, timeout=60)
        else:
            r = requests.post(f"{API}{path}", auth=auth, json=[body], timeout=90)
        data = r.json()
    except Exception as e:  # noqa: BLE001 — диагностика
        return None, f"сетевая ошибка: {e}"
    task = (data.get("tasks") or [{}])[0]
    if task.get("cost"):
        SPENT.append(task["cost"])
    if data.get("status_code") != 20000 or task.get("status_code") != 20000:
        return task, (f"status={data.get('status_code')}, "
                      f"task_status={task.get('status_code')}, "
                      f"message={task.get('status_message')}")
    return task, None


def report_keywords(task, label, raw=False):
    """Печатает итог ranked_keywords: сколько ключей и примеры."""
    results = task.get("result") if task else None
    if not results:
        print(f"  {label}: result пуст (result={results!r})")
        return 0
    res = results[0]
    total = res.get("total_count")
    items = res.get("items") or []
    print(f"  {label}: total_count={total}, items={len(items)}")
    for item in items[:5]:
        kw = (item.get("keyword_data") or {}).get("keyword")
        pos = ((item.get("ranked_serp_element") or {}).get("serp_item") or {}).get("rank_group")
        print(f"     поз.{pos} · «{kw}»")
    if raw and not items:
        print("     сырой result: " + json.dumps(res, ensure_ascii=False)[:500])
    return total or 0


def main() -> int:
    login = os.environ.get("DATAFORSEO_LOGIN", "").strip()
    password = os.environ.get("DATAFORSEO_PASSWORD", "").strip()
    forced_loc = os.environ.get("LOCATION_CODE", "").strip()
    rival = os.environ.get("RIVAL", "raketapay.ru").strip()
    if not login or not password:
        print("Секреты DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD не заданы.")
        return 0
    auth = (login, password)

    # 0. Контрольный вызов: работает ли метод в принципе
    print("=== 0. КОНТРОЛЬ: ranked_keywords по крупному домену в США ===")
    task, err = call(auth, "/dataforseo_labs/google/ranked_keywords/live",
                     {"target": CONTROL_DOMAIN, "location_code": CONTROL_LOCATION,
                      "language_code": "en", "limit": 5})
    control_ok = False
    if err:
        print(f"  Ошибка: {err}")
    else:
        control_ok = report_keywords(task, f"{CONTROL_DOMAIN} (US/en)", raw=True) > 0

    # 1. Справочник локаций Labs
    print("\n=== 1. Справочник локаций DataForSEO Labs ===")
    task, err = call(auth, "/dataforseo_labs/locations_and_languages")
    location_code, location_name = None, None
    if err:
        print(f"Ошибка: {err}")
    else:
        locs = task.get("result") or []
        print(f"Всего локаций в Labs: {len(locs)}")
        by_name = {l.get("location_name"): l for l in locs}
        for want in COUNTRY_PREFERENCE:
            loc = by_name.get(want)
            langs = [x.get("language_code") for x in (loc.get("available_languages") or [])] if loc else []
            ru = " (есть ru)" if "ru" in langs else (" (без ru)" if loc else "")
            print(f"  {'✓' if loc else '—'} {want}: "
                  f"{loc.get('location_code') if loc else 'нет в справочнике'}{ru}")
            if loc and location_code is None:
                location_code, location_name = loc["location_code"], want
    if forced_loc:
        location_code, location_name = int(forced_loc), f"принудительно {forced_loc}"
    if location_code is None:
        print("\nНи одной подходящей локации — Labs для русскоязычного Google недоступен.")
        return 0
    print(f"Выбрана локация: {location_code} ({location_name}), язык ru")

    base = {"location_code": location_code, "language_code": "ru", "limit": 10}

    # 2-3. Наш домен и домен конкурента
    print(f"\n=== 2. ranked_keywords в локации {location_name} ===")
    ours_task, err = call(auth, "/dataforseo_labs/google/ranked_keywords/live",
                          {**base, "target": OUR_DOMAIN})
    ours = 0 if err else report_keywords(ours_task, OUR_DOMAIN, raw=True)
    if err:
        print(f"  {OUR_DOMAIN}: ошибка: {err}")

    rival_task, err = call(auth, "/dataforseo_labs/google/ranked_keywords/live",
                           {**base, "target": rival})
    theirs = 0 if err else report_keywords(rival_task, rival, raw=True)
    if err:
        print(f"  {rival}: ошибка: {err}")

    # 4. Готовый список конкурентов
    print(f"\n=== 3. competitors_domain: {OUR_DOMAIN} ===")
    task, err = call(auth, "/dataforseo_labs/google/competitors_domain/live",
                     {**base, "target": OUR_DOMAIN})
    rivals_found = 0
    if err:
        print(f"  Ошибка: {err}")
    else:
        results = task.get("result") or []
        if not results:
            print(f"  result пуст (result={results!r})")
        else:
            res = results[0]
            rivals_found = res.get("total_count") or 0
            print(f"  total_count={rivals_found}, items={len(res.get('items') or [])}")
            for item in (res.get("items") or [])[:10]:
                m = ((item.get("metrics") or {}).get("organic") or {})
                print(f"     {item.get('domain'):28s} пересечение={item.get('intersections')} "
                      f"поз1={m.get('pos_1')} трафик≈{m.get('etv')}")

    print(f"\n=== Итого потрачено: ${round(sum(SPENT), 4)} ===")
    print("ВЕРДИКТ:")
    if not control_ok:
        print("  Контроль пуст → проблема в вызове или в доступе к Labs, "
              "а не в покрытии РФ. Разбираться с методом, вывода о базе не делать.")
    elif ours or theirs or rivals_found:
        print("  Контроль работает И по русскоязычным доменам есть данные → "
              "discovery можно строить на Labs.")
    else:
        print("  Контроль работает, но по русскоязычным доменам данных НЕТ → "
              "база Labs не покрывает наш рынок (у Google нет локации РФ). "
              "Остаёмся на собственных SERP-снимках, как в аудите.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
