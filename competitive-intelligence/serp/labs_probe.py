#!/usr/bin/env python3
"""Проба DataForSEO Labs API: покрывает ли база конкурентную аналитику по РФ.

Решение руководителя 31.08: перед тем как строить discovery конкурентов на
Labs, проверить пробой, есть ли в базе русскоязычный Google. Labs работает
только по базе DataForSEO (не live-выдача) и только по Google.

Проверяем четыре вещи, каждая — отдельная строка расхода:
  1. справочник локаций Labs (какие гео вообще доступны для русского языка);
  2. ranked_keywords по biz-soft.pro — знает ли база наш сайт;
  3. competitors_domain по biz-soft.pro — даёт ли база готовый список конкурентов;
  4. ranked_keywords по raketapay.ru — глубина следа лидера Яндекс-выдачи.

Если база пуста по русскоязычному Google — Labs не используется, discovery
строится на собственных SERP-снимках (исходный план аудита).

Env:
  DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD — учётные данные API
  LOCATION_CODE — принудительная локация (пусто = автовыбор из справочника Labs)
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


def first_result(task):
    return (task.get("result") or [{}])[0] if task else {}


def main() -> int:
    login = os.environ.get("DATAFORSEO_LOGIN", "").strip()
    password = os.environ.get("DATAFORSEO_PASSWORD", "").strip()
    forced_loc = os.environ.get("LOCATION_CODE", "").strip()
    rival = os.environ.get("RIVAL", "raketapay.ru").strip()
    if not login or not password:
        print("Секреты DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD не заданы.")
        return 0
    auth = (login, password)

    # 1. Справочник локаций Labs
    print("=== 1. Справочник локаций DataForSEO Labs ===")
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
            mark = "✓" if loc else "—"
            ru = " (есть ru)" if "ru" in langs else (" (без ru)" if loc else "")
            print(f"  {mark} {want}: {loc.get('location_code') if loc else 'нет в справочнике'}{ru}")
            if loc and location_code is None:
                location_code, location_name = loc["location_code"], want
    if forced_loc:
        location_code, location_name = int(forced_loc), f"принудительно {forced_loc}"
    if location_code is None:
        print("\nНи одной подходящей локации — Labs для русскоязычного Google недоступен.")
        return 0
    print(f"\nВыбрана локация: {location_code} ({location_name}), язык ru")

    base = {"location_code": location_code, "language_code": "ru", "limit": 10}

    # 2. Знает ли база наш сайт
    print(f"\n=== 2. ranked_keywords: {OUR_DOMAIN} ===")
    task, err = call(auth, "/dataforseo_labs/google/ranked_keywords/live",
                     {**base, "target": OUR_DOMAIN})
    if err:
        print(f"Ошибка: {err}")
    else:
        res = first_result(task)
        print(f"Всего ключей в базе по домену: {res.get('total_count')}")
        for item in (res.get("items") or [])[:5]:
            kw = (item.get("keyword_data") or {}).get("keyword")
            vol = ((item.get("keyword_data") or {}).get("keyword_info") or {}).get("search_volume")
            pos = ((item.get("ranked_serp_element") or {}).get("serp_item") or {}).get("rank_group")
            print(f"  поз.{pos} · vol {vol} · «{kw}»")

    # 3. Готовый список конкурентов
    print(f"\n=== 3. competitors_domain: {OUR_DOMAIN} ===")
    task, err = call(auth, "/dataforseo_labs/google/competitors_domain/live",
                     {**base, "target": OUR_DOMAIN})
    if err:
        print(f"Ошибка: {err}")
    else:
        res = first_result(task)
        print(f"Найдено конкурирующих доменов: {res.get('total_count')}")
        for item in (res.get("items") or [])[:10]:
            metrics = ((item.get("metrics") or {}).get("organic") or {})
            print(f"  {item.get('domain'):28s} пересечение={item.get('intersections')} "
                  f"поз.1-3={metrics.get('pos_1')}/{metrics.get('pos_2_3')} "
                  f"трафик≈{metrics.get('etv')}")

    # 4. Глубина следа лидера Яндекс-выдачи
    print(f"\n=== 4. ranked_keywords: {rival} (лидер Яндекс-выдачи) ===")
    task, err = call(auth, "/dataforseo_labs/google/ranked_keywords/live",
                     {**base, "target": rival})
    if err:
        print(f"Ошибка: {err}")
    else:
        res = first_result(task)
        print(f"Всего ключей в базе по домену: {res.get('total_count')}")
        for item in (res.get("items") or [])[:5]:
            kw = (item.get("keyword_data") or {}).get("keyword")
            pos = ((item.get("ranked_serp_element") or {}).get("serp_item") or {}).get("rank_group")
            print(f"  поз.{pos} · «{kw}»")

    print(f"\n=== Итого потрачено на пробу: ${round(sum(SPENT), 4)} ===")
    print("Вывод читать так: если total_count по доменам > 0 — база покрывает "
          "русскоязычный Google, discovery можно строить на Labs; если нули "
          "или ошибки — остаёмся на собственных SERP-снимках.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
