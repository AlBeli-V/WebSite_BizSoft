#!/usr/bin/env python3
"""Проба DataForSEO SERP API: диагностика справочника локаций + один платный запрос.

История проб (31.08): учётные данные работают, но location_code 2643 (Россия)
и 2112 (Беларусь) отклонены с 40501 Invalid Field — похоже, у DataForSEO
недоступны локации РФ/РБ (Google Ads удалил geotarget РФ; провайдер мог убрать
и РБ). Эта версия честно печатает состояние справочника по странам
(ru/by/kz/kg/us) со статусами ответов, выбирает первую доступную
русскоязычную локацию и делает ОДИН платный запрос без se_domain.

Методическая пометка: Google с 2022 не имеет гео-таргетинга России; для
реальных пользователей из РФ выдача близка к глобальной русскоязычной,
поэтому соседняя локация (KZ/KG) + language=ru — приемлемый прокси; выбор
фиксируется в конфиге CI и указывается в отчётах.

Env:
  DATAFORSEO_LOGIN    — логин API (почта аккаунта DataForSEO)
  DATAFORSEO_PASSWORD — пароль API (из кабинета, не пароль от сайта)
  QUERY               — запрос (по умолчанию «купить figma»)
  LOCATION_CODE       — принудительный location_code (пусто = автоопределение)
"""
import json
import os
import sys

import requests

API = "https://api.dataforseo.com/v3"
OUR_DOMAIN = "biz-soft.pro"
# Порядок предпочтения стран для русскоязычной выдачи-прокси
COUNTRY_PREFERENCE = ["ru", "by", "kz", "kg", "us"]


def api_get(auth, path):
    r = requests.get(f"{API}{path}", auth=auth, timeout=30)
    return r.json()


def print_serp(task):
    cost = task.get("cost")
    result = (task.get("result") or [{}])[0]
    items = [i for i in (result.get("items") or []) if i.get("type") == "organic"]
    print(f"Стоимость запроса: ${cost}. Organic-позиций: {len(items)}. Топ-10:")
    our = None
    for i in items:
        dom = (i.get("domain") or "").removeprefix("www.")
        if dom == OUR_DOMAIN and our is None:
            our = i.get("rank_group")
    for i in items[:10]:
        pos = i.get("rank_group")
        dom = (i.get("domain") or "").removeprefix("www.")
        title = (i.get("title") or "")[:60]
        print(f"  {pos:3d}. {dom:28s} {title}")
        print(f"       {i.get('url')}")
    print(f"\nПозиция {OUR_DOMAIN}: {our if our is not None else 'нет в топ-20'}")


def main() -> int:
    login = os.environ.get("DATAFORSEO_LOGIN", "").strip()
    password = os.environ.get("DATAFORSEO_PASSWORD", "").strip()
    query = os.environ.get("QUERY", "купить figma").strip()
    forced_loc = os.environ.get("LOCATION_CODE", "").strip()

    if not login or not password:
        print("Секреты DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD не заданы.")
        return 0
    auth = (login, password)

    # 1. Баланс (бесплатно)
    try:
        data = api_get(auth, "/appendix/user_data")
        money = data["tasks"][0]["result"][0].get("money", {})
        print(f"Аккаунт: ок. Баланс: ${money.get('balance')}")
    except Exception as e:  # noqa: BLE001 — диагностика
        print(f"Ошибка проверки аккаунта: {e}")
        return 0

    # 2. Справочник локаций по странам (бесплатно), с полными статусами
    print("\nСправочник локаций Google (/serp/google/locations/<cc>):")
    available = {}
    for cc in COUNTRY_PREFERENCE:
        try:
            data = api_get(auth, f"/serp/google/locations/{cc}")
            task = (data.get("tasks") or [{}])[0]
            result = task.get("result") or []
            st, msg = task.get("status_code"), task.get("status_message")
            first = ""
            if result:
                available[cc] = result
                first = f" · первая: {result[0].get('location_code')} {result[0].get('location_name')}"
            print(f"  {cc}: task_status={st} «{msg}», локаций: {len(result)}{first}")
        except Exception as e:  # noqa: BLE001
            print(f"  {cc}: ошибка запроса: {e}")

    # 3. Выбор локации и один платный запрос (без se_domain)
    body_item = {"keyword": query, "language_code": "ru", "device": "desktop", "depth": 20}
    if forced_loc:
        body_item["location_code"] = int(forced_loc)
        mode = f"принудительный location_code={forced_loc}"
    else:
        chosen = None
        for cc in COUNTRY_PREFERENCE:
            if available.get(cc):
                locs = available[cc]
                country = next((l for l in locs if l.get("location_type") == "Country"), locs[0])
                chosen = (cc, country)
                break
        if not chosen:
            print("\nНи одной локации не найдено — платный запрос не выполняется. "
                  "Похоже, аккаунт не активирован для SERP API; проверить в кабинете DataForSEO.")
            return 0
        cc, loc = chosen
        body_item["location_code"] = loc["location_code"]
        mode = f"{cc}: {loc['location_code']} {loc.get('location_name')} + language=ru"
        if cc not in ("ru",):
            mode += " (прокси-гео: у Google нет таргетинга РФ; фиксируется в конфиге CI)"
    print(f"\nПроба Google SERP: «{query}» · {mode}")
    try:
        r = requests.post(f"{API}/serp/google/organic/live/advanced",
                          auth=auth, json=[body_item], timeout=90)
        data = r.json()
    except Exception as e:  # noqa: BLE001
        print(f"Сетевая ошибка: {e}")
        return 0

    task = (data.get("tasks") or [{}])[0]
    if data.get("status_code") != 20000 or task.get("status_code") != 20000:
        print(f"Ошибка API: status={data.get('status_code')}, "
              f"task_status={task.get('status_code')}, message={task.get('status_message')}")
        print("Тело задачи для разбора:")
        print(json.dumps(body_item, ensure_ascii=False))
        return 0

    print_serp(task)
    print("\nВывод: доступ РАБОТАЕТ. Для регулярного сбора — дешёвая очередь "
          "task_post/task_get (standard), live — только для проб.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
